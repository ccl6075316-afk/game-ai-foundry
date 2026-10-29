extends SceneTree
## Read-only base geometry counts from the actual production fish factory.
const FACTORY = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const CACHE = preload("res://scripts/aquarium/FishAppearanceCache.gd")
var output := ""
var bindings := {}

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 1)
	output = args[0].simplify_path()
	var expected := ProjectSettings.globalize_path("res://../plans/reviews/fish-part-inventory-20261029").simplify_path()
	assert(output == expected and output.is_absolute_path())
	assert(DirAccess.make_dir_recursive_absolute(output) == OK)
	call_deferred("_run")

func _bind(path: String) -> void:
	bindings[path] = FileAccess.get_sha256(path)

func _triangles(primitive: int, vertices: int, indices: int) -> int:
	assert(primitive == Mesh.PRIMITIVE_TRIANGLES, "Unexpected primitive; no guessed face count")
	var count := indices if indices > 0 else vertices
	assert(count % 3 == 0)
	return count / 3

func _category(name: String) -> String:
	var lower := name.to_lower()
	if "body" in lower: return "body"
	for prefix in ["anal", "caudal", "dorsal", "pectoral", "pelvic", "adipose"]:
		if prefix in lower: return "fin"
	if lower == "tail_fin": return "fin"
	if "eye" in lower or "iris" in lower or "pupil" in lower: return "eye"
	if "jaw" in lower or "oral" in lower or "lip" in lower or "mouth" in lower: return "mouth"
	if "barbel" in lower: return "barbel"
	if lower == "cephalofoil": return "head_structure"
	if "head" in lower or "frontal" in lower: return "head_overlay"
	return "other"

func _inspect(model: Node3D) -> Dictionary:
	var parts := []
	var totals := {"triangles":0,"vertices":0,"surfaces":0,"parts":0,"hidden_triangles":0,"hidden_vertices":0}
	var measured := AABB()
	var first := true
	for raw in model.find_children("*", "MeshInstance3D", true, false):
		var node := raw as MeshInstance3D
		assert(node.mesh is ArrayMesh)
		var visible := node.is_visible_in_tree()
		var part := {"name":str(node.name),"node_path":str(model.get_path_to(node)),"category":_category(str(node.name)),"visible":visible,"triangles":0,"vertices":0,"surfaces":[]}
		for si in node.mesh.get_surface_count():
			var arrays := node.mesh.surface_get_arrays(si)
			var nv: int = arrays[Mesh.ARRAY_VERTEX].size()
			var ni: int = arrays[Mesh.ARRAY_INDEX].size() if arrays[Mesh.ARRAY_INDEX] != null else 0
			var nt := _triangles(node.mesh.surface_get_primitive_type(si), nv, ni)
			var lod_rows := []
			var stored: Array = (node.mesh as ArrayMesh).get("_surfaces")[si].get("lods", [])
			assert(stored.size() % 2 == 0)
			for at in range(0, stored.size(), 2):
				var lod_data: Variant = stored[at+1]
				var index_stride := RenderingServer.mesh_surface_get_format_index_stride(node.mesh.surface_get_format(si),nv)
				assert(index_stride in [2,4])
				if lod_data is PackedByteArray: assert(lod_data.size() % index_stride == 0)
				var lod_count: int = lod_data.size()/index_stride if lod_data is PackedByteArray else lod_data.size()
				assert(lod_count > 0)
				lod_rows.append({"threshold":stored[at],"triangles":_triangles(Mesh.PRIMITIVE_TRIANGLES,nv,lod_count)})
			var digest := HashingContext.new(); digest.start(HashingContext.HASH_SHA256); digest.update(var_to_bytes(arrays))
			var material := node.get_active_material(si)
			part.surfaces.append({"surface":si,"vertices":nv,"triangles":nt,"arrays_sha256":digest.finish().hex_encode(),"lods":lod_rows,"material_type":material.get_class() if material else "missing","material_path":material.resource_path if material else ""})
			part.vertices += nv; part.triangles += nt
		parts.append(part)
		if visible:
			totals.triangles += part.triangles; totals.vertices += part.vertices
			totals.surfaces += part.surfaces.size(); totals.parts += 1
			var box: AABB = node.global_transform * node.get_aabb()
			measured = box if first else measured.merge(box); first = false
		else:
			totals.hidden_triangles += part.triangles; totals.hidden_vertices += part.vertices
	parts.sort_custom(func(a,b):return a.triangles > b.triangles)
	for part in parts: part["share_of_visible_fish"] = float(part.triangles)/maxf(totals.triangles,1.0) if part.visible else 0.0
	return {"parts":parts,"totals":totals,"visible_rest_aabb_length_m":measured.size.x}

