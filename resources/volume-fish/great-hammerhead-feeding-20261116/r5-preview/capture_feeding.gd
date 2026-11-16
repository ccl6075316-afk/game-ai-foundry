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
var initial_prey_position: Vector3
var initial_prey_rotation: Quaternion
const GRIP := 1.56
const UPPER_LIP := Vector3(1.19542694, 0., -.26475)
const LOWER_LIP := Vector3(1.189027, 0., -.27055)
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
	prey_material=StandardMaterial3D.new()
	prey_material.vertex_color_use_as_albedo=true
	prey_material.roughness=.68
	prey_material.cull_mode=BaseMaterial3D.CULL_DISABLED
	return n
func deform_prey(t: float, grip_depth: float) -> void:
	var lag: float=(feeding.bend(t-.09)-feeding.bend(t))*feeding.eased(GRIP,1.78,t)
	var st:=SurfaceTool.new();st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var vertices: Array[Vector3]=[]
	var colors: Array[Color]=[]
	var belly:=Color(.69,.74,.71)
	var back:=Color(.26,.39,.42)
	for i in range(21):
		var x:=lerpf(-.060,.060,float(i)/20.)
		var fullness:=smoothstep(-.063,-.039,x)*(1.-.84*smoothstep(-.021,.057,x))
		var radius:=maxf(.0006,.010*fullness)
		var vertical_radius:=radius
		if config.prey_mode=="large":
			var free_end:=smoothstep(.001,.031,absf(x))
			radius*=1.43
			vertical_radius=lerpf(grip_depth/prey.scale.y, radius, free_end)
		var free:=smoothstep(.01,.060,absf(x))
		var bend_z:=.015*lag*free*free
		for j in range(10):
			var angle:=TAU*float(j)/10.
			var y:=cos(angle)
			vertices.append(Vector3(x,vertical_radius*y,radius*.71*sin(angle)+bend_z))
			colors.append(belly.lerp(back,smoothstep(-.45,.72,y)))
	for i in range(20):
		for j in range(10):
			var a:=i*10+j;var b:=i*10+(j+1)%10;var c:=a+10;var d:=b+10
			for idx in [a,c,b,b,c,d]:
				st.set_color(colors[idx])
				st.add_vertex(vertices[idx])
	var tail_z:=.015*lag
	var root:=Vector3(.059,0,tail_z)
	var notch:=Vector3(.074,0,tail_z*1.24)
	for tip in [Vector3(.086,.011,tail_z*1.55),Vector3(.084,-.010,tail_z*1.46)]:
		for point in [root,tip,notch]:
			st.set_color(back.lerp(belly,.25))
			st.add_vertex(point)
	st.generate_normals();prey_body.mesh=st.commit();prey_body.material_override=prey_material
func bone_point(native: Vector3, bone_name: String) -> Vector3:
	var bid:=skeleton.find_bone(bone_name)
	var p:=Vector3(native.x,native.z,-native.y)
	return skeleton.global_transform*(skeleton.get_bone_global_pose(bid)*skeleton.get_bone_global_rest(bid).affine_inverse()*p)
func shark_pose(t: float, travel: bool) -> Dictionary:
	controller.seek(1.0+t)
	carrier.transform=Transform3D.IDENTITY
	var values: Dictionary=feeding.apply(t)
	if travel:
		carrier.rotation.y=deg_to_rad(float(values.body_yaw))
		carrier.position=feeding.path_position(t)
		carrier.position.y=.025*feeding.eased(1.85,2.9,t)
	return values

func oral_frame() -> Dictionary:
	var upper:=bone_point(UPPER_LIP,"jaw_upper")
	var lower:=bone_point(LOWER_LIP,"jaw_lower")
	var up:=(upper-lower).normalized()
	var bid:=skeleton.find_bone("feeding_head")
	var head_delta:=skeleton.global_basis*skeleton.get_bone_global_pose(bid).basis*skeleton.get_bone_global_rest(bid).basis.inverse()
	var crosswise:=-(head_delta.z-up*head_delta.z.dot(up)).normalized()
	return {"upper":upper,"lower":lower,"center":upper.lerp(lower,.5),
		"crosswise":Basis(crosswise,up,crosswise.cross(up)).get_rotation_quaternion(),
		"lengthwise":head_delta.get_rotation_quaternion()}

