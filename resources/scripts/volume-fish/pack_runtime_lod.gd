extends SceneTree
## Packs build_runtime_lod.py output as a compressed, exportable Godot resource.
## godot --headless --path <game> --script <this file> -- <candidate.json> <lod.res>

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 2, "Expected candidate JSON and output .res")
	var inputs: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var entries := {}
	for species in inputs:
		var record: Dictionary = inputs[species]
		var meshes: Dictionary = record.meshes
		for mesh_name in meshes:
			for surface in meshes[mesh_name].values():
				for level in surface.levels:
					level[1] = Marshalls.base64_to_raw(level[1])
		entries[species] = {"sha256": record.sha256, "meshes": meshes}
	var packed := Resource.new()
	packed.set_meta("fish_lod", entries)
	assert(ResourceSaver.save(packed, args[1], ResourceSaver.FLAG_COMPRESS) == OK)
	quit()
