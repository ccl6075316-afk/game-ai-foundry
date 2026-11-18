extends SceneTree
## Exports native arrays, installed LOD indices and actual skin/morph palettes.
## --script <this file> -- <scratch output directory> [species ...]
const Exhibit = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const Cache = preload("res://scripts/aquarium/FishAppearanceCache.gd")
const ACTIONS := ["Swim", "Turn", "Ascend", "Dive"]
const CONTROL_KEYS := ["body_amplitude", "body_frequency", "fin_amplitude", "fin_frequency"]
const RANGE := {
	"Neutral": [0., 0., 0., 0.], "WideSlow": [2.5, .35, 2.5, .35],
	"WideFast": [2.5, 3., 2.5, 3.], "FinsOnly": [0., 0., 2.5, 3.],
	"BodyOnly": [2.5, 3., 0., 0.],
}
const MIXES := {
	"MixedLow": [.5, .7, .5, 1.3], "MixedMid": [1.5, 1.3, 1.25, .7],
	"Independent": [2.5, 3., .3, .35], "MaxDense": [2.5, 3., 2.5, 3.],
}

var pose_file: FileAccess
var pose_names: Array = []
var mesh_info: Array = []

func _initialize() -> void:
	run.call_deferred()

func save_json(path: String, data: Variant) -> void:
	var handle := FileAccess.open(path, FileAccess.WRITE)
	assert(handle != null, path)
	handle.store_string(JSON.stringify(data))
	handle.close()

func prepare(entry: Dictionary) -> Array:
	mesh_info.clear()
	var inventory := []
	for node in entry.model.find_children("*", "MeshInstance3D", true, false):
		var mesh: ArrayMesh = node.mesh
		var bind_indices := PackedInt32Array()
		var bind_names: Array[String] = []
		if node.skin != null:
			for i in node.skin.get_bind_count():
				var id: int = node.skin.get_bind_bone(i)
				if id < 0:
					id = entry.skeleton.find_bone(node.skin.get_bind_name(i))
				assert(id >= 0, "Unmapped skin bind")
				bind_indices.append(id)
				bind_names.append(entry.skeleton.get_bone_name(id))
		mesh_info.append({"node": node, "bind_indices": bind_indices})
		var surfaces := []
		var raw: Array = mesh.get("_surfaces")
		for si in mesh.get_surface_count():
			var a := mesh.surface_get_arrays(si)
			var points: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
			var morphs := []
			for shape in mesh.surface_get_blend_shape_arrays(si):
				var values: PackedVector3Array = shape[Mesh.ARRAY_VERTEX]
				if mesh.blend_shape_mode == Mesh.BLEND_SHAPE_MODE_NORMALIZED:
					for i in values.size():
						values[i] -= points[i]
				morphs.append(Array(values.to_byte_array().to_float32_array()))
			var indices: PackedInt32Array = a[Mesh.ARRAY_INDEX]
			var tiers := []
			var lods: Array = raw[si].get("lods", [])
			for i in range(0, lods.size(), 2):
				tiers.append([lods[i], Marshalls.raw_to_base64(lods[i + 1])])
			var material: Material = node.get_active_material(si)
			surfaces.append({
				"positions": Array(points.to_byte_array().to_float32_array()),
				"joints": Array(a[Mesh.ARRAY_BONES]) if a[Mesh.ARRAY_BONES] != null else [],
				"weights": Array(a[Mesh.ARRAY_WEIGHTS]) if a[Mesh.ARRAY_WEIGHTS] != null else [],
				"triangles": Array(indices), "morphs": morphs, "tiers": tiers,
				"index_width": raw[si].index_data.size() / indices.size(),
				"material": material.resource_name if material != null else "",
			})
		inventory.append({"name": String(node.name), "bindings": bind_names,
			"morph_count": mesh.get_blend_shape_count(), "surfaces": surfaces})
	return inventory

func store_palette(transform: Transform3D, values: PackedFloat32Array) -> void:
	for axis in 3:
		values.append(transform.basis.x[axis])
		values.append(transform.basis.y[axis])
		values.append(transform.basis.z[axis])
		values.append(transform.origin[axis])

func capture_pose(entry: Dictionary, name: String, t: float) -> void:
	var skeleton: Skeleton3D = entry.skeleton
	skeleton.force_update_all_bone_transforms()
	var inv: Transform3D = entry.carrier.global_transform.affine_inverse()
	var relative := inv * skeleton.global_transform
	var values := PackedFloat32Array()
	for mesh in mesh_info:
		var node: MeshInstance3D = mesh.node
		if mesh.bind_indices.is_empty():
			store_palette(inv * node.global_transform, values)
		else:
			for i in mesh.bind_indices.size():
				store_palette(relative * skeleton.get_bone_global_pose(mesh.bind_indices[i]) * node.skin.get_bind_pose(i), values)
		for i in node.get_blend_shape_count():
			values.append(node.get_blend_shape_value(i))
	pose_names.append([name, t])
	pose_file.store_buffer(values.to_byte_array())

