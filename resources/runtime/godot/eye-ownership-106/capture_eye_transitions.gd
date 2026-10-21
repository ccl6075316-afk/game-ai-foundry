extends "capture_trial.gd"
## Temporary actual-blend probe. No frozen runtime/controller/material edits.
func _write_eye_capture_receipt(_expected: int):
    super._write_eye_capture_receipt(24)
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(1200,800)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800)
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    hall._select_display("black_seabream");var entry:Dictionary=hall._selected()
    for tank in hall.tanks:tank.root.visible=tank.species=="black_seabream"
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):mesh.visible=entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
    entry.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
    assert(entry.controller.set_action("Swim",true));entry.controller.step(0.);entry.controller.seek(.2)
    if entry.has("jaw_controller"):entry.jaw_controller.apply(1.)
    await process_frame
    var r:Dictionary=region(entry)
    var stored:Array=[]
    for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
        for surface in mesh.mesh.get_surface_count():stored.append([mesh,surface,mesh.get_surface_override_material(surface),mesh.get_active_material(surface)])
    set_mode(entry,stored,"texture")
    var duration:float=entry.profile.transition_seconds
    assert(duration>0.)
    var initial:Dictionary=entry.controller.snapshot()
    assert(initial.action=="Swim" and abs(float(initial.time)-.2)<.000001)
    var rows:Array=[]
    var previous:String="Swim"
    for target in ["Turn","Ascend","Dive","Swim"]:
        # restart=true seeks0 and makes from==to: it is a reset, not a blend.
        assert(entry.controller.set_action(target,false));entry.controller.step(0.)
        var consumed:Dictionary=entry.controller.snapshot()
        assert(consumed.action==target and consumed.pending_action=="")
        assert(consumed.state=="transition" and abs(float(consumed.transition_remaining)-duration)<.000001)
        var elapsed:float=0.
        for fraction in [.25,.75,1.01]:
            var target_elapsed:float=duration*fraction
            entry.controller.step(target_elapsed-elapsed);elapsed=target_elapsed
            if entry.has("jaw_controller"):entry.jaw_controller.apply(1.)
            var snapshot:Dictionary=entry.controller.snapshot()
            assert(snapshot.action==target and snapshot.pending_action=="")
            if fraction<1.:
                assert(snapshot.state=="transition")
                assert(abs(float(snapshot.transition_remaining)-duration*(1.-fraction))<.000001)
            else:
                assert(snapshot.state=="steady" and float(snapshot.transition_remaining)==0.)
            for view in [["side",0.,0.],["top",0.,1.56]]:
                camera(entry,r,true,view[1],view[2]);set_mode(entry,stored,"texture")
                var file:String=out+"/%s-to-%s-%03d-%s.png"%[previous,target,int(round(fraction*100.)),view[0]]
                await shot(file)
                rows.append({"file":file,"sha256":FileAccess.get_sha256(file),"from":previous,"target_action":target,"fraction_of_transition":fraction,
                    "elapsed_transition_seconds":elapsed,"state":snapshot.state,"remaining":snapshot.transition_remaining,"snapshot":snapshot,
                    "camera_transform":str(hall.camera.global_transform),"view":view[0]})
        previous=target
    var eye:Dictionary=entry.model.get_meta("eye_ownership_106_receipt",{})
    var lod:Dictionary=entry.model.get_meta("eye_lod_106_receipt",{})
    var okay:bool=rows.size()==24 and not eye.is_empty() and not lod.is_empty() and not lod_only_reference
    var result:Dictionary={"schema_version":1,"ok":okay,"command":"fish.eye106-actual-action-transition-capture","stage":"validate","status":"done","next_action":"human_review",
        "inputs":{"eye_mode":eye_trial_mode,"eye_probe":eye_trial_probe,"script_sha256":FileAccess.get_sha256(get_script().resource_path)},"outputs":[out+"/capture.validation.json"],
        "summary":{"images":rows.size(),"initial_snapshot":initial,"transition_seconds":duration,"samples":rows,"install_receipt":eye,"lod_install_receipt":lod,
        "controller_semantics":"InitialSwim restart=true then seek.2; every actual transition uses set_action(target,false) followed by step0 to consume pending. restart=true would reset via seek0 and cannot demonstrate blending.",
        "scope":"Same102 Hall/region/camera; three cumulative times per four sequential action blends, head-side/top24PNG. Discrete visual transition evidence, not whole-fish acceptance."},"failures":[]}
    var file:=FileAccess.open(out+"/capture.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(result,"  "));file.close()
    hall.queue_free();await process_frame
    if RenderingServer.has_method("force_sync"):RenderingServer.force_sync()
    await process_frame;quit(0 if okay else 1)
