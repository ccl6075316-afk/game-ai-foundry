extends "portable/ReviewCaptureBase.gd"
var plan: Dictionary
var out: String
func _initialize() -> void:
	var args:=OS.get_cmdline_user_args()
	assert(args.size()==2)
	plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]));out=args[1]
	for path in plan.bindings:assert(FileAccess.get_sha256(path)==plan.bindings[path])
	assert(DisplayServer.get_name()!="headless")
	DirAccess.make_dir_recursive_absolute(out);root.hide();call_deferred("run")

func photo(entry: Dictionary, label: String, direction: Vector3, focus: Vector3, width: float) -> void:
	var camera: Camera3D=entry.camera
	if label.begins_with("head-front"):width=float(plan.front_width)
	camera.keep_aspect=Camera3D.KEEP_WIDTH;camera.size=width;camera.position=focus+direction*2.0
	camera.look_at(focus,Vector3(0,0,-1)if absf(direction.y)>.99 else Vector3.UP)
	for i in 3:await process_frame;RenderingServer.force_draw(false)
	var path:=out.path_join(entry.route+"-"+label+".png")
	assert(_view_image(entry).save_png(path)==OK)
	report.captures.append({"label":entry.route+"-"+label,"path":path,"direction":[direction.x,direction.y,direction.z],"focus":[focus.x,focus.y,focus.z],"ortho_width":width,"sha256":FileAccess.get_sha256(path)})

func run() -> void:
	for route in ["before","after"]:
		load_plan=plan.duplicate(true);load_plan.model=plan.models[route]
		var box:=SubViewportContainer.new();root.add_child(box)
		var entry:=super._load(route,box);entries.append(entry)
		entry.view.mesh_lod_threshold=0.0;entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	var views: Array=[{"name":"top","d":Vector3.UP},{"name":"left","d":Vector3(0,0,1)},{"name":"right","d":Vector3(0,0,-1)},{"name":"front","d":Vector3(1,0,0)},{"name":"bottom","d":Vector3.DOWN},{"name":"oblique","d":Vector3(.8,.4,1).normalized()}]
	for gray_mode in [false,true]:
		_set_gray(gray_mode)
		for detail in [false,true]:
			for v in views:
				var label: String=("head-"if detail else "whole-")+v.name+("-clay"if gray_mode else "-texture")
				for entry in entries:await photo(entry,label,v.d,Vector3(float(plan.head_focus[0]),float(plan.head_focus[1]),float(plan.head_focus[2]))if detail else Vector3.ZERO,float(plan.head_width)if detail else float(plan.whole_width))
	_set_gray(false)
	var motion_rows: Array=[]
	for action in ["Swim","Turn","Ascend","Dive"]:
		for entry in entries:
			entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
			var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(plan.motion_profile))
			assert(entry.controller.configure(entry.carrier,entry.model,entry.player,entry.skeleton,profile).ok)
			assert(entry.controller.set_action(action))
			for i in 90:entry.controller.step(1.0/60.0)
			assert(entry.controller.snapshot().action==action and entry.controller.snapshot().pending_action=="")
			motion_rows.append({"route":entry.route,"action_requested":action,"snapshot":entry.controller.snapshot()})
			await photo(entry,"motion-"+action,Vector3(.6,.5,1).normalized(),entry.carrier.global_position,float(plan.motion_width))
	for path in plan.bindings:assert(FileAccess.get_sha256(path)==plan.bindings[path])
	report.merge({"ok":true,"kind":"species_width_local_comparison","formal_acceptance":false,"fresh_process":true,"static_builders_disabled":true,"runtime_static_build_calls":0,"motion":motion_rows,"limits":"Actual local visual/motion sample only, not full fin177/490 or077/SOP acceptance."})
	FileAccess.open(out.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("WIDTH_TRIAL_CAPTURE_OK");quit()
