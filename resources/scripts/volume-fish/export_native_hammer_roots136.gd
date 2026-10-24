extends "./export_runtime_fin_roots.gd"
func run() -> void:
    var args=OS.get_cmdline_user_args();assert(args.size()>=3);plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var root_out=args[1];variant=args[2]
    export_membranes="--membranes" in args
    var profiles: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
    for spec in plan.items:
        if args.size()>3 and args[3]!="--membranes" and spec.species!=args[3]:continue
        var path: String=spec.model;out=root_out+"/"+spec.species;DirAccess.make_dir_recursive_absolute(out);samples=[]
        var carrier=Node3D.new();root.add_child(carrier);var model: Node3D
        var resource_path=ProjectSettings.localize_path(path.replace("\\","/"))
        if resource_path.begins_with("res://"):
            # Installed assets use precisely the imported resource the game loads.
            var packed=load(resource_path) as PackedScene;assert(packed!=null);model=packed.instantiate()
        else:
            var document=GLTFDocument.new();var state=GLTFState.new();assert(document.append_from_file(path,state)==OK);model=document.generate_scene(state)
        carrier.add_child(model)
        var skeleton: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0];var player=model.find_children("*","AnimationPlayer",true,false)[0];player.stop();skeleton.reset_bone_poses();skeleton.force_update_all_bone_transforms()
        var entry={"carrier":carrier,"model":model,"skeleton":skeleton,"player":player};prepare(entry,spec)
        var profile: Dictionary=profiles[spec.species];model.scale=Vector3.ONE*float(profile.real_length_cm)/100./float(spec.length_native)
        sample(entry,"Static",0.)
        if true:
            player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
            player.play(profile.base_clip)
            var native_clip: Animation=player.get_animation(profile.base_clip)
            for phase in 25:
                var native_time:=native_clip.length*float(phase)/25.
                player.seek(native_time,true);player.advance(0.);sample(entry,"Native",native_time)
            player.stop();skeleton.reset_bone_poses();skeleton.force_update_all_bone_transforms()
        var report={"ok":true,"model":path,"model_sha256":FileAccess.get_sha256(path),"selection":"Frozen explicit full basal bands and source basal polylines; seven points per root edge","expected_fins":spec.fins.keys(),"controller_source":"res://scripts/aquarium/FoundryFishMotion.gd","controller_sha256":FileAccess.get_sha256("res://scripts/aquarium/FoundryFishMotion.gd"),"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json"),"export_script_sha256":FileAccess.get_sha256(get_script().resource_path),"engine_version":Engine.get_version_info().string,"sample_limit":"Static rest;16 samples per four actions;four samples per four consecutive transitions. Unsampled instants are not certified.","body_triangles":faces.size(),"samples":samples}
        report["native_cycle_revision"]=1
        report["native_clip_seconds"]=player.get_animation(profile.base_clip).length
        report["sample_limit"]="Rest and25 native animation phases; same frozen complete basal bands."
        save_json(out+"/export.validation.json",report);print("NATIVE_ROOT_EXPORT ",spec.species," ",samples.size());carrier.queue_free();await process_frame
    quit()
