extends SceneTree
## Production entry regression and optional GPU A/B captures.
## --script <this file> -- <scratch output directory> [--render]
const Exhibit = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const Fishing = preload("res://scripts/screens/FishingVolumeFish.gd")
const Cache = preload("res://scripts/aquarium/FishAppearanceCache.gd")

var viewport: SubViewport
var camera: Camera3D
var output: String
var failures: Array[String] = []

func _initialize() -> void:
	run.call_deferred()

func check(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)
		push_error(message)

func mesh_data(model: Node3D) -> Dictionary:
	var result := {}
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var surfaces: Array = node.mesh.get("_surfaces")
		var base := []
		var levels := []
		for surface in surfaces:
			var entry: Dictionary = surface.duplicate()
			var lods: Array = entry.get("lods", [])
			var triangle_counts := [int(entry.index_count / 3)]
			var index_stride := int(entry.index_data.size() / entry.index_count)
			var valid := not lods.is_empty()
			for i in range(0, lods.size(), 2):
				triangle_counts.append(int(lods[i + 1].size() / (index_stride * 3)))
				valid = valid and triangle_counts[-1] < triangle_counts[-2]
			if not lods.is_empty():
				check(valid, "Invalid index level counts: " + String(node.name))
			levels.append(triangle_counts)
			entry.erase("lods")
			entry.erase("material")
			base.append(entry)
		result[String(node.name)] = {"base": base, "levels": levels}
	return result

func open_raw(species: String) -> Node3D:
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	assert(document.append_from_file("res://assets/models/fish/%s.glb" % species, state) == OK)
	return document.generate_scene(state) as Node3D

func base_equal(reference: Dictionary, actual: Dictionary) -> bool:
	if reference.keys() != actual.keys():
		return false
	for key in reference:
		if reference[key].base != actual[key].base:
			return false
	return true

func count_levels(data: Dictionary) -> Vector2i:
	var counts := Vector2i.ZERO
	for item in data.values():
		for tier in item.levels:
			counts.x += tier[0]
			counts.y += tier[-1]
	return counts

func setup_render(world: Node3D) -> void:
	var screen := DisplayServer.screen_get_usable_rect(DisplayServer.get_primary_screen())
	root.size = Vector2i(360, 240)
	root.position = screen.position + (screen.size - root.size) / 2
	root.unfocusable = true
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("19303c")
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color("d6e8e7")
	env.environment.ambient_light_energy = 0.85
	world.add_child(env)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-55, -25, 0)
	light.light_energy = 0.6
	world.add_child(light)
	camera = Camera3D.new()
	camera.fov = 42.0
	camera.far = 600.0
	camera.near = 0.01
	world.add_child(camera)
	camera.make_current()

func capture(path: String, threshold: float) -> int:
	viewport.mesh_lod_threshold = threshold
	await process_frame
	await RenderingServer.frame_post_draw
	var image := viewport.get_texture().get_image()
	check(image != null and image.save_png(path) == OK, "Missing GPU image: " + path)
	return RenderingServer.viewport_get_render_info(
		viewport.get_viewport_rid(), RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE,
		RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME
	)

func render_fish(entry: Dictionary, length_m: float) -> Array:
	var measured := []
	var cases := [
		["close-swim", "Swim", 270.0, Vector3(0.20, 0.14, 1)],
		["mid-turn", "Turn", 110.0, Vector3(0.20, 0.18, 1)],
		["far-dive", "Dive", 47.0, Vector3(-0.20, 0.43, 1)],
		["far-mouth", "Swim", 48.0, Vector3(0.86, -0.36, 0.68)],
		["far-rise", "Ascend", 47.0, Vector3(-0.23, -0.37, 1)],
	]
	for item in cases:
		var controller: RefCounted = entry.controller
		check(controller.set_action(item[1], true), "Action unavailable: " + str(item[1]))
		if item[0] == "far-mouth" and controller.has_method("play_jaw_action"):
			controller.play_jaw_action()
		for step in 72 if item[0] == "far-mouth" else 39:
			controller.step(1.0 / 60.0)
		entry.carrier.transform = Transform3D.IDENTITY
		var distance: float = viewport.size.y / (2.0 * tan(deg_to_rad(camera.fov * 0.5))) * length_m / item[2]
		camera.position = item[3].normalized() * distance
		camera.look_at(Vector3.ZERO)
		var path := output.path_join("%s_%s" % [entry.species, item[0]])
		var original := await capture(path + "_full.png", 0.0)
		var lod := await capture(path + "_lod.png", 1.0)
		check(original > 0 and lod > 0 and lod <= original, "Invalid draw counts: " + path)
		if item[0] == "close-swim":
			check(lod == original, "Close inspection switched away from full detail: " + entry.species)
			var full_image := Image.load_from_file(path + "_full.png")
			var lod_image := Image.load_from_file(path + "_lod.png")
			check(full_image.get_data() == lod_image.get_data(), "Close pixels changed: " + entry.species)
		if item[0].begins_with("far-"):
			check(lod < original, "Far camera drew full-detail only: " + path)
		measured.append({"case": item[0], "full_primitives": original, "lod_primitives": lod})
	check(
		measured[0].lod_primitives > measured[1].lod_primitives and
		measured[1].lod_primitives > measured[2].lod_primitives,
		"Three distinct levels were not rendered: " + entry.species
	)
	return measured

