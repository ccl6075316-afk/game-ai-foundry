extends SceneTree
## Complete GLB cold reader. No mesh packing, static patches, atlas recoloring or asset writes.
var config: Dictionary = {}
var model: Node3D
var carrier: Node3D
var camera_node: Camera3D
var player: AnimationPlayer
var skeleton: Skeleton3D
var controller
var meshes: Array[MeshInstance3D] = []
var bounds := AABB()
var target := Vector3.ZERO
var yaw := 0.0
var pitch := 0.0
var distance := 1.0
var base_distance := 1.0
var motion_paused := false
var gray := false
var ready_for_input := false
var checks: Array = []
var captures: Array = []
var elapsed := 0.0
var native_clip := ""
var inventory: Dictionary = {}
var closing := false

func _initialize() -> void:
    call_deferred("run")

func run() -> void:
    var config_path := ""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--config="): config_path = arg.trim_prefix("--config=")
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(config_path))
    if not parsed is Dictionary:
        push_error("Missing prepared viewer config")
        quit(2)
        return
    config = parsed
    root.size = Vector2i(1100, 760)
    root.title = "Fish asset viewer — " + str(config.get("species", ""))
    root.window_input.connect(_input)
    root.close_requested.connect(_finish)
    var world := Node3D.new()
    root.add_child(world)
    carrier = Node3D.new()
    world.add_child(carrier)
    var document := GLTFDocument.new()
    var state := GLTFState.new()
    var load_error := document.append_from_file(str(config.model), state)
    _check("direct_glb_load", load_error == OK)
    if load_error != OK:
        _finish()
        return
    model = document.generate_scene(state)
    _check("complete_scene_generated", model != null)
    if model == null:
        _finish()
        return
    carrier.add_child(model)
    model.scale = _v(config.model_scale)
    _collect(model)
    _check("runtime_meshes_present", not meshes.is_empty())
    if meshes.is_empty():
        _finish()
        return
    bounds = _world_bounds()
    inventory = _inventory()
    _check("runtime_mesh_count_preserved", inventory.mesh_count == int(config.inventory.mesh_count))
    _check("runtime_surface_count_preserved", inventory.surface_count == int(config.inventory.surface_count))
    camera_node = Camera3D.new()
    world.add_child(camera_node)
    camera_node.current = true
    camera_node.fov = 38.0
    camera_node.near = maxf(bounds.size.length() * 0.0005, 0.0001)
    camera_node.far = maxf(bounds.size.length() * 100.0, 100.0)
    base_distance = maxf(bounds.size.length() / (2.0 * tan(deg_to_rad(camera_node.fov * 0.5))) * 1.3, 0.05)
    _apply_camera(config.get("camera", {}))
    var environment := WorldEnvironment.new()
    environment.environment = Environment.new()
    environment.environment.background_mode = Environment.BG_COLOR
    environment.environment.background_color = Color(0.055, 0.075, 0.095)
    environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color = Color.WHITE
    environment.environment.ambient_light_energy = 0.65
    world.add_child(environment)
    var light := DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-35, -35, 0)
    light.light_energy = 1.1
    world.add_child(light)
    var label := Label.new()
    label.text = "Drag: orbit   Right drag: pan   Wheel: zoom   Space: pause   G: gray   0: frame   H/M: configured focus\nOriginal complete GLB | Visual review: pending | Part diagnostic: disabled (no verified recipe)"
    label.position = Vector2(12, 12)
    root.add_child(label)
    _start_native()
    if config.get("controller") != null:
        _configure_controller()
    ready_for_input = true
    set_auto_accept_quit(false)
    if config.mode == "smoke":
        await _smoke()
        _finish()
    elif config.mode == "capture":
        await _capture_declared()
        _finish()

func _collect(node: Node) -> void:
    if node is MeshInstance3D: meshes.append(node)
    if node is AnimationPlayer and player == null: player = node
    if node is Skeleton3D and skeleton == null: skeleton = node
    for child in node.get_children(): _collect(child)

func _world_bounds() -> AABB:
    var result := meshes[0].global_transform * meshes[0].get_aabb()
    for mesh in meshes: result = result.merge(mesh.global_transform * mesh.get_aabb())
    return result

