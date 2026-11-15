extends SceneTree
var output: String
var vp: SubViewport
var camera: Camera3D
var model: Node3D
var carrier: Node3D
var skeleton: Skeleton3D
var player: AnimationPlayer
var controller
var feeding
var prey: Node3D
var prey_body: MeshInstance3D
var prey_material: StandardMaterial3D
var config: Dictionary
var metadata: Array=[]
func _initialize() -> void:
	call_deferred("run")
func photo(name: String, focus: Vector3, direction: Vector3, size: float) -> void:
	camera.size=size;camera.position=focus+direction.normalized()*3
	camera.look_at(focus,Vector3(0,0,-1) if abs(direction.normalized().y)>.99 else Vector3.UP)
	await process_frame
	await RenderingServer.frame_post_draw
	assert(vp.get_texture().get_image().save_png(output.path_join(name+".png"))==OK)
func gray(value: bool) -> void:
	for ob in model.find_children("*","MeshInstance3D",true,false):
		for si in ob.mesh.get_surface_count():
			var mat:=StandardMaterial3D.new();mat.albedo_color=Color(.63,.69,.72);mat.roughness=1.
			if "lining" in ob.mesh.surface_get_material(si).resource_name:mat.albedo_color=Color(.48,.39,.35)
			ob.set_surface_override_material(si,mat if value else null)
func make_prey() -> Node3D:
	var n:=Node3D.new()
	prey_body=MeshInstance3D.new();n.add_child(prey_body)
	prey_material=StandardMaterial3D.new();prey_material.albedo_color=Color(.69,.78,.78);prey_material.roughness=.6;prey_material.cull_mode=BaseMaterial3D.CULL_DISABLED
	return n
func deform_prey(t: float) -> void:
	# Fixed central grip, distributed free-end deflection from delayed acceleration.
	# An authored follow-through response, not a tissue/fluids simulation.
	var lag: float=(feeding.bend(t-.085)-feeding.bend(t))*smoothstep(1.38,1.56,t)
	var st:=SurfaceTool.new();st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var vertices: Array[Vector3]=[]
	for i in range(21):
		var x:=lerpf(-.060,.060,float(i)/20.)
		var radius:=.006*sqrt(maxf(.001,1.-pow(x/.061,2.)))
		var free:=maxf(0.,absf(x)-.014)/.046
		var bend_z:=.030*lag*free*free
		for j in range(10):
			var angle:=TAU*float(j)/10.
			vertices.append(Vector3(x,radius*cos(angle),radius*sin(angle)+bend_z))
	for i in range(20):
		for j in range(10):
			var a:=i*10+j;var b:=i*10+(j+1)%10;var c:=a+10;var d:=b+10
			for idx in [a,c,b,b,c,d]:st.add_vertex(vertices[idx])
	var tail_z:=.030*lag
	for point in [Vector3(.058,0,tail_z),Vector3(.085,.012,tail_z*1.5),Vector3(.080,-.012,tail_z*1.4)]:st.add_vertex(point)
	st.generate_normals();prey_body.mesh=st.commit();prey_body.material_override=prey_material
func bone_point(native: Vector3, bone_name: String) -> Vector3:
	var bid:=skeleton.find_bone(bone_name)
	var p:=Vector3(native.x,native.z,-native.y)
	return skeleton.global_transform*(skeleton.get_bone_global_pose(bid)*skeleton.get_bone_global_rest(bid).affine_inverse()*p)
func pose(t: float, travel: bool=true) -> Dictionary:
	controller.seek(1.0+t)
	carrier.transform=Transform3D.IDENTITY
	var values: Dictionary=feeding.apply(t)
	if travel:
		carrier.rotation.y=deg_to_rad(float(values.body_yaw))
		carrier.position.x=float(values.travel)
		carrier.position.y=.025*smoothstep(1.85,2.9,t)
	# Larger unlabelled fish, held across the mouth. No teleport into a closed jaw.
	var contact:=bone_point(Vector3(.449,0,-.035406921),"jaw_upper")*.5+bone_point(Vector3(.442548394,0,-.037082918),"jaw_lower")*.5
	var f:=smoothstep(1.38,1.56,t)
	prey.position=Vector3(.445,-.043,0).lerp(contact,f)
	var bid:=skeleton.find_bone("feeding_head")
	var head_delta:=skeleton.global_basis*skeleton.get_bone_global_pose(bid).basis*skeleton.get_bone_global_rest(bid).basis.inverse()
	prey.quaternion=Quaternion.IDENTITY.slerp(head_delta.get_rotation_quaternion(),f)*Quaternion(Vector3.UP,PI/2.)
	deform_prey(t)
	prey.visible=true
	return values
