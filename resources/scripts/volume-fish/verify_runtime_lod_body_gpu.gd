extends SceneTree
## 077 GPU coverage of each body index variant read from the official LOD arrays.
const Exhibit = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const Cache = preload("res://scripts/aquarium/FishAppearanceCache.gd")
const VIEWS := [[0.,0.], [PI,0.], [PI/2.,0.], [-PI/2.,0.],
	[.5,.85], [.5,-.85], [PI+.5,.65], [PI+.5,-.65]]
const SIZE := 256

var viewport: SubViewport
var camera: Camera3D
var opaque: StandardMaterial3D
var transparent_reference: StandardMaterial3D

func _initialize() -> void:
	run.call_deferred()

func setup_viewport() -> Node3D:
	viewport = SubViewport.new()
	viewport.own_world_3d = true
	viewport.transparent_bg = true
	viewport.size = Vector2i(SIZE, SIZE)
	viewport.mesh_lod_threshold = 0.
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(viewport)
	var world := Node3D.new()
	viewport.add_child(world)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.current = true
	world.add_child(camera)
	opaque = StandardMaterial3D.new()
	opaque.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	opaque.cull_mode = BaseMaterial3D.CULL_DISABLED
	transparent_reference = opaque.duplicate()
	transparent_reference.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	transparent_reference.albedo_color = Color(1.,1.,1.,0.)
	return world

func variant_mesh(original: ArrayMesh, body_indices: Dictionary) -> ArrayMesh:
	var surfaces: Array = original.get("_surfaces")
	var body := []
	for key in body_indices:
		var index := int(key)
		var surface: Dictionary = surfaces[index].duplicate()
		var bytes := Marshalls.base64_to_raw(body_indices[key])
		var stride: int = surface.index_data.size() / surface.index_count
		assert(bytes.size() % (stride * 3) == 0)
		surface.index_data = bytes
		surface.index_count = bytes.size() / stride
		surface.erase("lods")
		body.append(surface)
	var result := original.duplicate() as ArrayMesh
	result.clear_surfaces()
	result.set("_surfaces", body)
	assert(result.get_surface_count() == body.size())
	return result

func capture() -> PackedByteArray:
	await process_frame
	RenderingServer.force_draw(false)
	var frame := viewport.get_texture().get_image()
	frame.convert(Image.FORMAT_RGBA8)
	return frame.get_data()

func compare(actual: PackedByteArray, reference: PackedByteArray) -> Vector2i:
	var missing := 0
	var opaque_pixels := 0
	for i in range(3, reference.size(), 4):
		if reference[i] > 128:
			opaque_pixels += 1
			if actual[i] < 128:
				missing += 1
	return Vector2i(missing, opaque_pixels)

func material_override(meshes: Dictionary, value: Material) -> void:
	for mesh in meshes:
		mesh.material_override = value

func run() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 2 and DisplayServer.get_name() != "headless")
	RenderingServer.set_render_loop_enabled(false)
	Engine.max_fps = 0
	var lod_sha := FileAccess.get_sha256("res://assets/models/fish/motion/fish-lod.res")
	var plan: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var world := setup_viewport()
	var factory := Exhibit.new()
	factory._load_profiles()
	Cache.begin_entry()
	var records := {}
	var failures := []
	var negative := 0
	for species in Exhibit.SPECIES:
		if not plan.has(species):
			continue
		var settings: Dictionary = plan[species]
		assert(settings.lod_sha256 == lod_sha)
		var profile: Dictionary = factory.profiles[species]
		var length_m := float(profile.real_length_cm) / 100.0
		var bucket := Node3D.new()
		world.add_child(bucket)
		factory._add_fish(bucket, species, length_m, profile)
		var entry: Dictionary = factory.fish.pop_back()
		assert(FileAccess.get_sha256(entry.model.scene_file_path) == settings.model_sha256)
		var originals := {}
		var materials := {}
		for node in entry.model.find_children("*", "MeshInstance3D", true, false):
			originals[node.name] = node.mesh
			materials[node.name] = []
			for i in node.mesh.get_surface_count():
				materials[node.name].append(node.get_active_material(i))
			node.hide()
		var render_rows := []
		for level in settings.variants.size():
			var variant: Dictionary = settings.variants[level]
			var kept := {}
			for node in entry.model.find_children("*", "MeshInstance3D", true, false):
				if not variant.has(node.name):
					continue
				kept[node] = true
				node.mesh = variant_mesh(originals[node.name], variant[node.name])
				for i in variant[node.name].keys().size():
					node.set_surface_override_material(i, materials[node.name][int(variant[node.name].keys()[i])])
				node.show()
			var poses := []
			for pose in 2:
				entry.controller.set_action("Swim", true)
				var amplitude := 0.0 if pose == 0 else 2.5
				entry.controller.set_motion_controls({"body_amplitude": amplitude, "fin_amplitude": amplitude,
					"body_frequency": 1., "fin_frequency": 1.}, true)
				entry.controller.seek(float(profile.period_seconds) * (.0 if pose == 0 else .37))
				entry.carrier.transform = Transform3D.IDENTITY
				entry.skeleton.force_update_all_bone_transforms()
				var rows := []
				for view in VIEWS:
					var axis := Vector3(cos(view[0]) * cos(view[1]), sin(view[1]), sin(view[0]) * cos(view[1]))
					camera.position = axis * length_m * 2.
					camera.look_at(Vector3.ZERO)
					camera.size = length_m * 1.25
					camera.near = length_m * .05
					camera.far = length_m * 5.
					material_override(kept, null)
					var actual := await capture()
					material_override(kept, opaque)
					var reference := await capture()
					var result := compare(actual, reference)
					rows.append([result.x, result.y])
					if result.y <= 30 or result.x != 0:
						failures.append([species, level, pose, rows.size()-1, result.x, result.y])
					if negative == 0:
						material_override(kept, transparent_reference)
						negative = compare(await capture(), reference).x
				poses.append(rows)
			material_override(kept, null)
			for node in kept:
				node.hide()
			render_rows.append(poses)
		records[species] = {"model_sha256": settings.model_sha256, "body_variants": render_rows}
		print("LOD_077 ", species, " variants=", render_rows.size(), " total_failures=", failures.size())
		bucket.queue_free()
		await process_frame
	var ok := failures.is_empty() and negative > 0 and records.size() == plan.size()
	var output := FileAccess.open(args[1], FileAccess.WRITE)
	output.store_string(JSON.stringify({"ok": ok, "lod_sha256": lod_sha, "negative_control_missing_pixels": negative,
		"fish": records, "failures": failures, "engine": Engine.get_version_info().string}, "\t") + "\n")
	output.close()
	factory.free()
	viewport.queue_free()
	Cache.clear()
	quit(0 if ok else 1)
