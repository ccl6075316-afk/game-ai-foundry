extends SceneTree
## 077 full-GLB cold read. No factory, static builders, or imported scene cache.
var plan: Dictionary
var out: String
var viewport: SubViewport
var camera: Camera3D
var carrier: Node3D
var model: Node3D
var skeleton: Skeleton3D
var player: AnimationPlayer
var body: MeshInstance3D
var originals: Array=[]
const PACKED_PARTS = preload("PackedFishParts.gd")
var packed_partition: Dictionary={}

func _initialize() -> void:
	call_deferred("run")

func pose_digest() -> String:
	assert(carrier.transform.is_finite() and model.transform.is_finite() and body.global_transform.is_finite())
	var poses: Array=[carrier.transform,model.transform,body.global_transform]
	for i in skeleton.get_bone_count():
		assert(skeleton.get_bone_global_pose(i).is_finite(),"Nonfinite actual rig pose")
		poses.append(skeleton.get_bone_global_pose(i))
	return var_to_bytes(poses).hex_encode().sha256_text()

func camera_digest() -> String:
	return var_to_bytes([camera.global_transform,camera.projection,camera.size,camera.near,camera.far,viewport.size]).hex_encode().sha256_text()

func capture(path: String) -> void:
	# Submit material and GPU skeleton updates before both halves of each pair.
	for i in 3:
		await process_frame
		if OS.get_environment("FOUNDRY_MANUAL_RENDER")=="1" or plan.has("packed_parts_manifest"):RenderingServer.force_draw(false)
		else:await RenderingServer.frame_post_draw
	assert(viewport.get_texture().get_image().save_png(out.path_join(path))==OK)

func set_materials(reference: Material=null) -> void:
	for s in originals.size():body.set_surface_override_material(s,originals[s] if reference==null else reference)

func texture_rgba_sha(texture: Texture2D) -> String:
	if texture==null:return ""
	var image: Image=texture.get_image();assert(image!=null)
	if image.is_compressed():assert(image.decompress()==OK)
	image.convert(Image.FORMAT_RGBA8)
	if image.has_mipmaps():image.clear_mipmaps()
	var context: HashingContext=HashingContext.new();context.start(HashingContext.HASH_SHA256);context.update(image.get_data())
	return context.finish().hex_encode()

