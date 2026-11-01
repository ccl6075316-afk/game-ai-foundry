extends RefCounted
## Validation-only logical partitions. Production entry remains the original one-surface mesh.
const POSITION_TOLERANCE := 0.000001
const UV_TOLERANCE := 0.000001
const NORMAL_TOLERANCE := 0.001
const WEIGHT_TOLERANCE := 1.0 / 65535.0 + 0.000001
const CELL := 0.00001

static func cycle_key(a: int, b: int, c: int) -> String:
	var values := ["%d:%d:%d" % [a, b, c], "%d:%d:%d" % [b, c, a], "%d:%d:%d" % [c, a, b]]
	values.sort()
	return values[0]

static func skin_weights(joints: Variant, weights: Variant, offset: int, count: int, names: Array) -> Dictionary:
	var result: Dictionary = {}
	for k in count:
		var weight := float(weights[offset + k])
		if weight <= 0.0000001: continue
		var name: String = names[int(joints[offset + k])]
		result[name] = float(result.get(name, 0.0)) + weight
	return result

static func weight_error(a: Dictionary, b: Dictionary) -> float:
	var error := 0.0
	for key in a: error = maxf(error, absf(float(a[key]) - float(b.get(key, 0.0))))
	for key in b: error = maxf(error, absf(float(b[key]) - float(a.get(key, 0.0))))
	return error

static func ordinary_surfaces(entry: Dictionary) -> Array:
	var rows: Array = []
	for node in entry.model.find_children("*", "MeshInstance3D", true, false):
		for surface in node.mesh.get_surface_count():
			rows.append({"name": str(node.name), "source_surface": surface, "mesh": node, "arrays": node.mesh.surface_get_arrays(surface), "material": node.get_active_material(surface)})
	return rows

