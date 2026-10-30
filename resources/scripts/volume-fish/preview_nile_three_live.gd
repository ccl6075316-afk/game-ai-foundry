extends "preview_nile_ab_textured.gd"
## Original production material bindings + isolated A/B exports. Review only.
var surfaces_ui: Array[Control]=[]
var pan_offset := Vector3.ZERO
var native_mode := false
var rest_mode := true
var state_label: Label
var pause_button: Button
var closing := false
var smoke := false
var original_receipt: Dictionary={}
var upper_lip_marked := false
var upper_lip_original_texture: Texture2D
const ORIGINAL_SHA := "4ee2c552939b682463120b52e40f2f98e996c2dad8f91f9144ab7d6de51ad25a"

func _live_directory() -> String:
	if "--revision11" in OS.get_cmdline_user_args():return directory.get_base_dir().path_join("round11-single-material-finalization")
	if "--revision10" in OS.get_cmdline_user_args():return directory.get_base_dir().path_join("round10-material-performance")
	if "--revision9" in OS.get_cmdline_user_args():return directory.get_base_dir().path_join("round9-fin-clearance")
	if "--revision8" in OS.get_cmdline_user_args():return directory.get_base_dir().path_join("round8-upper-lip-pixel-clusters")
	if "--revision7" in OS.get_cmdline_user_args():return directory.get_base_dir().path_join("round7-upper-lip-continuity")
	if "--revision6" in OS.get_cmdline_user_args():return directory.get_base_dir().path_join("round6-reference-repair")
	return directory.get_base_dir().path_join("round5-user-review-fixes") if "--revision5" in OS.get_cmdline_user_args() else directory

func _model_path(route: String) -> String:
	if route=="Original":
		var archive := directory.get_base_dir().path_join("round11-production-install/previous-nile-tilapia.glb")
		return archive if FileAccess.file_exists(archive) else "res://assets/models/fish/nile_tilapia.glb"
	if "--revision11" in OS.get_cmdline_user_args() or "--revision10" in OS.get_cmdline_user_args():
		if route=="A":return directory.get_base_dir().path_join("round6-reference-repair/A-artifacts/fish.glb")
		var candidate: String=_live_directory().path_join("final-artifacts/fish.glb" if "--revision11" in OS.get_cmdline_user_args() else "candidates-v2/merged-mask.glb")
		assert(FileAccess.file_exists(candidate));return candidate
	if "--revision9" in OS.get_cmdline_user_args():
		if route=="A":return directory.get_base_dir().path_join("round6-reference-repair/A-artifacts/fish.glb")
		var final_path: String=_live_directory().path_join("final-B-artifacts/fish.glb")
		assert(FileAccess.file_exists(final_path),"Frozen final Nile B R9 model missing: "+final_path)
		return final_path
	if "--revision7" in OS.get_cmdline_user_args() or "--revision8" in OS.get_cmdline_user_args():return _live_directory().path_join("B-artifacts/fish.glb") if route=="B" else directory.get_base_dir().path_join("round6-reference-repair/A-artifacts/fish.glb")
	if "--revision6" in OS.get_cmdline_user_args():return _live_directory().path_join(route+"-artifacts/fish.glb")
	if "--revision5" in OS.get_cmdline_user_args():return _live_directory().path_join(route+"-artifacts/fish.glb")
	return super._model_path(route)

