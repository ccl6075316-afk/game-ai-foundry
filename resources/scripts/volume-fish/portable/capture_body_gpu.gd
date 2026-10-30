extends SceneTree
## Discrete actual-body GPU alpha comparison only; no topology or anatomical pass.
const PARTS = preload("PackedFishParts.gd")
var viewport: SubViewport
var camera: Camera3D
var skeleton: Skeleton3D
var model: Node3D
var player: AnimationPlayer
var probes: Dictionary
var originals: Dictionary
var output: String

func _initialize() -> void: call_deferred("run")
func fail(message: String) -> void:
	var report := PARTS.failure(message)
	if not output.is_empty(): FileAccess.open(output.path_join("capture.validation.json"), FileAccess.WRITE).store_string(JSON.stringify(report))
	print(JSON.stringify(report)); quit(1)
func pose_digest() -> String:
	var values: Array = [model.global_transform]
	for i in skeleton.get_bone_count(): values.append(skeleton.get_bone_global_pose(i))
	return var_to_bytes(values).hex_encode().sha256_text()
func camera_digest() -> String:
	return var_to_bytes([camera.global_transform, camera.projection, camera.size, camera.near, camera.far, viewport.size]).hex_encode().sha256_text()
func set_materials(material: Material = null) -> void:
	for probe in probes.values():
		for si in probe.mesh.get_surface_count():
			probe.set_surface_override_material(si, originals[probe.get_instance_id()][si] if material == null else material)
func capture(path: String) -> void:
	for i in 3:
		await process_frame
		RenderingServer.force_draw(false)
	viewport.get_texture().get_image().save_png(output.path_join(path))
func texture_digest(texture: Texture2D) -> String:
	if texture == null: return ""
	var image := texture.get_image()
	if image == null: return ""
	if image.is_compressed(): image.decompress()
	image.convert(Image.FORMAT_RGBA8)
	if image.has_mipmaps(): image.clear_mipmaps()
	var context := HashingContext.new(); context.start(HashingContext.HASH_SHA256); context.update(image.get_data())
	return context.finish().hex_encode()
