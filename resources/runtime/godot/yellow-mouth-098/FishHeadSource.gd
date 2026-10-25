extends RefCounted
## Bound per species to actual native source landmarks and the installed model.
var profiles: Dictionary={}
func apply(model: Node3D,species: String) -> int:
    if profiles.is_empty():profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/head-source.json")).profiles
    if not profiles.has(species):return 0
    var p: Dictionary=profiles[species]
    assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256("res://assets/models/fish/"+species+".glb")==p.model_sha256,"Stale head source coordinates")
    var mesh=model.find_child(p.mesh,true,false) as MeshInstance3D
    assert(mesh!=null)
    var skin=mesh.get_active_material(0) as ShaderMaterial
    var mats: Array=[skin]
    if p.mouth_enabled:mats.append(mesh.get_active_material(1))
    for mat in mats:
        assert(mat is ShaderMaterial)
        mat.set_shader_parameter("head_source_repair",true)
        var e:Dictionary=p.eye;mat.set_shader_parameter("source_eye",Vector4(e.center[0],e.center[1],e.radius[0],e.radius[1]))
        mat.set_shader_parameter("eye_gap_native",Vector2(p.eye_gap_native[0],p.eye_gap_native[1]))
        mat.set_shader_parameter("eye_donor_u",e.donor_u)
        mat.set_shader_parameter("eye_donor_v",e.donor_v)
        if p.has("secondary_feature"):
            var feature:Array=p.secondary_feature;mat.set_shader_parameter("secondary_feature_enabled",true)
            mat.set_shader_parameter("secondary_feature",Vector4(feature[0],feature[1],feature[2],feature[3]))
        mat.set_shader_parameter("mouth_source_projection",p.mouth_enabled)
        mat.set_shader_parameter("mouth_shift_native_u",p.mouth_shift_native_u)
        mat.set_shader_parameter("opaque_skin",skin.get_shader_parameter("opaque_skin"))
        mat.set_shader_parameter("source_size",skin.get_shader_parameter("source_size"))
        mat.set_shader_parameter("yellow_source_trial",species=="yellow_croaker")
        if p.has("rim_local"):
            var local:Dictionary=p.rim_local
            var starts:=PackedVector4Array();var ends:=PackedVector4Array();var crosses:=PackedVector4Array()
            for v in local.starts:starts.append(Vector4(v[0],v[1],v[2],v[3]))
            for v in local.ends:ends.append(Vector4(v[0],v[1],v[2],v[3]))
            for v in local.cross_sections:crosses.append(Vector4(v[0],v[1],v[2],v[3]))
            mat.set_shader_parameter("rim_local_source",true)
            mat.set_shader_parameter("local_rim_count",starts.size());starts.resize(160);ends.resize(160)
            mat.set_shader_parameter("local_rim_start",starts);mat.set_shader_parameter("local_rim_end",ends)
            mat.set_shader_parameter("local_cross_count",crosses.size());crosses.resize(32);mat.set_shader_parameter("local_cross",crosses)
            mat.set_shader_parameter("local_eye_chart",Vector4(local.eye_native_center_x,local.eye_native_radius_x,local.eye_center_angle,local.eye_angular_radius))
        if p.mouth_enabled:
            for key in ["upper_skin_patch","lower_skin_patch"]:
                var rect:Array=p[key];mat.set_shader_parameter(key,Vector4(rect[0],rect[1],rect[2],rect[3]))
            var model_path:=PackedVector2Array();var model_tangents:=PackedFloat32Array()
            for v in p.model_path:model_path.append(Vector2(v[0],v[1]))
            for v in p.model_tangents:model_tangents.append(float(v))
            mat.set_shader_parameter("model_path_count",model_path.size());model_path.resize(8);model_tangents.resize(8)
            mat.set_shader_parameter("model_path",model_path);mat.set_shader_parameter("model_tangents",model_tangents)
            for key in ["model_aspect","model_gap","model_lip_roll"]:mat.set_shader_parameter(key,p[key])
            mat.set_shader_parameter("mouth_donor_window",Vector2(p.mouth_donor_window[0],p.mouth_donor_window[1]))
            var source_edges:=PackedVector3Array()
            for v in p.mouth_source_edges:source_edges.append(Vector3(v[0],v[1],v[2]))
            mat.set_shader_parameter("mouth_edge_count",source_edges.size());source_edges.resize(32);mat.set_shader_parameter("mouth_source_edges",source_edges)
            var path:=PackedVector2Array();var widths:=PackedVector2Array();var tangents:=PackedFloat32Array()
            for v in p.mouth_path:path.append(Vector2(v[0],v[1]))
            for v in p.source_width_path:widths.append(Vector2(v[0],v[1]))
            for v in p.mouth_tangents:tangents.append(float(v))
            mat.set_shader_parameter("mouth_path_count",path.size());path.resize(8);mat.set_shader_parameter("mouth_path",path)
            tangents.resize(8);mat.set_shader_parameter("mouth_tangents",tangents)
            mat.set_shader_parameter("source_width_count",widths.size());widths.resize(32);mat.set_shader_parameter("source_width_path",widths)
    return mats.size()