func controls(controller: RefCounted, values: Array, immediate := false) -> void:
	var fields := {}
	for i in CONTROL_KEYS.size():
		fields[CONTROL_KEYS[i]] = values[i]
	controller.set_motion_controls(fields, immediate)

func phases(entry: Dictionary, label: String, count: int) -> void:
	for i in count:
		var t := float(entry.profile.period_seconds) * i / count
		entry.controller.seek(t)
		capture_pose(entry, label, t)

func capture_sequence(entry: Dictionary) -> void:
	var controller: RefCounted = entry.controller
	var player: AnimationPlayer = entry.player
	var skeleton: Skeleton3D = entry.skeleton
	player.stop()
	skeleton.reset_bone_poses()
	capture_pose(entry, "Static", 0.)
	player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	var clip: String = entry.profile.base_clip
	player.play(clip)
	for i in 25:
		var t := player.get_animation(clip).length * i / 25.
		player.seek(t, true)
		player.advance(0.)
		capture_pose(entry, "Native", t)
	player.stop()
	skeleton.reset_bone_poses()
	for action in ACTIONS:
		assert(controller.set_action(action, true))
		controller.step(0.)
		phases(entry, action, 16)
	for action in ["Turn", "Ascend", "Dive", "Swim"]:
		controller.set_action(action, false)
		for i in 4:
			var step := float(entry.profile.transition_seconds) / 4.
			controller.step(step)
			capture_pose(entry, "Transition:" + action, step * (i + 1))
	for name in RANGE:
		controls(controller, RANGE[name], true)
		phases(entry, "Range:" + name, 16)
	for name in ["Neutral", "WideSlow", "WideFast", "FinsOnly"]:
		controls(controller, RANGE[name])
		for i in 4:
			controller.step(.125)
			capture_pose(entry, "RangeTransition:" + name, (i + 1) * .125)
	for name in MIXES:
		controls(controller, MIXES[name], true)
		phases(entry, "Clearance:" + name, 64)
	for i in 32:
		var f := float(i) / 31.
		controls(controller, [2.5 * (1. - f), .35 + 2.65 * f, 2.5 * f, 3. - 2.65 * f])
		controller.step(.0625)
		capture_pose(entry, "Clearance:ControlSweep", (i + 1) * .0625)
	assert(pose_names.size() == 490)
	if controller.has_method("play_jaw_action"):
		controls(controller, [1., 1., 1., 1.], true)
		controller.set_action("Swim", true)
		controller.play_jaw_action()
		var duration := 10.5 if entry.species == "whale_shark" else 2.4
		for i in roundi(duration * 60.) + 1:
			capture_pose(entry, "Mouth", i / 60.)
			controller.step(1. / 60.)

func run() -> void:
	var args := OS.get_cmdline_user_args()
	assert(not args.is_empty())
	var directory := args[0]
	DirAccess.make_dir_recursive_absolute(directory)
	Cache.begin_entry()
	var factory := Exhibit.new()
	factory._load_profiles()
	for species in Exhibit.SPECIES:
		if args.size() > 1 and species not in args.slice(1):
			continue
		var profile: Dictionary = factory.profiles[species]
		var bucket := Node3D.new()
		root.add_child(bucket)
		var length := float(profile.real_length_cm) / 100.
		factory._add_fish(bucket, species, length, profile)
		var entry: Dictionary = factory.fish.pop_back()
		pose_names.clear()
		var inventory := prepare(entry)
		var prefix := directory.path_join(species)
		pose_file = FileAccess.open(prefix + ".f32", FileAccess.WRITE)
		assert(pose_file != null)
		capture_sequence(entry)
		pose_file.close()
		save_json(prefix + ".json", {
			"species": species, "length_m": length,
			"model_sha256": FileAccess.get_sha256(entry.model.scene_file_path),
			"lod_sha256": FileAccess.get_sha256("res://assets/models/fish/motion/fish-lod.res"),
			"exhibit_sha256": FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd"),
			"controller_sha256": FileAccess.get_sha256(entry.controller.get_script().resource_path),
			"profile": entry.profile, "mesh": inventory, "poses": pose_names,
		})
		print("CONTACT_POSES ", species, " ", pose_names.size())
		bucket.queue_free()
		await process_frame
	factory.free()
	Cache.clear()
	quit()
