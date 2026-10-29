extends "preview_nile_three_live.gd"
var audit_dir: String
func _model_path(route: String) -> String:
	if "--revision7" in OS.get_cmdline_user_args():
		if route=="B":return directory.get_base_dir().path_join("round7-upper-lip-continuity/B-artifacts/fish.glb")
		if route=="A":return directory.get_base_dir().path_join("round6-reference-repair/A-artifacts/fish.glb")
	if route!="Original" and "--revision6" in OS.get_cmdline_user_args():return directory.get_base_dir().path_join("round6-reference-repair/"+route+"-artifacts/fish.glb")
	if route!="Original" and "--after" in OS.get_cmdline_user_args():return directory.get_base_dir().path_join("round5-user-review-fixes/"+route+"-artifacts/fish.glb")
	return super._model_path(route)
func _run() -> void:
	live=false;motion_paused=true
	audit_dir=directory.get_base_dir().path_join("round7-upper-lip-continuity" if "--revision7" in OS.get_cmdline_user_args() else "round6-reference-repair" if "--revision6" in OS.get_cmdline_user_args() else "round5-user-review-fixes")
	DirAccess.make_dir_recursive_absolute(audit_dir)
	for route in ["Original","A","B"]:
		var box := SubViewportContainer.new();box.stretch=false;root.add_child(box)
		var entry: Dictionary=_load(route,box)
		if entry.is_empty():quit(2);return
		entry.view.size=Vector2i(900,620);entries.append(entry)
	await process_frame
	for entry in entries:entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	_set_direction(Vector3(0,0,1));zoom=.52;pan_offset=Vector3.ZERO
	await _audit_capture("whole-before")
	zoom=.14;pan_offset=Vector3(.081,-.04,0)
	for mode in ["all","body-only","pectoral-only"]:
		for entry in entries:
			for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
				mesh.visible=mode=="all" or str(mesh.name).begins_with("Closed_body") if mode!="pectoral-only" else str(mesh.name).begins_with("Pectoral")
		await _audit_capture("pectoral-before-"+mode)
	for entry in entries:
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.show()
	zoom=.065;pan_offset=Vector3(.191,-.006,0)
	for view in [{"name":"side","dir":Vector3(0,0,1)},{"name":"oblique","dir":Vector3(.8,.1,1)},{"name":"front","dir":Vector3(1,.02,0)}]:
		_set_direction(view.dir)
		await _audit_capture("mouth-before-"+view.name)
		_set_gray(true);await _audit_capture("mouth-before-"+view.name+"-clay");_set_gray(false)
		if view.name=="front" and "--revision7" in OS.get_cmdline_user_args():
			var b: Dictionary=entries[2];var bm: MeshInstance3D=b.model.find_child("Closed_body_B",true,false)
			var mat: StandardMaterial3D=bm.mesh.surface_get_material(0);var previous: Texture2D=mat.albedo_texture
			mat.albedo_texture=ImageTexture.create_from_image(Image.load_from_file(audit_dir.path_join("upper-lip-marked-atlas.png")))
			await _audit_capture("upper-lip-front-marked");mat.albedo_texture=previous
	zoom=.12;pan_offset=Vector3(.161,.017,0)
	for view in [{"name":"top","dir":Vector3(0,1,.001)},{"name":"front-oblique","dir":Vector3(1,.4,.5)}]:
		_set_direction(view.dir);await _audit_capture("forehead-"+view.name)
	for entry in entries:
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
			mesh.visible=str(mesh.name)=="Pectoral_left"
			if mesh.visible:entry["fin_focus"]=entry.carrier.global_transform.affine_inverse()*(mesh.global_transform*mesh.get_aabb().get_center())
	_set_gray(true);zoom=.075;pan_offset=Vector3.ZERO;_set_direction(Vector3(-.9,.22,.07))
	await _audit_capture("fin-thickness-edge")
	FileAccess.open(audit_dir.path_join("diagnostic-cold-render"+("-after" if "--after" in OS.get_cmdline_user_args() else "")+".validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("NILE_REVIEW_DIAGNOSTIC_OK");quit()

func _audit_capture(label: String) -> void:
	if "--after" in OS.get_cmdline_user_args():label=label.replace("before","after")
	if "--revision6" in OS.get_cmdline_user_args():label=label.replace("before","current")
	if "--revision7" in OS.get_cmdline_user_args():label=label.replace("before","current")
	_cameras();await process_frame;await RenderingServer.frame_post_draw
	for entry in entries:
		var path := audit_dir.path_join(entry.route+"-"+label+".png")
		assert(entry.view.get_texture().get_image().save_png(path)==OK)
		report.captures.append({"route":entry.route,"label":label,"path":path,"sha256":FileAccess.get_sha256(path)})