func render_group(factory: Control, world: Node3D) -> Dictionary:
	var group := Node3D.new()
	world.add_child(group)
	viewport.size = Vector2i(970, 600)
	camera.position = Vector3(0, 0, 17)
	camera.look_at(Vector3.ZERO)
	for i in Exhibit.SPECIES.size():
		var species: String = Exhibit.SPECIES[i]
		var profile: Dictionary = factory.profiles[species]
		var length_m := float(profile.real_length_cm) / 100.0
		factory._add_fish(group, species, length_m, profile)
		var entry: Dictionary = factory.fish.pop_back()
		entry.controller.seek(0.2 + i * 0.08)
		entry.carrier.transform = Transform3D.IDENTITY
		entry.carrier.scale = Vector3.ONE / length_m
		entry.carrier.position = Vector3((i % 7 - 3) * 2.7, (1.5 - floorf(i / 7.0)) * 2.1, 0)
	var full := await capture(output.path_join("group_full.png"), 0.0)
	var reduced := await capture(output.path_join("group_lod.png"), 1.0)
	check(full > 0 and reduced > 0 and reduced < full, "No reduction with all species visible")
	group.queue_free()
	return {"species": Exhibit.SPECIES.size(), "full_primitives": full, "lod_primitives": reduced}

func run() -> void:
	var args := OS.get_cmdline_user_args()
	assert(not args.is_empty())
	output = args[0]
	DirAccess.make_dir_recursive_absolute(output)
	var render := "--render" in args
	Cache.begin_entry()
	var factory := Exhibit.new()
	factory._load_profiles()
	viewport = SubViewport.new()
	viewport.own_world_3d = true
	viewport.size = Vector2i(480, 320)
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS if render else SubViewport.UPDATE_DISABLED
	root.add_child(viewport)
	var world := Node3D.new()
	viewport.add_child(world)
	if render:
		setup_render(world)

	var results := {}
	for species in Exhibit.SPECIES:
		var profile: Dictionary = factory.profiles[species]
		var length_m := float(profile.real_length_cm) / 100.0
		var original := open_raw(species)
		var baseline := mesh_data(original)
		original.free()
		var bucket := Node3D.new()
		world.add_child(bucket)
		factory._add_fish(bucket, species, length_m, profile)
		var entry: Dictionary = factory.fish.pop_back()
		var first := mesh_data(entry.model)
		check(base_equal(baseline, first), "Full-detail streams changed: " + species)
		var counts := count_levels(first)
		check(counts.y < counts.x, "No simplified faces: " + species)
		var captures: Array = await render_fish(entry, length_m) if render else []
		bucket.queue_free()

		bucket = Node3D.new()
		world.add_child(bucket)
		factory._add_fish(bucket, species, length_m, profile)
		var cached: Dictionary = factory.fish.pop_back()
		check(mesh_data(cached.model) == first, "Cached entry differs: " + species)
		bucket.queue_free()

		var fishing := Fishing.new()
		root.add_child(fishing)
		check(fishing.configure(species), "Fishing configure failed: " + species)
		check(mesh_data(fishing.model) == first, "Fishing mesh differs: " + species)
		var lip_error := 0.0
		for action in Exhibit.ACTIONS:
			for frame in 10:
				fishing.animate(1.0 / 60.0, action)
				var hook := Vector3(0.32, 0.60, -0.24)
				fishing.place_hook(hook, Vector3(1, 0.31, -0.24))
				lip_error = maxf(lip_error, fishing.mouth_world().distance_to(hook))
		check(lip_error < 0.00001, "Hook no longer aligns: " + species)
		results[species] = {
			"sha256": FileAccess.get_sha256("res://assets/models/fish/%s.glb" % species),
			"full_triangles": counts.x, "far_triangles": counts.y,
			"maximum_hook_error_m": lip_error, "gpu": captures,
		}
		print("FISH_LOD ", species, " ", counts, " ", captures)
		fishing.queue_free()
		await process_frame
	var group: Dictionary = await render_group(factory, world) if render else {}
	if render:
		var expected := 0
		for fish in results.values():
			expected += fish.full_triangles
		check(group.full_primitives == expected, "Some fish were outside the group view")
	var report := {"ok": failures.is_empty(), "fish": results, "group": group, "failures": failures}
	FileAccess.open(output.path_join("runtime.validation.json"), FileAccess.WRITE).store_string(JSON.stringify(report, "\t") + "\n")
	factory.free()
	viewport.free()
	Cache.clear()
	quit(0 if failures.is_empty() else 1)
