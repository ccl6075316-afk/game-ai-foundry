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
                var t:float=[0.,.35,.75,1.25][k];entry.controller.seek(t)
                camera(entry,r,true,[0.,.65,PI/2.,PI][k],.12 if k==1 else 0.)
                var path=folder+"/"+action+"-%d.png"%k;await shot(path)
                samples.append({"action":action,"seconds":t,"view":["side","oblique","front","opposite"][k],"file":path,"sha256":FileAccess.get_sha256(path),"snapshot":entry.controller.snapshot()})
        var body=entry.model.find_child("Closed_body",true,false) as MeshInstance3D
        var material=body.get_active_material(0) as ShaderMaterial
        assert(material!=null)
        var rest=load("res://scripts/aquarium/RestSurface114.gd").new().validate(entry.model,body,0,material)
        records.append({"species":species,"model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),"samples":samples,"actual_import_rest114":rest})
    for name in starting_bindings:assert(FileAccess.get_sha256("res://"+name)==starting_bindings[name])
    var f=FileAccess.open(out+"/motion.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":records.size()==requested.size(),"status":"done","next_action":"human_review","records":records,"files":starting_bindings,"script_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Actual textured four actions,16 head views and actual imported rest-LUT validation. Discrete visual samples, not continuous-time proof."},"  "));quit()