func _load(route: String, container: SubViewportContainer) -> Dictionary:
	if route!="Original":
		var entry: Dictionary=super._load(route,container)
		entry.view.mesh_lod_threshold=0.
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
			for si in mesh.mesh.get_surface_count():
				var mat: StandardMaterial3D=mesh.mesh.surface_get_material(si)
				mat.shading_mode=BaseMaterial3D.SHADING_MODE_PER_PIXEL
				mat.roughness=1.;mat.metallic=0.;mat.metallic_specular=0.
				if not (route=="B" and ("--revision11" in OS.get_cmdline_user_args() or "--revision10" in OS.get_cmdline_user_args())) and str(mesh.name)!="Closed_body" and str(mesh.name)!="Closed_body_B":mat.diffuse_mode=BaseMaterial3D.DIFFUSE_LAMBERT
		return entry
	assert(FileAccess.get_sha256(_model_path(route))==ORIGINAL_SHA)
	var view := SubViewport.new();view.size=Vector2i(640,700);view.own_world_3d=true;view.mesh_lod_threshold=0.;view.render_target_update_mode=SubViewport.UPDATE_ALWAYS;container.add_child(view)
	var world := Node3D.new();view.add_child(world)
	var environment := WorldEnvironment.new();environment.environment=Environment.new()
	environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color("25343c")
	environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=.65;world.add_child(environment)
	var light := DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.65;world.add_child(light)
	var camera := Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=10;camera.current=true;world.add_child(camera)
	# Bypass this host's stale PackedScene import cache. The hash-gated actual
	# source GLB is imported by GLTFDocument; scene_file_path records that source.
	var document := GLTFDocument.new();var gltf_state := GLTFState.new()
	assert(document.append_from_file(ProjectSettings.globalize_path(_model_path(route)),gltf_state)==OK)
	var model := document.generate_scene(gltf_state) as Node3D;assert(model!=null)
	model.scene_file_path=_model_path(route)
	var carrier := Node3D.new();world.add_child(carrier);carrier.add_child(model);model.scale=Vector3.ONE*.402819722890854
	# This host's cached scene may predate the saved post-import hook. Restore
	# the frozen LOD-free metadata in memory; prove full-detail arrays unchanged.
	var frozen_file := FileAccess.open("res://assets/models/fish/motion/final178/nile_tilapia/old-lod-data.bin",FileAccess.READ)
	var frozen: Dictionary=frozen_file.get_var(true);frozen_file.close()
	for mesh in model.find_children("*","MeshInstance3D",true,false):
		var original: ArrayMesh=mesh.mesh;var stored: Array=original.get("_surfaces").duplicate(true);var digests := []
		for si in original.get_surface_count():
			digests.append(var_to_bytes(original.surface_get_arrays(si)).hex_encode().sha256_text())
			assert(frozen[str(mesh.name)][si].lods.is_empty(),"This viewer only restores this fish's frozen zero-LOD metadata")
			stored[si]["lods"]=[]
		var copy: ArrayMesh=original.duplicate(false);copy.clear_surfaces();copy.set("_surfaces",stored)
		for si in copy.get_surface_count():assert(var_to_bytes(copy.surface_get_arrays(si)).hex_encode().sha256_text()==digests[si],"Original full-detail arrays changed")
		mesh.mesh=copy
	var original_player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
	var library: AnimationLibrary=original_player.get_animation_library("")
	var original_clip := load("res://assets/models/fish/motion/final178/nile_tilapia/old-native-animation.res") as Animation
	library.remove_animation("Animation");library.add_animation("Animation",original_clip)
	if model.has_node("nile_tilapia"):original_player.root_node=NodePath("../nile_tilapia")
	var binding=load("res://scripts/aquarium/FinalizedNileTilapia178.gd").new()
	var bound: Dictionary=binding.apply(model,"nile_tilapia");assert(bound.static_build_calls==0)
	original_receipt=bound.final_asset178
	var original_body := model.find_child("Closed_body",true,false) as MeshInstance3D
	# The saved vertex-index tables target the old editor import order, while
	# GLTFDocument preserves source order. Use the already frozen old arrays and
	# existing exact attribute mapper; copy each lookup texel, no color redesign.
	var mapper=load(ProjectSettings.globalize_path("res://../experiments/grass-carp-static-merge/repro/vertex_map.gd")).new()
	var transport=load(ProjectSettings.globalize_path("res://../../../resources/scripts/volume-fish/LowPolyFishTransport.gd")).new()
	var material_mappings := {}
	for si in original_body.mesh.get_surface_count():
		var mapping: Dictionary=mapper._build_mapping(frozen.Closed_body[si].arrays,original_body,si)
		if mapping.is_empty():return {}
		var old_material := load("res://assets/models/fish/motion/final178/nile_tilapia/Closed_body-"+str(si)+".tres") as ShaderMaterial
		var current: Array=original_body.mesh.surface_get_arrays(si)
		var uv: PackedVector2Array=current[Mesh.ARRAY_TEX_UV]
		var part := {"positions":current[Mesh.ARRAY_VERTEX],"references":[],"uv":[]}
		for oi in mapping.new_to_old:part.references.append([[oi,oi,oi],[1.,0.,0.]])
		for value in uv:part.uv.append([value.x,value.y])
		var rebound: ShaderMaterial=transport.material(old_material,part)
		original_body.set_surface_override_material(si,rebound)
		var max_error := 0.
		if si==0:
			var image: Image=(rebound.get_shader_parameter("rest114_uvs") as Texture2D).get_image()
			for i in uv.size():
				var pixel := image.get_pixel(i%256,i/256);max_error=maxf(max_error,maxf(absf(pixel.r-uv[i].x),absf(pixel.g-uv[i].y)))
			assert(max_error<=.000001)
		material_mappings[str(si)]={"old_count":mapping.old_count,"current_count":mapping.new_count,"all_old_represented":mapping.old_represented==mapping.old_count,"max_position":mapping.max_position,"max_uv":mapping.max_uv,"max_weight":mapping.max_weight,"final_uv_lookup_error":max_error,"source_material":old_material.resource_path,"source_sha256":FileAccess.get_sha256(old_material.resource_path)}
	original_receipt["current_import_lookup_rebind"]=material_mappings
	var skeleton: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]
	var player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
	var count := 0;var materials := []
	for mesh in model.find_children("*","MeshInstance3D",true,false):
		for si in mesh.mesh.get_surface_count():
			count+=(mesh.mesh.surface_get_arrays(si)[Mesh.ARRAY_INDEX] as PackedInt32Array).size()/3
			var mat: Material=mesh.get_active_material(si);assert(mat!=null)
			materials.append({"mesh":str(mesh.name),"surface":si,"class":mat.get_class(),"path":mat.resource_path})
	assert(count==116994)
	var controller=MOTION.new()
	var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(ProjectSettings.globalize_path("res://../../../resources/volume-fish/motion/nile_tilapia-082.json")))
	var configured: Dictionary=controller.configure(carrier,model,player,skeleton,profile);assert(configured.ok)
	report.models.append({"route":route,"model_sha256":ORIGINAL_SHA,"triangles":count,"materials":materials,"original_material_receipt":original_receipt})
	return {"route":route,"model":model,"carrier":carrier,"view":view,"camera":camera,"controller":controller,"skeleton":skeleton,"player":player}

