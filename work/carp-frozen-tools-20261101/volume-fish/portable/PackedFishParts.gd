extends RefCounted
## Arbitrary explicit validation partitions. Never attach probes to the production runtime.
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

static func failure(message: String) -> Dictionary:
	return {"ok": false, "failures": [{"kind": "validation", "code": "portable_import_invalid", "message": message.left(1200)}]}

static func surfaces(entry: Dictionary, spec: Dictionary) -> Dictionary:
	var path: String = spec.get("packed_parts_manifest", "")
	if not path.is_absolute_path() or not FileAccess.file_exists(path) or FileAccess.get_sha256(path) != spec.get("packed_parts_manifest_sha256", ""):
		return failure("Missing/stale portable part manifest")
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary: return failure("Part manifest is not an object")
	var manifest: Dictionary = parsed
	if not manifest.get("ok", false) or manifest.get("kind") != "fish_portable_part_manifest" or manifest.get("schema_version") != 1:
		return failure("Unsupported portable part manifest")
	if manifest.get("model_sha256") != FileAccess.get_sha256(spec.model) or manifest.get("model") != spec.model:
		return failure("Stale portable model")
	if not manifest.get("parts") is Array or manifest.parts.is_empty() or not manifest.get("body_opacity", {}).get("ok", false):
		return failure("Explicit parts and opaque body proof required")
	if not manifest.has_all(["vertex_count", "triangles", "indices", "attributes", "joint_names"]) or not manifest.indices is Array or not manifest.attributes is Dictionary or not manifest.joint_names is Array:
		return failure("Incomplete canonical arrays")
	var vertex_count := int(manifest.vertex_count)
	if vertex_count < 1 or int(manifest.triangles) < 1 or manifest.indices.size() != int(manifest.triangles) * 3 or manifest.joint_names.is_empty():
		return failure("Invalid canonical counts")
	var lanes := {"POSITION":3,"NORMAL":3,"TEXCOORD_0":2,"JOINTS_0":4,"WEIGHTS_0":4}
	for semantic in lanes:
		if not manifest.attributes.get(semantic) is Array or manifest.attributes[semantic].size() != vertex_count:
			return failure("Invalid canonical attribute count: " + semantic)
		for values in manifest.attributes[semantic]:
			if not values is Array or values.size() != int(lanes[semantic]): return failure("Invalid canonical attribute lanes")
			for value in values:
				if not (value is float or value is int) or not is_finite(float(value)): return failure("Nonfinite canonical attribute")
				if semantic == "JOINTS_0" and (int(value) != value or value < 0 or value >= manifest.joint_names.size()): return failure("Invalid canonical joint index")
	for index in manifest.indices:
		if not (index is float or index is int) or int(index) != index or index < 0 or index >= vertex_count: return failure("Invalid canonical triangle index")
	var names_in_parts: Dictionary = {}
	var owned_vertices: Dictionary = {}; var owned_indices: Dictionary = {}
	var opaque_parts := 0
	for part in manifest.parts:
		if not part is Dictionary or not part.has_all(["name", "role", "source_node", "source_surface", "vertex_range", "index_range", "triangles", "opaque_uv"]):
			return failure("Incomplete explicit part inventory")
		var identity := str(part.source_node) + ":" + str(part.source_surface)
		if names_in_parts.has(identity): return failure("Duplicate explicit source surface")
		names_in_parts[identity] = true
		if part.opaque_uv: opaque_parts += 1
		if part.vertex_range.size() != 2 or part.index_range.size() != 2: return failure("Invalid partition ranges")
		var lo := int(part.vertex_range[0]); var hi := int(part.vertex_range[1])
		var start := int(part.index_range[0]); var finish := int(part.index_range[1])
		if lo < 0 or hi <= lo or hi > int(manifest.vertex_count) or start < 0 or finish <= start or finish > manifest.indices.size() or start % 3 != 0 or finish % 3 != 0:
			return failure("Invalid partition bounds")
		for at in range(lo, hi):
			if owned_vertices.has(at): return failure("Duplicate partition vertex")
			owned_vertices[at] = true
		for at in range(start, finish):
			if owned_indices.has(at) or int(manifest.indices[at]) < lo or int(manifest.indices[at]) >= hi:
				return failure("Duplicate or escaped partition index")
			owned_indices[at] = true
	if opaque_parts < 1 or owned_vertices.size() != int(manifest.vertex_count) or owned_indices.size() != manifest.indices.size():
		return failure("Incomplete once-only body/vertex/index inventory")
	var nodes: Array = entry.model.find_children("*", "MeshInstance3D", true, false)
	if not (nodes.size() == 1 and nodes[0].mesh.get_surface_count() == 1): return failure("Packed runtime must stay one actual mesh/surface")
	var mesh: MeshInstance3D = nodes[0]
	if not (mesh.skin != null and mesh.material_override == null): return failure("Invalid portable imported arrays/skin/triangles")
	var arrays: Array = mesh.mesh.surface_get_arrays(0)
	var positions: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	var joints: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
	var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	if not (indices.size() == int(manifest.triangles) * 3 and joints.size() % positions.size() == 0): return failure("Invalid portable imported arrays/skin/triangles")
	var slots: int = joints.size() / positions.size()
	var actual_names: Array = []
	for j in mesh.skin.get_bind_count():
		var bone := mesh.skin.get_bind_bone(j)
		if bone < 0: bone = entry.skeleton.find_bone(mesh.skin.get_bind_name(j))
		if not (bone >= 0): return failure("Invalid portable imported arrays/skin/triangles")
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
		if not (not candidates.is_empty()): return failure("Actual packed vertex unmatched by position/UV/normal/named skin: " + str(i))
		matches.append(candidates)
	if not (source_seen.size() == int(manifest.vertex_count)): return failure("Source vertex lost during import")
	var face_lookup: Dictionary = {}
	var source_indices: Array = manifest.indices
	var face_owner: Dictionary = {}
	for pi in manifest.parts.size():
		var part: Dictionary = manifest.parts[pi]
		for at in range(int(part.index_range[0]), int(part.index_range[1]), 3):
			var face: int = at / 3
			if face_owner.has(face): return failure("Duplicate face ownership")
			face_owner[face] = pi
			var key := cycle_key(source_indices[at], source_indices[at + 1], source_indices[at + 2])
			if not face_lookup.has(key): face_lookup[key] = []
			face_lookup[key].append(face)
	if not (face_owner.size() == int(manifest.triangles)): return failure("Invalid portable imported arrays/skin/triangles")
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
		if not (not possible.is_empty()): return failure("Missing/duplicated/reversed imported triangle at " + str(at / 3))
		var owners: Dictionary = {}
		for face in possible: owners[face_owner[face]] = true
		if not (owners.size() == 1): return failure("Triangle matches conflicting logical parts")
		var face: int = possible.keys()[0]
		consumed[face] = true
		actual_faces[face_owner[face]].append([indices[at], indices[at + 1], indices[at + 2]])
	if not (consumed.size() == int(manifest.triangles)): return failure("Packed triangle multiset not fully consumed")
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
		if not (compact_indices.size() == int(part.triangles) * 3): return failure("Invalid portable imported arrays/skin/triangles")
		var compact: Array = []; compact.resize(Mesh.ARRAY_MAX)
		var vp := PackedVector3Array(); var np := PackedVector3Array(); var uvp := PackedVector2Array(); var jp := PackedInt32Array(); var wp := PackedFloat32Array()
		for old in chosen:
			vp.append(positions[old]); np.append(normals[old]); uvp.append(uvs[old])
			for slot in slots: jp.append(joints[old * slots + slot]); wp.append(weights[old * slots + slot])
		compact[Mesh.ARRAY_VERTEX] = vp; compact[Mesh.ARRAY_NORMAL] = np; compact[Mesh.ARRAY_TEX_UV] = uvp; compact[Mesh.ARRAY_BONES] = jp; compact[Mesh.ARRAY_WEIGHTS] = wp; compact[Mesh.ARRAY_INDEX] = compact_indices
		result.append({"name": part.name, "role": part.role, "opaque_uv": part.opaque_uv, "source_node": part.source_node, "source_surface": part.source_surface, "mesh": mesh, "arrays": compact, "material": mesh.get_active_material(0), "actual_vertex_ids": chosen})
	return {"ok": true, "packed": true, "surfaces": result, "proof": {"ok": true, "manifest_sha256": FileAccess.get_sha256(path), "model_sha256": manifest.model_sha256, "logical_surfaces": result.size(), "logical_parts": manifest.parts.size(), "triangles_consumed": consumed.size(), "actual_vertices": positions.size(), "source_vertices": manifest.vertex_count, "winding": "all triangles fixed glTF CCW to Godot CW reversal", "maximum_import_errors": maximum, "mapping_tolerances": {"position": POSITION_TOLERANCE, "uv": UV_TOLERANCE, "normal_component": NORMAL_TOLERANCE, "named_weight": WEIGHT_TOLERANCE}, "runtime_meshes": 1, "runtime_surfaces": 1, "source_arrays_modified": false}}

static func make_probes(entry: Dictionary, packed: Dictionary, only_names: Array = []) -> Dictionary:
	if not packed.get("packed", false): return {}
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
