extends SceneTree
## Cold GLTFDocument import proof, no GPU/physical/anatomical acceptance.
const PARTS = preload("PackedFishParts.gd")
var output_path := ""

func _initialize() -> void: call_deferred("run")

func finish(report: Dictionary, code: int = 0) -> void:
	report["command"] = "portable.validate_import"
	report["status"] = "done" if code == 0 else "failed"
	report["next_action"] = "none" if code == 0 else "fix_input"
	if not report.has("failures"): report["failures"] = []
	if not output_path.is_empty():
		var handle := FileAccess.open(output_path, FileAccess.WRITE)
		if handle == null:
			report = PARTS.failure("Cannot create fresh import report")
			code = 1
		else: handle.store_string(JSON.stringify(report, "  ") + "\n")
	print(JSON.stringify(report))
	quit(code)

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() == 1 and args[0] == "--help":
		print("Usage: Godot --headless --path <isolated-project> --script validate_import.gd -- <parts-manifest.json> <fresh-report.json>\nOnly actual import/partition/native-track resolution is checked; no motion controller or full physical/GPU gates.")
		quit(); return
	if args.size() != 2:
		finish(PARTS.failure("Expected manifest path and fresh output report"), 1); return
	var manifest_path: String = args[0]
	var candidate_output: String = args[1].simplify_path()
	var repository: String = get_script().resource_path.get_base_dir().path_join("../../../..").simplify_path()
	var output_root := ""
	for allowed in [repository.path_join("work"), repository.path_join("output")]:
		if candidate_output.begins_with(allowed + "/"): output_root = allowed
	var projects: String = repository.path_join("projects") + "/"
	if candidate_output.begins_with(projects):
		var relative: PackedStringArray = candidate_output.trim_prefix(projects).split("/")
		if relative.size() >= 3 and relative[1] == "experiments": output_root = projects.path_join(relative[0]).path_join("experiments")
	if not candidate_output.is_absolute_path() or output_root.is_empty() or FileAccess.file_exists(candidate_output):
		finish(PARTS.failure("Report must be fresh under work/, output/ or projects/<project>/experiments/"), 1); return
	var output_directory := DirAccess.open(candidate_output.get_base_dir())
	if output_directory == null or output_directory.is_link(candidate_output.get_file()) or DirAccess.dir_exists_absolute(candidate_output):
		finish(PARTS.failure("Report basename must be fresh and cannot be a symlink or directory"), 1); return
	var cursor: String = candidate_output.get_base_dir()
	while cursor.length() >= output_root.length():
		var parent_dir := DirAccess.open(cursor.get_base_dir())
		if parent_dir == null or parent_dir.is_link(cursor.get_file()):
			finish(PARTS.failure("Output directory must exist without symlink aliases"), 1); return
		if cursor == output_root: break
		cursor = cursor.get_base_dir()
	output_path = candidate_output
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	if not parsed is Dictionary:
		finish(PARTS.failure("Cannot read portable manifest"), 1); return
	var manifest: Dictionary = parsed
	if not manifest.has_all(["model", "model_sha256", "expected", "body_names", "parts"]):
		finish(PARTS.failure("Incomplete portable manifest"), 1); return
	if FileAccess.get_sha256(manifest.model) != manifest.model_sha256:
		finish(PARTS.failure("Stale model hash"), 1); return
	var doc := GLTFDocument.new(); var state := GLTFState.new()
	if doc.append_from_file(manifest.model, state) != OK:
		finish(PARTS.failure("GLTFDocument rejected candidate"), 1); return
	var model := doc.generate_scene(state)
	if model == null:
		finish(PARTS.failure("GLTFDocument generated no scene"), 1); return
	root.add_child(model)
	var skeletons := model.find_children("*", "Skeleton3D", true, false)
	if skeletons.size() != 1:
		finish(PARTS.failure("Expected exactly one imported skeleton"), 1); return
	var skeleton: Skeleton3D = skeletons[0]
	if skeleton.get_bone_count() != int(manifest.expected.bones):
		finish(PARTS.failure("Imported bone count differs from candidate baseline/spec"), 1); return
	var entry := {"model": model, "skeleton": skeleton}
	var spec := {"model": manifest.model, "packed_parts_manifest": manifest_path, "packed_parts_manifest_sha256": FileAccess.get_sha256(manifest_path)}
	var result: Dictionary = PARTS.surfaces(entry, spec)
	if not result.get("ok", false):
		finish(result, 1); return
	var actual_material: Material = result.surfaces[0].material
	if not actual_material is StandardMaterial3D:
		finish(PARTS.failure("Unsupported imported body material type"), 1); return
	var material: StandardMaterial3D = actual_material
	if material.texture_filter != BaseMaterial3D.TEXTURE_FILTER_NEAREST or material.albedo_color.a != 1.0:
		finish(PARTS.failure("Imported body material changed nearest sampling or alpha factor"), 1); return
	var expected_alpha: int = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR if manifest.body_opacity.material_alpha_mode == "MASK" else BaseMaterial3D.TRANSPARENCY_DISABLED
	if material.transparency != expected_alpha or (expected_alpha == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR and material.alpha_scissor_threshold != 0.5):
		finish(PARTS.failure("Imported body material changed supported alpha mode/cutoff"), 1); return
	var report: Dictionary = result.proof
	report["actual_material"] = {"type": material.get_class(), "nearest_without_mipmaps": true, "transparency": material.transparency, "alpha_factor": material.albedo_color.a, "same_material_used_by_diagnostics": true}
	var counts: Dictionary = {}; var body_triangles := 0
	for row in result.surfaces:
		var triangles: int = (row.arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
		counts[row.name] = int(counts.get(row.name, 0)) + triangles
		if row.opaque_uv: body_triangles += triangles
	var probes: Dictionary = PARTS.make_probes(entry, result, manifest.body_names)
	var probe_triangles := 0; var probe_surfaces := 0
	for probe in probes.values():
		if probe.skin != result.surfaces[0].mesh.skin:
			finish(PARTS.failure("Diagnostic probe substituted actual skin"), 1); return
		for si in probe.mesh.get_surface_count():
			probe_triangles += (probe.mesh.surface_get_arrays(si)[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
			probe_surfaces += 1
			if probe.get_active_material(si) != result.surfaces[0].material:
				finish(PARTS.failure("Diagnostic probe substituted actual material"), 1); return
	PARTS.clear_probes(probes)
	if probe_triangles != body_triangles or model.find_children("*", "MeshInstance3D", true, false).size() != 1:
		finish(PARTS.failure("Diagnostic body count/runtime cleanup mismatch"), 1); return
	var raw_bytes := FileAccess.get_file_as_bytes(manifest.model)
	var source: Dictionary = JSON.parse_string(raw_bytes.slice(20, 20 + raw_bytes.decode_u32(12)).get_string_from_utf8())
	var channels := 0
	for animation in source.get("animations", []):
		for channel in animation.channels:
			channels += 1
			if skeleton.find_bone(source.nodes[int(channel.target.node)].name) < 0:
				finish(PARTS.failure("Raw animation channel target is not an imported bone"), 1); return
	if channels != int(manifest.expected.animation_channels):
		finish(PARTS.failure("Raw native channel count differs from baseline/spec"), 1); return
	var tracks := 0; var clip_count := 0
	for player in model.find_children("*", "AnimationPlayer", true, false):
		var animation_root: Node = player.get_node(player.root_node)
		for clip_name in player.get_animation_list():
			if clip_name == "RESET": continue
			clip_count += 1
			var clip: Animation = player.get_animation(clip_name)
			for i in clip.get_track_count():
				tracks += 1
				var track := clip.track_get_path(i)
				var target := animation_root.get_node_or_null(NodePath(track.get_concatenated_names())) as Skeleton3D
				if target != skeleton or track.get_subname_count() != 1 or skeleton.find_bone(str(track.get_subname(0))) < 0:
					finish(PARTS.failure("Unbound imported native animation track"), 1); return
	if clip_count != int(manifest.expected.clips):
		finish(PARTS.failure("Imported clip count differs from baseline/spec"), 1); return
	report.merge({"part_triangles": counts, "body_opacity": manifest.body_opacity, "manifest": manifest_path, "helper_sha256": FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("PackedFishParts.gd")), "importer_script_sha256": FileAccess.get_sha256(get_script().resource_path), "engine": Engine.get_version_info(), "body_probe": {"validation_only": true, "triangles": body_triangles, "surfaces": probe_surfaces, "same_actual_skin": true, "same_actual_material": true}, "native_smoke": {"bones": skeleton.get_bone_count(), "clips": clip_count, "raw_channels_resolved": channels, "imported_tracks_resolved": tracks, "immutable_track_optimization_allowed": true}, "scope": "Cold actual GLTFDocument array/skin/oriented-triangle partition and native-track resolution only. Physical490, fin roots/membranes, body GPU integrity, anatomy, motion-controller behavior and visual acceptance are unsupported by this generic proof."})
	finish(report)