func _set_direction(value: Vector3) -> void:
	direction=value.normalized();yaw=atan2(direction.x,direction.z);pitch=asin(direction.y)

func _reset_view() -> void:
	_set_direction(Vector3(0,0,1));zoom=.52;pan_offset=Vector3.ZERO

func _whole_fish() -> void:
	for entry in entries:
		entry.erase("fin_focus")
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.show()
	_set_gray(false);_reset_view()

func _fin_thickness_view() -> void:
	if "--revision11" in OS.get_cmdline_user_args() or "--revision10" in OS.get_cmdline_user_args():return
	_rest();_set_gray(true)
	for entry in entries:
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
			mesh.visible=str(mesh.name)=="Pectoral_left"
			if mesh.visible:entry["fin_focus"]=entry.carrier.global_transform.affine_inverse()*(mesh.global_transform*mesh.get_aabb().get_center())
	_set_direction(Vector3(-.9,.22,.07));zoom=.075;pan_offset=Vector3.ZERO;state_label.text="胸鳍端面 · 真实比例"

func _detail_view(part: String) -> void:
	_whole_fish();_rest()
	if part=="belly":zoom=.14;pan_offset=Vector3(.081,-.04,0);_set_direction(Vector3(0,0,1));state_label.text="腹颈纹理对照"
	elif part=="mouth":zoom=.085;pan_offset=Vector3(.185,-.006,0);_set_direction(Vector3(.8,.1,1));state_label.text="嘴形与颜色对照"
	elif part=="upper-lip":zoom=.065;pan_offset=Vector3(.191,-.006,0);_set_direction(Vector3(1,.02,0));state_label.text="上唇正面 · 左右连续纹理"
	else:zoom=.14;pan_offset=Vector3(.161,.017,0);_set_direction(Vector3(0,1,.001));state_label.text="两眼之间额头对照"

