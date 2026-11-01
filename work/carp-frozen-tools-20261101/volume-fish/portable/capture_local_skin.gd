extends "capture_fish_review.gd"
## Local skin/jaw check only: no288-frame movie or complete physical gate.
func photo(label: String) -> void:
	await super.photo(label)
	var actual: Image=_view_image(entries[0]);var bg: Color=actual.get_pixel(0,0);var count:=0
	for y in range(0,actual.get_height(),8):
		for x in range(0,actual.get_width(),8):
			if actual.get_pixel(x,y)!=bg:count+=1
	assert(count>=5,"Empty local evidence view: "+label)
func _run() -> void:
	load_plan=plan
	var box:=SubViewportContainer.new();root.add_child(box)
	var entry: Dictionary=super._load("local",box);entries.append(entry)
	entry.view.mesh_lod_threshold=0.0
	var frozen: String=static_check.static_binding_digest(entry.model)
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	zoom=float(plan.whole_camera_size);focus=Vector3.ZERO;await photo_views("whole")
	for detail in plan.details:
		zoom=float(detail.size);focus=Vector3(float(detail.at[0]),float(detail.at[1]),float(detail.at[2]));await photo_views(detail.name)
	var logical: Dictionary=PACKED_PARTS.surfaces(entry,plan);assert(logical.ok)
	var probes: Dictionary=PACKED_PARTS.make_probes(entry,logical,[plan.body])
	for row in logical.surfaces:row.mesh.hide()
	for probe in probes.values():probe.show()
	zoom=float(plan.whole_camera_size);focus=Vector3.ZERO;await photo_views("body-without-fins")
	PACKED_PARTS.clear_probes(probes)
	for row in logical.surfaces:row.mesh.show()
	assert(static_check.static_binding_digest(entry.model)==frozen,"Local review changed static asset")
	for path in bindings:assert(FileAccess.get_sha256(path)==bindings[path])
	report.merge({"ok":true,"kind":"portable_local_skin_review_capture","diagnostic_only":true,"formal_acceptance":false,"model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"runtime_static_build_calls":0,"direct_GLTFDocument":true,"static_arrays_uv_materials_unchanged":true,"scope":"Local actual texture/clay and pure-body review only; no movie,177/490,body077 or visual acceptance."})
	FileAccess.open(review_out.path_join("local-capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("LOCAL_SKIN_CAPTURE_OK");quit()
