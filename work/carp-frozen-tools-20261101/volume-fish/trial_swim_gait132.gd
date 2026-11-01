extends SceneTree
## External opt-in trial. Run under the actual game project; see launcher --help.

var foundry: String
var output: String
var mode: String
var config: Dictionary
var adapter_script
var factory
var world: Node3D
var entries: Array = []
var gait
var camera: Camera3D
var status: Label
var trial_paused := false
var elapsed := 0.0
var orbit := 0.0
var pitch := 0.12
var zoom := 0.85
var trace: Array = []
var capture_index := 0
var capture_frames := 240
var failures: Array = []

func _initialize() -> void:
    var args := OS.get_cmdline_user_args()
    if args.size() < 3:
        push_error("Expected foundry-root output-directory qa|preview|capture")
        quit(1)
        return
    foundry = args[0]
    output = args[1]
    mode = args[2]
    config = JSON.parse_string(FileAccess.get_file_as_string(foundry.path_join("resources/volume-fish/motion/bluegill-intermittent-132.json")))
    adapter_script = load(foundry.path_join("resources/runtime/godot/IntermittentFishGait.gd"))
    DirAccess.make_dir_recursive_absolute(output)
    call_deferred("run")

func _save(name: String, data: Variant) -> void:
    var file := FileAccess.open(output.path_join(name), FileAccess.WRITE)
    file.store_string(JSON.stringify(data, "  "))
    file.close()

func _check(condition: bool, message: String) -> void:
    if not condition: failures.append(message)

func _inputs() -> Dictionary:
    var paths := {"adapter":"resources/runtime/godot/IntermittentFishGait.gd", "gait_config":"resources/volume-fish/motion/bluegill-intermittent-132.json", "trial":"resources/scripts/volume-fish/trial_swim_gait132.gd"}
    var result := {}
    for key in paths:
        result[key] = {"path":foundry.path_join(paths[key]),"sha256":FileAccess.get_sha256(foundry.path_join(paths[key]))}
    for path in ["res://assets/models/fish/bluegill.glb", "res://scripts/aquarium/FoundryFishMotion.gd", "res://scripts/aquarium/FishSurfaceOwnership.gd", "res://assets/models/fish/motion/motion.json"]:
        result[path] = FileAccess.get_sha256(path)
    return result

func _setup() -> void:
    world = Node3D.new()
    root.add_child(world)
    # Use the exhibit's exact imported model, native pixel material ownership,
    # body opacity and scaling. Do not instantiate its 25-fish UI/world.
    factory = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()

func _spawn(origin: Vector3) -> Dictionary:
    var profile: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles.bluegill
    factory._add_fish(world, "bluegill", float(profile.real_length_cm) / 100.0, profile, origin)
    return factory.fish[-1]

func _make_gait(entry: Dictionary):
    var wrapper = adapter_script.new()
    var clip: Animation = entry.player.get_animation(entry.profile.base_clip)
    var configured: Dictionary = wrapper.configure(entry.controller, config, clip.length)
    assert(configured.ok, str(configured))
    return wrapper

func run() -> void:
    _setup()
    if mode == "qa":
        await _qa()
        return
    entries = [_spawn(Vector3(0.0, 0.21, 0.0)), _spawn(Vector3(0.0, -0.21, 0.0))]
    gait = _make_gait(entries[1])
    _build_view()
    if mode == "capture":
        await _capture()
    else:
        process_frame.connect(_update)

