extends "portable/FishAssetViewer.gd"
var saved_controller
var playback := "Swim"
var status_label: Label

func run() -> void:
	await super.run()
	if not ready_for_input:return
	root.title="路氏双髻鲨成品 · 3994面"
	saved_controller=controller
	for child in root.get_children():
		if child is Label:child.text="左键拖动旋转 · 右键拖动平移 · 滚轮缩放 · 空格暂停 · G灰模 · 0复位 · H头部 · M嘴部"
	var bar:=HBoxContainer.new();bar.position=Vector2(12,52);root.add_child(bar)
	for action in ["静止","原生","Swim","Turn","Ascend","Dive"]:
		var button:=Button.new();button.text=action;button.pressed.connect(func():_choose(action));bar.add_child(button)
	status_label=Label.new();status_label.position=Vector2(12,96);root.add_child(status_label)
	_choose("静止")
	print("SCALLOPED_FINAL_INTERACTIVE_READY model_sha256="+FileAccess.get_sha256(config.model))

func _choose(action: String) -> void:
	playback=action
	if action=="静止":
		motion_paused=true;controller=null;player.stop();skeleton.reset_bone_poses();carrier.transform=Transform3D.IDENTITY
	elif action=="原生":
		controller=null;motion_paused=false;carrier.transform=Transform3D.IDENTITY
		player.stop();skeleton.reset_bone_poses();player.play(native_clip);player.advance(0.);player.pause()
	else:
		controller=saved_controller;motion_paused=false
		assert(controller!=null and controller.set_action(action))
	if status_label!=null:status_label.text="当前："+action+"  |  已验收成品；后续默认只改动作"