func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2 or DisplayServer.get_name() == "headless":
		fail("Expected GPU display, plan and fresh output directory"); return
	var plan: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0])); output = args[1]
	for path in plan.frozen_inputs:
		if FileAccess.get_sha256(path) != plan.frozen_inputs[path]: fail("Stale GPU dependency"); return
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(plan.packed_parts_manifest))
	root.size = Vector2i(800,600)
	viewport = SubViewport.new(); viewport.size = Vector2i(800,600); viewport.own_world_3d = true; viewport.transparent_bg = true; viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS; viewport.mesh_lod_threshold = 0.0; root.add_child(viewport)
	var world := Node3D.new(); viewport.add_child(world)
	var environment := WorldEnvironment.new(); environment.environment = Environment.new(); environment.environment.background_mode = Environment.BG_CLEAR_COLOR; environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; environment.environment.ambient_light_color = Color.WHITE; environment.environment.ambient_light_energy = 1.0; world.add_child(environment)
	camera = Camera3D.new(); camera.projection = Camera3D.PROJECTION_ORTHOGONAL; camera.near = 0.001; camera.current = true; world.add_child(camera)
	var doc := GLTFDocument.new(); var state := GLTFState.new()
	if doc.append_from_file(plan.model,state) != OK: fail("GPU cold GLTFDocument import failed"); return
	model = doc.generate_scene(state); world.add_child(model)
	var skeletons := model.find_children("*", "Skeleton3D",true,false); var players := model.find_children("*", "AnimationPlayer",true,false)
	if skeletons.size() != 1 or players.size() != 1: fail("Expected one actual skeleton and native player"); return
	skeleton = skeletons[0]; player = players[0]
	var entry := {"model":model,"skeleton":skeleton}
	var partition := PARTS.surfaces(entry,plan)
	if not partition.get("ok",false): fail(str(partition.failures)); return
	var actual_mesh: MeshInstance3D = partition.surfaces[0].mesh
	var material: StandardMaterial3D = partition.surfaces[0].material as StandardMaterial3D
	if material == null or material.albedo_color.a != 1.0 or material.texture_filter != BaseMaterial3D.TEXTURE_FILTER_NEAREST or texture_digest(material.albedo_texture) != manifest.body_opacity.rgba_sha256:
		fail("Actual GPU donor pixels/sampling/alpha disagree with source"); return
	var expected_alpha: int = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR if manifest.body_opacity.material_alpha_mode == "MASK" else BaseMaterial3D.TRANSPARENCY_DISABLED
	if material.transparency != expected_alpha or (expected_alpha == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR and material.alpha_scissor_threshold != 0.5): fail("Actual GPU alpha mode/cutoff differs"); return
	probes = PARTS.make_probes(entry,partition,manifest.body_names)
	actual_mesh.hide()
	var body_surfaces := 0; var body_triangles := 0
	for probe in probes.values():
		probe.show(); var saved: Array = []
		for si in probe.mesh.get_surface_count():
			saved.append(probe.get_active_material(si)); body_surfaces += 1
			body_triangles += (probe.mesh.surface_get_arrays(si)[Mesh.ARRAY_INDEX] as PackedInt32Array).size()/3
		originals[probe.get_instance_id()] = saved
	var box: AABB = actual_mesh.get_aabb(); var center: Vector3 = model.global_transform * box.get_center(); var diameter := maxf(box.size.length(),0.1)
	camera.size = diameter * 1.25; camera.far = diameter * 10.0
	var reference := StandardMaterial3D.new(); reference.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; reference.cull_mode = BaseMaterial3D.CULL_DISABLED; reference.albedo_color = Color.WHITE
	var transparent := material.duplicate() as StandardMaterial3D; transparent.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR; transparent.alpha_scissor_threshold = 0.5; transparent.albedo_color = Color(1,1,1,0)
	var views := [[0.0,0.0],[PI,0.0],[PI/2,0.0],[-PI/2,0.0],[0.5,0.85],[0.5,-0.85],[PI+0.5,0.65],[PI+0.5,-0.65]]
	var records: Array = []; var negative: Dictionary = {}; var pose_digests: Array = []
	for pose in plan.poses.size():
		var pose_spec: Dictionary = plan.poses[pose]
		if not player.has_animation(pose_spec.clip): fail("Native clip missing in actual import"); return
		var clip := player.get_animation(pose_spec.clip)
		player.play(pose_spec.clip); player.seek(clip.length * float(pose_spec.fraction),true); player.advance(0.0); player.pause(); skeleton.force_update_all_bone_transforms()
		for settle in 3: await process_frame
		pose_digests.append(pose_digest())
		for view in views.size():
			var yaw: float = views[view][0]; var pitch: float = views[view][1]
			camera.position = center + Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch)) * diameter * 3.0; camera.look_at(center,Vector3.UP)
			var stem := "p%d-v%d" % [pose,view]; var pd := pose_digest(); var cd := camera_digest()
			set_materials(); await capture(stem+"-actual.png")
			if pose_digest() != pd or camera_digest() != cd: fail("Pose/camera changed during actual capture"); return
			set_materials(reference); await capture(stem+"-reference.png")
			if pose_digest() != pd or camera_digest() != cd: fail("Pose/camera changed during reference capture"); return
			var row := {"pose":pose,"view":view,"pose_before":pd,"pose_after":pose_digest(),"camera_before":cd,"camera_after":camera_digest(),"actual":stem+"-actual.png","reference":stem+"-reference.png"}
			for key in ["actual","reference"]: row[key+"_sha256"] = FileAccess.get_sha256(output.path_join(row[key]))
			records.append(row)
			if pose == 0 and view == 0:
				set_materials(transparent); await capture("negative-transparent-body.png")
				if pose_digest() != pd or camera_digest() != cd: fail("Negative pose/camera changed"); return
				negative = {"actual":"negative-transparent-body.png","reference":stem+"-reference.png","actual_sha256":FileAccess.get_sha256(output.path_join("negative-transparent-body.png")),"pose_digest":pd,"camera_digest":cd,"injection":"Every actual body surface has zero alpha; original geometry/skin/pose/camera retained."}
	set_materials(); PARTS.clear_probes(probes); actual_mesh.show()
	for path in plan.frozen_inputs:
		if FileAccess.get_sha256(path) != plan.frozen_inputs[path]: fail("GPU dependency changed during capture"); return
	var report := {"ok":true,"kind":"body_gpu_coverage_discrete_capture","model_sha256":FileAccess.get_sha256(plan.model),"plan_sha256":FileAccess.get_sha256(args[0]),"frozen_inputs":plan.frozen_inputs,"records":records,"negative":negative,"pose_digests":pose_digests,"poses":plan.poses,"body_surfaces":body_surfaces,"body_triangles":body_triangles,"partition_proof":partition.proof,"runtime_meshes_after_cleanup":model.find_children("*","MeshInstance3D",true,false).size(),"source_donor_rgba_sha256":manifest.body_opacity.rgba_sha256,"actual_donor_rgba_sha256":texture_digest(material.albedo_texture),"engine":Engine.get_version_info(),"scope":"Two discrete native poses, eight views. Actual same-pose body alpha coverage only; no closure/anatomy/full077/full490/continuous-time acceptance."}
	FileAccess.open(output.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("BODY_GPU_COVERAGE_DISCRETE_CAPTURE_OK"); quit()
