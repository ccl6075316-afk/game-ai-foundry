extends "verify_runtime_lod.gd"
## Hidden GPU closeout: animated distance sweeps and controlled full-exhibit A/B.
const WIDTH := 256
const HEIGHT := 144
const SAMPLE_COUNT := 16

func draw_frame(view: SubViewport, threshold: float) -> Dictionary:
	view.mesh_lod_threshold = threshold
	RenderingServer.force_draw(false)
	return {
		"image": view.get_texture().get_image(),
		"primitives": RenderingServer.viewport_get_render_info(
			view.get_viewport_rid(), RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE,
			RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME
		),
	}

func compare_frames(full: Image, reduced: Image) -> Dictionary:
	full.convert(Image.FORMAT_RGBA8)
	reduced.convert(Image.FORMAT_RGBA8)
	var a := full.get_data()
	var b := reduced.get_data()
	var foreground := 0
	var outline_delta := 0
	var color_delta := 0
	var background := full.get_pixel(0, 0)
	for y in HEIGHT:
		for x in WIDTH:
			var i := 4 * (y * WIDTH + x)
			var left := maxi(absi(a[i] - a[0]), maxi(absi(a[i + 1] - a[1]), absi(a[i + 2] - a[2]))) > 5
			var right := maxi(absi(b[i] - b[0]), maxi(absi(b[i + 1] - b[1]), absi(b[i + 2] - b[2]))) > 5
			foreground += int(left)
			outline_delta += int(left != right)
			if left or right:
				color_delta += maxi(absi(a[i] - b[i]), maxi(absi(a[i + 1] - b[i + 1]), absi(a[i + 2] - b[i + 2])))
	var valid_background := background.is_equal_approx(reduced.get_pixel(0, 0))
	return {
		"ok": foreground > 0 and valid_background,
		"pixels": foreground,
		"outline_percent": 100.0 * outline_delta / maxi(1, foreground),
		"mean_absolute_rgb_delta": float(color_delta) / maxi(1, foreground),
	}

func sweep(entry: Dictionary, length_m: float) -> Dictionary:
	var controller: RefCounted = entry.controller
	var actions := ["Swim", "Turn", "Ascend", "Dive"]
	if controller.has_method("play_jaw_action"):
		actions.append("Mouth")
	var report := {}
	var worst := -1.0
	var minimum_primitives := 2147483647
	var levels := {}
	for option in actions:
		check(controller.set_action("Swim" if option == "Mouth" else option, true), "Unavailable action")
		if option == "Mouth":
			controller.play_jaw_action()
		var action_worst := 0.0
		var outline_worst := 0.0
		for sample in SAMPLE_COUNT:
			for tick in 12 if option == "Mouth" else 5:
				controller.step(1.0 / 60.0)
			entry.carrier.transform = Transform3D.IDENTITY
			var angle := TAU * sample / SAMPLE_COUNT
			var direction := Vector3(sin(angle) * 0.7, 0.16 + sin(angle * 2.0) * 0.43, cos(angle))
			var projected_length := lerpf(185.0, 47.0, float(sample) / (SAMPLE_COUNT - 1))
			var focal_distance := HEIGHT / (2.0 * tan(deg_to_rad(camera.fov * 0.5)))
			camera.position = direction.normalized() * focal_distance * length_m / projected_length
			camera.look_at(Vector3.ZERO)
			await process_frame
			var full := draw_frame(viewport, 0.0)
			var reduced := draw_frame(viewport, 1.0)
			var difference := compare_frames(full.image, reduced.image)
			check(difference.ok and reduced.primitives > 0 and reduced.primitives <= full.primitives,
				"Invalid draw comparison: %s %s %d" % [entry.species, option, sample])
			action_worst = maxf(action_worst, difference.mean_absolute_rgb_delta)
			outline_worst = maxf(outline_worst, difference.outline_percent)
			minimum_primitives = mini(minimum_primitives, reduced.primitives)
			levels[reduced.primitives] = true
			if difference.mean_absolute_rgb_delta > worst:
				worst = difference.mean_absolute_rgb_delta
				full.image.save_png(output.path_join(entry.species + "_worst_full.png"))
				reduced.image.save_png(output.path_join(entry.species + "_worst_lod.png"))
		report[option] = {"samples": SAMPLE_COUNT, "worst_outline_percent": outline_worst,
			"worst_mean_absolute_rgb_delta": action_worst}
	check(levels.size() >= 3, "Distance sweep missed tiers: " + entry.species)
	return {"actions": report, "distinct_triangle_counts": levels.size(), "minimum_triangles": minimum_primitives}

