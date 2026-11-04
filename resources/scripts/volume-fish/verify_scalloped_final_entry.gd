extends SceneTree
## Actual finished entry against an independent native GLB load; no static builders.
const EXHIBIT = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const BINDER = preload("res://scripts/aquarium/FinalizedScallopedHammerhead.gd")
var entry: Dictionary
var direct: Dictionary
var comparisons := 0

func _initialize() -> void: call_deferred("run")

func compare_static(a: Node3D, b: Node3D, require_no_override: bool) -> Dictionary:
	var meshes := a.find_children("*","MeshInstance3D",true,false)
	assert(meshes.size()==9 and b.find_children("*","MeshInstance3D",true,false).size()==9)
	var triangles := 0; var surfaces := 0; var lods := 0
	for x in meshes:
		var y := b.find_child(str(x.name),true,false) as MeshInstance3D
		assert(y!=null and x.skin!=null and y.skin!=null)
		assert(x.transform==y.transform and x.mesh.get_surface_count()==y.mesh.get_surface_count())
		assert(x.material_override==null)
		for i in x.mesh.get_surface_count():
			if require_no_override: assert(x.get_surface_override_material(i)==null)
			var p: Array=x.mesh.surface_get_arrays(i); var q: Array=y.mesh.surface_get_arrays(i)
			for k in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TANGENT,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_TEX_UV2,Mesh.ARRAY_COLOR,Mesh.ARRAY_BONES,Mesh.ARRAY_WEIGHTS,Mesh.ARRAY_INDEX]:
				assert(var_to_bytes(p[k])==var_to_bytes(q[k]),str(x.name)+" array "+str(k))
			triangles+=(p[Mesh.ARRAY_INDEX] as PackedInt32Array).size()/3; surfaces+=1
			var m: StandardMaterial3D=x.get_active_material(i); var n: StandardMaterial3D=y.get_active_material(i)
			for key in ["texture_filter","transparency","cull_mode","roughness","metallic","metallic_specular","albedo_color","alpha_scissor_threshold","shading_mode","vertex_color_use_as_albedo"]:
				assert(m.get(key)==n.get(key),key)
			if m.albedo_texture == null: assert(n.albedo_texture == null)
			else: assert(n.albedo_texture != null and m.albedo_texture.get_image().get_data()==n.albedo_texture.get_image().get_data())
		for surface in x.mesh.get("_surfaces"):lods+=surface.get("lods",[]).size()
	assert(triangles==3994 and surfaces==24 and lods==0)
	return {"triangles":triangles,"meshes":meshes.size(),"surfaces":surfaces,"serialized_lod_entries":lods}

func pose(item: Dictionary, action: String, seconds: float) -> void:
	assert(item.controller.set_action(action,true)); item.controller.step(0.0); item.controller.seek(seconds)

func delta(a: Dictionary, b: Dictionary) -> float:
	var error:=0.0
	for i in a.skeleton.get_bone_count():
		var j: int=b.skeleton.find_bone(a.skeleton.get_bone_name(i)); assert(j>=0)
		var p: Transform3D=a.skeleton.get_bone_global_pose(i); var q: Transform3D=b.skeleton.get_bone_global_pose(j)
		error=maxf(error,p.origin.distance_to(q.origin))
		for axis in 3:error=maxf(error,p.basis[axis].distance_to(q.basis[axis]))
	return error

