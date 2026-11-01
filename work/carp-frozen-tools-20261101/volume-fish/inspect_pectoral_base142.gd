extends SceneTree
func _initialize():
    var args=OS.get_cmdline_user_args();var out=args[1];DirAccess.make_dir_recursive_absolute(out)
    var mesh=load(args[0]) as ArrayMesh;var rows=[]
    for si in mesh.get_surface_count():
        var mat=mesh.surface_get_material(si) as ShaderMaterial;assert(mat!=null);var textures={}
        var f=FileAccess.open(out.path_join("surface-%d.gdshader"%si),FileAccess.WRITE);f.store_string(mat.shader.code);f.close()
        for key in ["source_texture","opaque_skin"]:
            var value=mat.get_shader_parameter(key)
            if value is Texture2D:
                var im=value.get_image();assert(im!=null);var path=out.path_join("surface-%d-%s.png"%[si,key]);assert(im.save_png(path)==OK);textures[key]={"path":path,"size":[im.get_width(),im.get_height()],"sha256":FileAccess.get_sha256(path)}
        rows.append({"surface":si,"textures":textures})
    var f=FileAccess.open(out.path_join("inspection.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"source":args[0],"sha256":FileAccess.get_sha256(args[0]),"surfaces":rows}));f.close();quit()
