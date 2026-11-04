extends "capture_fish_review.gd"
## Short GPU-only shape checkpoint; no movie or full acceptance claim.
func _run() -> void:
	load_plan=plan
	var box:=SubViewportContainer.new();root.add_child(box)
	var entry: Dictionary=_load("B",box);entries.append(entry)
	entry.view.mesh_lod_threshold=0.;entry.model.scale=Vector3.ONE*float(plan.model_scale)
	var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(plan.motion_profile))
	entry.controller=load(plan.motion_runtime).new()
	assert(entry.controller.configure(entry.carrier,entry.model,entry.player,entry.skeleton,profile).ok)
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	zoom=float(plan.whole_camera_size);focus=Vector3.ZERO;await photo_views("whole")
	for detail in plan.details:
		if detail.name not in ["head","mouth"] and not plan.get("capture_all_details",false):continue
		zoom=float(detail.size);focus=Vector3(float(detail.at[0]),float(detail.at[1]),float(detail.at[2]));await photo_views(detail.name)
	for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.visible=str(mesh.name)==str(plan.body)
	zoom=float(plan.whole_camera_size);focus=Vector3.ZERO;await photo_views("body-without-fins")
	report.merge({"ok":true,"kind":"local_fish_shape_GPU_checkpoint","model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"full_acceptance":false,"frozen_inputs":bindings,"scope":"Rest multi-view body/head/mouth only; not complete fin, motion, integrity or production acceptance."})
	FileAccess.open(review_out.path_join("local-review.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("LOCAL_FORM_REVIEW_OK");quit()
