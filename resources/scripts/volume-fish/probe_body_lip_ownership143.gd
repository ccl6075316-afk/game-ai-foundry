extends SceneTree
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;var result={}
    for species in args.slice(1):
        hall._select_display(species);var e:Dictionary=hall._selected();var records=[]
        for name in ["Closed_body","Source_lips139"]:
            var node=e.model.find_child(name,true,false) as MeshInstance3D
            if node==null:continue
            for si in node.mesh.get_surface_count():
                var mat=node.get_active_material(si)
                if mat is ShaderMaterial:
                    var uniforms={}
                    for uniform in mat.shader.get_shader_uniform_list():
                        var value=mat.get_shader_parameter(uniform.name)
                        if value is Texture2D:
                            var im=value.get_image().duplicate()
                            if im.is_compressed():assert(im.decompress()==OK)
                            im.clear_mipmaps();var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(im.get_data());uniforms[String(uniform.name)]={"size":[im.get_width(),im.get_height()],"format":im.get_format(),"sha256":ctx.finish().hex_encode()}
                        else:uniforms[String(uniform.name)]=var_to_str(value)
                    records.append({"node":name,"surface":si,"material_id":mat.get_instance_id(),"path":mat.resource_path,"shader_id":mat.shader.get_instance_id(),"shader_sha256":mat.shader.code.sha256_text(),"has_pectoral_rgb":mat.shader.code.contains("pectoral142_mask"),"spatial_gate":mat.shader.code.contains("if(pectoral143_owner()>.5)"),"has_source_lip_marker":mat.shader.code.contains("lip135"),"uniforms":uniforms})
        result[species]=records
    var f=FileAccess.open(args[0],FileAccess.WRITE);f.store_string(JSON.stringify(result));f.close();hall.queue_free();await process_frame;quit()
