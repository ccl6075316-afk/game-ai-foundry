extends SceneTree
## Offline-only exporter; runtime loads compressed ArrayMesh resources.

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1:
		quit(2)
		return
	var directory: String = args[0]
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(directory.path_join("mesh_build.json")))
	var material := ShaderMaterial.new()
	material.shader = load("res://scripts/aquarium/visitors/VisitorMaterialV2.gdshader")
	var image := Image.load_from_file(directory.path_join("visitor_atlas.png"))
	var texture := ImageTexture.create_from_image(image)
	ResourceSaver.save(texture,directory.path_join("visitor_atlas.res"),ResourceSaver.FLAG_COMPRESS)
	material.set_shader_parameter("visitor_atlas",load(directory.path_join("visitor_atlas.res")))
	ResourceSaver.save(material,directory.path_join("visitor_material.tres"))
	material=load(directory.path_join("visitor_material.tres"))
	for key: String in data:
		var entry: Dictionary=data[key]
		var arrays: Array=[]
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX]=v3(entry.vertices)
		arrays[Mesh.ARRAY_NORMAL]=v3(entry.normals)
		arrays[Mesh.ARRAY_TEX_UV]=v2(entry.uv)
		arrays[Mesh.ARRAY_TEX_UV2]=v2(entry.uv2)
		var format := 0
		for index in 4:
			arrays[Mesh.ARRAY_CUSTOM0+index]=PackedFloat32Array(entry["custom%d" % index])
			format |= Mesh.ARRAY_CUSTOM_RGBA_FLOAT << (Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT+index*3)
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays,[],{},format)
		if mesh.get_surface_count()!=1 or mesh.surface_get_array_len(0)!=entry.vertices.size()/3:
			push_error("Invalid mesh "+key)
			quit(2)
			return
		mesh.surface_set_material(0,material)
		mesh.custom_aabb=AABB(Vector3(-0.6,-0.08,-0.65),Vector3(1.2,2.1,1.3))
		var path:=directory.path_join("visitor_%s.res" % key)
		if ResourceSaver.save(mesh,path,ResourceSaver.FLAG_COMPRESS)!=OK:
			quit(2)
			return
		var cold:=ResourceLoader.load(path,"ArrayMesh",ResourceLoader.CACHE_MODE_IGNORE) as ArrayMesh
		var saved:=cold.surface_get_arrays(0)
		for index in 4:
			var actual: PackedFloat32Array=saved[Mesh.ARRAY_CUSTOM0+index]
			var expected: Array=entry["custom%d" % index]
			if actual.size()!=expected.size():
				quit(2)
				return
			for i in actual.size():
				if absf(actual[i]-float(expected[i]))>0.000001:
					push_error("Attribute changed on save: "+key)
					quit(2)
					return
		print("VISITOR_V2_MESH ",key," triangles=",mesh.surface_get_array_len(0)/3)
	quit(0)

func v3(values: Array) -> PackedVector3Array:
	var out:=PackedVector3Array()
	for i in range(0,values.size(),3): out.append(Vector3(values[i],values[i+1],values[i+2]))
	return out

func v2(values: Array) -> PackedVector2Array:
	var out:=PackedVector2Array()
	for i in range(0,values.size(),2): out.append(Vector2(values[i],values[i+1]))
	return out
