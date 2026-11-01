extends SceneTree
const PARTS = preload("PackedFishValidation.gd")

func _initialize() -> void: call_deferred("run")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 2 or args.size() == 3)
	var manifest_path: String = args[0]
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	var doc := GLTFDocument.new(); var state := GLTFState.new()
	assert(doc.append_from_file(manifest.model, state) == OK)
	var carrier := Node3D.new(); root.add_child(carrier)
	var model := doc.generate_scene(state); carrier.add_child(model)
	var skeleton: Skeleton3D = model.find_children("*", "Skeleton3D", true, false)[0]
	var entry := {"model": model, "skeleton": skeleton}
	var spec := {"model": manifest.model, "body": manifest.body, "fins": manifest.fins, "packed_parts_manifest": manifest_path, "packed_parts_manifest_sha256": FileAccess.get_sha256(manifest_path)}
	var result: Dictionary = PARTS.surfaces(entry, spec)
	var counts: Dictionary = {}
	for row in result.surfaces:
		var n: int = (row.arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
		counts[row.name] = int(counts.get(row.name, 0)) + n
	var report: Dictionary = result.proof
	report.merge({"part_triangles": counts, "body_opacity": manifest.body_opacity, "manifest": manifest_path, "helper_sha256": FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("PackedFishValidation.gd")), "importer_script_sha256": FileAccess.get_sha256(get_script().resource_path), "engine": Engine.get_version_info(), "scope": "Actual new-process GLTFDocument array/skin/triangle partition proof only; no physical490 or GPUcoverage claim."})
	var probes: Dictionary = PARTS.make_probes(entry, result, [manifest.body])
	var body: MeshInstance3D = probes[manifest.body]
	var body_triangles := 0
	for si in body.mesh.get_surface_count(): body_triangles += (body.mesh.surface_get_arrays(si)[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
	assert(body_triangles == 904 and body.skin == result.surfaces[0].mesh.skin)
	report["body_probe"] = {"validation_only": true, "triangles": body_triangles, "surfaces": body.mesh.get_surface_count(), "same_actual_skin": true, "same_actual_material": body.get_active_material(0) == result.surfaces[0].material}
	PARTS.clear_probes(probes)
	assert(model.find_children("*", "MeshInstance3D", true, false).size() == 1)
	if args.size() == 3:
		var plan: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[2]))
		assert(plan.model == manifest.model and plan.model_sha256 == manifest.model_sha256)
		var profile: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(plan.motion_profile))
		var player: AnimationPlayer = model.find_children("*", "AnimationPlayer", true, false)[0]
		model.scale = Vector3.ONE * float(plan.model_scale)
		var controller = load(plan.motion_runtime).new()
		var configured: Dictionary = controller.configure(carrier, model, player, skeleton, profile)
		assert(configured.ok and controller._fin_tracks.size() == 7)
		var clip: Animation = player.get_animation(profile.base_clip)
		var raw_bytes := FileAccess.get_file_as_bytes(manifest.model)
		var source: Dictionary = JSON.parse_string(raw_bytes.slice(20, 20 + raw_bytes.decode_u32(12)).get_string_from_utf8())
		assert(source.animations.size() == 1 and source.animations[0].channels.size() == 54)
		for channel in source.animations[0].channels:
			assert(skeleton.find_bone(source.nodes[int(channel.target.node)].name) >= 0, "Raw animation target bone missing in actual import")
		assert(clip.get_track_count() > 0)
		var animation_root := player.get_node(player.root_node)
		for i in clip.get_track_count():
			var track := clip.track_get_path(i)
			var target := animation_root.get_node_or_null(NodePath(track.get_concatenated_names())) as Skeleton3D
			assert(target == skeleton and track.get_subname_count() == 1 and skeleton.find_bone(str(track.get_subname(0))) >= 0, "Unbound actual native animation channel")
		player.seek(0.0, true); player.advance(0.0)
		var before := skeleton.get_bone_pose_rotation(skeleton.find_bone("Caudal_2"))
		player.seek(clip.length * .37, true); player.advance(0.0)
		assert(before != skeleton.get_bone_pose_rotation(skeleton.find_bone("Caudal_2")))
		assert(controller.set_action("Turn", true)); controller.step(0.0); controller.seek(.75)
		assert(controller.snapshot().action == "Turn" and controller.snapshot().inside_envelope)
		report["motion_smoke"] = {"configure": configured, "raw_native_channels_target_bones_resolved": 54, "actual_imported_tracks_resolved": clip.get_track_count(), "immutable_track_optimization_allowed": true, "native_caudal_pose_changed": true, "fin_tracks": controller._fin_tracks.size(), "actual_action": controller.snapshot().action, "static_builder_calls": 0}
	FileAccess.open(args[1], FileAccess.WRITE).store_string(JSON.stringify(report, "  ") + "\n")
	print("PACKED_FISH_IMPORT_OK ", JSON.stringify(counts)); quit()