func _case(hz: int) -> Dictionary:
    var entry := _spawn(Vector3.ZERO)
    var wrapper = _make_gait(entry)
    var clip: Animation = entry.player.get_animation(entry.profile.base_clip)
    var rows: Array = []
    var min_speed := INF
    var max_speed := 0.0
    var max_phase_error := 0.0
    var max_fin_phase_error := 0.0
    var max_jump := 0.0
    var previous_clock := 0.0
    var previous_head := Vector3.ZERO
    var previous_time := 0.0
    var previous_poses: Dictionary = entry.controller.snapshot().bone_poses
    var coast: Array = []
    var propel: Array = []
    var max_frequency := 0.0
    var max_quaternion_error := 0.0
    var max_action_boundary_pose_error := 0.0
    var maximum_adjacent_pose_angle := 0.0
    var normalized_propel: Array = []
    var normalized_coast: Array = []
    var measured_propel_wave: Array = []
    var measured_coast_wave: Array = []
    var max_wave_reconstruction_error := 0.0
    var max_normalized_travel_error := 0.0
    var actions := ["Swim", "Turn", "Ascend", "Dive", "Swim"]
    for frame in 20 * hz:
        if frame % (4 * hz) == 0:
            var before: Dictionary = entry.controller.snapshot().bone_poses
            _check(wrapper.set_action(actions[frame / (4 * hz)]), "Action rejected")
            var after: Dictionary = entry.controller.snapshot().bone_poses
            for bone in before:
                for axis in 4: max_action_boundary_pose_error = maxf(max_action_boundary_pose_error, absf(float(before[bone][axis]) - float(after[bone][axis])))
        wrapper.step(1.0 / hz)
        var pose: Dictionary = entry.controller.snapshot()
        var state: Dictionary = wrapper.snapshot()
        var clock := float(pose.body_clock)
        max_phase_error = maxf(max_phase_error, absf(clock / clip.length - float(state.wall_seconds) * float(config.body_hz)))
        max_fin_phase_error = maxf(max_fin_phase_error, absf(float(pose.fin_clock) / clip.length - float(state.wall_seconds) * float(config.fin_hz)))
        max_jump = maxf(max_jump, absf((clock - previous_clock) / clip.length - float(config.body_hz) / hz))
        previous_clock = clock
        _check(pose.inside_envelope, "Candidate left tank envelope")
        for q in pose.bone_poses.values():
            var norm := 0.0
            for v in q:
                _check(is_finite(float(v)), "Nonfinite quaternion")
                norm += float(v) * float(v)
            max_quaternion_error = maxf(max_quaternion_error, absf(norm - 1.0))
        for bone in pose.bone_poses:
            var qa: Array = previous_poses[bone]
            var qb: Array = pose.bone_poses[bone]
            var difference := Quaternion(qa[0], qa[1], qa[2], qa[3]).inverse() * Quaternion(qb[0], qb[1], qb[2], qb[3])
            maximum_adjacent_pose_angle = maxf(maximum_adjacent_pose_angle, 2.0 * atan2(Vector3(difference.x, difference.y, difference.z).length(), absf(difference.w)))
        previous_poses = pose.bone_poses
        for v in pose.motion_controls.values(): _check(is_finite(float(v)), "Nonfinite control")
        max_frequency = maxf(max_frequency, maxf(float(pose.motion_controls.body_frequency), float(pose.motion_controls.fin_frequency)))
        var raw: Array = pose.head_path_local
        var head := Vector3(raw[0], raw[1], raw[2])
        var speed := 0.0 if frame == 0 else head.distance_to(previous_head) * hz
        previous_head = head
        if frame > hz:
            min_speed = minf(min_speed, speed)
            max_speed = maxf(max_speed, speed)
        var cycle_phase := fposmod(float(state.wall_seconds), float(config.cycle_seconds))
        var total_wave := 0.0
        for i in entry.controller._bones.size():
            var overlay: Dictionary = entry.controller._bone_overlay[i]
            var neutral: Quaternion = entry.controller._rest_rotations[i].slerp(entry.controller._base_rotations[i], float(entry.profile.base_body_gain) * float(state.body_amplitude))
            var zero_wave: Quaternion = neutral * Quaternion(entry.controller._yaw_axes[i], float(overlay.yaw_radians)) * Quaternion(entry.controller._pitch_axes[i], float(overlay.pitch_radians))
            var actual: Quaternion = entry.skeleton.get_bone_pose_rotation(entry.controller._bones[i])
            var measured: Quaternion = zero_wave.inverse() * actual
            var wave_angle := 2.0 * atan2(Vector3(measured.x, measured.y, measured.z).length(), absf(measured.w))
            total_wave += wave_angle
            max_wave_reconstruction_error = maxf(max_wave_reconstruction_error, absf(wave_angle - absf(float(overlay.wave_radians) * float(state.body_amplitude))))
        if frame > 0 and frame < 4 * hz:
            # Divide out native elliptical path speed; a disabled gait must fail.
            var native_speed: float = entry.controller._velocity((previous_time + float(pose.time)) * 0.5).length()
            var normalized_speed := speed / native_speed
            var actual_travel_ratio := (float(pose.time) - previous_time) * hz
            max_normalized_travel_error = maxf(max_normalized_travel_error, absf(normalized_speed - actual_travel_ratio))
            if cycle_phase > 0.4 and cycle_phase < float(config.propel_seconds) - 0.2: normalized_propel.append(normalized_speed)
            if cycle_phase > float(config.propel_seconds) + 0.5: normalized_coast.append(normalized_speed)
        previous_time = float(pose.time)
        if cycle_phase > 0.4 and cycle_phase < float(config.propel_seconds) - 0.2: propel.append(state.body_amplitude)
        if cycle_phase > float(config.propel_seconds) + 0.5: coast.append(state.body_amplitude)
        if cycle_phase > 0.4 and cycle_phase < float(config.propel_seconds) - 0.2: measured_propel_wave.append(total_wave)
        if cycle_phase > float(config.propel_seconds) + 0.5: measured_coast_wave.append(total_wave)
        if frame % hz == hz - 1:
            rows.append({"seconds":state.wall_seconds,"gait":state,"body_clock":clock,"fin_clock":pose.fin_clock,"position":pose.position,"bone_poses":pose.bone_poses,"action":pose.action,"controls":pose.motion_controls})
    var result := {"hz":hz,"samples":rows,"minimum_path_speed_m_s":min_speed,"maximum_path_speed_m_s":max_speed,"maximum_body_phase_error_cycles":max_phase_error,"maximum_fin_phase_error_cycles":max_fin_phase_error,"maximum_frame_phase_increment_error_cycles":max_jump,"maximum_action_boundary_pose_error":max_action_boundary_pose_error,"maximum_frequency_control":max_frequency,"maximum_quaternion_norm_error":max_quaternion_error,"propel_mean_amplitude":_mean(propel),"settled_coast_mean_amplitude":_mean(coast),"final":wrapper.snapshot()}
    result.merge({"maximum_adjacent_actual_bone_angle_rad":maximum_adjacent_pose_angle,"normalized_swim_propel_speed":_mean(normalized_propel),"normalized_swim_coast_speed":_mean(normalized_coast),"maximum_normalized_spatial_vs_clock_travel_error":max_normalized_travel_error,"actual_propel_wave_sum_radians":_mean(measured_propel_wave),"actual_coast_wave_sum_radians":_mean(measured_coast_wave),"maximum_actual_wave_reconstruction_error_radians":max_wave_reconstruction_error})
    factory.fish.erase(entry)
    entry.carrier.queue_free()
    return result

