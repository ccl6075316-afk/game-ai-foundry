extends "ReviewCaptureBase.gd"
var direction:=Vector3(0,0,1)
var zoom:=1.0
## Candidate-only evidence capture. Never installs assets or invokes a factory.
var plan: Dictionary
var plan_path: String
var review_out: String
var focus := Vector3.ZERO
var bindings: Dictionary={}
var frame_rows: Array=[]
const PACKED_PARTS = preload("PackedFishParts.gd")
var packed_partition: Dictionary={}
var packed_probes: Dictionary={}
var static_check=load("res://../../../resources/scripts/volume-fish/portable/validate_motion_controls.gd")

func _initialize() -> void:
	var args: PackedStringArray=OS.get_cmdline_user_args();assert(args.size()==2)
	plan_path=args[0];review_out=args[1].simplify_path()
	assert(plan_path.is_absolute_path() and review_out.is_absolute_path() and review_out.contains("/experiments/"))
	assert(DisplayServer.get_name()!="headless","Visual evidence requires actual GPU")
	plan=JSON.parse_string(FileAccess.get_file_as_string(plan_path));bindings=plan.frozen_inputs.duplicate()
	for key in ["model","motion_profile","motion_runtime"]:bindings[plan[key]]=plan[key+"_sha256"]
	for source in plan.get("review_sources",[]):
		assert(source.path.is_absolute_path() and FileAccess.get_sha256(source.path)==source.sha256,"Stale visual comparison source")
		bindings[source.path]=source.sha256
	for path in bindings:assert(FileAccess.get_sha256(path)==bindings[path],"Stale review input")
	for path in [get_script().resource_path,"res://../../../resources/scripts/volume-fish/portable/ReviewCaptureBase.gd","res://../../../resources/scripts/volume-fish/portable/validate_motion_controls.gd","res://scripts/aquarium/FoundryFishMotion.gd","res://scripts/aquarium/TankWaterRenderer.gd","res://scripts/aquarium/TankWaterProfile.gd","res://scripts/aquarium/TankWaterVolume.gdshader"]:bindings[ProjectSettings.globalize_path(path)]=FileAccess.get_sha256(path)
	if plan.has("packed_parts_manifest"):
		assert(FileAccess.get_sha256(plan.packed_parts_manifest)==plan.packed_parts_manifest_sha256)
		bindings[plan.packed_parts_manifest]=plan.packed_parts_manifest_sha256
		var helper_path: String=get_script().resource_path.get_base_dir().path_join("PackedFishParts.gd")
		bindings[helper_path]=FileAccess.get_sha256(helper_path)
	DirAccess.make_dir_recursive_absolute(review_out);root.hide();call_deferred("_run")

func _model_path(_route: String) -> String:return plan.model

func _cameras() -> void:
	for entry in entries:
		var basis: Basis=entry.carrier.global_basis;var point: Vector3=entry.carrier.global_position+basis*focus
		entry.camera.keep_aspect=Camera3D.KEEP_WIDTH;entry.camera.size=zoom;entry.camera.position=point+basis*direction*2.
		entry.camera.look_at(point,basis*Vector3.UP if absf(direction.y)<.99 else basis*Vector3(0,0,-1))

func settle() -> void:
	_cameras()
	for i in 3:await process_frame;RenderingServer.force_draw(not plan.has("packed_parts_manifest"))

func photo(label: String) -> void:
	await settle()
	var path: String=review_out.path_join(label+".png");assert(_view_image(entries[0]).save_png(path)==OK)
	report.captures.append({"label":label,"path":path,"sha256":FileAccess.get_sha256(path),"direction":[direction.x,direction.y,direction.z],"camera_size":zoom,"focus":[focus.x,focus.y,focus.z]})

func views() -> Array:
	return [{"name":"left","dir":Vector3(0,0,1)},{"name":"right","dir":Vector3(0,0,-1)},{"name":"front","dir":Vector3(1,0,0)},{"name":"rear","dir":Vector3(-1,0,0)},{"name":"top","dir":Vector3(0,1,0)},{"name":"bottom","dir":Vector3(0,-1,0)},{"name":"oblique","dir":Vector3(.8,.3,1).normalized()},{"name":"reverse-oblique","dir":Vector3(-.8,-.3,-1).normalized()}]

