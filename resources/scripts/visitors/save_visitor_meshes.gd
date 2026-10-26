extends SceneTree
## Offline exporter invoked by build_visitors.py; never loaded by the game.

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1:
		push_error("Expected visitor asset output directory")
		quit(2)
		return
	var directory: String = args[0]
	var payload: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(directory.path_join("mesh_build.json")))
	var shader := load("res://scripts/aquarium/visitors/VisitorMaterial.gdshader") as Shader
	var material := ShaderMaterial.new()
	material.shader = shader
	# Direct image loading also supports a brand-new atlas before editor import.
	var texture := ImageTexture.create_from_image(Image.load_from_file(directory.path_join("visitor_atlas.png")))
	var texture_path := directory.path_join("visitor_atlas.res")
	ResourceSaver.save(texture, texture_path, ResourceSaver.FLAG_COMPRESS)
	material.set_shader_parameter("visitor_atlas", load(texture_path))
	var material_path := directory.path_join("visitor_material.tres")
	if ResourceSaver.save(material, material_path) != OK:
		quit(2)
		return
	material = load(material_path) as ShaderMaterial
	for key: String in payload:
		var data: Dictionary = payload[key]
		var arrays: Array = []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = vec3_array(data.vertices)
		arrays[Mesh.ARRAY_NORMAL] = vec3_array(data.normals)
		arrays[Mesh.ARRAY_TEX_UV] = vec2_array(data.uvs)
		arrays[Mesh.ARRAY_TEX_UV2] = vec2_array(data.uv2s)
		# Float custom attributes carry geometry data without vertex-color gamma.
		arrays[Mesh.ARRAY_CUSTOM0] = PackedFloat32Array(data.pivots)
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT)
		if mesh.get_surface_count() != 1 or mesh.surface_get_array_len(0) != data.vertices.size() / 3:
			push_error("Mesh array generation failed: %s" % key)
			quit(2)
			return
		mesh.surface_set_material(0, material)
		# Walking extremities extend outside their rest mesh AABB.
		mesh.custom_aabb = AABB(Vector3(-0.4, -0.04, -0.55), Vector3(0.8, float(data.height)+0.10, 1.1))
		var error := ResourceSaver.save(mesh, directory.path_join("visitor_%s.res" % key), ResourceSaver.FLAG_COMPRESS)
		if error != OK:
			push_error("Mesh export failed: %s (%d)" % [key, error])
			quit(2)
			return
		var cold := ResourceLoader.load(directory.path_join("visitor_%s.res" % key), "ArrayMesh", ResourceLoader.CACHE_MODE_IGNORE) as ArrayMesh
		if cold == null or cold.get_surface_count() != 1:
			push_error("Saved mesh could not be reloaded: %s" % key)
			quit(2)
			return
		var stored: PackedFloat32Array = cold.surface_get_arrays(0)[Mesh.ARRAY_CUSTOM0]
		if stored.size() != data.pivots.size():
			push_error("Joint attribute size changed on export: %s" % key)
			quit(2)
			return
		for i in stored.size():
			if absf(stored[i] - float(data.pivots[i])) > 0.000001:
				push_error("Joint pivot changed on export: %s" % key)
				quit(2)
				return
		print("VISITOR_MESH %s vertices=%d triangles=%d" % [key, mesh.surface_get_array_len(0), data.triangles])
	quit(0)

func vec3_array(values: Array) -> PackedVector3Array:
	var out := PackedVector3Array()
	for i in range(0, values.size(), 3):
		out.append(Vector3(values[i], values[i+1], values[i+2]))
	return out

func vec2_array(values: Array) -> PackedVector2Array:
	var out := PackedVector2Array()
	for i in range(0, values.size(), 2):
		out.append(Vector2(values[i], values[i+1]))
	return out
