extends SceneTree
## Direct frozen-GLB experiment. No static builder, water, AI, collision or asset writes.
const MOTION = preload("res://scripts/aquarium/FoundryFishMotion.gd")
const MODEL_SCALE := .402819722890854
const FIXED_DELTA := 1.0 / 60.0
var model_path := ""
var output := ""
var mode := "benchmark"
var count := 1
var animated := false
var samples := 120
var warmup := 30
var view: SubViewport
var world: Node3D
var camera: Camera3D
var fish: Array[Dictionary] = []
var bound: Dictionary = {}
var inventory: Dictionary
var profile_path := "res://../../../resources/volume-fish/motion/nile_tilapia-082.json"
var init_ms := 0.0
var last_progress_usec := 0
var progress_label := "initialization"

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--model="): model_path = arg.trim_prefix("--model=").simplify_path()
		elif arg.begins_with("--output="): output = arg.trim_prefix("--output=").simplify_path()
		elif arg.begins_with("--mode="): mode = arg.trim_prefix("--mode=")
		elif arg.begins_with("--count="): count = int(arg.trim_prefix("--count="))
		elif arg.begins_with("--animated="): animated = arg.trim_prefix("--animated=") == "1"
		elif arg.begins_with("--samples="): samples = int(arg.trim_prefix("--samples="))
		elif arg.begins_with("--warmup="): warmup = int(arg.trim_prefix("--warmup="))
	assert(model_path.is_absolute_path() and FileAccess.file_exists(model_path))
	var experiment := ProjectSettings.globalize_path("res://../experiments/nile-dorsal-route-trial/round10-material-performance").simplify_path()
	assert(output.is_absolute_path() and output.begins_with(experiment + "/"))
	assert(mode in ["benchmark", "capture"] and count >= 1 and count <= 1000)
	assert(samples >= 30 and samples <= 300 and warmup >= 15 and warmup <= 120)
	assert(DisplayServer.get_name() != "headless", "Actual GPU required")
	assert(not FileAccess.file_exists(output.path_join("benchmark.validation.json")), "Do not overwrite existing measurements")
	DirAccess.make_dir_recursive_absolute(output)
	for path in [model_path, ProjectSettings.globalize_path(profile_path), ProjectSettings.globalize_path("res://scripts/aquarium/FoundryFishMotion.gd"), get_script().resource_path]:
		bound[path] = FileAccess.get_sha256(path)
	# A dedicated measurement window displays the always-updating GPU viewport.
	root.title = "Fish material measurement · temporary"
	root.size = Vector2i(1280, 720)
	last_progress_usec = Time.get_ticks_usec()
	call_deferred("run")

func environment_setup() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	# This temporary window alone must remain drawable when Codex takes focus.
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, true)
	Engine.max_fps = 0
	OS.low_processor_usage_mode = false
	view = SubViewport.new()
	view.size = Vector2i(1280, 720)
	view.own_world_3d = true
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	view.mesh_lod_threshold = 0.0
	view.msaa_3d = Viewport.MSAA_DISABLED
	var screen := SubViewportContainer.new()
	screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	screen.stretch = false
	root.add_child(screen)
	screen.add_child(view)
	world = Node3D.new()
	view.add_child(world)
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color("25343c")
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color.WHITE
	environment.environment.ambient_light_energy = .65
	world.add_child(environment)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-45, -35, 0)
	light.light_energy = .65
	light.shadow_enabled = false
	world.add_child(light)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.keep_aspect = Camera3D.KEEP_HEIGHT
	camera.near = .001
	camera.far = 100.0
	camera.size = 10.5
	world.add_child(camera)
	camera.position = Vector3(0, 0, 20)
	camera.look_at(Vector3.ZERO)
	camera.current = true
	RenderingServer.viewport_set_measure_render_time(view.get_viewport_rid(), true)
	var watchdog := Timer.new()
	watchdog.wait_time = 1.0
	watchdog.timeout.connect(check_stall)
	root.add_child(watchdog)
	watchdog.start()

func window_state() -> Dictionary:
	return {"root_visible": root.visible, "always_on_top": DisplayServer.window_get_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP), "window_mode": DisplayServer.window_get_mode(), "minimized": DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_MINIMIZED, "focused": DisplayServer.window_is_focused(), "can_draw": DisplayServer.window_can_draw(), "viewport_size": [view.size.x, view.size.y], "viewport_update_mode": view.render_target_update_mode, "viewport_rid_valid": view.get_viewport_rid().is_valid()}

