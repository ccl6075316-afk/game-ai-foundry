extends SceneTree
## Check the eight actual exhibit mouth buttons and the static hairtail exception.
const EXHIBIT = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const WIDTH = preload("res://scripts/aquarium/FinalizedWidthBatch20261101.gd")
const ELEVEN = preload("res://scripts/aquarium/FinalizedElevenFish20261105.gd")
const CACHE = preload("res://scripts/aquarium/FishAppearanceCache.gd")
const SPECIES = ["rainbow_trout", "atlantic_salmon", "red_emperor", "nile_tilapia", "atlantic_sailfish", "mahi_mahi", "african_catfish", "silver_arowana", "hairtail"]

func _initialize() -> void:
    create_timer(40.0).timeout.connect(func(): quit(2))
    call_deferred("run")


func run() -> void:
    var args := OS.get_cmdline_user_args()
    assert(args.size() == 1 and args[0].is_absolute_path())
    var rows: Dictionary = {}
    for species in SPECIES:
        rows[species] = exercise(species)
        await process_frame
        CACHE.clear()
    var report := {
        "ok": true, "kind": "installed_non_shark_mouth_actions",
        "engine": Engine.get_version_info().string, "fish": rows,
    }
    var file := FileAccess.open(args[0], FileAccess.WRITE)
    file.store_string(JSON.stringify(report, "  ") + "\n")
    print("INSTALLED_JAW_ACTION_OK ", rows.size())
    quit()


func exercise(species: String) -> Dictionary:
    var world := Node3D.new()
    root.add_child(world)
    var exhibit := EXHIBIT.new()
    exhibit.display = ""
    exhibit._build_controls()
    var w := WIDTH.new()
    var finalizer: RefCounted = w if w.table().has(species) else ELEVEN.new()
    var profile: Dictionary = finalizer.motion_profile(species)
    var length := float(profile.real_length_cm) / 100.0
    exhibit._add_fish(world, species, length, profile)
    assert(exhibit.fish.size() == 1)
    var entry: Dictionary = exhibit.fish[0]
    exhibit._refresh_buttons()
    assert(not exhibit.jaw_action_button.visible)
    exhibit.display = species
    exhibit._refresh_buttons()
    var actual_model_sha := FileAccess.get_sha256("res://assets/models/fish/" + species + ".glb")
    var skeleton: Skeleton3D = entry.skeleton
    if species == "hairtail":
        var static_receipt := check_hairtail(exhibit, entry, skeleton, profile, actual_model_sha)
        exhibit.fish.clear()
        entry.clear()
        exhibit.free()
        world.free()
        return static_receipt
    assert(exhibit.jaw_action_button.visible)
    assert(entry.controller.has_method("play_jaw_action"))
    var maximum := float(profile.jaw_action_degrees)
    var index := skeleton.find_bone("jaw_lower")
    assert(index >= 0)
    var rest := skeleton.get_bone_rest(index).basis.get_rotation_quaternion()
    var before: Vector3 = entry.carrier.position
    var samples: Array[float] = []
    exhibit.jaw_action_button.pressed.emit()
    for frame in 145:
        samples.append(jaw_angle(rest, skeleton.get_bone_pose_rotation(index)))
        assert(entry.controller.snapshot().action == "Swim")
        if frame == 60:
            exhibit.jaw_action_button.pressed.emit()
        if frame < 144:
            entry.controller.step(1.0 / 60.0)
            skeleton.force_update_all_bone_transforms()
    assert(entry.carrier.position.distance_to(before) > .01)
    assert(samples[0] < .06 and samples[-1] < .06 and absf(samples[72] - maximum) < .01)
    assert(absf(samples[36] - maximum * .5) < .01 and absf(samples[108] - maximum * .5) < .01)
    for frame in range(1, 73):
        assert(samples[frame] + .02 >= samples[frame - 1])
        assert(samples[frame + 72] <= samples[frame + 71] + .02)
    exhibit.jaw_action_button.pressed.emit()
    entry.controller.step(1.2)
    assert(absf(jaw_angle(rest, skeleton.get_bone_pose_rotation(index)) - maximum) < .01)
    var receipt := {
        "model_sha256": actual_model_sha,
        "button_route": true, "angle_samples": samples, "maximum_degrees": samples[72],
        "duration_seconds": 2.4, "swim_continued": true, "repeat_trigger_verified": true,
    }
    exhibit.fish.clear()
    entry.clear()
    exhibit.free()
    world.free()
    return receipt


func jaw_angle(rest: Quaternion, pose: Quaternion) -> float:
    var delta := rest.inverse() * pose
    return rad_to_deg(2.0 * atan2(Vector3(delta.x, delta.y, delta.z).length(), absf(delta.w)))


func check_hairtail(exhibit: Node, entry: Dictionary, skeleton: Skeleton3D, profile: Dictionary, model_sha: String) -> Dictionary:
    assert(not profile.has("jaw_action_degrees"))
    assert(not exhibit.jaw_action_button.visible)
    assert(not entry.controller.has_method("play_jaw_action"))
    assert(entry.controller.get_script().resource_path == "res://scripts/aquarium/FoundryFishMotion.gd")
    var index := skeleton.find_bone("LowerJaw")
    assert(index >= 0)
    var pose := skeleton.get_bone_pose_rotation(index)
    var origin: Vector3 = entry.carrier.position
    var checks: Dictionary = {}
    for action in ["Swim", "Turn", "Ascend", "Dive"]:
        assert(entry.controller.set_action(action, true))
        var largest_angle := 0.0
        for frame in 145:
            if frame == 36:
                exhibit.jaw_action_button.pressed.emit()
            entry.controller.step(1.0 / 60.0)
            assert(entry.controller.snapshot().action == action)
            largest_angle = maxf(largest_angle, jaw_angle(pose, skeleton.get_bone_pose_rotation(index)))
        assert(largest_angle < .06)
        checks[action] = {"samples": 145, "maximum_local_jaw_delta_degrees": largest_angle}
    assert(entry.carrier.position.distance_to(origin) > .01)
    return {"model_sha256": model_sha, "button_visible": false, "additive_jaw_action": false,
        "native_bone_preserved": "LowerJaw", "four_normal_actions": checks, "swim_continued": true}
