extends "benchmark_fish_materials.gd"
## Controlled GPU microbenchmark. Own minimized window is never a drawable prerequisite.
var explicit_draw_signals := 0

func _initialize() -> void:
	super._initialize()
	var base_path: String = get_script().get_base_script().resource_path
	bound[base_path] = FileAccess.get_sha256(base_path)
	root.always_on_top = false

func environment_setup() -> void:
	RenderingServer.set_render_loop_enabled(false)
	Engine.max_fps = 0
	OS.low_processor_usage_mode = false
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, false)
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_MINIMIZED)
	assert(DisplayServer.get_name() != "headless")
	assert(RenderingServer.get_current_rendering_driver_name() == "opengl3")
	var adapter := RenderingServer.get_video_adapter_name().to_lower()
	assert(not adapter.is_empty() and not ("dummy" in adapter or "llvmpipe" in adapter or "swiftshader" in adapter or "software" in adapter), "A real GPU is required")
	view = SubViewport.new()
	view.size = Vector2i(1280, 720)
	view.own_world_3d = true
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	view.mesh_lod_threshold = 0.0
	view.msaa_3d = Viewport.MSAA_DISABLED
	root.add_child(view)
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
	RenderingServer.frame_post_draw.connect(func(): explicit_draw_signals += 1)
	# Never call the base window watchdog or drawing guard: no automatic window presentation is measured.

func image_has_geometry(image: Image) -> bool:
	var reference := image.get_pixel(0, 0)
	for y in range(0, image.get_height(), 2):
		for x in range(0, image.get_width(), 2):
			if image.get_pixel(x, y) != reference: return true
	return false

