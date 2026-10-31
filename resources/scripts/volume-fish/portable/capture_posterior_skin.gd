extends "capture_fish_review.gd"
## Diagnostic isolation of each actual body surface and posterior donor patch.
func _run() -> void:
	load_plan=plan
	var box:=SubViewportContainer.new();root.add_child(box)
	var entry: Dictionary=super._load("posterior-skin",box);entries.append(entry)
	entry.view.mesh_lod_threshold=0.0
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	var frozen: String=static_check.static_binding_digest(entry.model)
	var logical: Dictionary=PACKED_PARTS.surfaces(entry,plan);assert(logical.ok)
	var detail: Dictionary=plan.details[-1]
	zoom=float(detail.size);focus=Vector3(float(detail.at[0]),float(detail.at[1]),float(detail.at[2]))
	for view in [views()[0],views()[4],views()[6]]:
		direction=view.dir;await photo("whole-tail-"+view.name)
	for row in logical.surfaces:row.mesh.hide()
	for row in logical.surfaces:
		if row.role!="body_skin":continue
		var subset: Dictionary=logical.duplicate();subset.surfaces=[row]
		var probes: Dictionary=PACKED_PARTS.make_probes(entry,subset)
		for probe in probes.values():probe.show()
		for view in [views()[0],views()[4],views()[6]]:
			direction=view.dir;await photo("body-surface-"+str(row.source_surface)+"-tail-"+view.name)
		PACKED_PARTS.clear_probes(probes)
	assert(static_check.static_binding_digest(entry.model)==frozen)
	report.merge({"ok":true,"diagnostic_only":true,"model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"partition_proof":logical.proof,"static_arrays_uv_materials_unchanged":true})
	FileAccess.open(review_out.path_join("posterior-capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	quit()
