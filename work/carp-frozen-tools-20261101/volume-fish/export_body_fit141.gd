extends SceneTree
func _initialize():
    var plan=JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]));assert(FileAccess.get_sha256(plan.body)==plan.body_sha256);assert(FileAccess.get_sha256(plan.source_resource.path)==plan.source_resource.sha256);var source=load(plan.source_resource.path) as ArrayMesh;var mesh=ArrayMesh.new();var data=JSON.parse_string(FileAccess.get_file_as_string(plan.body));assert(source.get_surface_count()==data.parts.size());var bounds=AABB();var first=true
    for si in source.get_surface_count():
        var old=source.surface_get_arrays(si);var arrays=old.duplicate();var points=PackedVector3Array();var normals=PackedVector3Array();var weights=PackedFloat32Array()
        for q in data.parts[si].vertices:
            var v=Vector3(q[0],q[1],q[2]);points.append(v)
            if first:bounds=AABB(v,Vector3.ZERO);first=false
            else:bounds=bounds.expand(v)
        for q in data.parts[si].normals:normals.append(Vector3(q[0],q[1],q[2]))
        for row in data.parts[si].weights:
            for value in row:weights.append(value)
        arrays[Mesh.ARRAY_VERTEX]=points;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_WEIGHTS]=weights;mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);mesh.surface_set_material(si,source.surface_get_material(si));var got=mesh.surface_get_arrays(si);assert(got[Mesh.ARRAY_VERTEX]==points,"Position update not readable")
        for field in [Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_BONES,Mesh.ARRAY_WEIGHTS,Mesh.ARRAY_INDEX]:assert(got[field]==old[field],"Non-position body data changed")
    mesh.custom_aabb=bounds;assert(ResourceSaver.save(mesh,plan.output,ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK);var reloaded=ResourceLoader.load(plan.output,"ArrayMesh",ResourceLoader.CACHE_MODE_IGNORE) as ArrayMesh
    for si in mesh.get_surface_count():
        var a=mesh.surface_get_arrays(si);var b=reloaded.surface_get_arrays(si)
        for field in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_BONES,Mesh.ARRAY_WEIGHTS,Mesh.ARRAY_INDEX]:assert(a[field]==b[field],"Cold body resource differs")
    var f=FileAccess.open(plan.output.get_base_dir().path_join("resource.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"body":plan.output,"sha256":FileAccess.get_sha256(plan.output),"source_resource_sha256":plan.source_resource.sha256,"scope":"Position-only persistent array rebuild, reusing raw original normals/weights to preserve their exact engine codes. UV, packed skin, indices, source normals and complete native material resources unchanged."}));f.close();print("BODY_FIT141_OK");quit()