func pose(t: float, travel: bool=true) -> Dictionary:
	var values:=shark_pose(t, travel)
	var mouth:=oral_frame()
	var contact: Vector3=mouth.center
	var small: bool=config.prey_mode=="small"
	var target_rotation: Quaternion=mouth.lengthwise if small else mouth.crosswise
	var attachment: float=feeding.eased(1.44,GRIP,t)
	prey.position=initial_prey_position.lerp(contact,attachment)
	prey.quaternion=initial_prey_rotation.slerp(target_rotation,attachment)
	var jaw_gap: float=mouth.upper.distance_to(mouth.lower)
	var pad: float=lerpf(.02205, jaw_gap*.5, attachment)
	deform_prey(t,pad)
	prey.visible=true
	if small:
		var swallow: float=feeding.eased(1.66,2.47,t)
		var inside:=bone_point(Vector3(.89,0,-.19),"feeding_head")
		prey.position=prey.position.lerp(inside,swallow)
	values["jaw_gap_m"]=jaw_gap
	values["prey_center_to_lip_midpoint_m"]=prey.position.distance_to(contact)
	if not small and t>=GRIP:
		var contact_offset: Vector3=prey.basis.y.normalized()*pad
		values["upper_grip_error_m"]=(prey.position+contact_offset).distance_to(mouth.upper)
		values["lower_grip_error_m"]=(prey.position-contact_offset).distance_to(mouth.lower)
	return values
