extends "capture_source_fins143.gd"
## Exact native-camera skin before/after plus actual UV-projected RGB change mask.
func colour_mode()->String:return "texture"
func prepare_model(_entry:Dictionary,_species:String):pass
func run():
    DirAccess.make_dir_recursive_absolute(out);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide();var rows=[];var owns=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[node.get_instance_id()]=node.visible
    for species in requested:
        shaders.clear()
        hall._select_display(species);var e:Dictionary=hall._selected();var folder=out.path_join(species);DirAccess.make_dir_recursive_absolute(folder);hall.viewport.size=original_size(species);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
        prepare_model(e,species)
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node)and intrinsic.get(node.get_instance_id(),false)
        for node in hall.world.find_children("*","Label3D",true,false):node.hide()
        e.player.stop();e.skeleton.reset_bone_poses();e.skeleton.force_update_all_bone_transforms();source_camera(e)
        if colour_mode()=="albedo":
            var stored=[]
            for node in e.model.find_children("*","MeshInstance3D",true,false):
                for si in node.mesh.get_surface_count():var mat=node.get_active_material(si);stored.append([node,si,mat,mat])
            set_mode(e,stored,"albedo")
        for name in owns[species].fins:e.model.find_child(name,true,false).hide()
        var native=folder.path_join("body-only-native.png");await shot(native);var files={native:FileAccess.get_sha256(native)};var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D;var original=body.get_active_material(0) as ShaderMaterial;assert(original!=null);var code:String=original.shader.code
        if code.contains("pectoral142_mask"):
            for node in e.model.find_children("*","MeshInstance3D",true,false):node.hide()
            body.show()
            for si in body.mesh.get_surface_count():
                if si==0:
                    var material=original.duplicate() as ShaderMaterial;var shader=Shader.new();var end=code.rfind("}");var factor="texture(pectoral142_mask,UV).r"+("*pectoral143_owner()"if code.contains("float pectoral143_owner()")else"");var probe=code.substr(0,end)+"\nALBEDO=vec3("+factor+");\n"+code.substr(end)
                    if probe.contains("render_mode unshaded"):pass
                    elif probe.contains("render_mode"):probe=probe.replace("render_mode","render_mode unshaded,")
                    else:probe=probe.replace("shader_type spatial;","shader_type spatial;\nrender_mode unshaded;\n")
                    shader.code=probe;material.shader=shader;body.set_surface_override_material(si,material)
                else:
                    var black=StandardMaterial3D.new();black.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;black.albedo_color=Color.BLACK;body.set_surface_override_material(si,black)
            var mask=folder.path_join("actual-body-mask.png");await shot(mask);files[mask]=FileAccess.get_sha256(mask)
            for si in body.mesh.get_surface_count():body.set_surface_override_material(si,null)
        rows.append({"species":species,"files":files,"scope":"Actual original-rest native camera, all moving fins hidden. RGB mask sampled through actual body UV; no local rescale or registration."})
    var f=FileAccess.open(out.path_join("capture.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==requested.size(),"records":rows,"fin_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/fin-source141.json"),"mouth_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/mouth-repair139.json"),"checker_sha256":FileAccess.get_sha256(get_script().resource_path)}));f.close();hall.queue_free();await process_frame;quit()
func original_size(species:String)->Vector2i:return Image.load_from_file(source_specs[species].source).get_size()
