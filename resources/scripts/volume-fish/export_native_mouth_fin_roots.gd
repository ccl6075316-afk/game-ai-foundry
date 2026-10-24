extends "export_runtime_fin_roots.gd"
## Same fin gate, replacing only body arrays with an explicitly frozen candidate.
var candidate_hashes:Dictionary={}

func prepare(entry:Dictionary,spec:Dictionary)->void:
    var cfg:Dictionary=spec.mouth_candidate
    for path in cfg.frozen_inputs:
        assert(FileAccess.get_sha256(path)==cfg.frozen_inputs[path],"Stale mouth candidate "+path)
    candidate_hashes=cfg.frozen_inputs
    var data=JSON.parse_string(FileAccess.get_file_as_string(cfg.body))
    var receipt=JSON.parse_string(FileAccess.get_file_as_string(cfg.skinning_report))
    var names:Array=receipt.summary.skin_joint_names
    var body=entry.model.find_child(spec.body,true,false) as MeshInstance3D
    var skin:Skin=body.skin
    var skeleton:Skeleton3D=entry.skeleton
    var mapping:Array=[]
    for source_name in names:
        var found=-1
        for i in skin.get_bind_count():
            var actual=String(skin.get_bind_name(i))
            if actual.is_empty():actual=skeleton.get_bone_name(skin.get_bind_bone(i))
            if actual==source_name or actual==source_name+"_2":
                assert(found<0);found=i
        assert(found>=0,"Unmapped bone "+source_name);mapping.append(found)
    var next=ArrayMesh.new()
    for part in data.parts:
        var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
        var v=PackedVector3Array();var n=PackedVector3Array()
        var joints=PackedInt32Array();var weights=PackedFloat32Array()
        for p in part.vertices:v.append(Vector3(p[0],p[1],p[2]))
        for p in part.normals:n.append(Vector3(p[0],p[1],p[2]))
        for i in part.joints.size():
            for k in 4:
                joints.append(mapping[int(part.joints[i][k])]);weights.append(part.weights[i][k])
        arrays[Mesh.ARRAY_VERTEX]=v;arrays[Mesh.ARRAY_NORMAL]=n
        arrays[Mesh.ARRAY_BONES]=joints;arrays[Mesh.ARRAY_WEIGHTS]=weights
        arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
    body.mesh=next
    super.prepare(entry,spec)

func save_json(path:String,value:Variant)->void:
    if path.ends_with("export.validation.json"):
        value["candidate_input_sha256"]=candidate_hashes
        value["source_glb_is_rig_and_fin_donor_only"]=true
    super.save_json(path,value)
