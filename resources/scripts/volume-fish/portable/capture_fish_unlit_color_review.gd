extends "capture_fish_local_form_review.gd"
## Diagnostic only: identical native geometry/cameras with albedo unlit.
func _load(label: String, box: SubViewportContainer) -> Dictionary:
	var entry: Dictionary=super._load(label,box)
	for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
		for i in range(mesh.mesh.get_surface_count()):
			var source=mesh.get_active_material(i)
			assert(source is BaseMaterial3D)
			var material=source.duplicate()
			material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
			mesh.set_surface_override_material(i,material)
	return entry

func _run() -> void:
	load_plan=plan
	var box:=SubViewportContainer.new();root.add_child(box)
	var entry: Dictionary=_load("B",box);entries.append(entry)
	entry.view.mesh_lod_threshold=0.;entry.model.scale=Vector3.ONE*float(plan.model_scale)
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	for detail in plan.details:
		zoom=float(detail.size);focus=Vector3(float(detail.at[0]),float(detail.at[1]),float(detail.at[2]));await photo_views(detail.name)
	report.merge({"ok":true,"kind":"unlit_color_diagnostic_only","model_sha256":plan.model_sha256,"source_static_authoring":false,"diagnostic_surface_material_overrides":true,"formal_acceptance":false})
	FileAccess.open(review_out.path_join("unlit-review.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("UNLIT_COLOR_REVIEW_OK");quit()
