extends SceneTree
## Exercise the mouth button in the released Bluegill's normal exhibit route.
const EXHIBIT = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const FINAL = preload("res://scripts/aquarium/FinalizedWidthBatch20261101.gd")
const SPECIES := "bluegill"
const MODEL := "res://assets/models/fish/bluegill.glb"

func _initialize() -> void:
    call_deferred("run")

func run() -> void:
    var args := OS.get_cmdline_user_args()
    assert(args.size() == 1 and args[0].is_absolute_path())
    var world := Node3D.new()
    root.add_child(world)
    var exhibit := EXHIBIT.new()
    exhibit._build_controls()
    exhibit._add_fish(world, SPECIES, .191, FINAL.new().motion_profile(SPECIES))
    assert(exhibit.fish.size() == 1)
    var entry: Dictionary = exhibit.fish[0]
    exhibit._refresh_buttons()
    assert(not exhibit.jaw_action_button.visible)
    exhibit.display = SPECIES
    exhibit._refresh_buttons()
    assert(exhibit.jaw_action_button.visible)
    var skeleton: Skeleton3D = entry.skeleton
    var index := skeleton.find_bone("jaw_lower")
    var rest := skeleton.get_bone_rest(index).basis.get_rotation_quaternion()
    var before: Vector3 = entry.carrier.position
    var values: Array[float] = []
    exhibit.jaw_action_button.pressed.emit()
    for frame in 145:
        values.append(jaw_angle(rest, skeleton.get_bone_pose_rotation(index)))
        assert(entry.controller.snapshot().action == "Swim")
        if frame == 60:
            exhibit.jaw_action_button.pressed.emit()
        if frame < 144:
            entry.controller.step(1.0 / 60.0)
            skeleton.force_update_all_bone_transforms()
    assert(entry.carrier.position.distance_to(before) > .01)
    assert(values[0] < .06 and values[-1] < .06 and absf(values[72] - 8.0) < .01)
    assert(absf(values[36] - 4.0) < .01 and absf(values[108] - 4.0) < .01)
    for i in range(1, 73):
        assert(values[i] + .02 >= values[i-1] and values[i+72] <= values[i+71] + .02)
    exhibit.jaw_action_button.pressed.emit()
    entry.controller.step(1.2)
    assert(absf(jaw_angle(rest, skeleton.get_bone_pose_rotation(index)) - 8.0) < .01)
    var report := {"ok":true, "species":SPECIES, "model_sha256":FileAccess.get_sha256(MODEL),
                   "kind":"canonical_bluegill_mouth_action", "actual_button_route":true,
                   "jaw_samples":values, "base_swim_continued":true, "can_retrigger":true,
                   "maximum_degrees":values[72], "duration_seconds":2.4}
    FileAccess.open(args[0], FileAccess.WRITE).store_string(JSON.stringify(report, "  ") + "\n")
    exhibit.fish.clear()
    entry.clear()
    exhibit.free()
    world.free()
    await process_frame
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    await process_frame
    print("BLUEGILL_JAW_ACTION_OK ", values.size(), " ", values[72])
    quit()

func jaw_angle(rest: Quaternion, current: Quaternion) -> float:
    var relative := rest.inverse() * current
    return rad_to_deg(2.0 * atan2(Vector3(relative.x, relative.y, relative.z).length(), absf(relative.w)))
