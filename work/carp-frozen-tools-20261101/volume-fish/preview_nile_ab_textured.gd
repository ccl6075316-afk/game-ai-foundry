extends SceneTree
## Loads only exported A/B GLBs. No production factory/static modeling chain.
const MOTION = preload("res://scripts/aquarium/FoundryFishMotion.gd")
var directory: String
var entries: Array = []
var live := false
var movie := false
var motion_paused := false
var gray := false
var direction := Vector3(0,0,1)
var zoom := .52
var yaw := 0.0
var pitch := 0.0
var report := {"kind":"nile_AB_cold_render","formal_acceptance":false,"static_construction_chain":false,"models":[],"captures":[],"motion_actions":[]}

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size()>0)
	directory=args[0].simplify_path();live="--live" in args;movie="--movie" in args
	assert(directory==ProjectSettings.globalize_path("res://../experiments/nile-dorsal-route-trial/round4-ab-textured").simplify_path())
	assert(DisplayServer.get_name()!="headless")
	call_deferred("_run")

func _button(bar: HBoxContainer, label: String, callback: Callable) -> void:
	var b := Button.new();b.text=label;b.pressed.connect(callback);bar.add_child(b)

func _model_path(route: String) -> String:
	return directory.path_join(route+"-artifacts/fish.glb")

func _load(route: String, container: SubViewportContainer) -> Dictionary:
	var view := SubViewport.new();view.size=Vector2i(900,620);view.own_world_3d=true;view.render_target_update_mode=SubViewport.UPDATE_ALWAYS;container.add_child(view)
	var world := Node3D.new();view.add_child(world)
	var environment := WorldEnvironment.new();environment.environment=Environment.new()
	environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color("25343c")
	environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=.65;world.add_child(environment)
	var light := DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.65;world.add_child(light)
	var camera := Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=10;camera.current=true;world.add_child(camera)
	var path := _model_path(route)
	var doc := GLTFDocument.new();var state := GLTFState.new();assert(doc.append_from_file(path,state)==OK)
	var model := doc.generate_scene(state);assert(model!=null)
	var carrier := Node3D.new();world.add_child(carrier);carrier.add_child(model);model.scale=Vector3.ONE*.402819722890854
	var skeleton: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]
	var player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
	var count := 0;var materials := [];var names := []
	for mesh in model.find_children("*","MeshInstance3D",true,false):
		names.append(str(mesh.name))
		for surface in mesh.mesh.get_surface_count():
			count+=(mesh.mesh.surface_get_arrays(surface)[Mesh.ARRAY_INDEX] as PackedInt32Array).size()/3
			var mat: StandardMaterial3D=mesh.mesh.surface_get_material(surface)
			assert(mat!=null)
			mat.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST;mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
			materials.append({"name":mat.resource_name,"texture":mat.albedo_texture!=null,"alpha":mat.transparency})
	var controller=MOTION.new()
	var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(ProjectSettings.globalize_path("res://../../../resources/volume-fish/motion/nile_tilapia-082.json")))
	var configured: Dictionary=controller.configure(carrier,model,player,skeleton,profile)
	assert(configured.ok,JSON.stringify(configured))
	report.models.append({"route":route,"model_sha256":FileAccess.get_sha256(path),"triangles":count,"meshes":names,"materials":materials,"motion_configure":configured,"animations":player.get_animation_list()})
	return {"route":route,"model":model,"carrier":carrier,"view":view,"camera":camera,"controller":controller,"skeleton":skeleton,"player":player}

func _set_gray(value: bool) -> void:
	gray=value
	var mat := StandardMaterial3D.new();mat.albedo_color=Color(.65,.68,.7);mat.roughness=1;mat.metallic_specular=0
	for entry in entries:
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.material_override=mat if gray else null

func _input_surface(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if event.button_index==MOUSE_BUTTON_WHEEL_UP:zoom=maxf(.06,zoom/1.12)
		if event.button_index==MOUSE_BUTTON_WHEEL_DOWN:zoom=minf(1.5,zoom*1.12)
	elif event is InputEventMouseMotion and event.button_mask&MOUSE_BUTTON_MASK_LEFT:
		yaw-=event.relative.x*.008;pitch=clampf(pitch+event.relative.y*.008,-1.55,1.55)
		direction=Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))

func _cameras() -> void:
	for entry in entries:
		var focus: Vector3=entry.carrier.global_position
		var dir: Vector3=entry.carrier.global_basis*direction
		entry.camera.size=zoom;entry.camera.position=focus+dir*2
		entry.camera.look_at(focus,entry.carrier.global_basis*Vector3.UP if absf(direction.y)<.99 else Vector3(0,0,-1))

func _capture(label: String) -> void:
	_cameras()
	await process_frame
	await RenderingServer.frame_post_draw
	for entry in entries:
		var path := directory.path_join(entry.route+"-artifacts/review/"+label+".png")
		DirAccess.make_dir_recursive_absolute(path.get_base_dir())
		assert(_view_image(entry).save_png(path)==OK)
		report.captures.append({"route":entry.route,"label":label,"path":path,"sha256":FileAccess.get_sha256(path)})