func run() -> void:
	assert(DisplayServer.get_name()!="headless","077 requires actual GPU rendering")
	var args: PackedStringArray=OS.get_cmdline_user_args();assert(args.size()==2)
	plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]));out=args[1]
	var inputs: Dictionary=plan.frozen_inputs.duplicate()
	for key in ["model","motion_profile","motion_runtime"]:
		assert(FileAccess.get_sha256(plan[key])==plan[key+"_sha256"],"Stale standalone dependency")
		inputs[plan[key]]=plan[key+"_sha256"]
	if plan.has("packed_parts_manifest"):inputs[plan.packed_parts_manifest]=plan.packed_parts_manifest_sha256
	for path in inputs:assert(FileAccess.get_sha256(path)==inputs[path])
	DirAccess.make_dir_recursive_absolute(out);root.size=Vector2i(800,600)
	viewport=SubViewport.new();viewport.size=Vector2i(800,600);viewport.own_world_3d=true;viewport.transparent_bg=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewport.mesh_lod_threshold=0.;root.add_child(viewport)
	var world: Node3D=Node3D.new();viewport.add_child(world)
	var environment: WorldEnvironment=WorldEnvironment.new();environment.environment=Environment.new();environment.environment.background_mode=Environment.BG_CLEAR_COLOR;environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=1.;world.add_child(environment)
	camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=10.;camera.current=true;world.add_child(camera)
	var document: GLTFDocument=GLTFDocument.new();var state: GLTFState=GLTFState.new()
	assert(document.append_from_file(plan.model,state)==OK);model=document.generate_scene(state);assert(model!=null)
	carrier=Node3D.new();world.add_child(carrier);carrier.add_child(model)
	assert(is_finite(float(plan.model_scale)) and float(plan.model_scale)>0);model.scale=Vector3.ONE*float(plan.model_scale)
	var skeletons: Array=model.find_children("*","Skeleton3D",true,false);var players: Array=model.find_children("*","AnimationPlayer",true,false)
	assert(skeletons.size()==1 and players.size()==1);skeleton=skeletons[0];player=players[0]
	if plan.has("packed_parts_manifest"):
		var logical: Dictionary=PACKED_PARTS.surfaces({"model":model,"skeleton":skeleton},plan)
		packed_partition=logical.proof
		var probes: Dictionary=PACKED_PARTS.make_probes({"model":model,"skeleton":skeleton},logical,[plan.body])
		body=probes[plan.body]
	else:body=model.find_child(plan.body,true,false) as MeshInstance3D
	assert(body!=null)
	if not packed_partition.is_empty():
		assert(packed_partition.runtime_meshes==1 and packed_partition.runtime_surfaces==1 and packed_partition.triangles_consumed==int(plan.expected_triangles))
		for mesh in model.find_children("*","MeshInstance3D",true,false):mesh.visible=mesh==body
	else:
		var names: Array=[];var triangles: int=0
		for mesh in model.find_children("*","MeshInstance3D",true,false):
			names.append(str(mesh.name));mesh.visible=mesh==body
			for s in mesh.mesh.get_surface_count():triangles+=(mesh.mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX] as PackedInt32Array).size()/3
		assert(names.size()==plan.fins.size()+1 and triangles==int(plan.expected_triangles))
		for name in plan.fins:assert(names.has(name))
	assert(body.mesh.get_surface_count()==int(plan.expected_body_surfaces))
	var materials: Array=[]
	for s in body.mesh.get_surface_count():
		var material: StandardMaterial3D=body.get_active_material(s) as StandardMaterial3D
		assert(material!=null and material.albedo_color.a==1.)
		if packed_partition.is_empty():assert(material.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED)
		else:assert(material.transparency==BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR and material.alpha_scissor_threshold==.5)
		assert(body.material_override==null)
		originals.append(material);materials.append({"surface":s,"name":material.resource_name,"texture":material.albedo_texture!=null,"transparency":material.transparency,"rgba_sha256":texture_rgba_sha(material.albedo_texture)})
	var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(plan.motion_profile))
	var controller=load(plan.motion_runtime).new();var configured: Dictionary=controller.configure(carrier,model,player,skeleton,profile);assert(configured.ok)
	var reference: StandardMaterial3D=StandardMaterial3D.new();reference.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;reference.cull_mode=BaseMaterial3D.CULL_DISABLED;reference.albedo_color=Color.WHITE
	var transparent: StandardMaterial3D=StandardMaterial3D.new();transparent.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR;transparent.alpha_scissor_threshold=.5;transparent.albedo_color=Color(1,1,1,0)
	var views: Array=[[0.,0.],[PI,0.],[PI/2.,0.],[-PI/2.,0.],[.5,.85],[.5,-.85],[PI+.5,.65],[PI+.5,-.65]]
	var records: Array=[];var negative: Dictionary={};var snapshots: Array=[]
	for pose in 2:
		if pose==0:
			player.stop();skeleton.reset_bone_poses();carrier.transform=Transform3D.IDENTITY
		else:
			assert(float(plan.maximum_amplitude)==2.5 and is_finite(float(plan.pose_time)))
			controller.set_motion_controls({"body_amplitude":2.5,"fin_amplitude":2.5},true)
			assert(controller.set_action("Turn",true));controller.step(0.);controller.seek(float(plan.pose_time))
			snapshots.append(controller.snapshot())
		skeleton.force_update_all_bone_transforms()
		for i in 3:await process_frame
		for v in views.size():
			var basis: Basis=carrier.global_basis.orthonormalized();var focus: Vector3=carrier.global_position
			var yaw: float=views[v][0];var pitch: float=views[v][1]
			camera.size=float(profile.real_length_cm)/100.*1.3
			camera.global_position=focus+basis*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*2.
			camera.look_at(focus,basis*Vector3.UP)
			var stem: String="p%d-v%d"%[pose,v];var pd: String=pose_digest();var cd: String=camera_digest()
			set_materials();await capture(stem+"-actual.png")
			assert(pose_digest()==pd and camera_digest()==cd)
			set_materials(reference);await capture(stem+"-closed.png")
			var row: Dictionary={"pose":pose,"view":v,"pose_before":pd,"pose_after":pose_digest(),"camera_before":cd,"camera_after":camera_digest(),"actual":stem+"-actual.png","reference":stem+"-closed.png"}
			for key in ["actual","reference"]:row[key+"_sha256"]=FileAccess.get_sha256(out.path_join(row[key]))
			records.append(row)
			if pose==0 and v==0:
				set_materials(transparent);await capture("negative-transparent-body.png")
				assert(pose_digest()==pd and camera_digest()==cd)
				negative={"actual":"negative-transparent-body.png","actual_sha256":FileAccess.get_sha256(out.path_join("negative-transparent-body.png")),"reference":stem+"-closed.png","injection":"All actual body surfaces use alpha-scissor material with zero alpha; geometry/pose/camera unchanged."}
	set_materials()
	for path in inputs:assert(FileAccess.get_sha256(path)==inputs[path],"Runtime dependency changed")
	var receipt: Dictionary={"model_sha256":FileAccess.get_sha256(plan.model),"plan_sha256":FileAccess.get_sha256(args[0]),"body":plan.body,"frozen_inputs":inputs,"records":records,"negative":negative,"motion":{"configure":configured,"snapshots":snapshots,"bone_count":skeleton.get_bone_count(),"materials":materials,"static_builders":false,"direct_GLTFDocument":true,"settle_frames_per_capture":3}}
	if not packed_partition.is_empty():receipt["packed_partition_proof"]=packed_partition;receipt["validation_only_actual_array_subset_probe"]=true
	FileAccess.open(out.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(receipt,"  ")+"\n")
	print("STANDALONE_BODY_077_CAPTURE_OK");quit()
