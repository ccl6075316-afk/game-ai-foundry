extends SceneTree
## Freeze current active material with exact imported arrays before RGB-only work.
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall._select_display(args[1]);var e:Dictionary=hall._selected();var node=e.model.find_child("Closed_body",true,false) as MeshInstance3D;assert(node!=null);var mesh=node.mesh.duplicate() as ArrayMesh
    for si in mesh.get_surface_count():
        var source=node.get_active_material(si);var material=source.duplicate()
        if material is ShaderMaterial:
            assert(source.shader!=null);var shader=Shader.new();shader.code=source.shader.code;material.shader=shader
            for uniform in source.shader.get_shader_uniform_list():
                var value=source.get_shader_parameter(uniform.name)
                if value is Texture2D:
                    var im=value.get_image().duplicate();assert(im!=null)
                    if im.is_compressed():assert(im.decompress()==OK)
                    material.set_shader_parameter(uniform.name,ImageTexture.create_from_image(im))
        mesh.surface_set_material(si,material)
    DirAccess.make_dir_recursive_absolute(args[0].get_base_dir());assert(ResourceSaver.save(mesh,args[0],ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK);var cold=ResourceLoader.load(args[0],"ArrayMesh",ResourceLoader.CACHE_MODE_IGNORE) as ArrayMesh
    for si in mesh.get_surface_count():
        var a=node.mesh.surface_get_arrays(si);var b=cold.surface_get_arrays(si)
        for field in Mesh.ARRAY_MAX:assert(a[field]==b[field])
        var material=mesh.surface_get_material(si);var reloaded=cold.surface_get_material(si)
        if material is ShaderMaterial:
            assert(reloaded is ShaderMaterial and reloaded.shader!=null and reloaded.shader.code==material.shader.code)
            for uniform in material.shader.get_shader_uniform_list():
                var before=material.get_shader_parameter(uniform.name);var after=reloaded.get_shader_parameter(uniform.name)
                if before is Texture2D:assert(after is Texture2D and before.get_size()==after.get_size()and before.get_image().get_data()==after.get_image().get_data(),"Portable body texture lost")
                else:assert(before==after,"Portable body input changed")
    hall.queue_free();await process_frame;quit()
