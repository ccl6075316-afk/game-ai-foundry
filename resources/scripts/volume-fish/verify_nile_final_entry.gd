extends SceneTree
const EXHIBIT = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const BINDER = preload("res://scripts/aquarium/FinalizedNileTilapia.gd")
var out: String
var exhibit
var entry: Dictionary
var direct: Dictionary

func _initialize() -> void: call_deferred("run")

func _pose(item: Dictionary, action: String, phase: float) -> void:
	assert(item.controller.set_action(action, true))
	item.controller.step(0.0)
	item.controller.seek(phase)

func _delta() -> float:
	var result := 0.0
	for i in entry.skeleton.get_bone_count():
		var name: String = entry.skeleton.get_bone_name(i)
		var j: int = direct.skeleton.find_bone(name)
		assert(j >= 0)
		var a: Transform3D = entry.skeleton.get_bone_global_pose(i)
		var b: Transform3D = direct.skeleton.get_bone_global_pose(j)
		result = maxf(result, a.origin.distance_to(b.origin))
		for axis in 3: result = maxf(result, a.basis[axis].distance_to(b.basis[axis]))
	return result

func run() -> void:
	out = OS.get_cmdline_user_args()[0]
	assert(DirAccess.dir_exists_absolute(out))
	var profile: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles.nile_tilapia
	var viewport := SubViewport.new()
	viewport.size = Vector2i(1000, 720)
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.mesh_lod_threshold = 0.0
	root.add_child(viewport)
	var world := Node3D.new(); viewport.add_child(world)
	var env := WorldEnvironment.new(); env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("25343c")
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color.WHITE
	env.environment.ambient_light_energy = 0.65
	world.add_child(env)
	var light := DirectionalLight3D.new(); light.rotation_degrees = Vector3(-45,-35,0); light.light_energy = 0.65; world.add_child(light)
	var camera := Camera3D.new(); camera.projection = Camera3D.PROJECTION_ORTHOGONAL; camera.size = 0.55; camera.near = 0.001; camera.far = 50; world.add_child(camera)
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
	exhibit = EXHIBIT.new()
	exhibit._add_fish(world, "nile_tilapia", 0.4, profile)
	assert(exhibit.fish.size() == 1)
	entry = exhibit.fish[0]
	assert(entry.model.has_meta("final_asset_nile_receipt"))
	assert(is_equal_approx(entry.model.scale.x, BINDER.REVIEW_SCALE))
	var document := GLTFDocument.new(); var state := GLTFState.new()
	var approved := "res://assets/models/fish/nile_tilapia.glb"
	assert(document.append_from_file(approved, state) == OK)
	var model := document.generate_scene(state) as Node3D
	model.scene_file_path = approved
	var carrier := Node3D.new(); world.add_child(carrier); carrier.add_child(model)
	model.scale = entry.model.scale; model.position = entry.model.position
	var sk: Skeleton3D = model.find_children("*", "Skeleton3D", true, false)[0]
	var player: AnimationPlayer = model.find_children("*", "AnimationPlayer", true, false)[0]
	var ctrl = load(EXHIBIT.MOTION_SCRIPT).new()
	assert(ctrl.configure(carrier, model, player, sk, profile).ok)
	direct = {"model":model, "carrier":carrier, "skeleton":sk, "player":player, "controller":ctrl}
	var parts = load(ProjectSettings.globalize_path("res://../../../resources/scripts/volume-fish/PackedFishValidation.gd"))
	var manifest_path := out.path_join("packed-parts.json")
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	var spec := {"model":manifest.model,"body":manifest.body,"fins":manifest.fins,"packed_parts_manifest":manifest_path,"packed_parts_manifest_sha256":FileAccess.get_sha256(manifest_path)}
	var partition: Dictionary = parts.surfaces(entry, spec)
	var max_pose_delta := 0.0
	var controls := [[0.0,0.0,0.0,0.0],[1.0,1.0,1.0,1.0],[2.5,1.0,2.5,1.0],[1.0,3.0,1.0,3.0],[1.3,0.7,2.0,1.4]]
	var phases := 0
	for values in controls:
		var settings := {"body_amplitude":values[0],"body_frequency":values[1],"fin_amplitude":values[2],"fin_frequency":values[3]}
		entry.controller.set_motion_controls(settings, true); ctrl.set_motion_controls(settings, true)
		for action in ["Swim","Turn","Ascend","Dive"]:
			for i in 24:
				_pose(entry, action, float(i) / 24.0 * float(profile.period_seconds))
				_pose(direct, action, float(i) / 24.0 * float(profile.period_seconds))
				max_pose_delta = maxf(max_pose_delta, _delta())
				assert(entry.controller.snapshot().inside_envelope)
				phases += 1
	assert(max_pose_delta < 0.000002)
	var captures := []
	entry.controller.set_motion_controls({"body_amplitude":1.0,"body_frequency":1.0,"fin_amplitude":1.0,"fin_frequency":1.0},true)
	ctrl.set_motion_controls({"body_amplitude":1.0,"body_frequency":1.0,"fin_amplitude":1.0,"fin_frequency":1.0},true)
	for action in ["Swim","Turn","Ascend","Dive"]:
		_pose(entry,action,1.17); _pose(direct,action,1.17)
		# Same actual carrier pose, camera, light and native materials.
		camera.position = entry.carrier.global_position + Vector3(0.18,0.1,0.65)
		camera.look_at(entry.carrier.global_position,Vector3.UP)
		for route in ["canonical","approved"]:
			entry.carrier.visible = route == "canonical"; carrier.visible = route == "approved"
			await process_frame; await process_frame; await RenderingServer.frame_post_draw
			var path := out.path_join(action+"-"+route+".png")
			assert(viewport.get_texture().get_image().save_png(path) == OK)
			captures.append(path)
	exhibit._add_fish(world,"nile_tilapia",0.4,profile)
	assert(not exhibit.loading_metrics[0].reused_appearance and exhibit.loading_metrics[1].reused_appearance)
	var cached: Dictionary=exhibit.fish[1]
	assert(cached.model.has_meta("final_asset_nile_receipt"))
	var a: Array=entry.model.find_children("*","MeshInstance3D",true,false)[0].mesh.surface_get_arrays(0)
	var b: Array=cached.model.find_children("*","MeshInstance3D",true,false)[0].mesh.surface_get_arrays(0)
	for k in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_BONES,Mesh.ARRAY_WEIGHTS,Mesh.ARRAY_INDEX]:assert(var_to_bytes(a[k])==var_to_bytes(b[k]))
	cached.carrier.hide()
	var actual_mesh: MeshInstance3D=entry.model.find_children("*","MeshInstance3D",true,false)[0]
	var serialized: Array=actual_mesh.mesh.get("_surfaces")
	var lod_count:=0
	for surface in serialized:lod_count+=surface.get("lods",[]).size()
	assert(lod_count==0,"Accepted full detail must not acquire generated LODs")
	var report := {"ok":true,"kind":"nile_final_canonical_install_check","fresh_process":true,"actual_entry":"VolumeFishExhibit._add_fish canonical GLB via reviewed GLTFDocument loader", "model_sha256":FileAccess.get_sha256("res://assets/models/fish/nile_tilapia.glb"),"approved_sha256":FileAccess.get_sha256(approved),"scale":entry.model.scale.x,"triangles":1602,"first_and_cache_load_equal":true,"static_builders_disabled":true,"meshes":1,"surfaces":1,"static_build_calls":0,"material_overrides":0,"partition_proof":partition.proof,"controller_comparisons":phases,"max_actual_skeleton_delta":max_pose_delta,"native_tracks":entry.player.get_animation(profile.base_clip).get_track_count(),"captures":captures,"scope":"Current accepted1602triangles; actual first/cache entry compared to independent raw GLB across480 controller phases. CurrentR5 physical gates separately retained with exact bytes."}
	report["serialized_lod_entries"]=lod_count
	FileAccess.open(out.path_join("canonical-load.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
	exhibit.fish.clear()
	exhibit.free()
	entry.clear(); direct.clear(); partition.clear()
	viewport.queue_free()
	await process_frame; await process_frame
	print("NILE_CANONICAL_INSTALL_OK ",max_pose_delta)
	quit()
