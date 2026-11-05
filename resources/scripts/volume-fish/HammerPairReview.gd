extends "portable/FishAssetViewer.gd"
## Native candidate-only review. No static model authoring or installed factory.
var saved_controller
var status_label: Label
var in_place := true

func run() -> void:
	await super.run()
	if not ready_for_input:return
	var label: String="大双髻鲨" if config.species=="great_hammerhead" else "无沟双髻鲨"
	root.title=label+" · 新版预览"
	saved_controller=controller
	for child in root.get_children():
		if child is Label:child.text="左键旋转 · 右键平移 · 滚轮缩放 · 空格暂停 · G灰模 · H头部 · M嘴部"
	var species_bar:=HBoxContainer.new();species_bar.position=Vector2(12,42);root.add_child(species_bar)
	for species in ["great_hammerhead","smooth_hammerhead"]:
		var button:=Button.new();button.text="大双髻鲨" if species=="great_hammerhead" else "无沟双髻鲨"
		button.disabled=species==config.species;button.pressed.connect(_switch_species.bind(species));species_bar.add_child(button)
	var action_bar:=HBoxContainer.new();action_bar.position=Vector2(12,82);root.add_child(action_bar)
	for row in [["静止","Static"],["原生","Native"],["游动","Swim"],["转向","Turn"],["上浮","Ascend"],["下潜","Dive"]]:
		var button:=Button.new();button.text=row[0];button.pressed.connect(_choose.bind(row[1]));action_bar.add_child(button)
	var views_bar:=HBoxContainer.new();views_bar.position=Vector2(12,122);root.add_child(views_bar)
	for row in [["侧面",0.,0.],["俯视",0.,1.48],["腹面",0.,-1.48],["斜视",.5,.25]]:
		var button:=Button.new();button.text=row[0];button.pressed.connect(_view_angle.bind(row[1],row[2]));views_bar.add_child(button)
	status_label=Label.new();status_label.position=Vector2(390,50);root.add_child(status_label)
	_choose("Static")
	DisplayServer.window_move_to_foreground()
	print("HAMMER_PAIR_NATIVE_REVIEW_READY "+config.species+" "+FileAccess.get_sha256(config.model))

func _choose(action: String) -> void:
	if action=="Static":
		motion_paused=true;controller=null;player.stop();skeleton.reset_bone_poses();carrier.transform=Transform3D.IDENTITY
	elif action=="Native":
		controller=null;motion_paused=false;carrier.transform=Transform3D.IDENTITY;player.stop();skeleton.reset_bone_poses();player.play(native_clip);player.advance(0.);player.pause()
	else:
		controller=saved_controller;motion_paused=false;assert(controller.set_action(action,true))
	if status_label!=null:status_label.text="新版候选 · 原地观察动作与连接"

func _view_angle(at_yaw: float,at_pitch: float) -> void:
	yaw=at_yaw;pitch=at_pitch;target=bounds.get_center();distance=base_distance;_update_camera()

func _process(delta: float) -> bool:
	var result: bool=super._process(delta)
	if ready_for_input and in_place and controller!=null:carrier.transform=Transform3D.IDENTITY
	return result

func _switch_species(species: String) -> void:
	var path: String=config.pair_configs[species]
	var args: PackedStringArray=["--path",config.game,"--rendering-method","gl_compatibility","--script",get_script().resource_path,"--","--config="+path]
	assert(OS.create_process(OS.get_executable_path(),args)>0)
	_finish()
