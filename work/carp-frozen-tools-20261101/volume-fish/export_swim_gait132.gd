extends "export_runtime_fin_roots.gd"
## Actual opt-in candidate sequence, including propel/coast and action changes.
## Same CLI contract as export_runtime_fin_roots.gd; only bluegill is supported.

func run() -> void:
    var args := OS.get_cmdline_user_args()
    assert(args.size() >= 3)
    plan = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
    var root_out: String = args[1]
    export_membranes = "--membranes" in args
    var foundry := ProjectSettings.globalize_path(get_script().resource_path).get_base_dir().get_base_dir().get_base_dir().get_base_dir()
    var adapter_path := foundry.path_join("resources/runtime/godot/IntermittentFishGait.gd")
    var config_path := foundry.path_join("resources/volume-fish/motion/bluegill-intermittent-132.json")
    var settings: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(config_path))
    var profiles: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
    var done := false
    for spec in plan.items:
        if spec.species != "bluegill": continue
        var path: String = spec.model
        assert(FileAccess.get_sha256(path) == str(spec.model_sha256), "Stale candidate fin selection")
        out = root_out.path_join("bluegill")
        DirAccess.make_dir_recursive_absolute(out)
        samples = []
        var carrier := Node3D.new()
        root.add_child(carrier)
        var model: Node3D = load(ProjectSettings.localize_path(path.replace("\\", "/"))).instantiate()
        carrier.add_child(model)
        var skeleton: Skeleton3D = model.find_children("*", "Skeleton3D", true, false)[0]
        var player: AnimationPlayer = model.find_children("*", "AnimationPlayer", true, false)[0]
        player.stop()
        skeleton.reset_bone_poses()
        skeleton.force_update_all_bone_transforms()
        var entry := {"carrier":carrier,"model":model,"skeleton":skeleton,"player":player}
        prepare(entry, spec)
        var profile: Dictionary = profiles.bluegill
        model.scale = Vector3.ONE * float(profile.real_length_cm) / 100.0 / float(spec.length_native)
        sample(entry, "Static", 0.0)
        if export_membranes:
            player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
            player.play(profile.base_clip)
            var native_clip: Animation = player.get_animation(profile.base_clip)
            for phase in 25:
                var native_time := native_clip.length * float(phase) / 25.0
                player.seek(native_time, true)
                player.advance(0.0)
                sample(entry, "Native", native_time)
            player.stop()
            skeleton.reset_bone_poses()
            skeleton.force_update_all_bone_transforms()
        var controller = load("res://scripts/aquarium/FoundryFishMotion.gd").new()
        assert(controller.configure(carrier, model, player, skeleton, profile).ok)
        var adapter = load(adapter_path).new()
        var clip: Animation = player.get_animation(profile.base_clip)
        assert(adapter.configure(controller, settings, clip.length).ok)
        # A single continuous 20-second sequence, 40 samples per action. No seek
        # is used: actual integrated wall-time clocks and coast envelopes apply.
        for action in ["Swim", "Turn", "Ascend", "Dive", "Swim"]:
            assert(adapter.set_action(action))
            sample(entry, "GaitTransition:" + action, adapter.elapsed)
            for k in 40:
                adapter.step(0.1)
                sample(entry, "Gait:" + action + ":" + str(adapter.snapshot().gait), adapter.elapsed)
        if export_membranes:
            var actions := ["Turn", "Dive", "Ascend", "Swim"]
            for k in 259:
                if k % 65 == 0: assert(adapter.set_action(actions[mini(3, k / 65)]))
                adapter.step(0.05)
                sample(entry, "GaitDense:" + str(controller._action) + ":" + str(adapter.snapshot().gait), adapter.elapsed)
        var report := {"ok":true,"model":path,"model_sha256":FileAccess.get_sha256(path),"selection":"Unchanged explicit whole basal bands and seven points per root edge from frozen plan","expected_fins":spec.fins.keys(),"controller_source":"res://scripts/aquarium/FoundryFishMotion.gd","controller_sha256":FileAccess.get_sha256("res://scripts/aquarium/FoundryFishMotion.gd"),"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json"),"export_script_sha256":FileAccess.get_sha256(get_script().resource_path),"base_exporter_sha256":FileAccess.get_sha256(foundry.path_join("resources/scripts/volume-fish/export_runtime_fin_roots.gd")),"gait_adapter_sha256":FileAccess.get_sha256(adapter_path),"gait_config_sha256":FileAccess.get_sha256(config_path),"engine_version":Engine.get_version_info().string,"sample_limit":"206 actual discrete candidate poses: static plus five action boundary poses plus 200 continuous 120Hz-integrated propel/coast/action samples over 20 wall seconds. Not continuous collision proof; no biological or visual acceptance.","body_triangles":faces.size(),"samples":samples,"production_installed":false,"candidate_gait_revision":132}
        if export_membranes:
            report["fin_membrane_revision"] = 1
            report["sample_limit"] = "490 discrete poses: rest + 25 native + 205 actual candidate poses over 20 wall seconds + 259 dense continuing candidate poses at 0.05 seconds with four more action switches. These are candidate gait samples, not the standard independent range dataset. No continuous collision or visual/biological acceptance."
        save_json(out.path_join("export.validation.json"), report)
        print("GAIT132_FIN_EXPORT_DONE bluegill ", samples.size())
        carrier.queue_free()
        await process_frame
        done = true
    assert(done, "No bluegill in frozen plan")
    quit()