func _run() -> void:
	assert(_triangles(Mesh.PRIMITIVE_TRIANGLES,3,0) == 1 and _triangles(Mesh.PRIMITIVE_TRIANGLES,4,6) == 2)
	var started := Time.get_ticks_msec()
	_bind(get_script().resource_path)
	_bind("res://assets/models/fish/motion/motion.json")
	_bind("res://scripts/aquarium/VolumeFishExhibit.gd")
	_bind("res://scripts/aquarium/FishSurfaceOwnership.gd")
	var factory := FACTORY.new()
	factory._load_profiles()
	var holder := Node3D.new(); root.add_child(holder)
	var inventory := []
	CACHE.begin_entry()
	for raw_species in FACTORY.SPECIES:
		var species := str(raw_species)
		var model_path := "res://assets/models/fish/"+species+".glb"
		_bind(model_path); _bind(model_path+".import")
		var count_before: int = factory.fish.size()
		var profile: Dictionary = factory.profiles[species]
		factory._add_fish(holder,species,float(profile.real_length_cm)/100.0,profile)
		assert(factory.fish.size() == count_before + 1)
		var entry: Dictionary = factory.fish[-1]
		var record := _inspect(entry.model)
		record["species"] = species; record["name_zh"] = FACTORY.LABELS[species]
		record["configured_length_cm"] = profile.real_length_cm
		record["runtime_length_m"] = entry.length_m
		record["length_source"] = "res://assets/models/fish/motion/motion.json#profiles/"+species+"/real_length_cm"
		record["model_sha256"] = bindings[model_path]
		record["bones"] = entry.skeleton.get_bone_count()
		record["actual_model_scale"] = entry.model.scale.x
		record["runtime_normalization_applied"] = entry.model.get_meta("runtime_normalization_applied",false)
		inventory.append(record)
		print("FISH_PARTS "+JSON.stringify({"species":species,"length_cm":profile.real_length_cm,"totals":record.totals}))
		factory.fish.erase(entry); entry.carrier.free(); CACHE.clear()
		await process_frame
	var changed := []
	for path in bindings:
		if bindings[path] != FileAccess.get_sha256(path): changed.append(path)
	assert(changed.is_empty() and inventory.size() == 28)
	var report := {"schema_version":1,"command":"fish.current-part-inventory","ok":true,"status":"done","next_action":"human_review","formal_acceptance":false,
		"scope":"Current factory visible base triangle/vertex counts; read-only, no decimation or source edits. LOD counts are separate and are not summed into base triangles. Stored vertices include UV/normal seams, surface splits and mesh instances; not unique spatial points.",
		"inputs_sha256":bindings,"source_changes":changed,"inventory":inventory,"engine":Engine.get_version_info(),"elapsed_ms":Time.get_ticks_msec()-started,
		"quantity_budget":"No production per-species population budget inferred from length. Exhibition/test counts are reported separately by the companion report builder.",
		"engine_output_scan":"pending external error scan","failures":[]}
	FileAccess.open(output.path_join("inventory.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	factory.free(); holder.free(); CACHE.clear()
	print("FISH_PARTS_DONE "+str(inventory.size())); quit()