func benchmark() -> void:
	assert(samples == 60 and warmup == 15, "Controlled protocol is60samples+15warmup")
	assert(not RenderingServer.is_render_loop_enabled())
	var raw: Array = []
	var motion_times: Array = []
	var refresh_times: Array = []
	var draw_times: Array = []
	var step_times: Array = []
	var draws: Array = []
	var primitives: Array = []
	var first_image: Image
	var last_image: Image
	var first_pose := ""
	var last_pose := ""
	var first_window: Dictionary
	var last_window: Dictionary
	for index in samples + warmup:
		var step_started := Time.get_ticks_usec()
		var motion_started := Time.get_ticks_usec()
		if animated:
			for item in fish:
				item.controller.step(FIXED_DELTA)
				item.carrier.transform = item.home
		var motion_finished := Time.get_ticks_usec()
		# Advance the normal engine frame/deferred work before the one explicit render.
		await process_frame
		var draw_started := Time.get_ticks_usec()
		assert(not RenderingServer.is_render_loop_enabled(), "Automatic render loop must remain disabled")
		var signals_before := explicit_draw_signals
		RenderingServer.force_draw(false)
		var image: Image = view.get_texture().get_image()
		var finished := Time.get_ticks_usec()
		assert(explicit_draw_signals - signals_before == 1, "Exactly one actual draw signal per controlled step")
		assert(image != null and image.get_size() == Vector2i(1280, 720))
		var actual_draws := RenderingServer.viewport_get_render_info(view.get_viewport_rid(), RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_DRAW_CALLS_IN_FRAME)
		var actual_primitives := RenderingServer.viewport_get_render_info(view.get_viewport_rid(), RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME)
		assert(actual_draws == inventory.surfaces * count and actual_primitives == 1710 * count, "Controlled GPU must draw every fish/surface")
		if index >= warmup:
			var row := {"motion_call_ms": (motion_finished - motion_started) / 1000.0, "engine_refresh_wait_ms": (draw_started - motion_finished) / 1000.0, "forced_draw_readback_ms": (finished - draw_started) / 1000.0, "controlled_step_ms": (finished - step_started) / 1000.0, "draw_calls": actual_draws, "primitives": actual_primitives, "explicit_draw_signals": explicit_draw_signals - signals_before}
			raw.append(row)
			motion_times.append(row.motion_call_ms); refresh_times.append(row.engine_refresh_wait_ms); draw_times.append(row.forced_draw_readback_ms); step_times.append(row.controlled_step_ms); draws.append(actual_draws); primitives.append(actual_primitives)
			if index == warmup:
				first_image = image
				first_pose = pose_digest(fish[0].skeleton)
				first_window = window_state()
			if index == samples + warmup - 1:
				last_image = image
				last_pose = pose_digest(fish[0].skeleton)
				last_window = window_state()
	assert(explicit_draw_signals == samples + warmup, "No extra automatic renders permitted")
	assert(first_window.minimized and last_window.minimized, "Only this process window must remain minimized")
	assert(not first_window.always_on_top and not last_window.always_on_top)
	assert(image_has_geometry(first_image) and image_has_geometry(last_image), "Readback must contain actual rendered fish")
	var first_digest := first_image.get_data().hex_encode().sha256_text()
	var last_digest := last_image.get_data().hex_encode().sha256_text()
	assert((first_pose != last_pose) == animated, "Actual skeleton pose change must match requested mode")
	assert((first_digest != last_digest) == animated, "Actual GPU image change must match requested mode")
	var first_path := output.path_join("first.png")
	var last_path := output.path_join("last.png")
	assert(first_image.save_png(first_path) == OK and last_image.save_png(last_path) == OK)
	var report := {"ok": true, "kind": "fish_material_controlled_case", "protocol": "controlled-v1", "model": model_path, "model_sha256": FileAccess.get_sha256(model_path), "frozen_inputs": bound,
		"settings": {"count": count, "animated": animated, "samples": samples, "warmup": warmup, "viewport": [view.size.x, view.size.y], "rendering_method": RenderingServer.get_current_rendering_method(), "rendering_driver": RenderingServer.get_current_rendering_driver_name(), "gpu": RenderingServer.get_video_adapter_name(), "gpu_api": RenderingServer.get_video_adapter_api_version(), "engine": Engine.get_version_info(), "display_server": DisplayServer.get_name(), "automatic_render_loop": false, "explicit_force_draws_per_step": 1, "swap_buffers": false, "readback_every_step": true, "hidden_own_window": false, "own_window_minimized": true, "always_on_top": false, "model_scale": MODEL_SCALE, "real_length_cm": 40, "fixed_simulation_delta_seconds": FIXED_DELTA, "camera_size": camera.size, "shadow": false, "water_AI_collision": false, "automatic_LOD": false, "layout": "Fixed40x25 slots, .45x.34m spacing; +X heading restored after real controller step; same camera for all counts."},
		"per_fish": inventory, "initialization_ms": init_ms, "direct_GLTFDocument": true, "runtime_static_build_calls": 0, "motion_call_ms": distribution(motion_times), "engine_refresh_wait_ms": distribution(refresh_times), "forced_draw_readback_ms": distribution(draw_times), "controlled_step_ms": distribution(step_times), "draw_calls": distribution(draws), "primitives": distribution(primitives), "raw_samples": raw, "actual_pose_changed": first_pose != last_pose, "actual_GPU_image_changed": first_digest != last_digest, "first_pose_sha256": first_pose, "last_pose_sha256": last_pose, "first_image_RGBA_sha256": first_digest, "last_image_RGBA_sha256": last_digest, "first_window_state": first_window, "last_window_state": last_window, "explicit_draw_signals_total": explicit_draw_signals,
		"images": [{"path": first_path, "sha256": FileAccess.get_sha256(first_path)}, {"path": last_path, "sha256": FileAccess.get_sha256(last_path)}], "gpu_timer_available": false,
		"scope": "Controlled real-GPU relative material microbenchmark. Each step includes normal engine frame/deferred wait, exactly one forced draw and synchronous full-image readback. Readback/image allocation and GPU/CPU synchronization are common overhead. These are not gameplay FPS, wall-frame latency or pure GPU milliseconds; do not combine with interrupted automatic-window matrices."}
	finish(report, "controlled.validation.json")