func photo_views(label: String) -> void:
	for view in views():
		direction=view.dir
		for clay in [false,true]:
			_set_gray(clay);await photo(label+"-"+view.name+("-clay" if clay else "-texture"))
	_set_gray(false)

func movie_frame(label: String, phase: int, native: bool=false, transition: bool=false) -> void:
	var entry: Dictionary=entries[0]
	var n: int=frame_rows.size();var orbit: float=TAU*float(n)/288.
	direction=Vector3(.45*sin(orbit),.2,.9*cos(orbit)).normalized();zoom=float(plan.whole_camera_size)*1.15;focus=Vector3.ZERO
	await settle()
	var relative: String="frames/frame-%04d.jpg"%n;var path: String=review_out.path_join(relative)
	assert(_view_image(entry).save_jpg(path,.88)==OK)
	var snapshot: Dictionary={} if native else entry.controller.snapshot()
	if not native:
		assert(snapshot.inside_envelope)
		if not transition:assert(snapshot.action==label and snapshot.pending_action=="")
	frame_rows.append({"path":relative,"sha256":FileAccess.get_sha256(path),"mode":"Native" if native else label,"phase":phase,"clip_time":entry.player.current_animation_position,"snapshot":snapshot,"bone_pose_sha256":pose_hash()})

func pose_hash() -> String:
	var poses: Array=[]
	for i in entries[0].skeleton.get_bone_count():
		var pose: Transform3D=entries[0].skeleton.get_bone_global_pose(i);assert(pose.is_finite());poses.append(pose)
	return var_to_bytes(poses).hex_encode().sha256_text()

