extends "capture_fish_review.gd"
## Compact local checkpoint and paint-template capture; no acceptance claims.
func _run() -> void:
	load_plan=plan
	var box:=SubViewportContainer.new();root.add_child(box)
	var entry: Dictionary=_load("B",box);entries.append(entry)
	entry.view.mesh_lod_threshold=0.;entry.model.scale=Vector3.ONE*float(plan.model_scale)
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	for detail in plan.details:
		if detail.name!="tail":continue
		zoom=float(detail.size);focus=Vector3(float(detail.at[0]),float(detail.at[1]),float(detail.at[2]))
		for view in views():
			if view.name not in ["left","oblique","top"]:continue
			direction=view.dir;_set_gray(true);await photo("tail-"+view.name+"-clay")
	zoom=float(plan.whole_camera_size);focus=whole_focus()
	for view in views():
		if view.name not in ["left","top","bottom","oblique","right"]:continue
		direction=view.dir
		_set_gray(true);await photo("whole-"+view.name+"-clay")
		_set_gray(false);await photo("whole-"+view.name+"-texture")
	if plan.get("trial_details",false):
		for detail in plan.details:
			if detail.name not in ["mouth","chest","tail","ventral_fins"]:continue
			zoom=float(detail.size);focus=Vector3(float(detail.at[0]),float(detail.at[1]),float(detail.at[2]))
			direction=Vector3(0,-1,0) if detail.name in ["mouth","ventral_fins"] else Vector3(.3,.25,1).normalized()
			_set_gray(false);await photo(detail.name+"-detail-texture")
			if detail.name=="mouth":_set_gray(true);await photo("mouth-detail-clay")
	for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.visible=str(mesh.name)==str(plan.body)
	zoom=float(plan.whole_camera_size);focus=whole_focus()
	direction=Vector3(0,0,1);_set_gray(true);await photo("body-left-clay")
	_set_gray(false);await photo("body-left-texture")
	if plan.get("trial_details",false):
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.visible=true
		direction=Vector3(.45,.25,1).normalized()
		var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(plan.motion_profile))
		entry.player.play(profile.base_clip);entry.player.seek(1.1,true);entry.player.advance(0.);await photo("motion-native")
		for action in ["Swim","Turn","Ascend","Dive"]:
			assert(entry.controller.set_action(action,true));entry.controller.step(0.)
			for i in 90:entry.controller.step(1./60.)
			entry.carrier.transform=Transform3D.IDENTITY;await photo("motion-"+action)
		for action in ["Swim","Turn","Ascend","Dive"]:
			assert(entry.controller.set_action(action,false))
			for i in 20:entry.controller.step(1./60.)
			entry.carrier.transform=Transform3D.IDENTITY;await photo("transition-"+action)
	report.merge({"ok":true,"model_sha256":plan.model_sha256,"full_acceptance":false})
	FileAccess.open(review_out.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	quit()
