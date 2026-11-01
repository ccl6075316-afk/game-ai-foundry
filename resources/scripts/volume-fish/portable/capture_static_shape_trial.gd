extends SceneTree
## Direct cold GLB evidence for a bounded static reference-shape experiment.
## This script creates cameras/lights only; no model geometry or material edits.
var cfg: Dictionary
var destination: String
func _initialize() -> void:
	var a=OS.get_cmdline_user_args();assert(a.size()==2)
	cfg=JSON.parse_string(FileAccess.get_file_as_string(a[0]));destination=a[1]
	assert(FileAccess.get_sha256(cfg.model)==cfg.model_sha256 and destination.contains("/experiments/"))
	DirAccess.make_dir_recursive_absolute(destination);call_deferred("run")
func run() -> void:
	root.size=Vector2i(900,620);root.position=Vector2i(-3000,-3000)
	var view:=SubViewport.new();view.size=Vector2i(900,620);view.own_world_3d=true;view.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(view)
	var world:=Node3D.new();view.add_child(world)
	var env:=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("25343c");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.65;world.add_child(env)
	var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.65;world.add_child(light)
	var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_file(cfg.model,state)==OK)
	var model=doc.generate_scene(state);world.add_child(model)
	var camera:=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.current=true;camera.near=.001;camera.far=3;camera.keep_aspect=Camera3D.KEEP_WIDTH;world.add_child(camera)
	var count:=0
	for node in model.find_children("*","MeshInstance3D",true,false):
		for si in node.mesh.get_surface_count():count+=node.mesh.surface_get_arrays(si)[Mesh.ARRAY_INDEX].size()/3
	assert(count==int(cfg.triangles))
	var captures: Array=[]
	for region in cfg.regions:
		var point:=Vector3(region.at[0],region.at[1],region.at[2]);camera.size=float(region.size)
		for v in [{"name":"side","dir":Vector3(0,0,1)},{"name":"front","dir":Vector3(1,0,0)},{"name":"top","dir":Vector3(0,1,.001)},{"name":"bottom","dir":Vector3(0,-1,.001)},{"name":"oblique","dir":Vector3(.7,.4,1)},{"name":"under-oblique","dir":Vector3(.7,-.6,1)}]:
			camera.position=point+v.dir.normalized();camera.look_at(point,Vector3.UP if absf(v.dir.y)<.99 else Vector3(0,0,-1))
			for i in 3:await process_frame;RenderingServer.force_draw(true)
			var path=destination.path_join(str(region.name)+"-"+v.name+".png");assert(view.get_texture().get_image().save_png(path)==OK)
			captures.append({"path":path,"sha256":FileAccess.get_sha256(path)})
	FileAccess.open(destination.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"ok":true,"kind":"direct_static_shape_trial_gpu_capture","model_sha256":cfg.model_sha256,"triangles":count,"captures":captures,"runtime_static_build_calls":0,"rigged":false,"complete_fish":false,"formal_acceptance":false},"  ")+"\n")
	print("STATIC_SHAPE_TRIAL_CAPTURE_OK");quit()
