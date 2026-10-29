extends SceneTree
## Experiment-only cold GLB fin loading into an unchanged production fish instance.
var output := ""
var factory
var world: Node3D
var viewport: SubViewport
var camera: Camera3D
var results := []
var factories := []
var reference_centers := {}
var live := false
var smoke := false
var live_entries := []
var live_cameras := []
var live_paused := false
var live_close := false
var live_direction := Vector3(0,0,1)
var live_frames := 0
var live_yaw := 0.0
var live_pitch := 0.0
var live_zoom := .72
var live_pan := Vector3.ZERO
var live_panel: Control
var live_surfaces := []
var live_closing := false
var round2 := false
var live_report_dir := ""
var live_gray := false
var live_capture := false
const SPECIES := "nile_tilapia"
const EXPECTED_SHA := "4ee2c552939b682463120b52e40f2f98e996c2dad8f91f9144ab7d6de51ad25a"

func _initialize() -> void:
	var args := OS.get_cmdline_user_args(); assert(args.size()>=1)
	output=args[0].simplify_path()
	live="--live" in args;smoke="--smoke" in args
	round2="--round2" in args;live_report_dir=output.path_join("round2") if round2 else output
	assert(output==ProjectSettings.globalize_path("res://../experiments/nile-dorsal-route-trial").simplify_path())
	assert(DisplayServer.get_name()!="headless")
	call_deferred("_live" if live else "_run")

func _live_button(bar: HBoxContainer, text: String, callback: Callable) -> void:
	var button := Button.new();button.text=text;button.pressed.connect(callback);bar.add_child(button)

func _live_view(direction: Vector3) -> void:
	direction=direction.normalized();live_yaw=atan2(direction.x,direction.z);live_pitch=asin(direction.y)

func _live_reset() -> void:
	live_close=false;live_zoom=.72;live_pan=Vector3.ZERO;_live_view(Vector3(0,0,1))

func _live_pan_pixels(relative: Vector2, height: float) -> void:
	var basis: Basis=live_cameras[0].global_transform.basis
	live_pan+=(-basis.x*relative.x+basis.y*relative.y)*live_zoom/maxf(height,1.)

func _live_input(event: InputEvent, surface: Control) -> void:
	if event is InputEventMouseButton:
		if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
			var exponent := -1. if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.
			live_zoom=clampf(live_zoom*pow(1.12,exponent*maxf(event.factor,1.)),.015,3.)
		elif event.pressed and event.double_click and event.button_index==MOUSE_BUTTON_LEFT:_live_reset()
	elif event is InputEventMouseMotion:
		if event.button_mask&MOUSE_BUTTON_MASK_LEFT:
			live_yaw-=event.relative.x*.008;live_pitch=clampf(live_pitch+event.relative.y*.008,-1.55,1.55)
		elif event.button_mask&(MOUSE_BUTTON_MASK_RIGHT|MOUSE_BUTTON_MASK_MIDDLE):_live_pan_pixels(event.relative,surface.size.y)
	elif event is InputEventMagnifyGesture:live_zoom=clampf(live_zoom/maxf(event.factor,.01),.015,3.)
	elif event is InputEventPanGesture:_live_pan_pixels(event.delta*8.,surface.size.y)

