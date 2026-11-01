extends "./capture_surface_mouth_audit.gd"
## Actual production materials only. No debug shader/albedo cache substitution.
func run():
    DirAccess.make_dir_recursive_absolute(out)
    for name in runtime_files("res://scripts/aquarium")+runtime_files("res://assets/models/fish/motion"):starting_bindings[name]=FileAccess.get_sha256("res://"+name)
    root.size=Vector2i(1200,800);hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800);hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    if requested.is_empty():requested=["african_catfish"]
    for species in requested:
        hall._select_display(species);var entry:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        var r=region(entry);var folder=out+"/"+species;DirAccess.make_dir_recursive_absolute(folder);var samples:Array=[]
        for action in ["Swim","Turn","Ascend","Dive"]:
            assert(entry.controller.set_action(action,true));entry.controller.step(0.)
            for k in 4:
                var t:float=float(entry.controller.snapshot().loop_seconds)*float(k)/4.;entry.controller.seek(t)
                camera(entry,r,true,[0.,.65,PI/2.,PI][k],.12 if k==1 else 0.)
                var path=folder+"/"+action+"-%d.png"%k;await shot(path)
                samples.append({"action":action,"seconds":t,"view":["side","oblique","front","opposite"][k],"file":path,"sha256":FileAccess.get_sha256(path),"snapshot":entry.controller.snapshot()})
        var profile:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles[species]
        for target in ["Swim","Turn","Ascend","Dive"]:
            entry.controller.set_action(target,false)
            for k in 3:
                entry.controller.step(float(profile.transition_seconds)/3.)
                camera(entry,r,true,[0.,.65,PI/2.][k],.12 if k==1 else 0.)
                var path=folder+"/Transition-"+target+"-%d.png"%k;await shot(path)
                samples.append({"action":"Transition:"+target,"view":["side","oblique","front"][k],"file":path,"sha256":FileAccess.get_sha256(path),"snapshot":entry.controller.snapshot()})
        entry.controller.set_action("Swim",true);entry.controller.step(0.);entry.controller.seek(0.)
        var player=entry.model.find_children("*","AnimationPlayer",true,false)[0] as AnimationPlayer
        var skeleton=entry.model.find_children("*","Skeleton3D",true,false)[0] as Skeleton3D
        player.stop();skeleton.reset_bone_poses();player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
        player.play(profile.base_clip)
        var clip=player.get_animation(profile.base_clip)
        for k in 4:
            var t:float=clip.length*float(k)/4.;player.seek(t,true);player.advance(0.);skeleton.force_update_all_bone_transforms()
            camera(entry,r,true,[0.,.65,PI/2.,PI][k],.12 if k==1 else 0.)
            var path=folder+"/Native-%d.png"%k;await shot(path)
            samples.append({"action":"Native","native_seconds":t,"native_phase":float(k)/4.,"file":path,"sha256":FileAccess.get_sha256(path)})
        var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D
        var material=body.get_active_material(0) as ShaderMaterial
        assert(material!=null)
        var rest=load("res://scripts/aquarium/RestSurface114.gd").new().validate(entry.model,body,0,material)
        records.append({"species":species,"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),"samples":samples,"actual_import_rest114":rest})
    for name in starting_bindings:assert(FileAccess.get_sha256("res://"+name)==starting_bindings[name])
    var f=FileAccess.open(out+"/motion.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":records.size()==requested.size(),"status":"done","next_action":"human_review","records":records,"files":starting_bindings,"script_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Actual textured four actions at quarter-cycle phases, transitions at thirds, native quarter-cycle and actual imported rest-LUT validation. Discrete visual samples, not continuous-time proof."},"  "));quit()
