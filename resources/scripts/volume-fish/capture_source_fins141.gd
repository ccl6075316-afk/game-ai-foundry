extends "capture_revision140.gd"
## Fixed source canvas, isolated fins and actual body occlusion are distinct views.
func source_image_for_species(species:String)->Image:
    return Image.load_from_file(get_script().resource_path.get_base_dir().path_join("../../../projects/fishing-2d/experiments/blender-fish/fin-source-141/source/"+species+"/source.png"))
func fin_camera_side(name:String)->float:
    return -1. if name.ends_with("_right") or name.ends_with("_Far") or name.ends_with("_-1") else 1.
func source_camera(e:Dictionary,side:float=1.):
    var tr:Transform3D=e.model.global_transform;var size:float=tr.basis.get_scale().x
    hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL;hall.camera.size=float(hall.viewport.size.y)/hall.viewport.size.x*size;hall.camera.near=.00001;hall.camera.global_position=tr*Vector3(0,0,2*side);hall.camera.look_at(tr*Vector3.ZERO,tr.basis.orthonormalized()*Vector3.UP)
func run():
    var root_out=out;DirAccess.make_dir_recursive_absolute(out);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide();ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[node.get_instance_id()]=node.visible
    var rows=[]
    for species in requested:
        hall._select_display(species);var e:Dictionary=hall._selected();var folder=root_out.path_join(species);DirAccess.make_dir_recursive_absolute(folder);var source=source_image_for_species(species);assert(source!=null);hall.viewport.size=source.get_size();hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic.get(node.get_instance_id(),false)
        for node in hall.world.find_children("*","Label3D",true,false):node.hide()
        e.player.stop();e.skeleton.reset_bone_poses();e.skeleton.force_update_all_bone_transforms();var stored=[];var files={};var bodies:Array=[];var body_profile=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/body-opacity.json")).profiles[species]
        for name in body_profile.surfaces:
            var body=e.model.find_child(name,true,false) as MeshInstance3D
            if body!=null and not ownership[species].fins.has(name):bodies.append(body)
        assert(not bodies.is_empty(),"No configured body for source occlusion audit")
        for node in e.model.find_children("*","MeshInstance3D",true,false):
            for si in node.mesh.get_surface_count():var mat=node.get_active_material(si);stored.append([node,si,mat,mat])
        source_camera(e)
        for mode in ["texture","clay","albedo"]:
            set_mode(e,stored,mode);var path=folder.path_join("source-canvas-"+mode+".png");await shot(path);files[path]=FileAccess.get_sha256(path)
        set_mode(e,stored,"texture")
        var fin_records=[]
        for name in ownership[species].fins:
            var fin=e.model.find_child(name,true,false) as MeshInstance3D;assert(fin!=null)
            for node in e.model.find_children("*","MeshInstance3D",true,false):node.hide()
            fin.show();source_camera(e,fin_camera_side(String(name)))
            var paths={}
            set_mode(e,stored,"albedo");var path=folder.path_join(name+"-isolated-native.png");await shot(path);paths.isolated_native={"path":path,"sha256":FileAccess.get_sha256(path)}
            for si in fin.mesh.get_surface_count():
                var mat=fin.get_active_material(si).duplicate() as ShaderMaterial;assert(mat!=null);var shader=Shader.new();var code:String=mat.shader.code;assert(code.contains("ALBEDO=c.rgb") or code.contains("ALBEDO=color.rgb"));shader.code=code.replace("ALBEDO=c.rgb","ALBEDO=vec3(1.0)").replace("ALBEDO=color.rgb","ALBEDO=vec3(1.0)");mat.shader=shader;fin.set_surface_override_material(si,mat)
            path=folder.path_join(name+"-full-mask.png");await shot(path);paths.full_mask={"path":path,"sha256":FileAccess.get_sha256(path)}
            for body in bodies:
                body.show()
                for si in body.mesh.get_surface_count():var mat=StandardMaterial3D.new();mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;mat.albedo_color=Color.BLACK;mat.cull_mode=BaseMaterial3D.CULL_DISABLED;body.set_surface_override_material(si,mat)
            path=folder.path_join(name+"-body-visible-mask.png");await shot(path);paths.body_visible_mask={"path":path,"sha256":FileAccess.get_sha256(path)}
            fin_records.append({"name":name,"files":paths,"camera_side":fin_camera_side(String(name)),"opposite_source_canvas_is_horizontally_mirrored":fin_camera_side(String(name))<0})
            set_mode(e,stored,"texture")
        for node in e.model.find_children("*","MeshInstance3D",true,false):node.visible=intrinsic.get(node.get_instance_id(),false)
        hall.viewport.size=Vector2i(1000,700);hall.camera.projection=Camera3D.PROJECTION_PERSPECTIVE;var r=region(e)
        for view in [{"name":"oblique","yaw":.65,"pitch":.2},{"name":"top","yaw":0.,"pitch":1.56},{"name":"bottom","yaw":0.,"pitch":-1.56},{"name":"opposite","yaw":PI,"pitch":.2}]:
            camera(e,r,false,view.yaw,view.pitch);var path=folder.path_join("whole-"+view.name+".png");await shot(path);files[path]=FileAccess.get_sha256(path)
        rows.append({"species":species,"ok":true,"files":files,"fins":fin_records,"source_canvas":[source.get_width(),source.get_height()],"scope":"Original skeleton rest, fixed full source camera. Full cutout and body-occluded GPU masks separate; opposite side is mirrored, not independently researched art."})
    var path=root_out.path_join("capture.validation.json");var f=FileAccess.open(path,FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==requested.size(),"rows":rows,"checker_sha256":FileAccess.get_sha256(get_script().resource_path),"fin_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/fin-source141.json") if FileAccess.file_exists("res://assets/models/fish/motion/fin-source141.json") else "baseline"}));f.close();hall.queue_free();await process_frame;quit()