func _toggle_upper_lip_marking() -> void:
	if not ("--revision7" in OS.get_cmdline_user_args() or "--revision8" in OS.get_cmdline_user_args() or "--revision9" in OS.get_cmdline_user_args()):return
	var body: MeshInstance3D=entries[2].model.find_child("Closed_body_B",true,false)
	var mat: StandardMaterial3D=body.mesh.surface_get_material(0)
	if upper_lip_original_texture==null:upper_lip_original_texture=mat.albedo_texture
	upper_lip_marked=not upper_lip_marked
	var marking_dir: String=directory.get_base_dir().path_join("round8-upper-lip-pixel-clusters") if "--revision9" in OS.get_cmdline_user_args() else _live_directory()
	mat.albedo_texture=ImageTexture.create_from_image(Image.load_from_file(marking_dir.path_join("upper-lip-marked-atlas.png"))) if upper_lip_marked else upper_lip_original_texture
	_detail_view("upper-lip")
	state_label.text="B 青线：实际上唇边界（仅标定）" if upper_lip_marked else "上唇正面 · 实际材质"

func _rest() -> void:
	native_mode=false;rest_mode=true;motion_paused=true;state_label.text="静止对照";pause_button.text="播放游动"
	for entry in entries:
		entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY;entry.skeleton.force_update_all_bone_transforms()

func _action(value: String) -> void:
	if not entries.is_empty() and entries[0].has("fin_focus"):_whole_fish()
	native_mode=false;rest_mode=false;motion_paused=false;pause_button.text="暂停"
	state_label.text={"Swim":"游动","Turn":"转身","Ascend":"上浮","Dive":"下潜"}[value]
	for entry in entries:assert(entry.controller.set_action(value,true));entry.controller.step(0.)

func _native() -> void:
	_rest();native_mode=true;rest_mode=false;motion_paused=false;state_label.text="原生循环";pause_button.text="暂停"
	for entry in entries:entry.player.play("Animation");entry.player.seek(0.,true);entry.player.advance(0.)

func _pause() -> void:
	if rest_mode:_action("Swim");return
	motion_paused=not motion_paused;pause_button.text="继续" if motion_paused else "暂停"