func _inventory() -> Dictionary:
    var surfaces := 0
    var vertices := 0
    for mesh in meshes:
        surfaces += mesh.mesh.get_surface_count()
        for surface in mesh.mesh.get_surface_count():
            vertices += mesh.mesh.surface_get_array_len(surface)
    return {"mesh_count": meshes.size(), "surface_count": surfaces, "vertices": vertices, "bone_count": skeleton.get_bone_count() if skeleton else 0}

func _v(values: Array) -> Vector3:
    return Vector3(float(values[0]), float(values[1]), float(values[2]))

func _focus(value: Dictionary) -> Vector3:
    var point := _v(value.get("position", [0.5, 0.5, 0.5]))
    if value.get("mode", "bbox_relative") == "model": return model.global_transform * point
    return bounds.position + bounds.size * point

func _apply_camera(value: Dictionary) -> void:
    bounds = _world_bounds()
    target = _focus(value.get("focus", {"mode":"bbox_relative", "position":[0.5,0.5,0.5]}))
    yaw = deg_to_rad(float(value.get("yaw_degrees", 0.0)))
    pitch = clampf(deg_to_rad(float(value.get("pitch_degrees", 0.0))), -1.5, 1.5)
    distance = base_distance * float(value.get("distance_scale", 1.0))
    _update_camera()

func _update_camera() -> void:
    camera_node.position = target + Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
    camera_node.look_at(target, Vector3.UP)

func _start_native() -> void:
    if player == null: return
    native_clip = str(config.get("native_clip", ""))
    if native_clip.is_empty():
        for clip in player.get_animation_list():
            if clip != "RESET":
                native_clip = clip
                break
    if not native_clip.is_empty() and player.has_animation(native_clip):
        player.play(native_clip)
        player.advance(0.0)
        player.pause()

func _configure_controller() -> void:
    var entry: Dictionary = config.controller
    var script = load(str(entry.runtime))
    _check("controller_script_loaded", script != null)
    if script == null: return
    controller = script.new()
    if not controller.has_method("configure") or not controller.has_method("step") or not controller.has_method("set_action") or player == null or skeleton == null:
        _check("controller_api_and_rig", false)
        controller = null
        return
    var profile = JSON.parse_string(FileAccess.get_file_as_string(str(entry.profile)))
    var result: Dictionary = controller.configure(carrier, model, player, skeleton, profile)
    _check("controller_configured", result.get("ok", false))
    if not result.get("ok", false):
        controller = null
        return
    _check("controller_action_supported", controller.set_action(str(entry.action)))

func _advance(delta: float) -> void:
    elapsed += delta
    if controller != null:
        controller.step(delta)
    elif player != null and not native_clip.is_empty():
        player.play(native_clip)
        player.advance(delta)
        player.pause()

func _process(delta: float) -> bool:
    if ready_for_input and config.mode == "interactive" and not motion_paused: _advance(delta)
    return false

func _input(event: InputEvent) -> bool:
    if not ready_for_input: return false
    if event is InputEventMouseMotion:
        if event.button_mask & MOUSE_BUTTON_MASK_LEFT:
            yaw -= event.relative.x * 0.008
            pitch = clampf(pitch + event.relative.y * 0.008, -1.5, 1.5)
        elif event.button_mask & MOUSE_BUTTON_MASK_RIGHT:
            target += (-camera_node.global_basis.x * event.relative.x + camera_node.global_basis.y * event.relative.y) * distance * 0.0015
        _update_camera()
    if event is InputEventMouseButton and event.pressed:
        if event.button_index == MOUSE_BUTTON_WHEEL_UP: distance *= 0.85
        if event.button_index == MOUSE_BUTTON_WHEEL_DOWN: distance *= 1.15
        distance = clampf(distance, base_distance * 0.02, base_distance * 30.0)
        _update_camera()
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode == KEY_SPACE: motion_paused = not motion_paused
        if event.keycode == KEY_0: _apply_camera(config.get("camera", {}))
        if event.keycode == KEY_G: _toggle_gray()
        if event.keycode in [KEY_H, KEY_M]:
            var key := "head" if event.keycode == KEY_H else "mouth"
            if config.focuses.has(key):
                target = _focus(config.focuses[key])
                _update_camera()
        if event.keycode == KEY_ESCAPE: _finish()
    return false

