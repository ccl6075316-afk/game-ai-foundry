extends "capture_fish_review.gd"
## Exercise the actual game entry, its prepared cache, and the direct cold GLB.
func parity(a: Node3D,b: Node3D) -> Dictionary:
	var aa := a.find_children("*","MeshInstance3D",true,false)
	var bb := b.find_children("*","MeshInstance3D",true,false)
	assert(aa.size()==1 and bb.size()==1)
	var x := aa[0] as MeshInstance3D
	var y := bb[0] as MeshInstance3D
	assert(x.mesh.get_surface_count()==1 and y.mesh.get_surface_count()==1)
	var xa := x.mesh.surface_get_arrays(0)
	var ya := y.mesh.surface_get_arrays(0)
	for k in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_BONES,Mesh.ARRAY_WEIGHTS,Mesh.ARRAY_INDEX]:
		assert(var_to_bytes(xa[k])==var_to_bytes(ya[k]),"Actual entry changed a reviewed static array")
	var xm := x.get_active_material(0) as StandardMaterial3D
	var ym := y.get_active_material(0) as StandardMaterial3D
	assert(xm!=null and ym!=null and xm.albedo_texture!=null and ym.albedo_texture!=null)
	var xi := xm.albedo_texture.get_image()
	var yi := ym.albedo_texture.get_image()
	assert(xi.get_size()==yi.get_size() and xi.get_data()==yi.get_data())
	assert(xm.transparency==BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR and xm.texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST)
	return {"ok":true,"all_arrays_byte_equal":true,"embedded_RGBA_equal":true,"mesh_count":1,"triangles":xa[Mesh.ARRAY_INDEX].size()/3}

func _run() -> void:
	load_plan=plan
	var box:=SubViewportContainer.new()
	root.add_child(box)
	var direct:=super._load("direct-source",box)
	var world: Node3D=direct.carrier.get_parent()
	direct.carrier.hide()
	var exhibit=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
	var cfg: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(plan.motion_profile))
	exhibit._add_fish(world,plan.species,float(cfg.real_length_cm)/100.0,cfg)
	var actual: Dictionary=exhibit.fish[0]
	assert(not exhibit.loading_metrics[0].reused_appearance)
	var receipt: Dictionary=actual.model.get_meta("final_width20261101_receipt")
	assert(receipt.static_builders_disabled and receipt.runtime_static_build_calls==0)
	assert(FileAccess.get_sha256(actual.model.scene_file_path)==plan.model_sha256)
	var compare:=parity(actual.model,direct.model)
	var entry: Dictionary=direct.duplicate()
	for k in ["model","carrier","player","skeleton","controller"]:entry[k]=actual[k]
	entries.append(entry)
	var frozen: String=static_check.static_binding_digest(entry.model)
	var max_rotation_error:=0.0
	var max_position_error:=0.0
	for action in ["Swim","Turn","Ascend","Dive"]:
		for target in [entry,direct]:assert(target.controller.set_action(action,true))
		for phase in 9:
			for target in [entry,direct]:target.controller.seek(float(phase)*.47)
			for i in entry.skeleton.get_bone_count():
				max_position_error=maxf(max_position_error,entry.skeleton.get_bone_pose_position(i).distance_to(direct.skeleton.get_bone_pose_position(i)))
				var a: Quaternion=entry.skeleton.get_bone_pose_rotation(i)
				var b: Quaternion=direct.skeleton.get_bone_pose_rotation(i)
				max_rotation_error=maxf(max_rotation_error,minf(Vector4(a.x-b.x,a.y-b.y,a.z-b.z,a.w-b.w).length(),Vector4(a.x+b.x,a.y+b.y,a.z+b.z,a.w+b.w).length()))
	assert(max_position_error<.00001 and max_rotation_error<.00001)
	for action in ["Turn","Ascend","Dive","Swim"]:
		assert(entry.controller.set_action(action,false))
		for i in 90:entry.controller.step(1.0/60.0)
		assert(entry.controller.snapshot().action==action and entry.controller.snapshot().inside_envelope)
	entry.player.stop()
	entry.skeleton.reset_bone_poses()
	entry.carrier.transform=Transform3D.IDENTITY
	zoom=float(plan.whole_camera_size)
	focus=Vector3.ZERO
	await photo_views("installed-whole")
	zoom=float(plan.details[0].size)
	var at: Array=plan.details[0].at
	focus=Vector3(at[0],at[1],at[2])
	await photo_views("installed-head")
	assert(static_check.static_binding_digest(entry.model)==frozen)
	exhibit._add_fish(world,plan.species,float(cfg.real_length_cm)/100.0,cfg)
	assert(exhibit.loading_metrics[1].reused_appearance)
	var cached:=parity(exhibit.fish[1].model,direct.model)
	var dependencies: Dictionary={}
	for path in ["res://scripts/aquarium/VolumeFishExhibit.gd","res://scripts/aquarium/FishSurfaceOwnership.gd","res://scripts/aquarium/FinalizedWidthBatch20261101.gd","res://assets/models/fish/motion/width20261101/manifest.json"]:dependencies[ProjectSettings.globalize_path(path)]=FileAccess.get_sha256(path)
	for path in bindings:assert(FileAccess.get_sha256(path)==bindings[path])
	report.merge({"ok":true,"kind":"actual_installed_fish_entry_cold_load","species":plan.species,"model_sha256":plan.model_sha256,"fresh_process":true,"static_builders_disabled":true,"runtime_static_build_calls":0,"errors":[],"actual_entry":"VolumeFishExhibit._add_fish","formal_entry_model":actual.model.scene_file_path,"receipt":receipt,"direct_parity":compare,"cached_parity":cached,"maximum_position_error":max_position_error,"maximum_quaternion_component_error":max_rotation_error,"four_actions_and_transitions":true,"dependencies":dependencies,"formal_acceptance":false})
	FileAccess.open(review_out.path_join("installed-cold.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
	exhibit.free()
	print("INSTALLED_WIDTH_COLD_OK ",plan.species)
	quit()