func _live() -> void:
	assert(FileAccess.get_sha256("res://assets/models/fish/nile_tilapia.glb")==EXPECTED_SHA)
	root.title="罗非鱼背鳍 · 原版 / 减面 / 低面重建"
	root.size=Vector2i(1380,780)
	auto_accept_quit=false;root.close_requested.connect(_live_shutdown)
	var panel := VBoxContainer.new();panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.add_child(panel)
	live_panel=panel
	var theme := Theme.new();var font := SystemFont.new();font.font_names=PackedStringArray(["PingFang SC"]);theme.default_font=font;theme.default_font_size=18;panel.theme=theme
	var title := Label.new();title.text="同一条鱼、同一材质、同步动作 · 仅背鳍不同（实验对照）";title.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;panel.add_child(title)
	var controls := HBoxContainer.new();controls.alignment=BoxContainer.ALIGNMENT_CENTER;panel.add_child(controls)
	for action in ["Swim","Turn","Ascend","Dive"]:
		var label: String={"Swim":"游动","Turn":"转身","Ascend":"上浮","Dive":"下潜"}[action]
		_live_button(controls,label,func():
			for entry in live_entries:entry.controller.set_action(action,true))
	_live_button(controls,"暂停 / 继续",func():live_paused=not live_paused)
	_live_button(controls,"整鱼 / 放大背鳍",func():live_close=not live_close;live_pan=Vector3.ZERO;live_zoom=.40 if live_close else .72)
	_live_button(controls,"侧面",func():_live_view(Vector3(0,0,1)))
	_live_button(controls,"斜视",func():_live_view(Vector3(.65,.25,1)))
	_live_button(controls,"俯视",func():_live_view(Vector3(0,1,.01)))
	_live_button(controls,"复位",_live_reset)
	_live_button(controls,"灰模 / 材质",func():
		live_gray=not live_gray
		var gray := StandardMaterial3D.new();gray.albedo_color=Color(.7,.7,.7);gray.roughness=1.;gray.metallic_specular=0.
		for entry in live_entries:
			for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.material_override=gray if live_gray else null)
	var columns := HBoxContainer.new();columns.size_flags_vertical=Control.SIZE_EXPAND_FILL;panel.add_child(columns)
	var modes := ["baseline","route-a-600","route-b-600"]
	var labels := ["原版背鳍 · 18,592 三角面","A 旧鳍减面 · 600 三角面","B 新建低面网格 · 584 三角面"]
	if round2:modes=["baseline","round2"];labels=["原版 · 全鳍 48,252 三角面","B 新鳍 · 4,428 三角面 · 弧度 / 渐薄 / 尾接头"]
	var receipts := []
	for index in modes.size():
		var column := VBoxContainer.new();column.size_flags_horizontal=Control.SIZE_EXPAND_FILL;columns.add_child(column)
		var heading := Label.new();heading.text=labels[index];heading.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;column.add_child(heading)
		var frame := Control.new();frame.size_flags_vertical=Control.SIZE_EXPAND_FILL;frame.size_flags_horizontal=Control.SIZE_EXPAND_FILL;column.add_child(frame)
		var container := SubViewportContainer.new();container.stretch=true;container.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);frame.add_child(container);container.mouse_filter=Control.MOUSE_FILTER_IGNORE
		var view := SubViewport.new();view.size=Vector2i(450,650);view.own_world_3d=true;view.render_target_update_mode=SubViewport.UPDATE_ALWAYS;container.add_child(view)
		var surface := Control.new();surface.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);surface.mouse_filter=Control.MOUSE_FILTER_STOP;frame.add_child(surface);surface.gui_input.connect(_live_input.bind(surface));live_surfaces.append(surface)
		var space := Node3D.new();view.add_child(space)
		var environment := WorldEnvironment.new();environment.environment=Environment.new();environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color("19303c");environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=.8;space.add_child(environment)
		var light := DirectionalLight3D.new();light.rotation_degrees=Vector3(-50,-25,0);light.light_energy=.8;space.add_child(light)
		var cam := Camera3D.new();cam.projection=Camera3D.PROJECTION_ORTHOGONAL;cam.near=.001;cam.far=10.;cam.current=true;space.add_child(cam);live_cameras.append(cam)
		preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
		var builder=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();builder._load_profiles();builder._add_fish(space,SPECIES,.4,builder.profiles[SPECIES]);factories.append(builder)
		var entry: Dictionary=builder.fish[-1];var fin := entry.model.find_child("Dorsal",true,false) as MeshInstance3D
		var frozen := _hash_meshes(entry.model);var receipt := {}
		if index>0:receipt=_bind_round2(entry) if round2 else _bind_candidate(fin,entry.skeleton,output.path_join(modes[index]).path_join("fin.glb"))
		if not round2:assert(frozen==_hash_meshes(entry.model))
		entry["comparison_fin"]=fin;live_entries.append(entry)
		assert(entry.controller.set_action("Swim",true));entry.controller.step(.2)
		var live_receipt := {"mode":modes[index],"receipt":receipt,"non_dorsal_meshes_unchanged":true}
		if round2:
			live_receipt["non_dorsal_meshes_unchanged"]=index==0
			live_receipt["scope"]="Baseline assembly; no candidate applied." if index==0 else "Seven fin mesh/skin replacements and local Closed_body tail-peduncle deformation; experimental preview only."
		receipts.append(live_receipt)
	var hint := Label.new();hint.text="左键拖动旋转 · 滚轮 / 捏合缩放 · 右键 / 中键拖动平移 · 双击复位 · 同步对照";hint.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;panel.add_child(hint)
	FileAccess.open(live_report_dir.path_join("live-preview.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"ok":true,"formal_acceptance":false,"installed_glb_unchanged":FileAccess.get_sha256("res://assets/models/fish/nile_tilapia.glb")==EXPECTED_SHA,"results":receipts},"  ")+"\n")
	print("FIN_LIVE_READY")

func _process(delta: float) -> bool:
	if not live or live_entries.is_empty() or live_closing or live_capture:return false
	live_frames+=1
	live_direction=Vector3(sin(live_yaw)*cos(live_pitch),sin(live_pitch),cos(live_yaw)*cos(live_pitch))
	var baseline: Dictionary=live_entries[0]
	var focus: Vector3=baseline.carrier.global_position
	if live_close:focus=_fin_center(baseline.comparison_fin,baseline.skeleton)
	for index in live_entries.size():
		var entry: Dictionary=live_entries[index]
		if not live_paused:entry.controller.step(minf(delta,.05))
		entry.skeleton.force_update_all_bone_transforms()
		var center := focus+live_pan
		var cam: Camera3D=live_cameras[index];cam.size=live_zoom;cam.position=center+live_direction*2.;cam.look_at(center)
	if smoke and live_frames==5:call_deferred("_live_smoke_inputs")
	return false

func _live_smoke_inputs() -> void:
	live_paused=true
	var surface: Control=live_surfaces[0]
	var point := surface.get_global_rect().get_center()
	var hover := InputEventMouseMotion.new();hover.position=point;hover.global_position=point;root.push_input(hover)
	await process_frame
	var wheel := InputEventMouseButton.new();wheel.position=point;wheel.global_position=point;wheel.button_index=MOUSE_BUTTON_WHEEL_UP;wheel.pressed=true;root.push_input(wheel)
	await process_frame
	assert(live_zoom<.72,"Wheel input did not reach comparison surface")
	var drag := InputEventMouseMotion.new();drag.position=point;drag.global_position=point;drag.relative=Vector2(40,20);drag.button_mask=MOUSE_BUTTON_MASK_LEFT;root.push_input(drag)
	await process_frame
	assert(absf(live_yaw)>.1 and live_pitch>.1,"Orbit input did not reach comparison surface")
	drag=InputEventMouseMotion.new();drag.position=point;drag.global_position=point;drag.relative=Vector2(20,10);drag.button_mask=MOUSE_BUTTON_MASK_RIGHT;root.push_input(drag)
	await process_frame
	assert(live_pan.length()>.001,"Pan input did not reach comparison surface")
	for index in live_cameras.size():assert(is_equal_approx(live_cameras[index].size,live_zoom))
	FileAccess.open(live_report_dir.path_join("interactive-input.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"ok":true,"via_root_viewport_input":true,"wheel_zoom":live_zoom,"orbit_yaw":live_yaw,"orbit_pitch":live_pitch,"pan_distance_m":live_pan.length(),"synchronized_cameras":live_cameras.size(),"formal_acceptance":false},"  ")+"\n")
	print("FIN_INTERACTIVE_INPUT_OK")
	_live_reset();live_paused=false
	await process_frame
	_live_smoke_finish()

func _live_smoke_finish() -> void:
	await RenderingServer.frame_post_draw
	assert(root.get_texture().get_image().save_png(live_report_dir.path_join("live-comparison.png"))==OK)
	if round2:
		live_capture=true
		for entry in live_entries:entry.skeleton.reset_bone_poses();entry.skeleton.force_update_all_bone_transforms()
		var reference := live_entries[0].model.find_child("Caudal",true,false) as MeshInstance3D
		var center := _fin_center(reference,live_entries[0].skeleton)
		var gray := StandardMaterial3D.new();gray.albedo_color=Color(.8,.8,.8);gray.roughness=1.;gray.metallic_specular=0.;gray.cull_mode=BaseMaterial3D.CULL_DISABLED
		for index in live_entries.size():
			var entry: Dictionary=live_entries[index]
			for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
				mesh.visible=mesh.name=="Caudal";mesh.material_override=gray if mesh.name=="Caudal" else null
			var cam: Camera3D=live_cameras[index];cam.size=.18;cam.position=center+Vector3(0,0,2);cam.look_at(center)
		for i in 3:await process_frame
		await RenderingServer.frame_post_draw
		assert(root.get_texture().get_image().save_png(live_report_dir.path_join("tail-independent-gray-compare.png"))==OK)
		for entry in live_entries:
			for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.show();mesh.material_override=null
		for i in 3:await process_frame
		await RenderingServer.frame_post_draw
		assert(root.get_texture().get_image().save_png(live_report_dir.path_join("tail-connection-material-compare.png"))==OK)
	_live_shutdown()

func _bind_round2(entry: Dictionary) -> Dictionary:
	var path := output.path_join("round2/fins.glb")
	var document := GLTFDocument.new();var state := GLTFState.new();assert(document.append_from_file(path,state)==OK)
	var candidate := document.generate_scene(state);root.add_child(candidate);candidate.hide()
	var source_skeleton := candidate.find_children("*","Skeleton3D",true,false)[0] as Skeleton3D
	var receipts := []
	for source in candidate.find_children("*","MeshInstance3D",true,false):
		var target := entry.model.find_child(source.name,true,false) as MeshInstance3D;assert(target!=null)
		var skin := source.skin.duplicate() as Skin
		for i in skin.get_bind_count():
			var name := skin.get_bind_name(i)
			if String(name).is_empty():name=source_skeleton.get_bone_name(skin.get_bind_bone(i))
			var bone: int=entry.skeleton.find_bone(name);assert(bone>=0);skin.set_bind_name(i,name);skin.set_bind_bone(i,bone)
		target.mesh=source.mesh;target.skin=skin
		for si in target.mesh.get_surface_count():
			var material := source.get_active_material(si).duplicate() as StandardMaterial3D;assert(material!=null);material.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST;material.cull_mode=BaseMaterial3D.CULL_DISABLED;target.set_surface_override_material(si,material)
		receipts.append({"name":str(target.name),"surfaces":target.mesh.get_surface_count()})
	assert(receipts.size()==7);candidate.free()
	# Preview-only replay of the exact local deformation saved in the source.
	# Original surface order/UV/weights are kept for the historical material.
	var body := entry.model.find_child("Closed_body",true,false) as MeshInstance3D
	var mesh := ArrayMesh.new();var plan=JSON.parse_string(FileAccess.get_file_as_string(output.path_join("round2/fin-build.plan.json")))
	for si in body.mesh.get_surface_count():
		var arrays := body.mesh.surface_get_arrays(si);var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
		for vi in vertices.size():
			var p := vertices[vi];var t := clampf((p.x+.35100001096725464)/float(plan.tail.blend_native),0.,1.);var amount := 1.-t*t*(3.-2.*t)
			p.z*=1.-amount*(1.-float(plan.tail.end_width_scale));p.y=.002973863855+(p.y-.002973863855)*(1.-amount*(1.-float(plan.tail.end_height_scale)));vertices[vi]=p
		arrays[Mesh.ARRAY_VERTEX]=vertices;mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);mesh.surface_set_material(si,body.get_active_material(si))
	body.mesh=mesh
	return {"fin_glb_sha256":FileAccess.get_sha256(path),"fins":receipts,"material_migration":"pending","tail_local_source_deformation_replayed":true,"formal_acceptance":false}

func _live_shutdown() -> void:
	if live_closing:return
	live_closing=true
	for cam in live_cameras:(cam.get_viewport() as SubViewport).render_target_update_mode=SubViewport.UPDATE_DISABLED
	for i in 3:await process_frame
	live_entries.clear();live_cameras.clear();live_surfaces.clear()
	for item in factories:item.fish.clear();item.free()
	factories.clear();live_panel.queue_free()
	for i in 3:await process_frame
	quit()

func _hash_meshes(model: Node3D) -> Dictionary:
	var rows := {}
	for raw in model.find_children("*","MeshInstance3D",true,false):
		var node := raw as MeshInstance3D
		if node.name=="Dorsal":continue
		var digest := HashingContext.new();digest.start(HashingContext.HASH_SHA256)
		for si in node.mesh.get_surface_count():digest.update(var_to_bytes(node.mesh.surface_get_arrays(si)))
		rows[str(node.name)]=digest.finish().hex_encode()
	return rows

func _fin_center(fin: MeshInstance3D, skeleton: Skeleton3D) -> Vector3:
	var arrays := fin.mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
	var weights: PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS]
	var joints: PackedInt32Array=arrays[Mesh.ARRAY_BONES]
	var stride := weights.size()/vertices.size()
	var palette := []
	for bind in fin.skin.get_bind_count():
		var bone := fin.skin.get_bind_bone(bind)
		if bone<0:bone=skeleton.find_bone(fin.skin.get_bind_name(bind))
		assert(bone>=0)
		palette.append(skeleton.global_transform*skeleton.get_bone_global_pose(bone)*fin.skin.get_bind_pose(bind))
	var bounds := AABB();var first := true
	for vi in vertices.size():
		var point := Vector3.ZERO
		for slot in stride:
			var at := vi*stride+slot
			if weights[at]>0:point+=(palette[joints[at]]*vertices[vi])*weights[at]
		if first:bounds=AABB(point,Vector3.ZERO);first=false
		else:bounds=bounds.expand(point)
	return bounds.get_center()

func _bind_candidate(fin: MeshInstance3D, skeleton: Skeleton3D, path: String) -> Dictionary:
	var document := GLTFDocument.new();var state := GLTFState.new()
	assert(document.append_from_file(path,state)==OK)
	var candidate := document.generate_scene(state);root.add_child(candidate);candidate.hide()
	var nodes := candidate.find_children("*","MeshInstance3D",true,false);assert(nodes.size()==1)
	var source := nodes[0] as MeshInstance3D
	var source_skeleton := candidate.find_children("*","Skeleton3D",true,false)[0] as Skeleton3D
	assert(source.name=="Dorsal" and source.mesh.get_surface_count()==1 and source.skin!=null)
	var skin := source.skin.duplicate() as Skin
	var bindings := []
	for i in skin.get_bind_count():
		var source_bone := skin.get_bind_bone(i)
		var bone_name := skin.get_bind_name(i)
		if String(bone_name).is_empty():bone_name=source_skeleton.get_bone_name(source_bone)
		var target_bone := skeleton.find_bone(bone_name);assert(target_bone>=0)
		skin.set_bind_name(i,bone_name);skin.set_bind_bone(i,target_bone)
		bindings.append(String(bone_name))
	var paint := fin.get_active_material(0)
	assert(paint is ShaderMaterial and "VERTEX_ID" not in paint.shader.code)
	fin.mesh=source.mesh;fin.skin=skin;fin.set_surface_override_material(0,paint)
	var arrays := fin.mesh.surface_get_arrays(0)
	var receipt := {"glb_sha256":FileAccess.get_sha256(path),"triangles":arrays[Mesh.ARRAY_INDEX].size()/3,"vertices":arrays[Mesh.ARRAY_VERTEX].size(),"bone_bindings":bindings,"cold_raw_glb_load":true,"old_fin_material_retained":true}
	candidate.free();return receipt

func _image(directory: String, name: String, direction: Vector3, center: Vector3, size: float) -> Dictionary:
	camera.size=size;camera.position=center+direction.normalized()*2.;camera.look_at(center)
	for i in 3:await process_frame
	await RenderingServer.frame_post_draw
	var path := directory.path_join(name+".png");assert(viewport.get_texture().get_image().save_png(path)==OK)
	return {"name":name,"path":path,"sha256":FileAccess.get_sha256(path)}

func _run() -> void:
	var model_path := "res://assets/models/fish/nile_tilapia.glb";assert(FileAccess.get_sha256(model_path)==EXPECTED_SHA)
	viewport=SubViewport.new();viewport.size=Vector2i(960,640);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(viewport)
	world=Node3D.new();viewport.add_child(world)
	var env := WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("19303c");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.8;world.add_child(env)
	var light := DirectionalLight3D.new();light.rotation_degrees=Vector3(-50,-25,0);light.light_energy=.8;world.add_child(light)
	camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=10.;camera.current=true;world.add_child(camera)
	var modes := ["baseline","route-a-600","route-b-600","route-a-2000","route-b-2000"]
	for mode in modes:
		var path := output.path_join(mode).path_join("fin.glb")
		if mode!="baseline" and not FileAccess.file_exists(path):continue
		preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
		factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
		factory._add_fish(world,SPECIES,.4,factory.profiles[SPECIES])
		var entry: Dictionary=factory.fish[-1];var model: Node3D=entry.model;var controller=entry.controller
		var fin := model.find_child("Dorsal",true,false) as MeshInstance3D
		var frozen := _hash_meshes(model);var receipt := {}
		if mode!="baseline":receipt=_bind_candidate(fin,entry.skeleton,path)
		assert(frozen==_hash_meshes(model))
		var directory := output.path_join("visual").path_join(mode);assert(DirAccess.make_dir_recursive_absolute(directory)==OK)
		var images := []
		var close_center := Vector3.ZERO
		var states := {}
		for action in ["Swim","Turn","Ascend","Dive"]:
			assert(controller.set_action(action,true));controller.step(.2);entry.skeleton.force_update_all_bone_transforms();states[action]=controller.snapshot()
			if mode=="baseline":reference_centers[action]=_fin_center(fin,entry.skeleton)
			close_center=reference_centers[action]
			images.append(await _image(directory,action.to_lower()+"-side",Vector3(0,0,1),entry.carrier.global_position,.55))
			if action in ["Swim","Turn"]:images.append(await _image(directory,action.to_lower()+"-fin-close",Vector3(.15,.15,1),close_center,.24))
		controller.set_action("Turn",true);controller.step(.2);controller.set_action("Swim",false);controller.step(.5);entry.skeleton.force_update_all_bone_transforms();states["transition"]=controller.snapshot()
		if mode=="baseline":reference_centers["transition"]=_fin_center(fin,entry.skeleton)
		close_center=reference_centers["transition"]
		images.append(await _image(directory,"transition-fin-close",Vector3(.15,.15,1),close_center,.24))
		var gray := StandardMaterial3D.new();gray.albedo_color=Color(.8,.8,.8);gray.roughness=1.;gray.metallic_specular=0;gray.cull_mode=BaseMaterial3D.CULL_DISABLED
		fin.material_override=gray
		for raw in model.find_children("*","MeshInstance3D",true,false):
			if raw!=fin:(raw as MeshInstance3D).hide()
		images.append(await _image(directory,"gray-fin-side",Vector3(0,.05,1),close_center,.24))
		images.append(await _image(directory,"gray-fin-edge",entry.model.global_transform.basis.x.normalized()+Vector3(0,0,.02),close_center,.09))
		results.append({"mode":mode,"receipt":receipt,"non_dorsal_meshes_unchanged":true,"images":images,"states":states,"formal_acceptance":false})
		entry.carrier.hide();factories.append(factory)
		print("FIN_PREVIEW "+mode)
	assert(FileAccess.get_sha256(model_path)==EXPECTED_SHA)
	var report := {"ok":true,"fresh_process":true,"formal_acceptance":false,"installed_glb_unchanged":true,"scope":"Only experimental per-instance Dorsal mesh/skin replaced by cold raw GLB; runtime materials, body and normal motion retained. Images are not anatomy/fin-root acceptance.","results":results}
	FileAccess.open(output.path_join("runtime-preview.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED
	for i in 3:await process_frame
	for item in factories:item.fish.clear();item.free()
	quit()
