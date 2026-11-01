extends SceneTree
func state(material:ShaderMaterial,helper)->Dictionary:
    var uniforms:Dictionary={}
    for uniform in material.shader.get_shader_uniform_list():
        var value=material.get_shader_parameter(uniform.name)
        if value is Texture2D:
            var img=value.get_image();uniforms[uniform.name]={"size":str(img.get_size()),"format":img.get_format(),"mipmaps":img.has_mipmaps(),"bytes_sha256":helper.digest(img.get_data())}
        else:uniforms[uniform.name]=helper.digest(value)
    return {"shader_sha256":material.shader.code.sha256_text(),"uniforms":uniforms}
func _initialize():call_deferred("run")
func run():
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false)
    var helper=load("res://scripts/aquarium/RestSurface114.gd").new();var records:Dictionary={};var linings:Dictionary={}
    var cfg=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-charts112.json"))
    for tank in hall.fish:
        if not cfg.profiles.has(tank.species):continue
        var p:Dictionary=cfg.profiles[tank.species];var mesh=tank.model.find_child(p.mesh,true,false) as MeshInstance3D
        var material=mesh.get_active_material(int(p.surface)) as ShaderMaterial;var uniforms:Dictionary={}
        for uniform in material.shader.get_shader_uniform_list():
            var value=material.get_shader_parameter(uniform.name)
            if value is Texture2D:
                var img=value.get_image()
                uniforms[uniform.name]={"size":str(img.get_size()),"format":img.get_format(),"mipmaps":img.has_mipmaps(),"bytes_sha256":helper.digest(img.get_data())}
            else:uniforms[uniform.name]=helper.digest(value)
        if tank.species in ["black_seabream","red_seabream","zander","red_emperor","brown_trout","grass_carp","nile_tilapia","sea_bass"]:linings[tank.species]=state(mesh.get_active_material(1) as ShaderMaterial,helper)
        records[tank.species]={"model_sha256":FileAccess.get_sha256(tank.model.scene_file_path),"shader_sha256":material.shader.code.sha256_text(),"uniforms":uniforms,"mesh":helper.snapshot(mesh)}
    var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);file.store_string(JSON.stringify({"ok":records.size()==cfg.profiles.size(),"status":"done","next_action":"human_review","records":records,"linings":linings}));file.close();quit()