func draw_environment_valid(state: Dictionary, stage: String) -> bool:
	if state.can_draw and state.root_visible and not state.minimized: return true
	var file := FileAccess.open(output.path_join("render-environment-rejected.validation.json"), FileAccess.WRITE)
	if file != null: file.store_string(JSON.stringify({"ok": false, "kind": "material_case_environment_rejected", "stage": stage, "progress": progress_label, "window_state": state, "reason": "Window not drawable; sample is rejected rather than counted as model slowness."}, "  ") + "\n")
	push_error("Window became non-drawable during measurement; rejecting case")
	quit(3)
	return false

func check_stall() -> void:
	if Time.get_ticks_usec() - last_progress_usec <= 8000000: return
	var file := FileAccess.open(output.path_join("stall.validation.json"), FileAccess.WRITE)
	if file != null: file.store_string(JSON.stringify({"ok": false, "kind": "material_case_stall", "mode": mode, "progress": progress_label, "window_state": window_state(), "seconds_since_progress": (Time.get_ticks_usec() - last_progress_usec) / 1000000.0, "model_sha256": FileAccess.get_sha256(model_path)}, "  ") + "\n")
	push_error("No capture/render progress for8seconds; aborting measurement without claiming completion")
	quit(3)

func inspect(model: Node3D) -> Dictionary:
	var result := {"meshes": 0, "surfaces": 0, "vertices": 0, "triangles": 0, "bones": 0, "materials": []}
	for skeleton in model.find_children("*", "Skeleton3D", true, false): result.bones += skeleton.get_bone_count()
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		result.meshes += 1
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for si in mesh.mesh.get_surface_count():
			var arrays: Array = mesh.mesh.surface_get_arrays(si)
			result.surfaces += 1
			result.vertices += (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			result.triangles += indices.size() / 3 if not indices.is_empty() else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size() / 3
			var material := mesh.get_active_material(si) as BaseMaterial3D
			assert(material != null)
			material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
			result.materials.append({"name": material.resource_name, "transparency": material.transparency, "shading_mode": material.shading_mode, "cull_mode": material.cull_mode})
	return result

func add_fish(prototype: Node3D, profile: Dictionary, index: int) -> void:
	var carrier := Node3D.new()
	world.add_child(carrier)
	var model := prototype.duplicate() as Node3D
	carrier.add_child(model)
	model.scale = Vector3.ONE * MODEL_SCALE
	var skeleton: Skeleton3D = model.find_children("*", "Skeleton3D", true, false)[0]
	var player: AnimationPlayer = model.find_children("*", "AnimationPlayer", true, false)[0]
	var controller = MOTION.new()
	var configured: Dictionary = controller.configure(carrier, model, player, skeleton, profile)
	assert(configured.ok, JSON.stringify(configured))
	controller.seek(float(index % 97) / 97.0 * 4.0)
	# Same 1000 slots and camera for every count. No scale change, LOD, culling or path clustering.
	var column := index % 40
	var row := index / 40
	var home := Transform3D(Basis.IDENTITY, Vector3((float(column) - 19.5) * .45, (12.0 - float(row)) * .34, 0))
	carrier.transform = home
	player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	fish.append({"carrier": carrier, "model": model, "skeleton": skeleton, "player": player, "controller": controller, "home": home})

func pose_digest(skeleton: Skeleton3D) -> String:
	var poses: Array = []
	for i in skeleton.get_bone_count(): poses.append(skeleton.get_bone_global_pose(i))
	return var_to_bytes(poses).hex_encode().sha256_text()

func distribution(values: Array) -> Dictionary:
	assert(not values.is_empty())
	var ordered := values.duplicate()
	ordered.sort()
	var total := 0.0
	for value in values: total += float(value)
	return {"mean": total / values.size(), "p50": ordered[int((ordered.size() - 1) * .5)], "p95": ordered[int((ordered.size() - 1) * .95)], "min": ordered[0], "max": ordered[-1]}

func base_report() -> Dictionary:
	return {"ok": true, "kind": "fish_material_performance_case", "model": model_path, "model_sha256": FileAccess.get_sha256(model_path), "frozen_inputs": bound,
		"settings": {"count": count, "animated": animated, "samples": samples, "warmup": warmup, "viewport": [view.size.x, view.size.y], "native_window_pixels": [root.size.x, root.size.y], "vsync": "disabled", "rendering_method": RenderingServer.get_current_rendering_method(), "rendering_driver": RenderingServer.get_current_rendering_driver_name(), "gpu": RenderingServer.get_video_adapter_name(), "engine": Engine.get_version_info(), "display_server": DisplayServer.get_name(), "model_scale": MODEL_SCALE, "real_length_cm": 40, "fixed_simulation_delta_seconds": FIXED_DELTA, "camera_size": camera.size, "shadow": false, "water_AI_collision": false, "automatic_LOD": false, "layout": "Fixed40x25 slots, .45x.34m spacing; +X heading restored after each real controller step; identical camera at all counts.", "viewport_always_update": true, "visible_measurement_window": true, "always_on_top": true},
		"window_state": window_state(), "per_fish": inventory, "initialization_ms": init_ms, "direct_GLTFDocument": true, "runtime_static_build_calls": 0,
		"scope": "Isolated renderer and real bone-controller cost. Motion call time excludes deferred engine skin/render work. Frame interval is whole process cadence, not GPU-only or a gameplay FPS promise. No water/AI/shadows. Sources and existing acceptance unchanged."}

func benchmark() -> void:
	var raw: Array = []
	var frame: Array = []
	var motion: Array = []
	var draws: Array = []
	var primitives: Array = []
	var objects: Array = []
	var renderer_cpu: Array = []
	var renderer_gpu: Array = []
	var start_pose := pose_digest(fish[0].skeleton)
	var previous := Time.get_ticks_usec()
	last_progress_usec = Time.get_ticks_usec()
	for index in samples + warmup:
		progress_label = "benchmark-frame-" + str(index)
		await process_frame
		var before_state := window_state() if index >= warmup else {}
		if index >= warmup and not draw_environment_valid(before_state, "before_sample"): return
		var started := Time.get_ticks_usec()
		if animated:
			for item in fish:
				item.controller.step(FIXED_DELTA)
				item.carrier.transform = item.home
		var motion_elapsed := (Time.get_ticks_usec() - started) / 1000.0
		await RenderingServer.frame_post_draw
		var now := Time.get_ticks_usec()
		last_progress_usec = now
		if index >= warmup:
			var after_state := window_state()
			if not draw_environment_valid(after_state, "after_sample"): return
			var cpu := RenderingServer.viewport_get_measured_render_time_cpu(view.get_viewport_rid())
			var gpu := RenderingServer.viewport_get_measured_render_time_gpu(view.get_viewport_rid())
			var row := {"frame_ms": (now - previous) / 1000.0, "motion_call_ms": motion_elapsed,
				"draw_calls": RenderingServer.viewport_get_render_info(view.get_viewport_rid(), RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_DRAW_CALLS_IN_FRAME), "primitives": RenderingServer.viewport_get_render_info(view.get_viewport_rid(), RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME), "render_objects": RenderingServer.viewport_get_render_info(view.get_viewport_rid(), RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_OBJECTS_IN_FRAME), "whole_window_draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), "renderer_cpu_interval_ms": cpu, "renderer_gpu_interval_ms": gpu, "window_can_draw_before": before_state.can_draw, "window_can_draw_after": after_state.can_draw, "window_focused_before": before_state.focused, "window_focused_after": after_state.focused}
			raw.append(row)
			frame.append(row.frame_ms); motion.append(motion_elapsed); draws.append(row.draw_calls); primitives.append(row.primitives); objects.append(row.render_objects); renderer_cpu.append(cpu); renderer_gpu.append(gpu)
		previous = now
	var end_pose := pose_digest(fish[0].skeleton)
	assert((start_pose != end_pose) == animated, "Actual skeleton motion must match requested case")
	var image := view.get_texture().get_image()
	assert(image.get_size() == Vector2i(1280, 720), "Actual benchmark pixels must match fixed viewport")
	var layout_path := output.path_join("layout.png")
	assert(image.save_png(layout_path) == OK)
	var report := base_report()
	report.merge({"frame_ms": distribution(frame), "motion_call_ms": distribution(motion), "draw_calls": distribution(draws), "primitives": distribution(primitives), "render_objects": distribution(objects), "renderer_cpu_interval_ms": distribution(renderer_cpu), "renderer_gpu_interval_ms": distribution(renderer_gpu), "gpu_timer_available": renderer_gpu.max() > 0, "raw_samples": raw, "actual_first_fish_pose_changed": start_pose != end_pose, "layout_image": {"path": layout_path, "sha256": FileAccess.get_sha256(layout_path)}})
	finish(report, "benchmark.validation.json")

func capture() -> void:
	var item: Dictionary = fish[0]
	item.carrier.transform = Transform3D.IDENTITY
	item.player.stop()
	item.skeleton.reset_bone_poses()
	var views := [{"name": "left", "direction": Vector3(0, 0, 1)}, {"name": "right", "direction": Vector3(0, 0, -1)}, {"name": "front", "direction": Vector3(1, 0, 0)}, {"name": "rear", "direction": Vector3(-1, 0, 0)}, {"name": "top", "direction": Vector3(0, 1, 0)}, {"name": "bottom", "direction": Vector3(0, -1, 0)}, {"name": "oblique", "direction": Vector3(.8, .3, 1).normalized()}, {"name": "reverse_oblique", "direction": Vector3(-.8, -.3, -1).normalized()}]
	var rows: Array = []
	for pose in ["rest", "Swim"]:
		if pose == "Swim":
			assert(item.controller.set_action("Swim", true)); item.controller.step(0.0)
			for i in 48: item.controller.step(FIXED_DELTA)
			item.carrier.transform = Transform3D.IDENTITY
		for framing in [{"name": "whole", "size": .52, "focus": Vector3.ZERO}, {"name": "head", "size": .19, "focus": Vector3(.155, .005, 0)}, {"name": "fins", "size": .34, "focus": Vector3(-.055, .02, 0)}]:
			for direction in views:
				camera.size = framing.size
				camera.position = framing.focus + direction.direction * 2.0
				camera.look_at(framing.focus, Vector3.UP if absf(direction.direction.y) < .99 else Vector3(0, 0, -1))
				progress_label = pose + "-" + framing.name + "-" + direction.name
				for i in 3: await process_frame
				RenderingServer.force_draw()
				var name: String = pose + "-" + framing.name + "-" + direction.name
				var path := output.path_join(name + ".png")
				assert(view.get_texture().get_image().save_png(path) == OK)
				last_progress_usec = Time.get_ticks_usec()
				rows.append({"name": name, "path": path, "sha256": FileAccess.get_sha256(path), "pose_sha256": pose_digest(item.skeleton), "camera_size": camera.size, "focus": [framing.focus.x, framing.focus.y, framing.focus.z], "direction": [direction.direction.x, direction.direction.y, direction.direction.z], "window_state": window_state()})
	var report := base_report()
	report.merge({"kind": "fish_material_capture", "captures": rows, "scope": "Current actual direct GLB 8-view, rest and real Swim pose; whole/head/fins closeups. Geometry/material comparison evidence, not formal fish acceptance."})
	finish(report, "capture.validation.json")

func finish(report: Dictionary, filename: String) -> void:
	for path in bound: assert(FileAccess.get_sha256(path) == bound[path], "Changed source during experiment")
	var file := FileAccess.open(output.path_join(filename), FileAccess.WRITE)
	assert(file != null)
	file.store_string(JSON.stringify(report, "  ") + "\n")
	print("FISH_MATERIAL_CASE_OK ", filename)
	quit()

func run() -> void:
	var start := Time.get_ticks_usec()
	environment_setup()
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	assert(document.append_from_file(model_path, state) == OK)
	var prototype := document.generate_scene(state) as Node3D
	assert(prototype != null)
	inventory = inspect(prototype)
	assert(inventory.triangles == 1710 and inventory.bones == 18, "Unexpected study geometry")
	var profile: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(profile_path))
	for i in (1 if mode == "capture" else count): add_fish(prototype, profile, i)
	prototype.free()
	init_ms = (Time.get_ticks_usec() - start) / 1000.0
	if mode == "capture": await capture()
	else: await benchmark()