static func surfaces(entry: Dictionary, spec: Dictionary) -> Dictionary:
	if not spec.has("packed_parts_manifest"):
		return {"surfaces": ordinary_surfaces(entry), "packed": false}
	var path: String = spec.packed_parts_manifest
	assert(path.is_absolute_path() and FileAccess.get_sha256(path) == spec.packed_parts_manifest_sha256, "Stale packed part manifest")
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
	assert(manifest.ok and manifest.kind == "fish_packed_part_manifest" and manifest.schema_version == 1)
	assert(manifest.model_sha256 == FileAccess.get_sha256(spec.model) and manifest.model == spec.model)
	assert(manifest.body == spec.body and manifest.parts.size() == 9 and manifest.body_opacity.ok)
	var expected_fins: Array = spec.fins.keys() if spec.fins is Dictionary else spec.fins
	assert(expected_fins.size() == 7)
	for name in expected_fins: assert(name in manifest.fins)
	var names_in_parts: Dictionary = {}
	var body_surfaces: Array = []
	for part in manifest.parts:
		assert(part.name == spec.body or part.name in expected_fins)
		names_in_parts[part.name] = int(names_in_parts.get(part.name, 0)) + 1
		if part.name == spec.body: body_surfaces.append(int(part.source_surface))
	assert(names_in_parts.size() == 8 and names_in_parts.get(spec.body, 0) == 2)
	for name in expected_fins: assert(names_in_parts.get(name, 0) == 1, "Missing/duplicated packed logical fin")
	body_surfaces.sort(); assert(body_surfaces == [0, 1])
	var nodes: Array = entry.model.find_children("*", "MeshInstance3D", true, false)
	assert(nodes.size() == 1 and nodes[0].mesh.get_surface_count() == 1, "Packed runtime must stay one actual mesh/surface")
	var mesh: MeshInstance3D = nodes[0]
	assert(mesh.skin != null and mesh.material_override == null)
	var arrays: Array = mesh.mesh.surface_get_arrays(0)
	var positions: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	var joints: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
	var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	assert(indices.size() == int(manifest.triangles) * 3 and joints.size() % positions.size() == 0)
	var slots: int = joints.size() / positions.size()
	var actual_names: Array = []
	for j in mesh.skin.get_bind_count():
		var bone := mesh.skin.get_bind_bone(j)
		if bone < 0: bone = entry.skeleton.find_bone(mesh.skin.get_bind_name(j))
		assert(bone >= 0)
		actual_names.append(entry.skeleton.get_bone_name(bone))
	var attrs: Dictionary = manifest.attributes
	var cells: Dictionary = {}
	var source_weights: Array = []
	for i in int(manifest.vertex_count):
		var p := Vector3(attrs.POSITION[i][0], attrs.POSITION[i][1], attrs.POSITION[i][2])
		var cell := Vector3i((p / CELL).floor())
		if not cells.has(cell): cells[cell] = []
		cells[cell].append(i)
		source_weights.append(skin_weights(attrs.JOINTS_0[i], attrs.WEIGHTS_0[i], 0, 4, manifest.joint_names))
	var matches: Array = []
	var maximum := {"position": 0.0, "uv": 0.0, "normal_component": 0.0, "weight": 0.0}
	var source_seen: Dictionary = {}
	for i in positions.size():
		var candidates: Array = []
		var base := Vector3i((positions[i] / CELL).floor())
		var actual_weight := skin_weights(joints, weights, i * slots, slots, actual_names)
		for dx in [-1, 0, 1]:
			for dy in [-1, 0, 1]:
				for dz in [-1, 0, 1]:
					for source in cells.get(base + Vector3i(dx, dy, dz), []):
						var p := Vector3(attrs.POSITION[source][0], attrs.POSITION[source][1], attrs.POSITION[source][2])
						var uv := Vector2(attrs.TEXCOORD_0[source][0], attrs.TEXCOORD_0[source][1])
						var n := Vector3(attrs.NORMAL[source][0], attrs.NORMAL[source][1], attrs.NORMAL[source][2])
						var pe := positions[i].distance_to(p)
						var ue := uvs[i].distance_to(uv)
						var ne := (normals[i] - n).abs()
						var normal_error := maxf(ne.x, maxf(ne.y, ne.z))
						var we := weight_error(actual_weight, source_weights[source])
						if pe <= POSITION_TOLERANCE and ue <= UV_TOLERANCE and normal_error <= NORMAL_TOLERANCE and we <= WEIGHT_TOLERANCE:
							candidates.append(source); source_seen[source] = true
							maximum.position = maxf(maximum.position, pe); maximum.uv = maxf(maximum.uv, ue); maximum.normal_component = maxf(maximum.normal_component, normal_error); maximum.weight = maxf(maximum.weight, we)
		assert(not candidates.is_empty(), "Actual packed vertex unmatched by position/UV/normal/named skin: " + str(i))
		matches.append(candidates)
	assert(source_seen.size() == int(manifest.vertex_count), "Source vertex lost during import")
	var face_lookup: Dictionary = {}
	var source_indices: Array = manifest.indices
	var face_owner: Dictionary = {}
	for pi in manifest.parts.size():
		var part: Dictionary = manifest.parts[pi]
		for at in range(int(part.index_range[0]), int(part.index_range[1]), 3):
			var face: int = at / 3
			assert(not face_owner.has(face)); face_owner[face] = pi
			var key := cycle_key(source_indices[at], source_indices[at + 1], source_indices[at + 2])
			if not face_lookup.has(key): face_lookup[key] = []
			face_lookup[key].append(face)
	assert(face_owner.size() == int(manifest.triangles))
	var consumed: Dictionary = {}
	var actual_faces: Dictionary = {}
	for pi in manifest.parts.size(): actual_faces[pi] = []
	# Godot changes glTF's CCW convention to its CW indices. One fixed reversal for every face.
	for at in range(0, indices.size(), 3):
		var possible: Dictionary = {}
		for a in matches[indices[at]]:
			for b in matches[indices[at + 2]]:
				for c in matches[indices[at + 1]]:
					for face in face_lookup.get(cycle_key(a, b, c), []):
						if not consumed.has(face): possible[face] = true
		assert(not possible.is_empty(), "Missing/duplicated/reversed imported triangle at " + str(at / 3))
		var owners: Dictionary = {}
		for face in possible: owners[face_owner[face]] = true
		assert(owners.size() == 1, "Triangle matches conflicting logical parts")
		var face: int = possible.keys()[0]
		consumed[face] = true
		actual_faces[face_owner[face]].append([indices[at], indices[at + 1], indices[at + 2]])
	assert(consumed.size() == int(manifest.triangles), "Packed triangle multiset not fully consumed")
	var result: Array = []
	for pi in manifest.parts.size():
		var part: Dictionary = manifest.parts[pi]
		var used: Dictionary = {}
		var chosen: Array[int] = []
		var compact_indices := PackedInt32Array()
		for triangle in actual_faces[pi]:
			for old in triangle:
				if not used.has(old): used[old] = chosen.size(); chosen.append(old)
				compact_indices.append(used[old])
		assert(compact_indices.size() == int(part.triangles) * 3)
		var compact: Array = []; compact.resize(Mesh.ARRAY_MAX)
		var vp := PackedVector3Array(); var np := PackedVector3Array(); var uvp := PackedVector2Array(); var jp := PackedInt32Array(); var wp := PackedFloat32Array()
		for old in chosen:
			vp.append(positions[old]); np.append(normals[old]); uvp.append(uvs[old])
			for slot in slots: jp.append(joints[old * slots + slot]); wp.append(weights[old * slots + slot])
		compact[Mesh.ARRAY_VERTEX] = vp; compact[Mesh.ARRAY_NORMAL] = np; compact[Mesh.ARRAY_TEX_UV] = uvp; compact[Mesh.ARRAY_BONES] = jp; compact[Mesh.ARRAY_WEIGHTS] = wp; compact[Mesh.ARRAY_INDEX] = compact_indices
		result.append({"name": part.name, "source_surface": part.source_surface, "mesh": mesh, "arrays": compact, "material": mesh.get_active_material(0), "actual_vertex_ids": chosen})
	return {"packed": true, "surfaces": result, "proof": {"ok": true, "manifest_sha256": FileAccess.get_sha256(path), "model_sha256": manifest.model_sha256, "logical_surfaces": result.size(), "logical_parts": 8, "triangles_consumed": consumed.size(), "actual_vertices": positions.size(), "source_vertices": manifest.vertex_count, "winding": "all triangles fixed glTF CCW to Godot CW reversal", "maximum_import_errors": maximum, "mapping_tolerances": {"position": POSITION_TOLERANCE, "uv": UV_TOLERANCE, "normal_component": NORMAL_TOLERANCE, "named_weight": WEIGHT_TOLERANCE}, "runtime_meshes": 1, "runtime_surfaces": 1, "source_arrays_modified": false}}

static func make_probes(entry: Dictionary, packed: Dictionary, only_names: Array = []) -> Dictionary:
	assert(packed.packed)
	var probes: Dictionary = {}
	for row in packed.surfaces:
		if not only_names.is_empty() and not row.name in only_names: continue
		var original: MeshInstance3D = row.mesh
		if not probes.has(row.name):
			var probe := MeshInstance3D.new(); probe.name = row.name + "_validation_probe"
			original.get_parent().add_child(probe); probe.transform = original.transform; probe.skin = original.skin; probe.skeleton = original.skeleton; probe.mesh = ArrayMesh.new(); probe.hide()
			probes[row.name] = probe
		var target: MeshInstance3D = probes[row.name]
		var array_mesh := target.mesh as ArrayMesh
		array_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, row.arrays)
		array_mesh.surface_set_material(array_mesh.get_surface_count() - 1, row.material)
	return probes

static func clear_probes(probes: Dictionary) -> void:
	for probe in probes.values(): probe.free()
