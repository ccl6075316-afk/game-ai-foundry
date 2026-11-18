extends SceneTree
## Exports the ArrayMesh layout used by the production raw-GLB loaders.
## godot --headless --path <game> --script <this file> -- <scratch/input.json> [--verify-installed]

func _initialize() -> void:
	_export.call_deferred()

func _export() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1 or (args.size() == 2 and args[1] == "--verify-installed"))
	var verify_installed := "--verify-installed" in args
	var output := FileAccess.open(args[0], FileAccess.WRITE)
	assert(output != null)
	var folder := "res://assets/models/fish/"
	var entries := {}
	for file in DirAccess.get_files_at(folder):
		if not file.ends_with(".glb"):
			continue
		var path := folder.path_join(file)
		var document := GLTFDocument.new()
		var state := GLTFState.new()
		assert(document.append_from_file(path, state) == OK, path)
		var model := document.generate_scene(state) as Node3D
		assert(model != null, path)
		if verify_installed:
			model.scene_file_path = path
			assert(load("res://scripts/aquarium/FishMeshLod.gd").apply(model, file.get_basename()))
		root.add_child(model)
		var meshes := {}
		for node in model.find_children("*", "MeshInstance3D", true, false):
			var mesh: ArrayMesh = node.mesh
			var surfaces := []
			for si in mesh.get_surface_count():
				var arrays := mesh.surface_get_arrays(si)
				var positions: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
				var relative: Transform3D = model.global_transform.affine_inverse() * node.global_transform
				var model_positions := PackedVector3Array()
				for point in positions:
					model_positions.append(relative * point)
				var raw: Dictionary = mesh.get("_surfaces")[si]
				var morph := PackedByteArray()
				morph.resize(positions.size())
				for shape in mesh.surface_get_blend_shape_arrays(si):
					var offsets: PackedVector3Array = shape[Mesh.ARRAY_VERTEX]
					for vertex in offsets.size():
						var delta := offsets[vertex]
						if mesh.blend_shape_mode == Mesh.BLEND_SHAPE_MODE_NORMALIZED:
							delta -= positions[vertex]
						if delta.length_squared() > 1e-12:
							morph[vertex] = 1
				var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
				var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
				var joints: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
				var skin_joints: Array[String] = []
				if node.skin != null:
					var skeleton := node.get_node_or_null(node.skeleton) as Skeleton3D
					for bind in node.skin.get_bind_count():
						var joint: StringName = node.skin.get_bind_name(bind)
						if joint.is_empty() and skeleton != null:
							joint = skeleton.get_bone_name(node.skin.get_bind_bone(bind))
						skin_joints.append(joint)
				var surface := {
					"positions": Array(positions.to_byte_array().to_float32_array()),
					"model_positions": Array(model_positions.to_byte_array().to_float32_array()),
					"normals": Array(arrays[Mesh.ARRAY_NORMAL].to_byte_array().to_float32_array()) if arrays[Mesh.ARRAY_NORMAL] != null else [],
					"uv": Array(arrays[Mesh.ARRAY_TEX_UV].to_byte_array().to_float32_array()) if arrays[Mesh.ARRAY_TEX_UV] != null else [],
					"indices": Array(indices),
					"weights": Array(weights) if weights != null else [],
					"joints": Array(joints) if joints != null else [],
					"skin_joints": skin_joints,
					"morph": Array(morph),
					"index_width": 2 if raw.index_data.size() == indices.size() * 2 else 4,
					"index_sha256": _sha(raw.index_data),
					"material": String(mesh.surface_get_material(si).resource_name) if mesh.surface_get_material(si) else "",
				}
				if verify_installed:
					var levels := []
					var serialized: Array = raw.get("lods", [])
					for level in range(0, serialized.size(), 2):
						levels.append(Marshalls.raw_to_base64(serialized[level + 1]))
					surface["installed_lods"] = levels
				surfaces.append(surface)
			assert(not meshes.has(String(node.name)), str(node.name))
			meshes[String(node.name)] = surfaces
		entries[file.get_basename()] = {"sha256": FileAccess.get_sha256(path), "meshes": meshes}
		model.free()
	output.store_string(JSON.stringify(entries, "", false, true))
	output.close()
	quit()

func _sha(bytes: PackedByteArray) -> String:
	var digest := HashingContext.new()
	digest.start(HashingContext.HASH_SHA256)
	digest.update(bytes)
	return digest.finish().hex_encode()