func _mean(values: Array) -> float:
    var total := 0.0
    for v in values: total += float(v)
    return total / maxi(1, values.size())

func _qa() -> void:
    var case30 := _case(30)
    await process_frame
    var case60 := _case(60)
    var maximum_pose_difference := 0.0
    var maximum_position_difference := 0.0
    for i in case30.samples.size():
        var a: Dictionary = case30.samples[i]
        var b: Dictionary = case60.samples[i]
        for bone in a.bone_poses:
            for axis in 4: maximum_pose_difference = maxf(maximum_pose_difference, absf(float(a.bone_poses[bone][axis]) - float(b.bone_poses[bone][axis])))
        for axis in 3: maximum_position_difference = maxf(maximum_position_difference, absf(float(a.position[axis]) - float(b.position[axis])))
    for item in [case30, case60]:
        _check(item.maximum_path_speed_m_s > item.minimum_path_speed_m_s * 1.5, "Path speed did not vary")
        _check(item.propel_mean_amplitude > item.settled_coast_mean_amplitude * 4.0, "Coast wave did not relax")
        _check(item.maximum_body_phase_error_cycles < 0.000001, "Body phase drift")
        _check(item.maximum_fin_phase_error_cycles < 0.000001, "Fin phase drift")
        _check(item.maximum_frame_phase_increment_error_cycles < 0.000001, "Phase jump at action/gait boundary")
        _check(item.maximum_frequency_control <= 3.0, "Frequency silently clipped")
        _check(item.maximum_quaternion_norm_error < 0.00001, "Invalid rotation")
        _check(item.maximum_action_boundary_pose_error < 0.00001, "Pose jumps at zero-delta action switch")
        _check(item.maximum_adjacent_actual_bone_angle_rad < 0.25, "Excessive adjacent skeleton pose jump")
        _check(item.normalized_swim_propel_speed > item.normalized_swim_coast_speed * 1.4, "No gait-coupled normalized speed change")
        _check(item.maximum_normalized_spatial_vs_clock_travel_error < 0.002, "Spatial travel disagrees with gait clock")
        _check(item.actual_propel_wave_sum_radians > item.actual_coast_wave_sum_radians * 4.0, "Actual skeleton wave did not relax")
        _check(item.maximum_actual_wave_reconstruction_error_radians < 0.00001, "Actual wave differs from independent propulsion envelope")
        _check(item.final.substeps == 2400 and item.final.dropped_seconds == 0.0, "Unexpected substep/catchup loss")
    _check(maximum_pose_difference < 0.000001 and maximum_position_difference < 0.000001, "30/60 Hz mismatch")
    # Stalls have bounded work and explicitly recorded lost time.
    var entry := _spawn(Vector3.ZERO)
    var wrapper = _make_gait(entry)
    var invalid = adapter_script.new()
    _check(not invalid.configure(entry.controller, config, NAN).ok, "NaN clip length accepted")
    var bad_config := config.duplicate(true)
    bad_config.body_hz = NAN
    _check(not invalid.configure(entry.controller, bad_config, 2.4166667).ok, "NaN oscillator rate accepted")
    var previous: float = entry.controller._profile.actions.Swim.clip_speed
    entry.controller._profile.actions.Swim.clip_speed = 0.2
    _check(not invalid.configure(entry.controller, config, 2.4166667).ok, "Incompatible slow clip rate accepted")
    entry.controller._profile.actions.Swim.clip_speed = previous
    wrapper.step(2.0)
    _check(wrapper.substeps == 30 and absf(wrapper.dropped_seconds - 1.75) < 0.000001, "Unbounded catch-up")
    var report := {"schema_version":1,"ok":failures.is_empty(),"command":"fish.swim-gait132.qa","stage":"validate","status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","inputs":_inputs(),"summary":{"cases":[case30,case60],"maximum_30_60_pose_component_difference":maximum_pose_difference,"maximum_30_60_position_difference_m":maximum_position_difference,"stall_case":wrapper.snapshot(),"production_installed":false,"scope":"Actual imported bluegill and production materials/controller; candidate wall-time oscillator, four actions and transitions, fixed-step numerical checks. Not a fin-contact/body-integrity/biological/visual acceptance or performance benchmark."},"failures":failures}
    _save("gait.validation.json", report)
    print("GAIT132_QA ", report.ok, " pose difference=", maximum_pose_difference, " phase error=", case60.maximum_body_phase_error_cycles)
    factory.free()
    quit(0 if report.ok else 1)

