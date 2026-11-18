extends SceneTree
## Same-pose, reciprocal camera sweeps over actual exhibit and fishing entrants.
const Exhibit = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const Fishing = preload("res://scripts/screens/FishingVolumeFish.gd")
const Cache = preload("res://scripts/aquarium/FishAppearanceCache.gd")
const PIXELS := [270.,220.,190.,170.,155.,140.,124.,110.,96.,83.,72.,64.,57.,48.,42.,36.]
var viewport: SubViewport
var camera: Camera3D
var failures := []

func _initialize() -> void:
	run.call_deferred()

func measure(target: Vector3, length_m: float, pixels: float) -> Dictionary:
	var distance := viewport.size.y * length_m / (2. * tan(deg_to_rad(camera.fov / 2.)) * pixels)
	camera.position = target + Vector3(.19,.12,1.).normalized() * distance
	camera.look_at(target)
	await process_frame
	RenderingServer.force_draw(false)
	var rgb := viewport.get_texture().get_image()
	var count := RenderingServer.viewport_get_render_info(viewport.get_viewport_rid(),
		RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME)
	return {"triangles": count, "pixel_sha256": rgb.get_data().hex_encode().sha256_text()}

func sweep(species: String, entry: String, target: Vector3, length_m: float) -> Dictionary:
	var outward := []
	for pixels in PIXELS:
		outward.append(await measure(target, length_m, pixels))
	var inward := []
	for i in range(PIXELS.size() - 1, -1, -1):
		inward.append(await measure(target, length_m, PIXELS[i]))
	inward.reverse()
	var counts := {}
	for row in outward:
		counts[row.triangles] = true
	var levels: Array = counts.keys()
	levels.sort()
	levels.reverse()
	if outward != inward or levels.size() < 3 or levels[-1] <= 0:
		failures.append([species, entry, levels, outward == inward])
	return {"both_directions_pixel_exact": outward == inward, "gpu_counts": levels,
		"counts_at_projected_pixels": outward.map(func(row): return row.triangles)}

func run() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1 and DisplayServer.get_name() != "headless")
	RenderingServer.set_render_loop_enabled(false)
	Engine.max_fps = 0
	viewport = SubViewport.new()
	viewport.size = Vector2i(360, 260)
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var world := Node3D.new()
	viewport.add_child(world)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("19303c")
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color.WHITE
	world.add_child(env)
	camera = Camera3D.new()
	camera.fov = 42.
	camera.near = .01
	camera.current = true
	world.add_child(camera)
	Cache.begin_entry()
	var factory := Exhibit.new()
	factory._load_profiles()
	var report := {}
	for species in Exhibit.SPECIES:
		var profile: Dictionary = factory.profiles[species]
		var length_m := float(profile.real_length_cm) / 100.
		var bucket := Node3D.new()
		world.add_child(bucket)
		factory._add_fish(bucket, species, length_m, profile)
		var entry: Dictionary = factory.fish.pop_back()
		entry.controller.set_action("Swim", true)
		entry.controller.seek(float(profile.period_seconds) * .31)
		entry.carrier.transform = Transform3D.IDENTITY
		var exhibit_result := await sweep(species, "exhibit_and_aquarium_factory", Vector3.ZERO, length_m)
		bucket.free()

		var fishing := Fishing.new()
		world.add_child(fishing)
		assert(fishing.configure(species), species)
		for i in 25:
			fishing.animate(1. / 60., "Swim")
		fishing.place_hook(Vector3.ZERO, Vector3.RIGHT)
		assert(fishing.mouth_world().length() < .00001, species)
		var fishing_result := await sweep(species, "fishing", fishing.carrier.global_position, fishing.length_m)
		fishing.free()
		report[species] = {"exhibit_and_aquarium_factory": exhibit_result, "fishing": fishing_result}
		print("LOD_SWITCH ", species, " ", exhibit_result.gpu_counts, " ", fishing_result.gpu_counts)
	var out := FileAccess.open(args[0], FileAccess.WRITE)
	out.store_string(JSON.stringify({
		"ok": failures.is_empty(), "failures": failures, "projected_pixels": PIXELS, "fish": report,
		"lod_sha256": FileAccess.get_sha256("res://assets/models/fish/motion/fish-lod.res"),
		"engine": Engine.get_version_info().string,
	}, "\t") + "\n")
	out.close()
	factory.free()
	viewport.queue_free()
	Cache.clear()
	quit(0 if failures.is_empty() else 1)