func _input_surface(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if event.button_index==MOUSE_BUTTON_WHEEL_UP:zoom=clampf(zoom/1.12,.025,2.)
		elif event.button_index==MOUSE_BUTTON_WHEEL_DOWN:zoom=clampf(zoom*1.12,.025,2.)
		elif event.button_index==MOUSE_BUTTON_LEFT and event.double_click:_reset_view()
	elif event is InputEventMouseMotion:
		if event.button_mask&MOUSE_BUTTON_MASK_LEFT:
			yaw-=event.relative.x*.008;pitch=clampf(pitch+event.relative.y*.008,-1.55,1.55)
			direction=Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))
		elif event.button_mask&(MOUSE_BUTTON_MASK_RIGHT|MOUSE_BUTTON_MASK_MIDDLE):_pan(event.relative)
	elif event is InputEventMagnifyGesture:zoom=clampf(zoom/maxf(event.factor,.01),.025,2.)
	elif event is InputEventPanGesture:_pan(event.delta*8.)
	if entries.size()==3:
		_cameras()
		var sizes := [];var directions := []
		for entry in entries:sizes.append(entry.camera.size);directions.append([direction.x,direction.y,direction.z])
		FileAccess.open(_live_directory().path_join("three-navigation.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"ok":true,"last_input_class":event.get_class(),"zoom":zoom,"yaw":yaw,"pitch":pitch,"pan":[pan_offset.x,pan_offset.y,pan_offset.z],"camera_sizes":sizes,"directions":directions},"  ")+"\n")

func _pan(relative: Vector2) -> void:
	var camera: Camera3D=entries[0].camera
	var local_basis: Basis=entries[0].carrier.global_basis.inverse()*camera.global_basis
	pan_offset+=(-local_basis.x*relative.x+local_basis.y*relative.y)*zoom/maxf(1.,float(camera.get_viewport().size.x))

func _cameras() -> void:
	for entry in entries:
		var basis: Basis=entry.carrier.global_basis
		var focus: Vector3=entry.carrier.global_position+basis*(pan_offset+entry.get("fin_focus",Vector3.ZERO))
		var dir: Vector3=basis*direction
		entry.camera.keep_aspect=Camera3D.KEEP_WIDTH
		entry.camera.size=zoom;entry.camera.position=focus+dir*2.
		entry.camera.look_at(focus,basis*Vector3.UP if absf(direction.y)<.99 else basis*Vector3(0,0,-1))

func _run() -> void:
	live=true;smoke="--smoke" in OS.get_cmdline_user_args();motion_paused=true
	root.title="罗非鱼 · 原版 / A / B · 材质交互对照"
	root.content_scale_size=Vector2i.ZERO;root.content_scale_mode=Window.CONTENT_SCALE_MODE_DISABLED;root.content_scale_factor=1.
	root.size=Vector2i(1600,900);root.min_size=Vector2i(1100,650);root.mode=Window.MODE_MAXIMIZED
	auto_accept_quit=false;root.close_requested.connect(_shutdown)
	var panel := VBoxContainer.new();panel.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.add_child(panel)
	var theme := Theme.new();var font := SystemFont.new();font.font_names=PackedStringArray(["Microsoft YaHei UI","Microsoft YaHei"]);theme.default_font=font;theme.default_font_size=19;panel.theme=theme
	var title := Label.new();title.text="原版 / A / B　同尺度 · 同机位 · 同步操作";title.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;panel.add_child(title)
	var bar := HBoxContainer.new();bar.alignment=BoxContainer.ALIGNMENT_CENTER;panel.add_child(bar)
	_button(bar,"静止",_rest)
	for action in ["Swim","Turn","Ascend","Dive"]:
		_button(bar,{"Swim":"游动","Turn":"转身","Ascend":"上浮","Dive":"下潜"}[action],_action.bind(action))
	_button(bar,"原生循环",_native)
	pause_button=Button.new();pause_button.text="播放游动";pause_button.pressed.connect(_pause);bar.add_child(pause_button)
	_button(bar,"灰模 / 材质",func():_set_gray(not gray))
	var views := HBoxContainer.new();views.alignment=BoxContainer.ALIGNMENT_CENTER;panel.add_child(views)
	_button(views,"侧面",_set_direction.bind(Vector3(0,0,1)))
	_button(views,"另一侧",_set_direction.bind(Vector3(0,0,-1)))
	_button(views,"斜视",_set_direction.bind(Vector3(.65,.25,1)))
	_button(views,"正面",_set_direction.bind(Vector3(1,0,0)))
	_button(views,"俯视",_set_direction.bind(Vector3(0,1,.001)))
	_button(views,"放大",func():zoom=clampf(zoom/1.25,.025,2.))
	_button(views,"缩小",func():zoom=clampf(zoom*1.25,.025,2.))
	_button(views,"复位",_reset_view)
	# Old isolated-fin and marked-R8-atlas diagnostics do not apply to the packed atlas.
	if not ("--revision11" in OS.get_cmdline_user_args() or "--revision10" in OS.get_cmdline_user_args()):_button(views,"鳍厚度（放大）",_fin_thickness_view)
	_button(views,"完整鱼",_whole_fish)
	state_label=Label.new();state_label.text="静止对照";views.add_child(state_label)
	var details := HBoxContainer.new();details.alignment=BoxContainer.ALIGNMENT_CENTER;panel.add_child(details)
	_button(details,"腹颈近看",_detail_view.bind("belly"))
	_button(details,"嘴部近看",_detail_view.bind("mouth"))
	_button(details,"额头近看",_detail_view.bind("forehead"))
	if "--revision7" in OS.get_cmdline_user_args() or "--revision8" in OS.get_cmdline_user_args() or "--revision9" in OS.get_cmdline_user_args():
		_button(details,"上唇正面",_detail_view.bind("upper-lip"))
		_button(details,"上唇标定线 开/关",_toggle_upper_lip_marking)
	elif "--revision11" in OS.get_cmdline_user_args() or "--revision10" in OS.get_cmdline_user_args():_button(details,"上唇正面",_detail_view.bind("upper-lip"))
	var row := HBoxContainer.new();row.size_flags_vertical=Control.SIZE_EXPAND_FILL;panel.add_child(row)
	for route in ["Original","A","B"]:
		var col := VBoxContainer.new();col.size_flags_horizontal=Control.SIZE_EXPAND_FILL;col.size_flags_stretch_ratio=1.;row.add_child(col)
		var label := Label.new();label.text=route;label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;col.add_child(label)
		var note := Label.new();note.text="原游戏材质 · 凸眼" if route=="Original" else "新材质 · 平面眼";note.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;col.add_child(note)
		var frame := Control.new();frame.size_flags_vertical=Control.SIZE_EXPAND_FILL;frame.size_flags_horizontal=Control.SIZE_EXPAND_FILL;col.add_child(frame)
		var box := SubViewportContainer.new();box.stretch=true;box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);box.mouse_filter=Control.MOUSE_FILTER_IGNORE;frame.add_child(box)
		var loaded: Dictionary=_load(route,box)
		if loaded.is_empty():push_error("Unable to load "+route);quit(2);return
		entries.append(loaded)
		var actual_inventory: Dictionary=report.models[-1]
		label.text=("原版" if route=="Original" else route)+" · "+str(actual_inventory.triangles)+" 面"+(" · 单材质" if route=="B" and ("--revision11" in OS.get_cmdline_user_args() or "--revision10" in OS.get_cmdline_user_args()) else "")
		var surface := Control.new();surface.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);surface.mouse_filter=Control.MOUSE_FILTER_STOP;frame.add_child(surface);surface.gui_input.connect(_input_surface);surfaces_ui.append(surface)
	var help := Label.new();help.text="任一鱼画面：左键拖动旋转 · 滚轮缩放 · 右键 / 中键拖动平移 · 双击复位（三个视图同步）";help.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;panel.add_child(help)
	await process_frame;_rest();_reset_view();_cameras()
	for i in 3:await process_frame
	if smoke:RenderingServer.force_draw(false)
	else:await RenderingServer.frame_post_draw
	var path := _live_directory().path_join("three-live-preview.png");assert(root.get_texture().get_image().save_png(path)==OK)
	report["kind"]="nile_three_textured_live_review";report["ok"]=true;report["scope"]="Original exact game materials via178 saved binding; A/B own embedded new materials. Same lights/cameras, all static geometry read unchanged."
	report["original_binding"]=original_receipt;report["screenshot_sha256"]=FileAccess.get_sha256(path);report["entry_script_sha256"]=FileAccess.get_sha256(get_script().resource_path)
	FileAccess.open(_live_directory().path_join("three-live.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("NILE_THREE_LIVE_READY")
	if smoke:
		await _smoke_inputs()
		await _shutdown()

func _smoke_inputs() -> void:
	var center := surfaces_ui[1].get_global_rect().get_center()
	var hover := InputEventMouseMotion.new();hover.position=center;hover.global_position=center;root.push_input(hover)
	await process_frame
	var wheel := InputEventMouseButton.new();wheel.position=center;wheel.global_position=center;wheel.button_index=MOUSE_BUTTON_WHEEL_UP;wheel.pressed=true;root.push_input(wheel)
	await process_frame;assert(zoom<.52,"Wheel not received")
	var down := InputEventMouseButton.new();down.position=center;down.global_position=center;down.button_index=MOUSE_BUTTON_LEFT;down.pressed=true;root.push_input(down)
	await process_frame
	var drag := InputEventMouseMotion.new();drag.position=center;drag.global_position=center;drag.relative=Vector2(40,20);drag.button_mask=MOUSE_BUTTON_MASK_LEFT;root.push_input(drag)
	await process_frame;assert(absf(yaw)>.1 and pitch>.1,"Orbit not received")
	down.pressed=false;root.push_input(down);await process_frame
	down=InputEventMouseButton.new();down.position=center;down.global_position=center;down.button_index=MOUSE_BUTTON_RIGHT;down.pressed=true;root.push_input(down);await process_frame
	drag=InputEventMouseMotion.new();drag.position=center;drag.global_position=center;drag.relative=Vector2(20,10);drag.button_mask=MOUSE_BUTTON_MASK_RIGHT;root.push_input(drag)
	await process_frame;assert(pan_offset.length()>.001,"Pan not received")
	down.pressed=false;root.push_input(down);await process_frame
	for entry in entries:assert(is_equal_approx(entry.camera.size,zoom))
	var result := {"ok":true,"via_root_input":true,"zoom":zoom,"yaw":yaw,"pitch":pitch,"pan_distance":pan_offset.length(),"synchronized_views":3}
	for action in ["Swim","Turn","Ascend","Dive"]:
		_action(action)
		for entry in entries:
			entry.controller.step(.2)
			assert(entry.controller.snapshot().action==action and entry.controller.snapshot().pending_action=="")
		await process_frame
	_native();_set_gray(true);_set_gray(false);_rest();_reset_view();_cameras()
	if "--revision11" in OS.get_cmdline_user_args() or "--revision10" in OS.get_cmdline_user_args():
		var packed_meshes: Array=entries[2].model.find_children("*","MeshInstance3D",true,false)
		assert(packed_meshes.size()==1 and packed_meshes[0].mesh.get_surface_count()==1 and packed_meshes[0].visible)
		result["packed_full_entry_meshes"]=1;result["packed_full_entry_surfaces"]=1
		result["incompatible_fin_isolation_and_R8_marked_atlas_disabled"]=true
	else:_fin_thickness_view();await process_frame;_whole_fish();_rest()
	if "--revision7" in OS.get_cmdline_user_args() or "--revision8" in OS.get_cmdline_user_args() or "--revision9" in OS.get_cmdline_user_args():
		_toggle_upper_lip_marking();await process_frame;assert(upper_lip_marked)
		_toggle_upper_lip_marking();await process_frame;assert(not upper_lip_marked)
		result["upper_lip_marking_toggle"]=true
	FileAccess.open(_live_directory().path_join("three-interactive-input.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(result,"  ")+"\n")
	print("NILE_THREE_INTERACTION_OK")

func _process(delta: float) -> bool:
	if closing:return false
	if not motion_paused:
		for entry in entries:
			if native_mode:entry.player.advance(minf(delta,.05))
			else:entry.controller.step(minf(delta,.05))
	if not entries.is_empty():_cameras()
	return false

func _shutdown() -> void:
	if closing:return
	closing=true
	for entry in entries:entry.view.render_target_update_mode=SubViewport.UPDATE_DISABLED
	for i in 3:await process_frame
	quit()