func percentile(values: Array[float], fraction: float) -> float:
	values.sort()
	return values[clampi(ceili(values.size() * fraction) - 1, 0, values.size() - 1)]

func benchmark_actual_exhibit() -> Dictionary:
	root.size = Vector2i(1280, 720)
	var exhibit := Exhibit.new()
	exhibit.shared_tank = true
	root.add_child(exhibit)
	exhibit.set_process(false)
	exhibit.viewport.size = Vector2i(1280, 720)
	exhibit.viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	check(exhibit.fish.size() == 28, "Missing fish in real shared exhibit")
	var results := {"full": [], "lod": []}
	# Balance order and start each run at the same actual controller phase.
	for mode in ["full", "lod", "lod", "full"]:
		var mode_results: Array = results[mode]
		var times: Array[float] = []
		var triangles: Array[float] = []
		var draw_calls: Array[float] = []
		for i in 100:
			for entry in exhibit.fish:
				entry.controller.seek(0.21 + float(i) / 60.0)
			await process_frame
			exhibit.viewport.mesh_lod_threshold = 0.0 if mode == "full" else 1.0
			var started := Time.get_ticks_usec()
			RenderingServer.force_draw(false)
			var frame := exhibit.viewport.get_texture().get_image()
			var milliseconds := (Time.get_ticks_usec() - started) / 1000.0
			if i >= 20:
				times.append(milliseconds)
				triangles.append(RenderingServer.viewport_get_render_info(exhibit.viewport.get_viewport_rid(),
					RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME))
				draw_calls.append(RenderingServer.viewport_get_render_info(exhibit.viewport.get_viewport_rid(),
					RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_DRAW_CALLS_IN_FRAME))
			if i == 40 and mode_results.is_empty():
				frame.save_png(output.path_join("exhibit_" + mode + ".png"))
		mode_results.append({"p50_draw_readback_ms": percentile(times, 0.5), "p95_draw_readback_ms": percentile(times, 0.95),
			"p50_primitives": percentile(triangles, 0.5), "p50_draw_calls": percentile(draw_calls, 0.5), "samples": times.size()})
	exhibit.queue_free()
	return results

func run() -> void:
	output = OS.get_cmdline_user_args()[0]
	DirAccess.make_dir_recursive_absolute(output)
	assert(DisplayServer.get_name() != "headless")
	RenderingServer.set_render_loop_enabled(false)
	Engine.max_fps = 0
	Cache.begin_entry()
	var factory := Exhibit.new()
	factory._load_profiles()
	viewport = SubViewport.new()
	viewport.own_world_3d = true
	viewport.size = Vector2i(WIDTH, HEIGHT)
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var world := Node3D.new()
	viewport.add_child(world)
	setup_render(world)
	var results := {}
	for species in Exhibit.SPECIES:
		var profile: Dictionary = factory.profiles[species]
		var length_m := float(profile.real_length_cm) / 100.0
		var bucket := Node3D.new()
		world.add_child(bucket)
		factory._add_fish(bucket, species, length_m, profile)
		results[species] = await sweep(factory.fish.pop_back(), length_m)
		print("LOD_SWEEP ", species, " ", results[species])
		bucket.queue_free()
		await process_frame
	viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
	var benchmark := await benchmark_actual_exhibit()
	var report := {
		"ok": failures.is_empty(), "failures": failures, "fish": results, "exhibit": benchmark,
		"engine": Engine.get_version_info().string, "adapter": RenderingServer.get_video_adapter_name(),
		"lod_resource_sha256": FileAccess.get_sha256("res://assets/models/fish/motion/fish-lod.res"),
		"scope": "Co-posed GPU pixel comparisons during moving camera/animation and controlled draw + mandatory viewport readback on the real shared exhibit. No wall-clock FPS or continuous collision claim.",
	}
	FileAccess.open(output.path_join("release.validation.json"), FileAccess.WRITE).store_string(JSON.stringify(report, "\t") + "\n")
	factory.free()
	viewport.free()
	Cache.clear()
	quit(0 if failures.is_empty() else 1)