func run() -> void:
	var args:=OS.get_cmdline_user_args();assert(args.size()>=2)
	output=args[1];DirAccess.make_dir_recursive_absolute(output)
	var dir: String=get_script().resource_path.get_base_dir()
	config=JSON.parse_string(FileAccess.get_file_as_string(dir.path_join("motion.json")))
	vp=SubViewport.new();vp.size=Vector2i(1280,720);vp.own_world_3d=true;vp.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(vp)
	var env:=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("153745");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color(.8,.91,1);env.environment.ambient_light_energy=.3;vp.add_child(env)
	var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-48,-35,0);light.light_energy=1.0;light.shadow_enabled=true;light.directional_shadow_max_distance=5.;light.shadow_bias=.003;light.shadow_normal_bias=.1;vp.add_child(light)
	var fill:=DirectionalLight3D.new();fill.rotation_degrees=Vector3(25,100,0);fill.light_energy=.25;vp.add_child(fill)
	carrier=Node3D.new();vp.add_child(carrier)
	var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_file(args[0],state)==OK);model=doc.generate_scene(state);carrier.add_child(model)
	skeleton=model.find_children("*","Skeleton3D",true,false)[0];player=model.find_children("*","AnimationPlayer",true,false)[0]
	controller=load("res://scripts/aquarium/FoundryFishMotion.gd").new()
	var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/eleven20261105/blacktip_reef_shark.json"));assert(controller.configure(carrier,model,player,skeleton,profile).ok)
	feeding=load(dir.path_join("FeedingMotion.gd")).new();feeding.configure(skeleton,config)
	prey=make_prey();vp.add_child(prey)
	camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.keep_aspect=Camera3D.KEEP_WIDTH;camera.current=true;vp.add_child(camera)
	assert(controller.set_action("Swim",true));controller.step(0)
	for clay in [true,false]:
		gray(clay)
		for stamp in [{"name":"rest","t":.4},{"name":"half","t":1.19},{"name":"open","t":1.38},{"name":"bite","t":1.66},{"name":"shake_left","t":2.02},{"name":"shake_right","t":2.25},{"name":"carry","t":3.3}]:
			pose(stamp.t,false);prey.visible=false
			for view in ["side","front","bottom","oblique"]:
				var dirs={"side":Vector3(0,-.1,1),"front":Vector3(1,-.3,0),"bottom":Vector3(0,-1,0),"oblique":Vector3(.8,-.6,1)}
				await photo(("gray" if clay else "texture")+"-"+stamp.name+"-"+view,Vector3(.410,-.040,0),dirs[view],.27)
	gray(false)
	pose(1.46)
	await photo("feeding-whole",Vector3(.05,-.010,0),Vector3(.12,-.12,1),1.24)
	await photo("feeding-close",Vector3(.398,-.045,0),Vector3(.42,-.48,1),.39)
	for stamp in [1.2,1.38,1.56,1.80,2.10,2.25,2.4,2.6,2.8,3.3]:
		var v:=pose(stamp)
		if stamp==1.80:
			await photo("grip-front",Vector3(.445+float(v.travel),-.040,0),Vector3(1,-.18,0),.27)
		await photo("prey-%03d"%roundi(stamp*100),Vector3(.405+float(v.travel),-.035,0),Vector3(.42,-.48,1),.39)
	# Render full event, then slow oblique and frontal mouth replays.
	if args.size()<3 or args[2]!="stills":
		for frame in range(101):
			var t:=float(frame)/24.;var values:=pose(t)
			await photo("wide-%03d"%frame,Vector3(.05+.65*float(values.travel),-.005,0),Vector3(.12,-.12,1),1.70)
			metadata.append({"frame":frame,"view":"wide","time":t,"controls":values})
		for frame in range(144):
			var t:=.8+float(frame)/48.;var values:=pose(t)
			await photo("close-%03d"%frame,prey.position+Vector3(-.025,0,0),Vector3(.42,-.48,1),.39)
			metadata.append({"frame":frame,"view":"close_half_speed","time":t,"controls":values})
		for frame in range(144):
			var t:=.8+float(frame)/48.;var values:=pose(t)
			await photo("front-%03d"%frame,Vector3(.02+float(values.travel),.015,0),Vector3(.06,1,.08),1.30)
			metadata.append({"frame":frame,"view":"overhead_half_speed","time":t,"controls":values})
	FileAccess.open(output.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"model_sha256":FileAccess.get_sha256(args[0]),"motion_sha256":FileAccess.get_sha256(dir.path_join("motion.json")),"controller_sha256":FileAccess.get_sha256(dir.path_join("FeedingMotion.gd")),"fps":24,"entry":"Direct cold GLTFDocument load; actual FoundryFishMotion plus isolated FeedingMotion after body motion; no static mesh rebuilds","frames":metadata,"prey":"procedural larger unlabelled fish. Capture/coordinated trunk bend/reversal/settled carry, flexible prey free ends at fixed grip. No fracture/swallow simulation. Motion scale artistic.","status":"preview, not installed game acceptance"},"  "))
	quit()


