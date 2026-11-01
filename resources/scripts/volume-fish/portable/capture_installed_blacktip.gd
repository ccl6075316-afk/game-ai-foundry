extends "capture_fish_review.gd"
## Fresh-process proof of the actual VolumeFishExhibit._add_fish entry.
## Its SHA-gated finalizer returns before all legacy static factories.
var exhibit

func _q(v: Variant, step: float) -> Variant:
	if v is Vector3: return [roundi(v.x/step),roundi(v.y/step),roundi(v.z/step)]
	if v is Vector2: return [roundi(v.x/step),roundi(v.y/step)]
	return roundi(float(v)/step)

func _corners(node: MeshInstance3D, surface: int) -> Array:
	var a := node.mesh.surface_get_arrays(surface)
	var stride: int = a[Mesh.ARRAY_BONES].size()/a[Mesh.ARRAY_VERTEX].size()
	var result: Array = []
	for t in range(0,a[Mesh.ARRAY_INDEX].size(),3):
		var corners: Array = []
		for k in 3:
			var i: int = a[Mesh.ARRAY_INDEX][t+k]
			var weights: Dictionary = {}
			for j in stride:
				var weight: float = a[Mesh.ARRAY_WEIGHTS][i*stride+j]
				if weight == 0.0: continue
				var bone: int = a[Mesh.ARRAY_BONES][i*stride+j]
				var name: String = str(node.skin.get_bind_name(bone))
				if name.is_empty():
					var skeleton := node.get_node(node.skeleton) as Skeleton3D
					name = str(skeleton.get_bone_name(node.skin.get_bind_bone(bone)))
				weights[name] = int(weights.get(name,0)) + roundi(weight/0.00001)
			corners.append(JSON.stringify([_q(a[Mesh.ARRAY_VERTEX][i],0.000001),_q(a[Mesh.ARRAY_NORMAL][i],0.0001),_q(a[Mesh.ARRAY_TEX_UV][i],0.000001),weights]))
		corners.sort();result.append(JSON.stringify(corners))
	result.sort();return result

func _parity(actual: Node3D, direct: Node3D) -> Dictionary:
	var rows: Array = []
	for node in direct.find_children("*","MeshInstance3D",true,false):
		var other: MeshInstance3D = actual.find_child(str(node.name),true,false)
		assert(other != null and other.mesh.get_surface_count() == node.mesh.get_surface_count())
		for si in node.mesh.get_surface_count():
			var same: bool = _corners(node,si) == _corners(other,si)
			if not same:
				var diagnostic := {}
				for label in ["direct","imported"]:
					var m: MeshInstance3D = node if label == "direct" else other
					var raw := m.mesh.surface_get_arrays(si)
					var attrs := {}
					for slot in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_BONES,Mesh.ARRAY_WEIGHTS,Mesh.ARRAY_INDEX]:
						var values: Array = []
						for v in raw[slot]:
							if v is Vector3: values.append([v.x,v.y,v.z])
							elif v is Vector2: values.append([v.x,v.y])
							else:values.append(v)
						attrs[str(slot)] = values
					var bind_names: Array = []
					for j in m.skin.get_bind_count():bind_names.append(str(m.skin.get_bind_name(j)))
					diagnostic[label] = {"attrs":attrs,"bind_names":bind_names}
				FileAccess.open(review_out.path_join("import-array-diagnostic.json"),FileAccess.WRITE).store_string(JSON.stringify(diagnostic))
				quit(1);return {"ok":false}
			assert(same,"Imported triangle attributes differ: "+str(node.name)+"/"+str(si))
			var a := node.get_active_material(si) as StandardMaterial3D
			var b := other.get_active_material(si) as StandardMaterial3D
			assert(a != null and b != null and a.albedo_color.is_equal_approx(b.albedo_color))
			var texture_equal := (a.albedo_texture == null) == (b.albedo_texture == null)
			if a.albedo_texture != null:
				var ai := a.albedo_texture.get_image();var bi := b.albedo_texture.get_image()
				var sizes := [ai.get_size(),bi.get_size(),ai.get_format(),bi.get_format(),ai.has_mipmaps(),bi.has_mipmaps()]
				if ai.is_compressed():assert(ai.decompress() == OK)
				if bi.is_compressed():assert(bi.decompress() == OK)
				ai.clear_mipmaps();bi.clear_mipmaps();ai.convert(Image.FORMAT_RGBA8);bi.convert(Image.FORMAT_RGBA8)
				texture_equal = texture_equal and ai.get_size() == bi.get_size() and ai.get_data() == bi.get_data()
				if not texture_equal:
					ai.save_png(review_out.path_join("direct-material.png"));bi.save_png(review_out.path_join("imported-material.png"))
					print("TEXTURE_DIFFERENCE ",node.name,"/",si," ",sizes," path=",b.albedo_texture.resource_path)
					quit(1);return {"ok":false}
			assert(texture_equal and b.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED and b.texture_filter == BaseMaterial3D.TEXTURE_FILTER_NEAREST)
			assert(other.mesh.get("_surfaces")[si].get("lods",[]).is_empty(),"Unexpected generated LOD")
			rows.append({"mesh":str(node.name),"surface":si,"triangle_attributes_equal":same,"rgba_equal":texture_equal,"actual_lods":0})
	assert(actual.find_children("*","MeshInstance3D",true,false).size() == 9)
	return {"ok":true,"surfaces":rows,"position_uv_quantization":0.000001,"normal_quantization":0.0001,"named_weight_quantization":0.00001}