func _build_view() -> void:
    root.size = Vector2i(1120, 840)
    DisplayServer.window_set_title("Bluegill gait 132 — isolated A/B trial")
    root.window_input.connect(_input)
    var env := WorldEnvironment.new()
    env.environment = Environment.new()
    env.environment.background_mode = Environment.BG_COLOR
    env.environment.background_color = Color("16313c")
    env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.environment.ambient_light_color = Color("d6e8e7")
    env.environment.ambient_light_energy = 0.85
    world.add_child(env)
    var light := DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-55, -25, 0)
    light.light_color = Color("e3f6ff")
    light.light_energy = 0.6
    world.add_child(light)
    camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.near = 0.01
    world.add_child(camera)
    _camera()
    var ui := CanvasLayer.new()
    root.add_child(ui)
    var box := VBoxContainer.new()
    box.position = Vector2(20, 14)
    ui.add_child(box)
    var title := Label.new()
    title.text = "BLUEGILL / Lepomis macrochirus — opt-in gait 132\nA · installed baseline   |   B · propel → coast (engineering trial)"
    title.add_theme_font_size_override("font_size", 21)
    box.add_child(title)
    var row := HBoxContainer.new()
    box.add_child(row)
    for name in ["Pause", "Restart", "Swim", "Turn", "Ascend", "Dive", "Side", "Oblique", "Top"]:
        var button := Button.new()
        button.text = name
        button.pressed.connect(_button.bind(name))
        row.add_child(button)
    status = Label.new()
    status.add_theme_font_size_override("font_size", 17)
    box.add_child(status)
    var foot := Label.new()
    foot.text = "Same production model/materials. No production changes.\nDrag: orbit · wheel: zoom · Space: pause · R: restart · Esc: close\nNumeric gait settings are hypotheses, not species measurements."
    foot.position = Vector2(20, 752)
    ui.add_child(foot)
    for pair in [["A",0.21],["B",-0.21]]:
        var label := Label3D.new()
        label.text = pair[0]
        label.position = Vector3(-0.38, float(pair[1]), 0.0)
        label.font_size = 64
        label.pixel_size = 0.001
        label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
        world.add_child(label)

