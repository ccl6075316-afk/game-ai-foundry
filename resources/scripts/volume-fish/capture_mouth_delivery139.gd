extends "capture_surface_mouth_audit.gd"
## Actual configured game, anatomical views and twenty seconds of real controls.
func delivery_profiles()->Dictionary:return JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles
func delivery_binding(e:Dictionary,species:String)->Dictionary:return load("res://scripts/aquarium/MouthRepair139.gd").new().validate(e.model,species)
func run():
    DirAccess.make_dir_recursive_absolute(out);var root_out=out
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.viewport.size=Vector2i(1000,700);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    var profiles=delivery_profiles()
    if requested.is_empty():requested=profiles.keys()
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[node.get_instance_id()]=node.visible
    var dependencies={}
    for dir in ["res://scripts/aquarium","res://assets/models/fish/motion"]:
        for path in runtime_files(dir):dependencies[path]=FileAccess.get_sha256("res://"+path)
    var rows=[]
    for species in requested:
        out=root_out.path_join(species);DirAccess.make_dir_recursive_absolute(out)
        assert(profiles.has(species) and not species.ends_with("hammerhead"))
        hall._select_display(species);var e:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic.get(node.get_instance_id(),false)
        for node in hall.world.find_children("*","Label3D",true,false):node.hide()
        var binding=delivery_binding(e,species)
        assert(binding is Dictionary and binding.get("ok",false),"Invalid pre-capture resource/visibility binding: "+species)
        e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true)
        e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
        if e.has("jaw_controller"):e.jaw_controller.apply(1.)
        var r=region(e);var stored=[];var files={}
        for node in e.model.find_children("*","MeshInstance3D",true,false):
            for si in node.mesh.get_surface_count():var mat=node.get_active_material(si);stored.append([node,si,mat,mat])
        var views={"side":[0.,0.],"opposite":[PI,0.],"front":[PI/2.,0.],"top":[0.,1.56],"bottom":[0.,-1.56],"oblique":[.65,.2]}
        for view in views:
            var angle=views[view];camera(e,r,true,angle[0],angle[1])
            for mode in ["texture","clay","albedo"]:
                set_mode(e,stored,mode);var path=out+"/head-%s-%s.png"%[view,mode];await shot(path);files[path]=FileAccess.get_sha256(path)
        set_mode(e,stored,"texture")
        for view in views:
            var angle=views[view];camera(e,r,false,angle[0],angle[1]);var path=out+"/whole-%s.png"%view;await shot(path);files[path]=FileAccess.get_sha256(path)
        for name in ownership[species].fins:e.model.find_child(name,true,false).hide()
        for view in ["side","bottom","oblique"]:
            var angle=views[view];camera(e,r,false,angle[0],angle[1]);var path=out+"/hidden-fin-%s.png"%view;await shot(path);files[path]=FileAccess.get_sha256(path)
        for name in ownership[species].fins:
            var node=e.model.find_child(name,true,false);node.visible=intrinsic.get(node.get_instance_id(),false)
        if e.has("jaw_controller"):
            for gape in [0.,.5,1.]:
                e.jaw_controller.apply(gape);camera(e,r,true,.65,.2);var path=out+"/jaw-%.1f.png"%gape;await shot(path);files[path]=FileAccess.get_sha256(path)
        var lips=e.model.find_child("Source_lips139",true,false)
        if lips:
            lips.hide();camera(e,r,true,.65,.2);var path=out+"/body-without-lips.png";await shot(path);files[path]=FileAccess.get_sha256(path);lips.show()
        # Actual selected exhibit with its authored glass/floor, then isolated
        # orbit: these serve different readability and surface-review purposes.
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=intrinsic.get(node.get_instance_id(),false)
        hall._focus_selected(true,2.6);hall._update_camera();var water=out+"/game-exhibit.png";await shot(water);files[water]=FileAccess.get_sha256(water)
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic.get(node.get_instance_id(),false)
        hall.viewport.size=Vector2i(600,400);var frame_dir=out+"/video-frames";DirAccess.make_dir_recursive_absolute(frame_dir)
        e.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        var actions=["Swim","Turn","Ascend","Dive"];var samples=[]
        for frame in 480:
            if frame%120==0:assert(e.controller.set_action(actions[frame/120],frame==0))
            e.controller.step(1./24.)
            if e.has("jaw_controller"):e.jaw_controller.apply(.5+.5*sin(frame/24.))
            camera(e,r,false,float(frame)/480.*TAU,.23*sin(float(frame)/480.*TAU))
            var path=frame_dir+"/frame-%04d.png"%frame;await shot(path)
            if frame%24==0:samples.append({"frame":frame,"time_seconds":frame/24.,"action":actions[frame/120],"snapshot":e.controller.snapshot(),"file":path,"sha256":FileAccess.get_sha256(path)})
        hall.viewport.size=Vector2i(1000,700)
        rows.append({"species":species,"binding":binding,"files":files,"video":{"fps":24,"frames":480,"duration_seconds":20,"samples":samples},"head_region":{"position":[r.head.position.x,r.head.position.y,r.head.position.z],"size":[r.head.size.x,r.head.size.y,r.head.size.z]},"source_model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb")})
        print("MOUTH_DELIVERY139 ",species," frames=480")
    for path in dependencies:assert(FileAccess.get_sha256("res://"+path)==dependencies[path])
    var f=FileAccess.open(root_out+"/capture.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":rows.size()==requested.size(),"rows":rows,"runtime_dependencies":dependencies,"checker_sha256":FileAccess.get_sha256(get_script().resource_path),"config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/mouth-repair139.json"),"scope":"Actual configured139 resources: six head views in clay/albedo/texture, whole and hidden-fin views, jaw branch, actual exhibit and20s orbit through all four actions. Operator must review images/video; not automatic visual acceptance."}));f.close()
    hall.queue_free();await process_frame;quit()
