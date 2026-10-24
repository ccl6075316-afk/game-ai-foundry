extends SceneTree
## Fresh-process exact retained shader/inputs after the contact-only export.
func _initialize():
    var args=OS.get_cmdline_user_args();var before=load(args[0])as ArrayMesh;var after=load(args[1])as ArrayMesh;assert(before.get_surface_count()==after.get_surface_count());var count=0
    for si in before.get_surface_count():
        var a=before.surface_get_material(si);var b=after.surface_get_material(si);assert(a.get_class()==b.get_class())
        if a is ShaderMaterial:
            assert(a.shader.code==b.shader.code)
            for row in a.shader.get_shader_uniform_list():
                var x=a.get_shader_parameter(row.name);var y=b.get_shader_parameter(row.name)
                if x is Texture2D:assert(y is Texture2D and x.get_image().get_format()==y.get_image().get_format()and x.get_image().get_size()==y.get_image().get_size()and x.get_image().get_data()==y.get_image().get_data())
                else:assert(x==y)
                count+=1
        else:assert(false,"Explicit property review required for another retained material type")
        var aa=before.surface_get_arrays(si);var bb=after.surface_get_arrays(si)
        for field in Mesh.ARRAY_MAX:
            if field!=Mesh.ARRAY_VERTEX:assert(aa[field]==bb[field])
        assert(RenderingServer.mesh_get_surface(before.get_rid(),si).get("lods",[])==RenderingServer.mesh_get_surface(after.get_rid(),si).get("lods",[]))
    var f=FileAccess.open(args[2],FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"original_sha256":FileAccess.get_sha256(args[0]),"actual_sha256":FileAccess.get_sha256(args[1]),"uniforms_exact":count,"all_nonposition_arrays_and_lods_exact":true,"scope":"Actual cold resource retains original soft-dorsal shader, uniforms/native images, non-position arrays andLOD data. Position-only contact correction; no new source-shape or closed-shell acceptance."}));f.close();quit()