func _view_image(entry: Dictionary) -> Image:
	var original: Image=entry.view.get_texture().get_image()
	var width := mini(900,original.get_width());var height := mini(620,original.get_height())
	return original.get_region(Rect2i((original.get_width()-width)/2,(original.get_height()-height)/2,width,height))

func _run() -> void:
	root.title="罗非鱼整鱼 A / B · 同皮肤对照";root.size=Vector2i(1440,820)
	var panel := VBoxContainer.new();panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.add_child(panel)
	var bar := HBoxContainer.new();panel.add_child(bar)
	for action in ["Swim","Turn","Ascend","Dive"]:
		_button(bar,action,func():
			for entry in entries:entry.controller.set_action(action,true))
	_button(bar,"Pause",func():motion_paused=not motion_paused)
	_button(bar,"Clay / Texture",func():_set_gray(not gray))
	_button(bar,"Side",func():direction=Vector3(0,0,1);yaw=0;pitch=0)
	_button(bar,"Oblique",func():direction=Vector3(.65,.25,1).normalized())
	_button(bar,"Front",func():direction=Vector3(1,0,0))
	_button(bar,"Top",func():direction=Vector3(0,1,.001).normalized())
	var row := HBoxContainer.new();row.size_flags_vertical=Control.SIZE_EXPAND_FILL;panel.add_child(row)
	for route in ["A","B"]:
		var col := VBoxContainer.new();col.size_flags_horizontal=Control.SIZE_EXPAND_FILL;row.add_child(col)
		var label := Label.new();label.text=route+" · "+("1492" if route=="A" else "1458")+" triangles";label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;col.add_child(label)
		var box := SubViewportContainer.new();box.stretch=true;box.size_flags_vertical=Control.SIZE_EXPAND_FILL;box.size_flags_horizontal=Control.SIZE_EXPAND_FILL;col.add_child(box);box.gui_input.connect(_input_surface)
		entries.append(_load(route,box))
	await process_frame
	motion_paused=true
	# Rest-pose renders, not a fortuitous animation frame.
	for entry in entries:
		entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	for view in [{"name":"side","dir":Vector3(0,0,1)},{"name":"back-side","dir":Vector3(0,0,-1)},{"name":"oblique","dir":Vector3(.65,.25,1).normalized()},{"name":"front","dir":Vector3(1,0,0)},{"name":"top","dir":Vector3(0,1,.001).normalized()}]:
		direction=view.dir
		for clay in [false,true]:
			_set_gray(clay);await _capture(view.name+("-clay" if clay else "-texture"))
	_set_gray(false);direction=Vector3(.4,.18,1).normalized()
	for action in ["Swim","Turn","Ascend","Dive"]:
		for entry in entries:
			assert(entry.controller.set_action(action,true));entry.controller.step(0.)
			for i in 48:entry.controller.step(1./60)
		await _capture("motion-"+action)
		report.motion_actions.append(action)
	# Actual transition sequence, with representative intermediate images.
	for action in ["Swim","Turn","Ascend","Dive","Swim"]:
		for entry in entries:
			assert(entry.controller.set_action(action,false))
			for i in 30:entry.controller.step(1./60)
		await _capture("transition-to-"+action)
	report["ok"]=true
	FileAccess.open(directory.path_join("cold-render.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("NILE_AB_COLD_RENDER_OK")
	if movie:await _movie()
	if live:motion_paused=false;direction=Vector3(0,0,1)
	else:quit()

func _movie() -> void:
	var movie_dir := directory.path_join("movie-frames")
	DirAccess.make_dir_recursive_absolute(movie_dir)
	var frames := [];var frame := 0
	direction=Vector3(.45,.18,1).normalized();_set_gray(false)
	for mode in ["Native","Swim","Turn","Ascend","Dive"]:
		for entry in entries:
			if mode=="Native":
				entry.carrier.transform=Transform3D.IDENTITY;entry.skeleton.reset_bone_poses();entry.player.play("Animation")
			else:assert(entry.controller.set_action(mode,false))
		for phase in 30:
			for entry in entries:
				if mode=="Native":entry.player.seek(float(phase)*2.4/30.,true);entry.player.advance(0.)
				else:entry.controller.step(1./15.)
			_cameras();await process_frame;await RenderingServer.frame_post_draw
			var image := Image.create(1800,650,false,Image.FORMAT_RGB8);image.fill(Color("25343c"))
			for index in entries.size():
				var tile: Image=_view_image(entries[index]);tile.convert(Image.FORMAT_RGB8)
				image.blit_rect(tile,Rect2i(0,0,900,620),Vector2i(index*900,30))
			var path := movie_dir.path_join("frame-%04d.jpg"%frame);assert(image.save_jpg(path,.9)==OK)
			frames.append({"path":path,"sha256":FileAccess.get_sha256(path),"mode":mode,"phase":phase});frame+=1
	FileAccess.open(directory.path_join("movie-frames.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"frames":frames,"fps":15,"layout":"A left; B right. Native clip 0-2s, then Swim/Turn/Ascend/Dive each2s; real controller transitions; camera follows carrier."},"  ")+"\n")

func _process(delta: float) -> bool:
	if live and not motion_paused:
		for entry in entries:entry.controller.step(minf(delta,.05))
	if not entries.is_empty():_cameras()
	return false
