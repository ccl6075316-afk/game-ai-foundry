extends SceneTree

# Isolated GLB import smoke test. This does not replace actual game assembly.
func _initialize() -> void:
	var args := {}
	for arg in OS.get_cmdline_user_args():
		var pair := String(arg).trim_prefix("--").split("=", false, 1)
		if pair.size() == 2:
			args[pair[0]] = pair[1]
	var model := String(args.get("model", ""))
	var output := String(args.get("output", ""))
	var limit := int(args.get("max_triangles", "1500"))
	if model.is_empty() or output.is_empty():
		push_error("Requires --model and --output")
		quit(2)
		return
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	var error := document.append_from_file(model, state)
	var report := {"kind":"isolated_nile_budget_glb_cold_probe", "model":model,
		"ok":error == OK, "error":error, "scope":"Isolated GLB, not production game assembly",
		"model_sha256":FileAccess.get_sha256(model), "max_triangles":limit,
		"triangles":0, "meshes":[], "animation_players":0, "animations":0, "skins":0}
	if error == OK:
		var root := document.generate_scene(state)
		if root == null:
			report["ok"] = false
		else:
			_walk(root, report)
			root.free()
			report["ok"] = report["triangles"] <= limit and report["meshes"].size() == 8 and report["skins"] == 1 and report["animations"] >= 1
	var file := FileAccess.open(output, FileAccess.WRITE)
	if file == null:
		push_error("Cannot write report")
		quit(2)
		return
	file.store_string(JSON.stringify(report, "  ") + "\n")
	file.close()
	print(JSON.stringify(report))
	quit(0 if report["ok"] else 1)

func _walk(node: Node, report: Dictionary) -> void:
	if node is MeshInstance3D:
		var mesh_node := node as MeshInstance3D
		var count := 0
		if mesh_node.mesh != null:
			for surface in range(mesh_node.mesh.get_surface_count()):
				var arrays := mesh_node.mesh.surface_get_arrays(surface)
				count += (arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
		report["triangles"] += count
		report["meshes"].append({"name":node.name, "triangles":count, "has_skin":mesh_node.skin != null})
	if node is Skeleton3D:
		report["skins"] += 1
	if node is AnimationPlayer:
		report["animation_players"] += 1
		var player := node as AnimationPlayer
		for library_name in player.get_animation_library_list():
			report["animations"] += player.get_animation_library(library_name).get_animation_list().size()
	for child in node.get_children():
		_walk(child, report)