func _camera() -> void:
    camera.size = zoom
    camera.position = Vector3(sin(orbit) * cos(pitch), sin(pitch), cos(orbit) * cos(pitch)) * 2.0
    camera.look_at(Vector3.ZERO)

func _button(name: String) -> void:
    if name == "Pause": trial_paused = not trial_paused
    elif name == "Restart":
        entries[0].controller.set_action("Swim", true)
        entries[0].controller.step(0.0)
        gait.restart()
        elapsed = 0.0
    elif name in ["Side", "Oblique", "Top"]:
        orbit = 0.0 if name != "Oblique" else 0.55
        pitch = 1.48 if name == "Top" else 0.12
        _camera()
    else:
        entries[0].controller.set_action(name)
        gait.set_action(name)

func _input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode == KEY_SPACE: _button("Pause")
        elif event.keycode == KEY_R: _button("Restart")
        elif event.keycode == KEY_ESCAPE: quit()
    if event is InputEventMouseMotion and event.button_mask & MOUSE_BUTTON_MASK_LEFT:
        orbit -= event.relative.x * 0.006
        pitch = clampf(pitch + event.relative.y * 0.006, -1.4, 1.48)
        _camera()
    if event is InputEventMouseButton and event.pressed:
        if event.button_index == MOUSE_BUTTON_WHEEL_UP: zoom = maxf(0.45, zoom * 0.9)
        elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN: zoom = minf(1.5, zoom * 1.1)
        _camera()

func _advance(dt: float) -> void:
    entries[0].controller.step(minf(dt, 0.25))
    gait.step(dt)
    elapsed += dt
    var state: Dictionary = gait.snapshot()
    status.text = "B: %s  |  travel ×%.2f  |  body amplitude %.2f  |  body %.2f Hz / fins %.2f Hz%s" % [state.gait, state.travel_rate, state.body_amplitude, state.body_hz, state.fin_hz, "  PAUSED" if trial_paused else ""]

func _update() -> void:
    if not trial_paused: _advance(root.get_process_delta_time())

func _capture() -> void:
    DirAccess.make_dir_recursive_absolute(output.path_join("frames"))
    for frame in capture_frames:
        if frame == 120: _button("Turn")
        _advance(1.0 / 30.0)
        await process_frame
        await RenderingServer.frame_post_draw
        root.get_texture().get_image().save_png(output.path_join("frames/frame-%04d.png" % frame))
        trace.append({"frame":frame,"seconds":elapsed,"candidate":gait.snapshot(),"candidate_body_clock":entries[1].controller._body_clock,"baseline_time":entries[0].controller._time})
    _save("capture.validation.json", {"schema_version":1,"ok":true,"command":"fish.swim-gait132.capture","stage":"validate","status":"done","next_action":"human_review","inputs":_inputs(),"summary":{"frames":capture_frames,"fps":30,"renderer":RenderingServer.get_video_adapter_name(),"rendering_method":RenderingServer.get_current_rendering_method(),"sequence":"4 seconds Swim, then 4 seconds Turn; same cameras and actual production model/materials","production_installed":false,"trace":trace},"failures":[]})
    factory.free()
    quit()