func _run() -> void:
	load_plan=plan
	var box: SubViewportContainer=SubViewportContainer.new();root.add_child(box)
	var entry: Dictionary=super._load("B",box);entries.append(entry)
	entry.view.mesh_lod_threshold=0.;entry.model.scale=Vector3.ONE*float(plan.model_scale)
	var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(plan.motion_profile))
	entry.controller=load(plan.motion_runtime).new();assert(entry.controller.configure(entry.carrier,entry.model,entry.player,entry.skeleton,profile).ok)
	if plan.has("packed_parts_manifest"):packed_partition=PACKED_PARTS.surfaces(entry,plan)
	var frozen_static: String=static_check.static_binding_digest(entry.model)
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	zoom=float(plan.whole_camera_size);focus=Vector3.ZERO;await photo_views("whole")
	for detail in plan.details:
		zoom=float(detail.size);focus=Vector3(float(detail.at[0]),float(detail.at[1]),float(detail.at[2]));await photo_views(detail.name)
	var part_meshes: Dictionary={}
	if not packed_partition.is_empty():
		packed_probes=PACKED_PARTS.make_probes(entry,packed_partition)
		for row in packed_partition.surfaces:row.mesh.hide()
		part_meshes=packed_probes
	else:
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):part_meshes[str(mesh.name)]=mesh
	for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.visible=mesh==part_meshes[plan.body]
	zoom=float(plan.whole_camera_size);focus=Vector3.ZERO;await photo_views("body-without-fins")
	for fin in plan.fins:
		var selected: MeshInstance3D=part_meshes[fin];assert(selected!=null)
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.visible=mesh==selected
		var bounds: AABB=selected.get_aabb();focus=entry.carrier.global_transform.affine_inverse()*(selected.global_transform*bounds.get_center())
		zoom=maxf(.035,bounds.size.length()*float(plan.model_scale)*1.7)
		for view in [views()[0],views()[1],views()[6]]:
			direction=view.dir
			for clay in [false,true]:_set_gray(clay);await photo("fin-"+fin+"-"+view.name+("-clay" if clay else "-texture"))
	_set_gray(false)
	if not packed_partition.is_empty():
		PACKED_PARTS.clear_probes(packed_probes)
		for row in packed_partition.surfaces:row.mesh.show()
	else:
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.show()
	DirAccess.make_dir_recursive_absolute(review_out.path_join("frames"))
	entry.carrier.transform=Transform3D.IDENTITY;entry.player.play(profile.base_clip)
	for phase in 48:
		entry.player.seek(fposmod(float(phase)/12.,entry.player.get_animation(profile.base_clip).length),true);entry.player.advance(0.)
		await movie_frame("Native",phase,true)
	for action in ["Swim","Turn","Ascend","Dive"]:
		assert(entry.controller.set_action(action,true));entry.controller.step(0.)
		for phase in 48:entry.controller.step(1./12.);await movie_frame(action,phase)
	for action in ["Turn","Ascend","Dive","Swim"]:
		assert(entry.controller.set_action(action,false))
		for phase in 12:entry.controller.step(1./12.);await movie_frame(action,phase,false,true)
	assert(frame_rows.size()==288)
	FileAccess.open(review_out.path_join("movie-frames.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"fps":12,"duration_seconds":24,"frames":frame_rows,"sequence":"Native4s; Swim/Turn/Ascend/Dive4s each; four real1s transitions","model_sha256":plan.model_sha256},"  ")+"\n")
	# Actual depth-aware renderer and natural-freshwater preset, with hall lights.
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	var world: Node3D=entry.carrier.get_parent();var environment: WorldEnvironment=world.find_children("*","WorldEnvironment",true,false)[0]
	environment.environment.background_color=Color("19303c");environment.environment.ambient_light_color=Color("d6e8e7");environment.environment.ambient_light_energy=.85
	var light: DirectionalLight3D=world.find_children("*","DirectionalLight3D",true,false)[0];light.rotation_degrees=Vector3(-55,-25,0);light.light_color=Color("e3f6ff");light.light_energy=.6
	var shading: Array=[]
	for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
		for s in mesh.mesh.get_surface_count():
			var material: StandardMaterial3D=mesh.get_active_material(s);shading.append([material,material.shading_mode]);material.shading_mode=BaseMaterial3D.SHADING_MODE_PER_PIXEL
	var tank: Node3D=Node3D.new();tank.position=Vector3(0,-1.4,0);world.add_child(tank)
	var water=load("res://scripts/aquarium/TankWaterRenderer.gd").new();world.add_child(water);await process_frame
	var config: Dictionary=load("res://scripts/aquarium/TankWaterProfile.gd").preset(3)
	water.sync([{"tank":tank,"data":{"water":config}}],0.);water.frozen=true;assert(water.count==1)
	zoom=float(plan.whole_camera_size);focus=Vector3.ZERO
	for view in [views()[0],views()[6]]:direction=view.dir;await photo("water-natural-freshwater-"+view.name)
	for saved in shading:saved[0].shading_mode=saved[1]
	assert(static_check.static_binding_digest(entry.model)==frozen_static,"Review changed static model/material bindings")
	for path in bindings:assert(FileAccess.get_sha256(path)==bindings[path],"Review dependency changed")
	var sources: Array=plan.get("review_sources",[])
	for source in sources:assert(FileAccess.get_sha256(source.path)==source.sha256,"Stale visual comparison source")
	report.merge({"kind":"standalone_fish_review_capture","ok":true,"formal_acceptance":false,"model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"frozen_inputs":bindings,"review_sources":sources,"static_arrays_uv_material_digest":frozen_static,"static_arrays_uv_materials_unchanged":true,"direct_GLTFDocument":true,"runtime_static_build_calls":0,"water":{"renderer":"TankWaterRenderer.gd","preset":3,"config":config,"tank_position":[0,-1.4,0],"hall_environment":true},"movie":{"frames":288,"fps":12,"duration_seconds":24},"limits":"Captures are evidence for actual visual review, not automatic anatomical/style acceptance or continuous fin clearance proof."})
	if not packed_partition.is_empty():report["packed_partition_proof"]=packed_partition.proof;report["part_isolation_only_validation_probes"]=true
	FileAccess.open(review_out.path_join("review-capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("STANDALONE_FISH_REVIEW_CAPTURE_OK");quit()
