extends "./capture_surface_mouth_audit.gd"
func run():
    DirAccess.make_dir_recursive_absolute(out)
    for file in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):starting_bindings[file]=FileAccess.get_sha256("res://"+file)
    root.size=Vector2i(1200,800);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800);hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    if requested.is_empty():requested=hall.SPECIES
    for species in requested:
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        var r:Dictionary=region(entry);var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder);var shots:Array=[]
        for pair in [["Swim","Turn"],["Turn","Ascend"],["Ascend","Dive"],["Dive","Swim"]]:
            entry.controller.set_action(pair[0],true);entry.controller.step(0.);entry.controller.seek(.75);entry.controller.set_action(pair[1],false)
            entry.controller.step(float(entry.profile.transition_seconds)*.5)
            if entry.has("jaw_controller"):entry.jaw_controller.apply(1.)
            for view in [["side",0.,0.],["front",PI/2.,0.],["top",0.,1.56]]:
                camera(entry,r,true,view[1],view[2]);var path=folder+"/"+pair[0]+"-to-"+pair[1]+"-"+view[0]+".png";await shot(path);shots.append({"from":pair[0],"to":pair[1],"fraction":.5,"view":view[0],"snapshot":entry.controller.snapshot(),"file":path,"sha256":FileAccess.get_sha256(path)})
        records.append({"species":species,"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"shots":shots});print("TRANSITION112 ",species)
    for file in starting_bindings:assert(starting_bindings[file]==FileAccess.get_sha256("res://"+file),"Runtime changed during transition capture")
    var f=FileAccess.open(out+"/transitions.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"records":records,"files":starting_bindings,"scope":"Actual runtime midpoint transitions in side/front/top; not exhaustive continuous-time proof"}));f.close();quit()
