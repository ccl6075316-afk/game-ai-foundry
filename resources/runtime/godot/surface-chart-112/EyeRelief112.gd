extends RefCounted
const CONFIG="res://assets/models/fish/motion/eye-relief112.json"
func apply(model: Node3D,species: String)->int:
    var data=JSON.parse_string(FileAccess.get_file_as_string(CONFIG))
    assert(data is Dictionary and data.get("profiles") is Dictionary)
    if not data.profiles.has(species):return 0
    var p: Dictionary=data.profiles[species]
    assert(FileAccess.get_sha256("res://assets/models/fish/"+species+".glb")==p.model_sha256,"Stale eye relief112")
    if p.has("support_body_resource"):
        var support:Dictionary=p.support_body_resource
        assert(FileAccess.get_sha256(support.path)==support.sha256,"Stale current-body eye support")
        var owner:String=p.get("support_owner","mouth-repair139")
        assert(owner in ["mouth-repair139","fin-source141"],"Unknown current-eye support owner")
        var installed=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/"+owner+".json"))
        assert(installed.profiles[species].body==support,"Eye cap no longer matches installed body")
    var body=model.find_child(p.mesh,true,false) as MeshInstance3D
    assert(body!=null and body.skin!=null)
    var skin=body.get_active_material(int(p.source_surface)) as ShaderMaterial
    assert(skin!=null)
    var texture=skin.get_shader_parameter("source_texture") as Texture2D
    assert(texture!=null and texture.get_size()==Vector2(p.source_size[0],p.source_size[1]))
    if p.has("source_rgba_sha256"):
        var image=texture.get_image().duplicate()
        if image.is_compressed():assert(image.decompress()==OK)
        image.clear_mipmaps() # Compare original base pixels, not imported mip storage.
        image.convert(Image.FORMAT_RGBA8)
        var context=HashingContext.new();context.start(HashingContext.HASH_SHA256);context.update(image.get_data())
        assert(context.finish().hex_encode()==p.source_rgba_sha256,"Native eye pixels changed")
    var skeleton=body.get_node(body.skeleton) as Skeleton3D
    assert(skeleton!=null)
    var bind_map: Array[int]=[]
    var used_bones: Dictionary={}
    for cap in p.caps:
        for i in cap.joints.size():
            for j in 4:
                if float(cap.weights[i][j])>0.00000001:used_bones[int(cap.joints[i][j])]=true
    for source_bone in p.bones.size():
        if not used_bones.has(source_bone):
            bind_map.append(0)
            continue
        var name: String=p.bones[source_bone]
        var bone_index=skeleton.find_bone(name)
        if bone_index<0:bone_index=skeleton.find_bone(str(name)+"_2")
        assert(bone_index>=0,"Missing112 source bone: "+str(name))
        var bind_index=-1
        for j in body.skin.get_bind_count():
            if body.skin.get_bind_bone(j)==bone_index or body.skin.get_bind_name(j)==name:bind_index=j;break
        assert(bind_index>=0,"Unmapped112 eye bone: "+str(name))
        bind_map.append(bind_index)
    for cap in p.caps:
        var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
        var vertices=PackedVector3Array();var normals=PackedVector3Array();var uv=PackedVector2Array();var bones=PackedInt32Array();var weights=PackedFloat32Array()
        for v in cap.vertices:vertices.append(Vector3(v[0],v[1],v[2]))
        for v in cap.normals:normals.append(Vector3(v[0],v[1],v[2]))
        for v in cap.uv:uv.append(Vector2(v[0],v[1]))
        for row in cap.joints:
            for bone in row:bones.append(bind_map[int(bone)])
        for row in cap.weights:
            for weight in row:weights.append(float(weight))
        arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_TEX_UV]=uv
        arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights
        if p.get("godot_clockwise",false):
            var clockwise=PackedInt32Array()
            for ti in range(0,cap.indices.size(),3):clockwise.append_array(PackedInt32Array([cap.indices[ti],cap.indices[ti+2],cap.indices[ti+1]]))
            arrays[Mesh.ARRAY_INDEX]=clockwise
        else:arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(cap.indices)
        var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        var material=StandardMaterial3D.new();material.albedo_texture=texture
        material.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST;material.roughness=1.;material.metallic=0.;material.metallic_specular=0.;material.cull_mode=BaseMaterial3D.CULL_DISABLED
        mesh.surface_set_material(0,material)
        var instance=MeshInstance3D.new();instance.name="Eye_relief112_"+str(cap.side);instance.mesh=mesh
        body.get_parent().add_child(instance);instance.transform=body.transform;instance.skin=body.skin;instance.skeleton=body.skeleton
        instance.set_meta("decorative_relief112",{"underlying_body":p.mesh,"model_sha256":p.model_sha256,"profile_sha256":FileAccess.get_sha256(CONFIG),"source_rgba_sha256":p.get("source_rgba_sha256","")})
    model.set_meta("eye_relief112_receipt",{"species":species,"caps":2,"underlying_body_intact":true,"model_sha256":p.model_sha256,"profile_sha256":FileAccess.get_sha256(CONFIG),"helper_sha256":FileAccess.get_sha256(get_script().resource_path)})
    return 2
