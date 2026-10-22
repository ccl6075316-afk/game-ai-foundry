extends "./capture_surface_mouth_audit.gd"
## Current actual game, zero-amplitude source pose, same frozen camera per fish.
## Separately records jaw0/jaw1 for species with a real jaw controller.
func run():
    DirAccess.make_dir_recursive_absolute(out)
    for name in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):starting_bindings[name]=FileAccess.get_sha256("res://"+name)
    root.size=Vector2i(1200,800);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800);hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    if requested.is_empty():requested=hall.SPECIES
    for species in requested:
        assert(species in hall.SPECIES)
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        entry.controller.set_motion_controls({"body_amplitude":0.,"body_frequency":1.,"fin_amplitude":0.,"fin_frequency":1.},true);entry.controller.set_action("Swim",true);entry.controller.step(0.);entry.controller.seek(0.)
        var r=region(entry);var stored:Array=[];var samples:Array=[];var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder)
        for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
            for si in mesh.mesh.get_surface_count():stored.append([mesh,si,mesh.get_surface_override_material(si),mesh.get_active_material(si)])
        var jaw_states=[-1.]
        if entry.has("jaw_controller"):jaw_states=[0.,1.]
        for jaw in jaw_states:
            if jaw>=0.:entry.jaw_controller.apply(jaw)
            var prefix="jaw%d-"%int(jaw) if jaw>=0. else ""
            for view in [["side",0.,0.],["front",PI/2.,0.],["top",0.,1.56],["oblique",.65,.20]]:
                camera(entry,r,true,view[1],view[2])
                for mode in ["texture","clay"]:
                    set_mode(entry,stored,mode);var file=folder+"/"+prefix+view[0]+"-"+mode+".png";await shot(file);samples.append({"jaw_ratio":jaw,"view":view[0],"mode":mode,"file":file,"sha256":FileAccess.get_sha256(file)})
        set_mode(entry,stored,"texture")
        records.append({"species":species,"name":hall.LABELS[species],"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),"separate_jaw":entry.has("jaw_controller"),"body_region":str(r.body),"head_region":str(r.head),"samples":samples});print("HEAD_SCREEN117 ",species)
    for name in starting_bindings:assert(FileAccess.get_sha256("res://"+name)==starting_bindings[name])
    var f=FileAccess.open(out+"/capture.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":records.size()==requested.size(),"status":"done","next_action":"human_review","records":records,"files":starting_bindings,"scope":"Read-only actual game zero-amplitude source-pose head4views/clay/texture. Separate-jaw0/1 explicitly separated; no biological acceptance from screen alone."},"  "));quit()