func _run() -> void:
	load_plan = plan
	var container := SubViewportContainer.new();root.add_child(container)
	# Scene world and direct source are evidence probes only. The installed model
	# itself is loaded exclusively through the game's actual _add_fish method.
	var direct := super._load("direct-source",container)
	var world: Node3D = direct.carrier.get_parent()
	direct.carrier.hide()
	exhibit = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
	var cfg: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles[plan.species]
	assert(cfg == JSON.parse_string(FileAccess.get_file_as_string(plan.motion_profile)))
	exhibit._add_fish(world,plan.species,1.5,cfg)
	var item: Dictionary = exhibit.fish[0]
	assert(not exhibit.loading_metrics[0].reused_appearance)
	var receipt: Dictionary = item.model.get_meta("final_blacktip_anatomy_receipt")
	assert(receipt.static_builders_disabled and receipt.runtime_static_build_calls == 0)
	assert(FileAccess.get_sha256(item.model.scene_file_path) == plan.model_sha256)
	var entry: Dictionary = direct.duplicate()
	for key in ["model","carrier","player","skeleton","controller"]:entry[key] = item[key]
	entries.append(entry)
	entry.view.mesh_lod_threshold = 0.0
	var parity := _parity(entry.model,direct.model)
	if not parity.ok:return
	var frozen: String = static_check.static_binding_digest(entry.model)
	var max_position_error := 0.0
	var max_rotation_error := 0.0
	var worst: Dictionary = {}
	var poses: Array = []
	for action in ["Swim","Turn","Ascend","Dive"]:
		for target in [entry,direct]: assert(target.controller.set_action(action,true))
		for phase in 9:
			for target in [entry,direct]:target.controller.seek(float(phase)*0.47)
			for i in entry.skeleton.get_bone_count():
				assert(entry.skeleton.get_bone_name(i) == direct.skeleton.get_bone_name(i))
				max_position_error = maxf(max_position_error,entry.skeleton.get_bone_pose_position(i).distance_to(direct.skeleton.get_bone_pose_position(i)))
				var qa: Quaternion = entry.skeleton.get_bone_pose_rotation(i)
				var qb: Quaternion = direct.skeleton.get_bone_pose_rotation(i)
				var error := minf(Vector4(qa.x-qb.x,qa.y-qb.y,qa.z-qb.z,qa.w-qb.w).length(),Vector4(qa.x+qb.x,qa.y+qb.y,qa.z+qb.z,qa.w+qb.w).length())
				if error > max_rotation_error:worst = {"bone":str(entry.skeleton.get_bone_name(i)),"action":action,"phase":phase,"actual":[qa.x,qa.y,qa.z,qa.w],"direct":[qb.x,qb.y,qb.z,qb.w]}
				max_rotation_error = maxf(max_rotation_error,error)
			assert(entry.controller.snapshot().inside_envelope)
		poses.append({"action":action,"phases":9})
	if max_position_error >= 0.00001 or max_rotation_error >= 0.00001:
		print("ACTUAL_RIG_DIFFERENCE ",JSON.stringify({"position":max_position_error,"quaternion":max_rotation_error,"worst":worst}))
		preload("res://scripts/aquarium/FishAppearanceCache.gd").clear();exhibit.free();quit(1);return
	for action in ["Turn","Ascend","Dive","Swim"]:
		assert(entry.controller.set_action(action,false))
		for i in 16: entry.controller.step(0.0625)
		assert(entry.controller.snapshot().action == action and entry.controller.snapshot().inside_envelope)
	entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform = Transform3D.IDENTITY
	zoom = 1.8;focus = Vector3.ZERO;await photo_views("installed-whole")
	zoom = 0.46;focus = Vector3(0.64,-0.02,0.0);await photo_views("installed-head")
	zoom = 0.7;focus = Vector3(-0.5,0,0);await photo_views("installed-tail")
	assert(static_check.static_binding_digest(entry.model) == frozen)
	# Repeat the real entry through its prepared-appearance cache branch.
	exhibit._add_fish(world,plan.species,1.5,cfg)
	assert(exhibit.loading_metrics[1].reused_appearance)
	var cached_parity := _parity(exhibit.fish[1].model,direct.model)
	var dependencies := {}
	for path in ["res://scripts/aquarium/VolumeFishExhibit.gd","res://scripts/aquarium/FishSurfaceOwnership.gd","res://scripts/aquarium/FinalizedBlacktipAnatomy20261101.gd","res://assets/models/fish/motion/motion.json","res://assets/models/fish/blacktip_reef_shark.glb.import"]:dependencies[ProjectSettings.globalize_path(path)] = FileAccess.get_sha256(path)
	for path in bindings:assert(FileAccess.get_sha256(path) == bindings[path])
	report.merge({"ok":true,"kind":"actual_installed_fish_entry_cold_load","species":plan.species,"model_sha256":plan.model_sha256,"fresh_process":true,"static_builders_disabled":true,"runtime_static_build_calls":0,"errors":[],"actual_entry":"VolumeFishExhibit._add_fish","formal_entry_model":item.model.scene_file_path,"receipt":receipt,"imported_vs_direct":parity,"cached_vs_direct":cached_parity,"rig_motion":{"bones":18,"actions":poses,"maximum_position_error":max_position_error,"maximum_quaternion_component_distance":max_rotation_error,"real_transitions":4},"actual_lod_policy":"No generated LOD; full reviewed3944 triangles retained at all distances","dependencies":dependencies,"static_arrays_uv_materials_unchanged":true,"formal_acceptance":false})
	FileAccess.open(review_out.path_join("installed-cold.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	# Release source-only diagnostic objects and the unparented formal entry owner.
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
	exhibit.free()
	print("INSTALLED_BLACKTIP_COLD_OK");quit()
