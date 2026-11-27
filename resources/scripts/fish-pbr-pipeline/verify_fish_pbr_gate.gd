extends SceneTree
## Universal Single-Material PBR Fish Hard QA Gate (Godot 4.7+).
## Usage:
##   Godot --path projects/fishing-2d/game --script resources/scripts/fish-pbr-pipeline/verify_fish_pbr_gate.gd -- \
##     --species red_seabream --glb /abs/path/to/model.glb --out /abs/path/to/qa_dir \
##     [--max-vram-mb 16.5] [--dump-mouth-recipe /abs/path/to/mouth-anchor.json]

const Factory := preload("res://scripts/aquarium/FishInstanceFactory.gd")
const JawActionMotion := preload("res://scripts/aquarium/FishJawActionMotion.gd")
const BaseMotion := preload("res://scripts/aquarium/FoundryFishMotion.gd")

func _init() -> void:
	call_deferred("_run")

func _parse_args() -> Dictionary:
	var out := {"species": "", "glb": "", "out": "", "max_vram_mb": 16.5, "dump_mouth_recipe": ""}
	var args := OS.get_cmdline_user_args()
	var i := 0
	while i < args.size():
		match args[i]:
			"--species":
				i += 1; if i < args.size(): out.species = args[i]
			"--glb":
				i += 1; if i < args.size(): out.glb = args[i]
			"--out":
				i += 1; if i < args.size(): out.out = args[i]
			"--max-vram-mb":
				i += 1; if i < args.size(): out.max_vram_mb = float(args[i])
			"--dump-mouth-recipe":
				i += 1; if i < args.size(): out.dump_mouth_recipe = args[i]
		i += 1
	return out

func _load_glb(path: String) -> Node3D:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_file(path, state)
	if err != OK:
		return null
	return doc.generate_scene(state) as Node3D

func _settle(frames := 6) -> void:
	for i in frames:
		await process_frame
	await RenderingServer.frame_post_draw

func _save(vp: SubViewport, out_dir: String, name: String) -> void:
	if out_dir.is_empty():
		return
	DirAccess.make_dir_recursive_absolute(out_dir)
	var img: Image = vp.get_texture().get_image()
	img.save_png(out_dir.path_join(name))

func _tex_vram_mb(tex: Texture2D) -> float:
	if tex == null:
		return 0.0
	var sz := tex.get_size()
	return float(sz.x * sz.y) * 4.0 * 1.3333 / (1024.0 * 1024.0)

func _find_existing_mouth_anchor(species: String) -> Dictionary:
	for sub in ["width20261101", "eleven20261105"]:
		var p := "res://assets/models/fish/motion/%s/%s-mouth-anchor.json" % [sub, species]
		if FileAccess.file_exists(p):
			return JSON.parse_string(FileAccess.get_file_as_string(p))
	return {}

