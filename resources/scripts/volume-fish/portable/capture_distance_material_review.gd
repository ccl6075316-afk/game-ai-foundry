extends "capture_fish_review.gd"
## Direct final GLB at real camera distances, with actual serialized LOD inventory.
func _run() -> void:
	load_plan=plan
	var box:=SubViewportContainer.new();root.add_child(box)
	var entry: Dictionary=super._load("distance",box);entries.append(entry)
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
	var frozen: String=static_check.static_binding_digest(entry.model)
	var inventory: Array=[]
	for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
		var serialized: Variant=mesh.mesh.get("_surfaces")
		var surfaces: Array=[]
		for s in mesh.mesh.get_surface_count():
			var lods: Variant=serialized[s].get("lods",[]) if serialized is Array else null
			surfaces.append({"surface":s,"triangles":mesh.mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX].size()/3,"serialized_lod_entries":lods.size() if lods is Array or lods is Dictionary else -1,"material":mesh.get_active_material(s).resource_name})
		inventory.append({"mesh":str(mesh.name),"surfaces":surfaces})
	entry.camera.projection=Camera3D.PROJECTION_PERSPECTIVE;entry.camera.fov=36.
	var cases: Array=[{"name":"far","distance":8.,"at":[-.20,-.06,0.]},{"name":"normal","distance":5.,"at":[-.20,-.06,0.]},{"name":"close-head","distance":1.8,"at":[.88,-.07,0.]}]
	for item in cases:
		plan.camera_distance=item.distance;focus=Vector3(item.at[0],item.at[1],item.at[2])
		for threshold in [0.,1.]:
			entry.view.mesh_lod_threshold=threshold
			for v in [views()[0],views()[1],views()[4],views()[6]]:
				direction=v.dir;await photo(item.name+"-lod"+str(int(threshold))+"-"+v.name)
	assert(static_check.static_binding_digest(entry.model)==frozen)
	for path in bindings:assert(FileAccess.get_sha256(path)==bindings[path])
	report.merge({"ok":true,"kind":"actual_material_anchor_distance_and_lod_review","model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"actual_mesh_inventory":inventory,"camera_cases":cases,"lod_thresholds":[0.,1.],"static_arrays_uv_materials_unchanged":true,"runtime_static_build_calls":0,"scope":"Actual imported render meshes and serialized LOD entries, both viewport thresholds at three perspective distances. This candidate has no alternative species model installed. Images require operator review; no automatic eye/skin acceptance."})
	FileAccess.open(review_out.path_join("distance-material.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	print("DISTANCE_MATERIAL_REVIEW_OK");quit()
