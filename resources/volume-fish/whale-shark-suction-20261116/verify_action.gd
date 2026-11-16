extends SceneTree
## Compare the actual exhibit button and each imported shape against the approved Godot sampling.
const EXHIBIT = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const FINAL = preload("res://scripts/aquarium/FinalizedElevenFish20261105.gd")
const CACHE = preload("res://scripts/aquarium/FishAppearanceCache.gd")
const FISHING = preload("res://scripts/screens/FishingVolumeFish.gd")
const RUNTIME = preload("res://scripts/aquarium/WhaleSharkSuctionMotion.gd")
const SPECIES := "whale_shark"

var exhibit: Control
var world: Node3D
var pending := true


func _initialize() -> void:
    create_timer(45.).timeout.connect(func(): quit(2) if pending else quit())
    call_deferred("run")


func run() -> void:
    var args := OS.get_cmdline_user_args()
    assert(args.size() == 2 and args[0].is_absolute_path() and args[1].is_absolute_path())
    var accepted: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
    var trace: Dictionary = accepted.playback
    var hash := FileAccess.get_sha256("res://assets/models/fish/whale_shark.glb")
    assert(accepted.ok and accepted.model_sha256 == hash and trace.sample_count == 631)
    world = Node3D.new()
    root.add_child(world)
    exhibit = EXHIBIT.new()
    exhibit._load_profiles()
    exhibit._build_controls()
    CACHE.clear()
    CACHE.begin_entry()
    var profile: Dictionary = exhibit.profiles[SPECIES]
    exhibit._add_fish(world, SPECIES, 8.0, profile)
    assert(exhibit.fish.size() == 1 and not exhibit.loading_metrics[0].reused_appearance)
    var entry: Dictionary = exhibit.fish[0]
    assert(entry.controller.get_script() == RUNTIME)
    var original_center := float(FINAL.new().table()[SPECIES].review_model_center_x)
    assert(absf(entry.model.position.x + original_center) < .000002)
    assert(entry.model.scale == Vector3.ONE)
    assert(weights(entry.model) == Vector3.ZERO)
    exhibit.display = ""
    exhibit._refresh_buttons()
    assert(not exhibit.jaw_action_button.visible)
    exhibit.display = SPECIES
    exhibit._refresh_buttons()
    assert(exhibit.jaw_action_button.visible and exhibit.jaw_action_button.text == "吸滤")
    var start: Vector3 = entry.carrier.position
    exhibit.jaw_action_button.pressed.emit()

    var max_error := 0.0
    var cached: Dictionary
    var fishing_check: Dictionary
    for frame in range(int(trace.sample_count)):
        var answer := weights(entry.model)
        var requested := Vector3(trace.mouth[frame], trace.throat[frame], trace.seal[frame])
        max_error = maxf(max_error, maxf(absf(answer.x-requested.x), maxf(absf(answer.y-requested.y), absf(answer.z-requested.z))))
        assert(entry.controller.snapshot().action == "Swim")
        if frame == 44:
            assert(answer.x > .99)
            exhibit._add_fish(world, SPECIES, 8.0, profile)
            cached = exhibit.fish[1]
            assert(exhibit.loading_metrics[1].reused_appearance)
            assert(cached.model.position == entry.model.position and weights(cached.model) == Vector3.ZERO)
            assert(weights(entry.model) == answer, "Cache instance altered the live exhibit shapes")
            fishing_check = exercise_fishing()
        if frame + 1 < int(trace.sample_count):
            entry.controller.step(1.0 / 60.0)
    assert(max_error < .000002)
    assert(weights(entry.model) == Vector3.ZERO and weights(cached.model) == Vector3.ZERO)
    assert(entry.carrier.position.distance_to(start) > .01)

    exhibit.jaw_action_button.pressed.emit()
    entry.controller.step(.74)
    assert(weights(entry.model).x > .99)
    exhibit.jaw_action_button.pressed.emit()
    assert(weights(entry.model) == Vector3.ZERO)
    entry.controller.step(.74)
    assert(weights(entry.model).x > .99)
    entry.controller.step(10.5)
    assert(weights(entry.model) == Vector3.ZERO)
    exhibit._add_fish(world, "carp", float(exhibit.profiles.carp.real_length_cm)/100.0, exhibit.profiles.carp)
    exhibit.display = "carp"
    exhibit._refresh_buttons()
    assert(exhibit.jaw_action_button.visible and exhibit.jaw_action_button.text == "张嘴")

    var result := {
        "ok": true, "model_sha256": hash, "kind":"installed_whale_shark_suction_button",
        "engine":Engine.get_version_info().string, "button":"吸滤", "cycle_seconds":trace.cycle_seconds,
        "repeats":trace.repeats, "approved_sample_count":trace.sample_count, "max_shape_weight_error":max_error,
        "swim_continued":true, "closed_end_and_retrigger_verified":true, "cached_instance_neutral":true,
        "fishing_uses_idle_mouth":fishing_check, "ordinary_fish_button_unchanged":true,
        "approved_playback_report_sha256":FileAccess.get_sha256(args[0]),
    }
    var file := FileAccess.open(args[1], FileAccess.WRITE)
    file.store_string(JSON.stringify(result,"  ") + "\n")
    file.close()
    print("WHALE_SHARK_SUCTION_INSTALLED ", hash, " max error=", max_error)
    CACHE.clear()
    exhibit.fish.clear()
    exhibit.free()
    world.free()
    pending = false
    await process_frame
    quit()


func weights(model: Node3D) -> Vector3:
    var values := Vector3.ZERO
    for index in RUNTIME.MOUTH_MESHES.size():
        var mesh := model.find_child(RUNTIME.MOUTH_MESHES[index], true, false) as MeshInstance3D
        assert(mesh != null)
        var intake := mesh.get_blend_shape_value(mesh.find_blend_shape_by_name(&"SuctionIntake"))
        var seal := mesh.get_blend_shape_value(mesh.find_blend_shape_by_name(&"SuctionSeal"))
        if index == 0:
            var throat := mesh.get_blend_shape_value(mesh.find_blend_shape_by_name(&"BuccalPump"))
            values = Vector3(intake, throat, seal)
        else:
            assert(is_equal_approx(values.x, intake) and is_equal_approx(values.z, seal))
    return values


func exercise_fishing() -> Dictionary:
    var actor := FISHING.new()
    world.add_child(actor)
    assert(actor.configure(SPECIES) and actor.ready_model)
    assert(weights(actor.model) == Vector3.ZERO)
    var recipe: Dictionary = FINAL.new().mouth_recipe(SPECIES)
    var point := Vector3(recipe.position_native[0], recipe.position_native[1], recipe.position_native[2])
    assert(actor.mouth_vertex.distance_to(point) < .0000001)
    var hook := Vector3(.32,.58,.23)
    var checked := []
    for action in ["Swim", "Turn", "Ascend", "Dive"]:
        actor.animate(.47, action)
        assert(weights(actor.model) == Vector3.ZERO)
        actor.place_hook(hook, Vector3.LEFT)
        assert(actor.mouth_world().distance_to(hook) < .00001)
        checked.append(action)
    actor.free()
    return {"shape_weights_zero":true, "original_upper_lip":true, "hook_placement_actions":checked}