func _run() -> void:
	root.set_flag(Window.FLAG_NO_FOCUS, true)
	var opts := _parse_args()
	if opts.species.is_empty() or opts.glb.is_empty():
		push_error("Usage: -- --species <name> --glb <path> [--out <dir>] [--max-vram-mb 16.5] [--dump-mouth-recipe <path>]")
		quit(2)
		return

	var vp := SubViewport.new()
	vp.size = Vector2i(1440, 810)
	vp.msaa_3d = Viewport.MSAA_4X
	vp.own_world_3d = true
	vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(vp)

	var world := Node3D.new()
	vp.add_child(world)

	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color("13222d")
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color("89a8bc")
	e.ambient_light_energy = 0.55
	e.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.environment = e
	world.add_child(env)

	var key := DirectionalLight3D.new()
	key.light_color = Color("fff5e8")
	key.light_energy = 2.4
	key.rotation_degrees = Vector3(-42.0, 28.0, 0.0)
	world.add_child(key)

	var rim := DirectionalLight3D.new()
	rim.light_color = Color("7bc8e8")
	rim.light_energy = 1.2
	rim.rotation_degrees = Vector3(-20.0, -145.0, 0.0)
	world.add_child(rim)

	var cam := Camera3D.new()
	cam.fov = 30.0
	cam.near = 0.01
	cam.far = 30.0
	world.add_child(cam)
	cam.current = true

	var factory := Factory.new()
	var profiles := factory.load_profiles()
	var profile: Dictionary
	if factory.width.table().has(opts.species):
		profile = factory.width.motion_profile(opts.species).duplicate(true)
	elif profiles.has(opts.species):
		profile = profiles[opts.species].duplicate(true)
	else:
		push_error("Unknown species in motion profiles: " + opts.species)
		quit(2)
		return

	var carrier := Node3D.new()
	world.add_child(carrier)
	var model := _load_glb(opts.glb)
	if model == null:
		push_error("Failed to load GLB: " + opts.glb)
		quit(1)
		return
	carrier.add_child(model)

	var meshes := model.find_children("*", "MeshInstance3D", true, false)
	var anims := model.find_children("*", "AnimationPlayer", true, false)
	var skels := model.find_children("*", "Skeleton3D", true, false)
	if meshes.is_empty() or anims.is_empty() or skels.is_empty():
		push_error("Missing MeshInstance3D / AnimationPlayer / Skeleton3D in GLB")
		quit(1)
		return

	var mesh_node := meshes[0] as MeshInstance3D
	var anim := anims[0] as AnimationPlayer
	var skel := skels[0] as Skeleton3D
	var mat := mesh_node.get_active_material(0) as StandardMaterial3D

	# Normalize model to real_length_cm exactly as FishInstanceFactory does
	var bounds := AABB()
	var first_box := true
	var to_model := model.global_transform.affine_inverse()
	for m: MeshInstance3D in meshes:
		var box := (to_model * m.global_transform) * m.get_aabb()
		bounds = box if first_box else bounds.merge(box)
		first_box = false
	var length_m := float(profile.real_length_cm) / 100.0
	model.scale = Vector3.ONE * (length_m / bounds.size.x)
	model.position = -bounds.get_center() * model.scale

	var checks := {}
	checks["single_mesh_single_material_draw_call_1"] = (meshes.size() == 1 and mesh_node.mesh.get_surface_count() == 1)
	checks["alpha_mode_mask_05"] = (
		mat != null
		and mat.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
		and is_equal_approx(mat.alpha_scissor_threshold, 0.5)
	)
	var orm_tex: Texture2D = mat.roughness_texture if (mat != null and mat.roughness_texture != null) else (mat.metallic_texture if mat != null else null)
	checks["has_pbr_normal_and_orm"] = (
		mat != null
		and mat.albedo_texture != null
		and mat.normal_enabled
		and mat.normal_texture != null
		and orm_tex != null
	)

	var seen_rids := {}
	var vram_mb := 0.0
	for tex in [mat.albedo_texture, mat.normal_texture, orm_tex]:
		if tex != null and not seen_rids.has(tex.get_rid()):
			seen_rids[tex.get_rid()] = true
			vram_mb += _tex_vram_mb(tex)
	checks["vram_within_budget"] = vram_mb > 0.0 and vram_mb <= float(opts.max_vram_mb)

	var jaw_deg := float(profile.get("jaw_action_degrees", 0.0))
	var use_jaw := jaw_deg > 0.0 and skel.find_bone("jaw_lower") >= 0
	var controller: RefCounted = JawActionMotion.new() if use_jaw else BaseMotion.new()
	var cfg_res: Dictionary = controller.configure(carrier, model, anim, skel, profile, Vector3.ZERO)
	checks["controller_configure_ok"] = bool(cfg_res.get("ok", false))

	var step_ok := true
	var jaw_max_rot := 0.0
	var jaw_idx := skel.find_bone("jaw_lower")
	var jaw_rest_q := skel.get_bone_rest(jaw_idx).basis.get_rotation_quaternion() if jaw_idx >= 0 else Quaternion.IDENTITY
	var actions := ["Swim", "Turn", "Ascend", "Dive"]
	for a_idx in actions.size():
		controller.set_action(actions[a_idx])
		if a_idx == 0 and use_jaw:
			controller.play_jaw_action()
		for k in 120:
			controller.step(1.0 / 60.0)
			if not carrier.global_position.is_finite():
				step_ok = false
			if use_jaw:
				var ang := rad_to_deg(jaw_rest_q.angle_to(skel.get_bone_pose_rotation(jaw_idx)))
				jaw_max_rot = maxf(jaw_max_rot, ang)
	checks["480_frames_4_actions_finite"] = step_ok
	if use_jaw:
		checks["jaw_action_reaches_target_deg"] = absf(jaw_max_rot - jaw_deg) <= 0.25

	# Check upper-lip hook anchor & optionally dump exact verified mouth-anchor.json
	var existing_anchor := _find_existing_mouth_anchor(opts.species)
	var lip_err_mm := -1.0
	if not existing_anchor.is_empty():
		var arr := mesh_node.mesh.surface_get_arrays(0)
		var verts: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
		var uvs: PackedVector2Array = arr[Mesh.ARRAY_TEX_UV]
		var bones: PackedInt32Array = arr[Mesh.ARRAY_BONES]
		var weights: PackedFloat32Array = arr[Mesh.ARRAY_WEIGHTS]
		var stride: int = bones.size() / maxi(verts.size(), 1)
		var target_pos := Vector3(
			float(existing_anchor.position_native[0]),
			float(existing_anchor.position_native[1]),
			float(existing_anchor.position_native[2])
		)
		var best_vi := -1
		var best_d := 999.0
		for vi in verts.size():
			var d := verts[vi].distance_to(target_pos)
			if d < best_d:
				best_d = d
				best_vi = vi
		lip_err_mm = best_d * 1000.0
		checks["upper_lip_hook_anchor_preserved_lt_2mm"] = best_d < 0.002

		if not opts.dump_mouth_recipe.is_empty() and best_vi >= 0:
			var raw_j := []
			var raw_w := []
			var w_bones := {}
			for off in stride:
				var bi := int(bones[best_vi * stride + off])
				var bw := float(weights[best_vi * stride + off])
				raw_j.append(bi)
				raw_w.append(bw)
				if bw > 0.0000001:
					var bone_id := mesh_node.skin.get_bind_bone(bi)
					if bone_id < 0:
						bone_id = skel.find_bone(str(mesh_node.skin.get_bind_name(bi)))
					if bone_id >= 0:
						var bname := skel.get_bone_name(bone_id)
						w_bones[bname] = float(w_bones.get(bname, 0.0)) + bw
			var recipe := {
				"kind": "existing_skinned_upper_lip_vertex_recipe",
				"species": opts.species,
				"model_sha256": FileAccess.get_sha256(opts.glb),
				"mesh": str(mesh_node.name),
				"surface": 0,
				"vertex_index": best_vi,
				"position_native": [verts[best_vi].x, verts[best_vi].y, verts[best_vi].z],
				"texcoord0": [uvs[best_vi].x, uvs[best_vi].y],
				"raw_joint_indices": raw_j,
				"raw_weights": raw_w,
				"weighted_bones": w_bones,
				"body_vertex_ranges": [[0, verts.size()]],
				"binding_space": "mesh_native",
				"semantic": "Verified single-material PBR skinned upper-lip vertex matching canonical anchor.",
			}
			var rf := FileAccess.open(opts.dump_mouth_recipe, FileAccess.WRITE)
			rf.store_string(JSON.stringify(recipe, "  ") + "\n")
			rf.close()

	# Render 4 standardized visual QA views
	var cam_scale := length_m
	controller.set_motion_controls({"body_amplitude": 1.0, "body_frequency": 1.0, "fin_amplitude": 1.0}, true)

	controller.set_action("Swim", true)
	controller.seek(0.45)
	carrier.position = Vector3.ZERO; carrier.rotation = Vector3.ZERO
	cam.position = Vector3(0.35, 0.14, 1.52) * cam_scale
	cam.look_at(Vector3.ZERO)
	await _settle(6)
	_save(vp, opts.out, "01_swim_3q.png")

	controller.set_action("Turn", true)
	for i in 55:
		controller.step(1.0 / 60.0)
	carrier.position = Vector3.ZERO; carrier.rotation = Vector3.ZERO
	cam.position = Vector3(0.0, 1.65, 0.25) * cam_scale
	cam.look_at(Vector3.ZERO)
	await _settle(6)
	_save(vp, opts.out, "02_turn_top.png")

	controller.set_action("Ascend", true)
	if use_jaw:
		controller.play_jaw_action()
	for i in 72:
		controller.step(1.0 / 60.0)
	carrier.position = Vector3.ZERO; carrier.rotation = Vector3.ZERO
	cam.position = Vector3(0.56, 0.01, 0.56) * cam_scale
	cam.look_at(Vector3(0.36, -0.025, 0.0) * cam_scale)
	await _settle(6)
	_save(vp, opts.out, "03_jaw_closeup.png")

	controller.set_action("Swim", true)
	controller.seek(0.25)
	carrier.position = Vector3.ZERO; carrier.rotation = Vector3.ZERO
	cam.position = Vector3(-0.78, -0.18, 1.18) * cam_scale
	cam.look_at(Vector3(0.02, -0.04, 0.0) * cam_scale)
	await _settle(6)
	_save(vp, opts.out, "04_rear_fins_depth.png")

	var arr0 := mesh_node.mesh.surface_get_arrays(0)
	var tri_count: int = arr0[Mesh.ARRAY_INDEX].size() / 3
	var vert_count: int = (arr0[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
	var report := {
		"ok": not checks.values().has(false),
		"species": opts.species,
		"model_sha256": FileAccess.get_sha256(opts.glb),
		"draw_calls": mesh_node.mesh.get_surface_count(),
		"triangles": tri_count,
		"gpu_vertices": vert_count,
		"bones": skel.get_bone_count(),
		"vram_uncompressed_mip_mb": snapped(vram_mb, 0.01),
		"jaw_max_rot_deg": snapped(jaw_max_rot, 0.01),
		"upper_lip_err_mm": snapped(lip_err_mm, 0.02),
		"checks": checks,
		"configure_result": cfg_res,
	}
	if not opts.out.is_empty():
		var jf := FileAccess.open(opts.out.path_join("gate_report.json"), FileAccess.WRITE)
		jf.store_string(JSON.stringify(report, "  ") + "\n")
		jf.close()
	print("FISH_PBR_GATE_JSON ", JSON.stringify(report))
	quit(0 if report.ok else 1)
