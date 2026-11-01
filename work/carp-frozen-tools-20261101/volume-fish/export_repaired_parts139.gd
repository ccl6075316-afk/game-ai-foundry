extends "export_bound_mouth_fin_roots.gd"
## Complete repaired fin resources and body share the actual original skin rig.
func prepare(entry:Dictionary,spec:Dictionary)->void:
    var cfg:Dictionary=spec.mouth_candidate
    for path in cfg.frozen_inputs:assert(FileAccess.get_sha256(path)==cfg.frozen_inputs[path])
    var data=JSON.parse_string(FileAccess.get_file_as_string(cfg.fins))
    assert(data.species==spec.species and data.species=="peacock_bass")
    for fin in data.fins:
        var node=entry.model.find_child(fin.name,true,false) as MeshInstance3D;assert(node!=null)
        var mapping=[]
        for name in fin.skin_joint_names:
            var found=-1
            for i in node.skin.get_bind_count():
                var actual=String(node.skin.get_bind_name(i))
                if actual.is_empty():actual=entry.skeleton.get_bone_name(node.skin.get_bind_bone(i))
                if actual==name or actual==name+"_2":assert(found<0);found=i
            assert(found>=0);mapping.append(found)
        var mesh=ArrayMesh.new()
        for part in fin.parts:
            var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
            var v=PackedVector3Array();var n=PackedVector3Array();var bones=PackedInt32Array();var weights=PackedFloat32Array()
            for p in part.vertices:v.append(Vector3(p[0],p[1],p[2]))
            for p in part.normals:n.append(Vector3(p[0],p[1],p[2]))
            for i in part.joints.size():
                for k in 4:bones.append(mapping[int(part.joints[i][k])]);weights.append(part.weights[i][k])
            arrays[Mesh.ARRAY_VERTEX]=v;arrays[Mesh.ARRAY_NORMAL]=n;arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
            mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        node.mesh=mesh
    super.prepare(entry,spec)
func save_json(path:String,value:Variant)->void:
    if path.ends_with("export.validation.json"):
        value["fin_exporter_parent_sha256"]=FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("export_bound_mouth_fin_roots.gd"))
    super.save_json(path,value)
