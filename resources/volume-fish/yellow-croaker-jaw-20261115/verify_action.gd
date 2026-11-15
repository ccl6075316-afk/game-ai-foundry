extends SceneTree
## Check the released exhibit's dedicated mouth action against the normal body controller.
const EXHIBIT = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const RELEASE = preload("res://scripts/aquarium/FinalizedElevenFish20261105.gd")
const BASE = preload("res://scripts/aquarium/FoundryFishMotion.gd")
const SPECIES := "yellow_croaker"
const PATH := "res://assets/models/fish/yellow_croaker.glb"
const STEP := 1.0 / 60.0

func _initialize() -> void:
    call_deferred("run")

func jaw_angle(skeleton: Skeleton3D) -> float:
    var index := skeleton.find_bone("jaw_lower")
    var rest := skeleton.get_bone_rest(index).basis.get_rotation_quaternion()
    return rad_to_deg(rest.angle_to(skeleton.get_bone_pose_rotation(index)))

func pose_delta(a: Dictionary, b: Dictionary) -> float:
    var maximum: float = a.carrier.transform.origin.distance_to(b.carrier.transform.origin)
    for axis in 3:
        maximum = maxf(maximum, a.carrier.transform.basis[axis].distance_to(b.carrier.transform.basis[axis]))
    for bone in a.skeleton.get_bone_count():
        if a.skeleton.get_bone_name(bone) == "jaw_lower":
            continue
        var left: Transform3D = a.skeleton.get_bone_global_pose(bone)
        var right: Transform3D = b.skeleton.get_bone_global_pose(bone)
        maximum = maxf(maximum, left.origin.distance_to(right.origin))
        for axis in 3:
            maximum = maxf(maximum, left.basis[axis].distance_to(right.basis[axis]))
    return maximum

func run() -> void:
    var args := OS.get_cmdline_user_args()
    assert(args.size() == 1 and args[0].is_absolute_path())
    var world := Node3D.new()
    root.add_child(world)
    var release := RELEASE.new()
    var profile: Dictionary = release.motion_profile(SPECIES)
    var exhibit := EXHIBIT.new()
    exhibit._build_controls()
    exhibit._add_fish(world, SPECIES, .6, profile)
    var official: Dictionary = exhibit.fish[0]
    var lod_entries := 0
    for mesh in official.model.find_children("*", "MeshInstance3D", true, false):
        for surface in mesh.mesh.get("_surfaces"):
            lod_entries += surface.get("lods", []).size()
    assert(lod_entries == 0)
    exhibit._refresh_buttons()
    assert(not exhibit.jaw_action_button.visible)
    exhibit.display = SPECIES
    exhibit._refresh_buttons()
    assert(exhibit.jaw_action_button.visible)
    var carrier := Node3D.new()
    world.add_child(carrier)
    var model := release.load_model(PATH, SPECIES)
    carrier.add_child(model)
    model.transform = official.model.transform
    var skeleton: Skeleton3D = model.find_children("*", "Skeleton3D", true, false)[0]
    var player: AnimationPlayer = model.find_children("*", "AnimationPlayer", true, false)[0]
    var base := BASE.new()
    assert(base.configure(carrier, model, player, skeleton, profile).ok)
    var original := {"controller": base, "carrier": carrier, "skeleton": skeleton}
    var maximum := 0.0
    var controls := 0
    for values in [[0.,0.,0.,0.], [1.,1.,1.,1.], [2.5,1.,2.5,1.], [1.,3.,1.,3.], [1.3,.7,2.,1.4]]:
        var settings := {"body_amplitude":values[0], "body_frequency":values[1],
                         "fin_amplitude":values[2], "fin_frequency":values[3]}
        for item in [official, original]:
            item.controller.set_motion_controls(settings, true)
        for action in ["Swim", "Turn", "Ascend", "Dive"]:
            for i in 24:
                for item in [official, original]:
                    assert(item.controller.set_action(action, true))
                    item.controller.step(0.0)
                    item.controller.seek(float(i)/24.0*float(profile.period_seconds))
                    item.skeleton.force_update_all_bone_transforms()
                maximum = maxf(maximum, pose_delta(official, original))
                controls += 1
    var transitions := 0
    for action in ["Turn", "Ascend", "Dive", "Swim"]:
        for item in [official, original]:
            assert(item.controller.set_action(action))
        for i in 90:
            for item in [official, original]:
                item.controller.step(STEP)
                item.skeleton.force_update_all_bone_transforms()
            maximum = maxf(maximum, pose_delta(official, original))
            transitions += 1
    assert(jaw_angle(official.skeleton) < .06)
    exhibit.jaw_action_button.pressed.emit()
    var degrees := []
    for i in range(145):
        if i == 60:
            # An active jaw event does not snap shut if the user taps twice.
            exhibit.jaw_action_button.pressed.emit()
        degrees.append(jaw_angle(official.skeleton))
        if i == 144:
            break
        for item in [official, original]:
            item.controller.step(STEP)
            item.skeleton.force_update_all_bone_transforms()
        maximum = maxf(maximum, pose_delta(official, original))
    assert(maximum < .000002)
    assert(degrees[0] < .06 and absf(degrees[72] - 14.0) < .01 and degrees[-1] < .06)
    assert(absf(degrees[36]-7.0)<.01 and absf(degrees[108]-7.0)<.01)
    for i in range(1, 73):
        assert(degrees[i] + .01 >= degrees[i-1] and degrees[i+72] <= degrees[i+71] + .01)
    var result := {"ok":true, "kind":"canonical_croaker_mouth_action", "species":SPECIES,
        "model_sha256":FileAccess.get_sha256(PATH), "body_control_comparisons":controls,
        "body_transition_comparisons":transitions, "maximum_body_transform_delta":maximum,
        "jaw_samples":degrees.size(), "jaw_degrees":degrees, "duration_seconds":2.4,
        "actual_button_route":true, "does_not_interrupt_swim":true, "serialized_lod_entries":lod_entries}
    FileAccess.open(args[0], FileAccess.WRITE).store_string(JSON.stringify(result, "  ") + "\n")
    print("CROAKER_ACTION_OK ", controls, " ", transitions, " ", degrees[72])
    exhibit.fish.clear()
    official.clear()
    original.clear()
    exhibit.free()
    world.free()
    await process_frame
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    await process_frame
    quit()