func _toggle_gray() -> void:
    gray = not gray
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(0.65, 0.67, 0.7)
    material.roughness = 1.0
    for mesh in meshes: mesh.material_override = material if gray else null

func _pose_signature() -> Array:
    var result: Array = []
    for node in model.find_children("*", "Node3D", true, false): result.append(node.transform)
    if skeleton:
        for bone in skeleton.get_bone_count(): result.append(skeleton.get_bone_pose(bone))
    result.append(carrier.transform)
    return result

func _smoke() -> void:
    await process_frame
    var before := camera_node.transform
    var event := InputEventMouseMotion.new()
    event.button_mask = MOUSE_BUTTON_MASK_LEFT
    event.relative = Vector2(30, 12)
    _input(event)
    _check("orbit_changes_camera", not before.is_equal_approx(camera_node.transform))
    var old_target := target
    event.button_mask = MOUSE_BUTTON_MASK_RIGHT
    _input(event)
    _check("pan_changes_target", not old_target.is_equal_approx(target))
    var old_distance := distance
    var wheel := InputEventMouseButton.new()
    wheel.pressed = true
    wheel.button_index = MOUSE_BUTTON_WHEEL_UP
    _input(wheel)
    _check("zoom_changes_distance", distance < old_distance)
    if player != null and not native_clip.is_empty():
        # Exercise the exported native clip separately from the optional controller.
        var saved = controller
        controller = null
        var pose := _pose_signature()
        for step_index in 17: _advance(1.0 / 60.0)
        _check("native_clip_changes_pose", pose != _pose_signature())
        controller = saved
    if config.get("controller") != null:
        _check("requested_controller_available", controller != null)
        if controller != null:
            var pose := _pose_signature()
            for step_index in 17: _advance(1.0 / 60.0)
            _check("controller_changes_pose", pose != _pose_signature())
    _check("mesh_surface_inventory_unchanged", _inventory() == inventory)
    _apply_camera(config.get("camera", {}))
    await _save_capture("smoke-overview")

func _capture_declared() -> void:
    for capture in config.captures:
        # Each declared time is absolute; reject backwards time instead of pretending to reset a controller.
        var at := float(capture.get("time_seconds", elapsed))
        if at < elapsed:
            _check("capture_times_monotonic", false)
            continue
        while elapsed + 0.00001 < at: _advance(minf(1.0 / 60.0, at - elapsed))
        var settings: Dictionary = config.get("camera", {}).duplicate(true)
        settings.merge(capture, true)
        _apply_camera(settings)
        await _save_capture(str(capture.name))

func _save_capture(name: String) -> void:
    if DisplayServer.get_name() == "headless":
        _check("gpu_capture_available", false)
        return
    await process_frame
    await RenderingServer.frame_post_draw
    var path: String = str(config.output).path_join(name + ".png")
    var image := root.get_texture().get_image()
    var result := image.save_png(path)
    _check("capture_" + name, result == OK)
    if result == OK: captures.append({"name":name, "path":path, "sha256":FileAccess.get_sha256(path), "time_seconds":elapsed, "visual_review":"pending", "camera":{"target":[target.x,target.y,target.z],"yaw":yaw,"pitch":pitch,"distance":distance}})

func _check(name: String, passed: bool) -> void:
    checks.append({"name":name,"passed":passed})

func _finish() -> void:
    if closing: return
    closing = true
    var passed := not checks.is_empty()
    for check in checks: passed = passed and check.passed
    var report := {"schema_version":1, "kind":"fish_asset_viewer_validation", "ok":passed, "status":"done" if passed else "failed", "next_action":"human_review", "model":config.get("model"), "model_sha256":config.get("model_sha256"), "spec_sha256":config.get("spec_sha256"), "model_role":config.get("model_role"), "mode":config.get("mode"), "runtime_inventory":inventory, "checks":checks, "captures":captures, "visual_review":"pending", "part_diagnostics":{"enabled":false,"reason":"No verified part diagnostic recipe configured"}, "limitations":["Viewer technical smoke is not fish acceptance, fin validation or SOP approval", "Bounding box uses imported rest geometry; animation may extend outside it"]}
    var file := FileAccess.open(str(config.output).path_join("viewer.validation.json"), FileAccess.WRITE)
    if file: file.store_string(JSON.stringify(report, "  ") + "\n")
    quit(0 if passed else 1)