func run() -> void:
	var out: String=OS.get_cmdline_user_args()[0]; assert(DirAccess.dir_exists_absolute(out))
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
	preload("res://scripts/aquarium/FishRuntimeData.gd").clear()
	preload("res://scripts/aquarium/FishRuntimeData.gd").begin_entry()
	var viewport:=SubViewport.new(); viewport.size=Vector2i(1000,720); viewport.own_world_3d=true; viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS; viewport.mesh_lod_threshold=0.0; root.add_child(viewport)
	var world:=Node3D.new(); viewport.add_child(world)
	var env:=WorldEnvironment.new(); env.environment=Environment.new(); env.environment.background_mode=Environment.BG_COLOR; env.environment.background_color=Color("25343c"); env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR; env.environment.ambient_light_color=Color.WHITE; env.environment.ambient_light_energy=0.65; world.add_child(env)
	var light:=DirectionalLight3D.new(); light.rotation_degrees=Vector3(-45,-35,0); light.light_energy=0.65; world.add_child(light)
	var camera:=Camera3D.new(); camera.projection=Camera3D.PROJECTION_ORTHOGONAL; camera.size=2.9; camera.near=0.001; camera.far=50; world.add_child(camera)
	var exhibit=EXHIBIT.new()
	# Passing the legacy profile proves the final entry replaces it with the reviewed file.
	var legacy: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles.scalloped_hammerhead
	exhibit._add_fish(world,"scalloped_hammerhead",2.5,legacy); entry=exhibit.fish[0]
	assert(entry.model.has_meta("final_asset_scalloped_receipt") and entry.model.scale==Vector3.ONE)
	var profile: Dictionary=BINDER.new().motion_profile(); assert(entry.profile==profile)
	var path: String=entry.model.scene_file_path
	var doc:=GLTFDocument.new(); var state:=GLTFState.new(); assert(doc.append_from_file(ProjectSettings.globalize_path(path),state)==OK)
	var model:=doc.generate_scene(state) as Node3D; model.scene_file_path=path
	var carrier:=Node3D.new(); world.add_child(carrier); carrier.add_child(model); model.scale=entry.model.scale; model.position=entry.model.position
	var sk: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]; var player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
	var ctrl=load(EXHIBIT.MOTION_SCRIPT).new(); assert(ctrl.configure(carrier,model,player,sk,profile).ok)
	direct={"carrier":carrier,"model":model,"skeleton":sk,"player":player,"controller":ctrl}
	var static_result:=compare_static(entry.model,model,true)
	var max_delta:=0.0
	for values in [[0.0,0.0,0.0,0.0],[1.0,1.0,1.0,1.0],[2.5,1.0,2.5,1.0],[1.0,3.0,1.0,3.0],[1.3,0.7,2.0,1.4]]:
		var settings: Dictionary={"body_amplitude":values[0],"body_frequency":values[1],"fin_amplitude":values[2],"fin_frequency":values[3]}
		entry.controller.set_motion_controls(settings,true); ctrl.set_motion_controls(settings,true)
		for action in ["Swim","Turn","Ascend","Dive"]:
			for i in 24:
				pose(entry,action,float(i)/24.0*float(profile.period_seconds)); pose(direct,action,float(i)/24.0*float(profile.period_seconds))
				max_delta=maxf(max_delta,delta(entry,direct)); assert(entry.controller.snapshot().inside_envelope); comparisons+=1
	assert(max_delta==0.0)
	var normal: Dictionary={"body_amplitude":1.0,"body_frequency":1.0,"fin_amplitude":1.0,"fin_frequency":1.0}
	entry.controller.set_motion_controls(normal,true); ctrl.set_motion_controls(normal,true)
	var captures:=[]
	for action in ["Swim","Turn","Ascend","Dive"]:
		pose(entry,action,1.17); pose(direct,action,1.17)
		camera.position=entry.carrier.global_position+Vector3(0.5,0.4,4.0); camera.look_at(entry.carrier.global_position,Vector3.UP)
		for route in ["canonical","approved"]:
			entry.carrier.visible=route=="canonical"; carrier.visible=route=="approved"
			await process_frame; await process_frame; await RenderingServer.frame_post_draw
			var image_path:=out.path_join(action+"-"+route+".png"); assert(viewport.get_texture().get_image().save_png(image_path)==OK); captures.append(image_path)
	exhibit._add_fish(world,"scalloped_hammerhead",2.5,legacy)
	var cached: Dictionary=exhibit.fish[1]; cached.carrier.hide()
	assert(not exhibit.loading_metrics[0].reused_appearance and exhibit.loading_metrics[1].reused_appearance)
	assert(cached.profile==profile and cached.model.has_meta("final_asset_scalloped_receipt") and cached.model.scale==entry.model.scale and cached.model.position==entry.model.position)
	compare_static(cached.model,model,false)
	for action in ["Swim","Turn","Ascend","Dive"]:
		pose(cached,action,1.17); pose(direct,action,1.17); assert(delta(cached,direct)==0.0)
	var transitions:=0
	for action in ["Swim","Turn","Ascend","Dive"]:
		entry.controller.set_action(action,false); ctrl.set_action(action,false)
		for i in 90:
			entry.controller.step(1.0/60); ctrl.step(1.0/60); max_delta=maxf(max_delta,delta(entry,direct)); transitions+=1
	assert(max_delta==0.0)
	var report: Dictionary={"ok":true,"kind":"scalloped_final_canonical_install_check","fresh_process":true,"actual_entry":"VolumeFishExhibit._add_fish","approved_model_sha256":BINDER.MODEL_SHA,"model_sha256":FileAccess.get_sha256(path),"static":static_result,"scale":entry.model.scale.x,"static_build_calls":0,"static_builders_disabled":true,"first_load_material_overrides":0,"cached_effective_materials_identical":true,"first_and_cache_load_equal":true,"controller_comparisons":comparisons,"transition_steps":transitions,"maximum_actual_bone_pose_delta":max_delta,"captures":captures,"motion_sha256":FileAccess.get_sha256(BINDER.MOTION_PATH),"runtime_dependencies":preload("res://scripts/aquarium/FishRuntimeData.gd")._digests.duplicate(),"scope":"Current formal entry and cached entry vs independent raw approved GLB, all mesh arrays and embedded pixels exact; physical490 and opacity reports separate."}
	FileAccess.open(out.path_join("canonical-load.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear(); exhibit.fish.clear(); exhibit.free(); entry.clear(); direct.clear(); viewport.queue_free(); await process_frame; await process_frame
	print("SCALLOPED_CANONICAL_INSTALL_OK"); quit()
