extends SceneTree
## Interactive behavior smoke only; does not validate fish geometry or collision.
var viewer
var output := ""
var initial_count := 25
var checks: Array = []
var before: Dictionary = {}
var test_started := 0

func _initialize() -> void:
    call_deferred("run")

func run() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--test-output="): output = arg.trim_prefix("--test-output=")
        elif arg.begins_with("--count="): initial_count = arg.get_slice("=", 1).to_int()
    var allowed := ProjectSettings.globalize_path("res://../plans/reviews/fish-school-v1").simplify_path() + "/"
    if output.is_empty() or not output.is_absolute_path() or output != output.simplify_path() or not output.begins_with(allowed):
        push_error("--test-output must be absolute inside fish-school-v1")
        quit(2)
        return
    if initial_count < 25 or initial_count > 112 or initial_count % 25 != 0 or DirAccess.make_dir_recursive_absolute(output) != OK:
        push_error("Invalid initial count or unwritable test output")
        quit(2)
        return
    test_started = Time.get_ticks_usec()
    viewer = load("res://scenes/fish_school_review.tscn").instantiate()
    viewer.count = initial_count
    before = viewer._bindings()
    root.add_child(viewer)
    if not await _wait_loaded():
        _check("initial_load", false)
        await _finish()
        return
    viewer.set_process(false)
    _check("interactive_not_benchmark", not viewer.benchmark)
    _check("initial_roster", _fish_match(initial_count))
    var old_camera: Transform3D = viewer.camera.transform
    _mouse(MOUSE_BUTTON_LEFT, true)
    var motion := InputEventMouseMotion.new()
    motion.relative = Vector2(30, -12)
    viewer._unhandled_input(motion)
    _mouse(MOUSE_BUTTON_LEFT, false)
    _check("mouse_orbit", not viewer.camera.transform.is_equal_approx(old_camera))
    var old_target: Vector3 = viewer.target
    _mouse(MOUSE_BUTTON_RIGHT, true)
    motion.relative = Vector2(18, 8)
    viewer._unhandled_input(motion)
    _mouse(MOUSE_BUTTON_RIGHT, false)
    _check("mouse_pan", not viewer.target.is_equal_approx(old_target))
    var old_distance: float = viewer.distance
    _mouse(MOUSE_BUTTON_WHEEL_UP, true)
    _check("mouse_zoom", viewer.distance < old_distance)
    var positions: PackedVector3Array = viewer.simulation.positions.duplicate()
    _check("pause_button_found", _button("暂停 / 继续"))
    viewer._process(1.0 / 60.0)
    _check("paused_positions_preserved", viewer.paused and viewer.simulation.positions == positions)
    _button("暂停 / 继续")
    _check("resume_button", not viewer.paused)
    var old_mode: String = viewer.mode
    _check("tier_button_found", _button("切换全频 / 分层动作"))
    _check("tier_mode_changed", viewer.mode != old_mode)
    viewer._request_count.call_deferred(50)
    var transition_deadline := Time.get_ticks_msec() + 2000
    while viewer.count != 50 and Time.get_ticks_msec() < transition_deadline: await process_frame
    _check("count_transition_loaded", viewer.count == 50 and await _wait_loaded())
    viewer.set_process(false)
    _check("transition50_actual_species_and_lengths", _fish_match(50))
    viewer._process(1.0 / 60.0)
    if DisplayServer.get_name() != "headless":
        await RenderingServer.frame_post_draw
        var error := root.get_texture().get_image().save_png(output.path_join("interactive50.png"))
        _check("interactive_screenshot_saved", error == OK)
    else:
        _check("rendered_viewer_required", false)
    await _finish()

func _wait_loaded() -> bool:
    var deadline := Time.get_ticks_msec() + 180000
    while not viewer.loaded and Time.get_ticks_msec() < deadline:
        if not viewer.setup_error.is_empty(): return false
        await process_frame
    return viewer.loaded

