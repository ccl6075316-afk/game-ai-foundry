extends "preview_nile_ab_textured.gd"
## Geometry-only baseline comparison. Never substitutes old GLB textures for
## the original game's static shader appearance. Reads all models unchanged.
var comparison_dir: String

func _model_path(route: String) -> String:
	if route=="Original":return ProjectSettings.globalize_path("res://assets/models/fish/nile_tilapia.glb")
	return super._model_path(route)

func _run() -> void:
	comparison_dir=directory.path_join("original-comparison")
	DirAccess.make_dir_recursive_absolute(comparison_dir)
	assert(FileAccess.get_sha256(_model_path("Original"))=="4ee2c552939b682463120b52e40f2f98e996c2dad8f91f9144ab7d6de51ad25a")
	for route in ["Original","A","B"]:
		var box := SubViewportContainer.new();box.stretch=false;root.add_child(box)
		entries.append(_load(route,box))
	await process_frame
	_set_gray(true)
	for entry in entries:
		entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	for view in [{"name":"side","dir":Vector3(0,0,1)},{"name":"oblique","dir":Vector3(.65,.25,1).normalized()},{"name":"front","dir":Vector3(1,0,0)},{"name":"top","dir":Vector3(0,1,.001).normalized()}]:
		direction=view.dir;_cameras();await process_frame;await RenderingServer.frame_post_draw
		for entry in entries:
			var path := comparison_dir.path_join(entry.route+"-"+view.name+".png")
			assert(_view_image(entry).save_png(path)==OK)
			report.captures.append({"route":entry.route,"view":view.name,"path":path,"sha256":FileAccess.get_sha256(path)})
	report["kind"]="nile_original_geometry_comparison"
	report["ok"]=true;report["scope"]="Same gray opaque material/camera/light/rest pose. Geometry comparison only; original game texture/shader appearance not reconstructed or judged by these gray renders."
	FileAccess.open(comparison_dir.path_join("cold-render.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("NILE_ORIGINAL_COMPARISON_OK");quit()
