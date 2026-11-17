extends "viewer.gd"

var orbit_angle := Vector2.ZERO
var has_orbit := false
var pan_offset := Vector3.ZERO
var live_controls := false
var side_button: Button
var top_button: Button
var belly_button: Button
var close_button: Button
var whole_button: Button

func run() -> void:
    await super.run()
    if closing:
        return

    var controls := play_button.get_parent()
    var sidebar := pause_button.get_parent()
    for child in sidebar.get_children():
        if child is HBoxContainer:
            for button in child.get_children():
                if button is Button and button.text == "俯视":
                    child.hide()
                    break

    var framing := controls.get_child(progress.get_index() - 1)
    whole_button = framing.get_child(0) as Button
    close_button = framing.get_child(1) as Button
    var angles := HBoxContainer.new()
    controls.add_child(angles)
    controls.move_child(angles, progress.get_index())
    side_button = _button(angles, "侧面", func(): _view(0., 0.))
    _button(angles, "正面", func(): _view(90., 0.))
    top_button = _button(angles, "俯视", func(): _view(0., 90.))
    belly_button = _button(angles, "腹视", func(): _view(0., -90.))
    live_controls = true

    if "--camera-test" in OS.get_cmdline_user_args():
        await verify_camera_controls()
        _finish()
        return

    await _save_capture("window-controls")
    write("camera-startup.validation.json", {
        "ok": checks.all(func(item): return item.passed),
        "pid": OS.get_process_id(),
        "screen": root.current_screen,
        "model_sha256": FileAccess.get_sha256(config.model),
        "captures": captures,
    })

func _apply_camera(value: Dictionary) -> void:
    if not live_controls:
        super._apply_camera(value)
        return
    pan_offset = Vector3.ZERO
    if value.is_empty():
        has_orbit = false
        zoom_factor = 1.
    else:
        has_orbit = true
        orbit_angle = Vector2(
            deg_to_rad(value.yaw_degrees),
            deg_to_rad(value.pitch_degrees)
        )
    update_view()

func _update_camera() -> void:
    if not live_controls:
        super._update_camera()
        return
    # The replay updates the follow target and framing on every pose.
    target += pan_offset
    if has_orbit:
        yaw = orbit_angle.x
        pitch = orbit_angle.y
    var orientation := Basis.from_euler(Vector3(-pitch, yaw, 0.))
    camera_node.transform = Transform3D(orientation, target + orientation.z * distance)

func _input(event: InputEvent) -> bool:
    if not live_controls:
        return super._input(event)
    if event is InputEventMouseMotion:
        if event.position.x < sidebar_width:
            return false
        if event.button_mask & MOUSE_BUTTON_MASK_LEFT:
            has_orbit = true
            orbit_angle = Vector2(yaw - event.relative.x * .008,
                clampf(pitch + event.relative.y * .008, -PI / 2., PI / 2.))
        elif event.button_mask & MOUSE_BUTTON_MASK_RIGHT:
            var units_per_pixel := camera_node.size / float(viewport.size.x)
            pan_offset += (-camera_node.basis.x * event.relative.x
                + camera_node.basis.y * event.relative.y) * units_per_pixel
        else:
            return false
        update_view()
        return true
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode == KEY_0:
            _apply_camera({})
            return true
        if event.keycode in [KEY_H, KEY_M]:
            near_mouth = true
            update_view()
            return true
    return super._input(event)

func record_playback_view(name: String, expected_direction: Vector3) -> void:
    var start := stamp
    var previous_position := carrier.position
    var previous_camera_position := camera_node.position
    for frame in range(30):
        _process(1. / 60.)
    _check(name + "_playback_advances", playing and stamp > start + .45)
    _check(name + "_camera_follows", not carrier.position.is_equal_approx(previous_position)
        and not camera_node.position.is_equal_approx(previous_camera_position))
    _check(name + "_angle_persists", camera_node.basis.z.is_equal_approx(expected_direction))

func verify_camera_controls() -> void:
    for index in range(branch.item_count):
        branch.select(index)
        branch.item_selected.emit(index)
        var label := "large" if large else "small"
        top_button.pressed.emit()
        record_playback_view(label + "_top", Vector3.UP)
        await _save_capture(label + "-playing-top")
        _check(label + "_top_at_capture", playing and camera_node.basis.z.is_equal_approx(Vector3.UP))
        close_button.pressed.emit()
        record_playback_view(label + "_close_top", Vector3.UP)
        await _save_capture(label + "-playing-close-top")

        belly_button.pressed.emit()
        whole_button.pressed.emit()
        record_playback_view(label + "_belly", Vector3.DOWN)

        side_button.pressed.emit()
        record_playback_view(label + "_side", Vector3.BACK)
        var motion := InputEventMouseMotion.new()
        motion.position = Vector2(sidebar_width + 250., 180.)
        motion.relative = Vector2(45., 35.)
        motion.button_mask = MOUSE_BUTTON_MASK_LEFT
        _check(label + "_drag_handled", _input(motion))
        var dragged_direction := camera_node.basis.z
        _check(label + "_drag_rotates", not dragged_direction.is_equal_approx(Vector3.BACK))
        record_playback_view(label + "_drag", dragged_direction)

        motion.button_mask = MOUSE_BUTTON_MASK_RIGHT
        _check(label + "_pan_handled", _input(motion) and pan_offset.length() > .01)
        var previous_pan := pan_offset
        var previous_zoom := zoom_factor
        var wheel := InputEventMouseButton.new()
        wheel.position = motion.position
        wheel.button_index = MOUSE_BUTTON_WHEEL_UP
        wheel.pressed = true
        _check(label + "_wheel_zoom", _input(wheel) and zoom_factor < previous_zoom)
        record_playback_view(label + "_pan_zoom", dragged_direction)
        _check(label + "_pan_persists", pan_offset.is_equal_approx(previous_pan))

        var reset := InputEventKey.new()
        reset.pressed = true
        reset.keycode = KEY_0
        _check(label + "_reset_keeps_playing", _input(reset) and playing and not has_orbit
            and pan_offset.is_zero_approx() and zoom_factor == 1.)
    playing = false
    write("camera-controls.validation.json", {
        "ok": checks.all(func(item): return item.passed),
        "checks": checks,
        "captures": captures,
        "model_sha256": FileAccess.get_sha256(config.model),
    })