func _fish_match(expected: int) -> bool:
    if viewer.entries.size() != expected or viewer.roster.size() != 25: return false
    var counts := {}
    for entry in viewer.entries:
        if not is_instance_valid(entry.model) or not is_instance_valid(entry.skeleton): return false
        if entry.model.scene_file_path != "res://assets/models/fish/" + entry.species + ".glb": return false
        if not is_equal_approx(entry.length_m, float(entry.profile.real_length_cm) / 100.0): return false
        if entry.skeleton.get_bone_count() < 1: return false
        counts[entry.species] = counts.get(entry.species, 0) + 1
    if counts.size() != 25: return false
    for species in viewer.roster:
        if counts.get(species, 0) != expected / 25: return false
    return true

func _button(label: String) -> bool:
    for button in viewer.find_children("*", "Button", true, false):
        if button.text == label:
            button.pressed.emit()
            return true
    return false

func _mouse(button: int, pressed: bool) -> void:
    var event := InputEventMouseButton.new()
    event.button_index = button
    event.pressed = pressed
    viewer._unhandled_input(event)

func _check(label: String, passed: bool) -> void:
    checks.append({"check":label,"passed":passed})

func _finish() -> void:
    var after: Dictionary = viewer._bindings()
    var changed: Array = []
    for path in before:
        if before[path] != after.get(path, ""): changed.append(path)
    for path in after:
        if not before.has(path): changed.append(path)
    _check("production_source_bindings_unchanged", changed.is_empty())
    var passed := true
    for check in checks: passed = passed and check.passed
    var report := {"schema_version":1,"command":"fish.school.viewer-smoke","stage":"validate","ok":passed,"status":"done" if passed else "failed","next_action":"human_review" if passed else "fix_input","inputs":{"initial_count":initial_count,"transition_count":50,"test_sha256":FileAccess.get_sha256(get_script().resource_path),"source_bindings_sha256":before,"changed_sources":changed},"summary":{"checks":checks,"elapsed_ms":(Time.get_ticks_usec()-test_started)/1000.0,"actual_count":viewer.entries.size(),"species_counts":viewer.inventory.get("species_counts",{}),"rendering_method":RenderingServer.get_current_rendering_method(),"display_server":DisplayServer.get_name()},"scope":"Interactive wiring and source preservation only; no model, fin, collision, new swim quality or capacity acceptance","outputs":[output.path_join("viewer.validation.json"),output.path_join("interactive50.png")],"failures":[]}
    viewer.set_process(false)
    viewer.entries.clear()
    viewer.motion_pending.clear()
    if is_instance_valid(viewer.factory):
        viewer.factory.fish.clear()
        viewer.factory.free()
        viewer.factory = null
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    viewer.queue_free()
    # Let deferred node frees and renderer resource release complete before quit.
    for frame in 3: await process_frame
    _check("viewer_nodes_released", not is_instance_valid(viewer))
    viewer = null
    passed = true
    for check in checks: passed = passed and check.passed
    report.ok = passed
    report.status = "done" if passed else "failed"
    report.next_action = "human_review" if passed else "fix_input"
    report.summary.cleanup = "Entries, detached factory, appearance templates and viewer explicitly released; inspect full process stdout for shutdown diagnostics"
    if not passed: report.failures.append({"kind":"validation","code":"viewer_check_failed","message":"Inspect named checks; no successful viewer claim"})
    var file := FileAccess.open(output.path_join("viewer.validation.json"), FileAccess.WRITE)
    if file == null:
        push_error("Cannot write viewer validation")
        quit(2)
        return
    file.store_string(JSON.stringify(report,"  ") + "\n")
    file.close()
    print("FISH_SCHOOL_VIEWER_SMOKE ", JSON.stringify({"ok":passed,"checks":checks,"report":output.path_join("viewer.validation.json")}))
    quit(0 if passed else 1)