func run() -> void:
	var args:=OS.get_cmdline_user_args();assert(args.size()>=2)
	output=args[1];DirAccess.make_dir_recursive_absolute(output)
	var dir: String=get_script().resource_path.get_base_dir()
	var small:=args.size()>3 and args[3]=="small"
	var config_file:="motion-small.json" if small else "motion.json"
	config=JSON.parse_string(FileAccess.get_file_as_string(dir.path_join(config_file)))
	vp=SubViewport.new();vp.size=Vector2i(960,540);vp.own_world_3d=true;vp.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(vp)
	var env:=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("153745");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color(.8,.91,1);env.environment.ambient_light_energy=.3;vp.add_child(env)
	var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-48,-35,0);light.light_energy=1.0;light.shadow_enabled=true;light.directional_shadow_max_distance=5.;light.shadow_bias=.003;light.shadow_normal_bias=.1;vp.add_child(light)
	var fill:=DirectionalLight3D.new();fill.rotation_degrees=Vector3(25,100,0);fill.light_energy=.25;vp.add_child(fill)
	carrier=Node3D.new();vp.add_child(carrier)
	var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_file(args[0],state)==OK);model=doc.generate_scene(state);carrier.add_child(model)
	skeleton=model.find_children("*","Skeleton3D",true,false)[0];player=model.find_children("*","AnimationPlayer",true,false)[0]
	var swim_path:=ProjectSettings.globalize_path(dir).path_join("../../../runtime/godot/VolumeFishMotion.gd").simplify_path()
	controller=load(swim_path).new()
	var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(dir.path_join("swim-profile.json")));assert(controller.configure(carrier,model,player,skeleton,profile).ok)
	feeding=load(dir.path_join("FeedingMotion.gd")).new();feeding.configure(skeleton,config)
	prey=make_prey();prey.scale=Vector3.ONE*(1.1 if small else 7.);vp.add_child(prey)
	camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.keep_aspect=Camera3D.KEEP_WIDTH;camera.current=true;vp.add_child(camera)
	assert(controller.set_action("Swim",true));controller.step(0)
	shark_pose(GRIP,true)
	var initial_contact:=oral_frame()
	initial_prey_position=initial_contact.center
	initial_prey_rotation=initial_contact.lengthwise if small else initial_contact.crosswise
	var mode: String=args[2] if args.size()>2 else "video"
	if mode == "eyes":
		for stamp in [0.4, 1.38, 2.25]:
			pose(stamp, false);prey.visible=false
			for side in [-1,1]:
				var point:=bone_point(Vector3(1.315867,side*.50,-.1956535),"feeding_head")
				var suffix:="%s-%s" % [str(side), str(stamp)]
				await photo("eye-side-"+suffix,point,Vector3(0,0,-side),.13)
				await photo("eye-oblique-"+suffix,point,Vector3(.48,-.34,-side),.14)
		quit()
		return
	if mode == "poses":
		var sampled: Array=[]
		for frame in range(253):
			var t:=float(frame)/60.
			sampled.append({"t":t,"values":pose(t)})
		FileAccess.open(output.path_join("pose.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"model_sha256":FileAccess.get_sha256(args[0]),"frames":sampled}, "  "))
		quit()
		return
	for clay in ([true,false] if mode == "stills" else []):
		gray(clay)
		for stamp in [{"name":"rest","t":.4},{"name":"half","t":1.19},{"name":"open","t":1.38},{"name":"bite","t":1.66},{"name":"shake_left","t":2.02},{"name":"shake_right","t":2.25},{"name":"carry","t":3.3}]:
			pose(stamp.t,false);prey.visible=false
			for view in ["side","front","bottom","oblique"]:
				var dirs={"side":Vector3(0,-.1,1),"front":Vector3(1,-.3,0),"bottom":Vector3(0,-1,0),"oblique":Vector3(.8,-.6,1)}
				await photo(("gray" if clay else "texture")+"-"+stamp.name+"-"+view,Vector3(1.14,-.27,0),dirs[view],.62)
	gray(false)
	if mode == "stills":
		for stamp in [1.38,1.56,1.80,2.10,2.25,2.4,2.6,3.3,4.2]:
			pose(stamp)
			await photo("prey-%03d"%roundi(stamp*100),bone_point(Vector3(1.16,0,-.27),"feeding_head"),Vector3(.42,-.48,1),1.15)
	else:
		for frame in range(252):
			var t:=float(frame)/60.;var values:=pose(t)
			await photo("wide-%03d"%frame,carrier.position+Vector3(-.19,-.06,0),Vector3(.19,-.23,1),5.75)
			metadata.append({"frame":frame,"view":"wide","time":t,"controls":values})
		for frame in range(252):
			var t:=1.18+float(frame)/120.;var values:=pose(t)
			if small:
				await photo("close-%03d"%frame,bone_point(Vector3(1.16,0,-.27),"feeding_head"),Vector3(.42,-.48,1),1.2)
			else:
				await photo("close-%03d"%frame,carrier.position+Vector3(-.40,-.03,0),Vector3(0,.94,.34),5.85)
			metadata.append({"frame":frame,"view":"close_half_speed","time":t,"controls":values})
	FileAccess.open(output.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"model_sha256":FileAccess.get_sha256(args[0]),"motion_sha256":FileAccess.get_sha256(dir.path_join(config_file)),"controller_sha256":FileAccess.get_sha256(dir.path_join("FeedingMotion.gd")),"fps":60,"entry":"Direct cold GLTFDocument load; actual FoundryFishMotion plus isolated FeedingMotion after body motion; no static mesh rebuilds","frames":metadata,"prey_mode":config.prey_mode,"prey":"Small: rigid prey moves into oral interior, never shrunk or visibility-hidden; authored ingestion, not fluid simulation. Large: thick free ends and narrow grip, whole-body lateral processing; no tissue fracture. Motion scale artistic, no calibrated hammerhead frequency.","status":"preview, not installed game acceptance"},"  "))
	quit()



