extends "capture_fish_review.gd"
## Actual cold-read isolated fins, for thickness/camber and whole native outline.
## Isolation is evidence only; no replacement geometry or runtime production edit.
func _run() -> void:
	load_plan=plan
	var box:=SubViewportContainer.new();root.add_child(box)
	var entry: Dictionary=super._load("fin-volume",box);entries.append(entry)
	entry.view.mesh_lod_threshold=0.0
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	var frozen: String=static_check.static_binding_digest(entry.model)
	var logical: Dictionary=PACKED_PARTS.surfaces(entry,plan);assert(logical.ok)
	var probes: Dictionary=PACKED_PARTS.make_probes(entry,logical,plan.fins)
	assert(probes.size()==plan.fins.size())
	for row in logical.surfaces:row.mesh.hide()
	for name in plan.fins:
		var probe: MeshInstance3D=probes[name];probe.show()
		var bounds: AABB=probe.get_aabb();var scaling: float=float(plan.model_scale)
		focus=(probe.transform*bounds.get_center())*scaling
		zoom=maxf(bounds.size.length()*scaling*1.25,.015)
		for view in [views()[0],views()[2],views()[4],views()[6]]:
			direction=view.dir
			for clay in [false,true]:
				_set_gray(clay);await photo("fin-"+str(name)+"-"+view.name+("-clay" if clay else "-texture"))
		_set_gray(false);probe.hide()
	PACKED_PARTS.clear_probes(probes)
	for row in logical.surfaces:row.mesh.show()
	assert(static_check.static_binding_digest(entry.model)==frozen)
	for path in bindings:assert(FileAccess.get_sha256(path)==bindings[path])
	report.merge({"ok":true,"kind":"cold_actual_isolated_fin_volume_views","model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"fin_inventory":plan.fins,"direct_GLTFDocument":true,"runtime_static_build_calls":0,"static_arrays_uv_materials_unchanged":true,"formal_acceptance":false,"scope":"Actual isolated side/end/top/oblique, texture/clay views. Whole-fish attachment and posed checks remain separate; no image is automatically accepted."})
	FileAccess.open(review_out.path_join("fin-volume-capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("FIN_VOLUME_CAPTURE_OK");quit()
