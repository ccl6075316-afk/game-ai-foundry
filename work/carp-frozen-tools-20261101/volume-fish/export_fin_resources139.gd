extends SceneTree
## Preserve actual original fin materials and bind the frozen repaired geometry.
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var data=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var out=args[1]
    assert(data.species=="peacock_bass");DirAccess.make_dir_recursive_absolute(out)
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall._select_display(data.species)
    var e:Dictionary=hall._selected();var portable=load(get_script().resource_path.get_base_dir().path_join("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd"));var rows=[]
    for fin in data.fins:
        var node=e.model.find_child(fin.name,true,false) as MeshInstance3D;var mapping=[]
        for name in fin.skin_joint_names:
            var found=-1
            for i in node.skin.get_bind_count():
                var actual=String(node.skin.get_bind_name(i))
                if actual.is_empty():actual=e.skeleton.get_bone_name(node.skin.get_bind_bone(i))
                if actual==name or actual==name+"_2":assert(found<0);found=i
            assert(found>=0);mapping.append(found)
        var mesh=ArrayMesh.new();assert(fin.parts.size()==node.mesh.get_surface_count())
        for si in fin.parts.size():
            var part=fin.parts[si];var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
            var v=PackedVector3Array();var n=PackedVector3Array();var uv=PackedVector2Array();var bones=PackedInt32Array();var weights=PackedFloat32Array()
            for q in part.vertices:v.append(Vector3(q[0],q[1],q[2]))
            for q in part.normals:n.append(Vector3(q[0],q[1],q[2]))
            for q in part.uv:uv.append(Vector2(q[0],q[1]))
            for i in part.joints.size():
                for k in 4:bones.append(mapping[int(part.joints[i][k])]);weights.append(part.weights[i][k])
            arrays[Mesh.ARRAY_VERTEX]=v;arrays[Mesh.ARRAY_NORMAL]=n;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
            if part.has("uv2"):
                var uv2=PackedVector2Array()
                for q in part.uv2:uv2.append(Vector2(q[0],q[1]))
                arrays[Mesh.ARRAY_TEX_UV2]=uv2
            if part.has("colors"):
                var colors=PackedColorArray()
                for q in part.colors:colors.append(Color(q[0],q[1],q[2],q[3] if q.size()>3 else 1.))
                arrays[Mesh.ARRAY_COLOR]=colors
            mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);mesh.surface_set_material(si,portable.freeze(node.get_active_material(si)))
        var path=out.path_join(fin.name+".res");assert(ResourceSaver.save(mesh,path,ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
        rows.append({"name":fin.name,"path":path,"sha256":FileAccess.get_sha256(path)})
    var f=FileAccess.open(out.path_join("resources.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==data.fins.size(),"fins":rows,"input_sha256":FileAccess.get_sha256(args[0]),"scope":"Portable repaired fin resources with original materials and actual skin bind names. Complete roots/membranes/GPU and visual review required."}));f.close()
    hall.queue_free();await process_frame;quit()
