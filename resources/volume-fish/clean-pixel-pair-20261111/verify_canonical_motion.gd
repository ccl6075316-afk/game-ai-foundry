extends SceneTree
## Fresh canonical and prepared-cache loading against the accepted raw GLB.
const EXHIBIT = preload("res://scripts/aquarium/VolumeFishExhibit.gd")
const FINAL = preload("res://scripts/aquarium/FinalizedElevenFish20261105.gd")
var species: String
var out: String
var entry: Dictionary
var direct: Dictionary
var exhibit

func _initialize() -> void:
	create_timer(40.).timeout.connect(func():push_error("Canonical release check timed out");quit(2))
	call_deferred("run")
func pose(item: Dictionary, action: String, t: float) -> void:
	assert(item.controller.set_action(action,true));item.controller.step(0.0);item.controller.seek(t)
func delta() -> float:
	var result:=0.0
	for i in entry.skeleton.get_bone_count():
		var j: int=direct.skeleton.find_bone(entry.skeleton.get_bone_name(i));assert(j>=0)
		var a: Transform3D=entry.skeleton.get_bone_global_pose(i)
		var b: Transform3D=direct.skeleton.get_bone_global_pose(j)
		result=maxf(result,a.origin.distance_to(b.origin))
		for axis in 3:result=maxf(result,a.basis[axis].distance_to(b.basis[axis]))
	return result
func parity(a: Node3D,b: Node3D, _cached: bool=false) -> void:
	var x = a.find_children("*", "MeshInstance3D", true, false)
	var y = b.find_children("*", "MeshInstance3D", true, false)
	assert(x.size() == y.size())
	for i in x.size():
		assert(x[i].name == y[i].name and x[i].mesh.get_surface_count() == y[i].mesh.get_surface_count())
		for surface in x[i].mesh.get_surface_count():
			assert(var_to_bytes(x[i].mesh.surface_get_arrays(surface)) == var_to_bytes(y[i].mesh.surface_get_arrays(surface)))
			var xm = x[i].get_active_material(surface)
			var ym = y[i].get_active_material(surface)
			assert(xm.texture_filter == BaseMaterial3D.TEXTURE_FILTER_NEAREST)
			for property in ["transparency", "alpha_scissor_threshold", "texture_filter", "cull_mode", "albedo_color", "roughness", "metallic", "emission", "emission_enabled"]:
				assert(xm.get(property) == ym.get(property))
			for property in ["albedo_texture", "emission_texture"]:
				var xt = xm.get(property)
				var yt = ym.get(property)
				assert((xt == null) == (yt == null))
				if xt != null:
					assert(xt.get_image().get_data() == yt.get_image().get_data())
func run() -> void:
	var args:=OS.get_cmdline_user_args();assert(args.size()==2);out=args[0];species=args[1]
	assert(DirAccess.dir_exists_absolute(out) and out.contains("/work/clean-pixel-pair-release-20261111/"))
	var row: Dictionary=FINAL.new().table()[species]
	var route: String="res://assets/models/fish/"+species+".glb"
	assert(FileAccess.get_sha256(route)==row.model_sha256)
	var cfg: Dictionary=FINAL.new().motion_profile(species)
	var viewport:=SubViewport.new();viewport.size=Vector2i(1000,720);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewport.mesh_lod_threshold=0.0;root.add_child(viewport)
	var world:=Node3D.new();viewport.add_child(world)
	var env:=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("25343c");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.65;world.add_child(env)
	var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.65;world.add_child(light)
	var camera:=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=float(row.real_length_cm)/100.*1.25;camera.near=.001;camera.far=50;world.add_child(camera)
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear();exhibit=EXHIBIT.new()
	exhibit._add_fish(world,species,float(row.real_length_cm)/100.,cfg);entry=exhibit.fish[0]
	assert(not exhibit.loading_metrics[0].reused_appearance and entry.model.has_meta("final_eleven_receipt"))
	assert(is_equal_approx(entry.model.scale.x,float(row.review_model_scale)))
	var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_file(route,state)==OK)
	var model: Node3D=document.generate_scene(state);model.scene_file_path=route
	var carrier:=Node3D.new();world.add_child(carrier);carrier.add_child(model);model.scale=entry.model.scale;model.position=entry.model.position
	FINAL.new()._bind_nearest(model.find_children("*", "MeshInstance3D", true, false))
	var sk: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]
	var player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
	var ctrl=load(EXHIBIT.MOTION_SCRIPT).new();assert(ctrl.configure(carrier,model,player,sk,cfg).ok)
	direct={"model":model,"carrier":carrier,"skeleton":sk,"player":player,"controller":ctrl};parity(entry.model,model)
	var max_delta:=0.0;var phases:=0;var controls: Array=[[0.,0.,0.,0.],[1.,1.,1.,1.],[2.5,1.,2.5,1.],[1.,3.,1.,3.],[1.3,.7,2.,1.4]]
	for values in controls:
		var settings: Dictionary={"body_amplitude":values[0],"body_frequency":values[1],"fin_amplitude":values[2],"fin_frequency":values[3]}
		entry.controller.set_motion_controls(settings,true);ctrl.set_motion_controls(settings,true)
		for action in ["Swim","Turn","Ascend","Dive"]:
			for i in 24:
				for item in [entry,direct]:pose(item,action,float(i)/24.*float(cfg.period_seconds))
				max_delta=maxf(max_delta,delta());assert(entry.controller.snapshot().inside_envelope);phases+=1
	assert(max_delta<.000002)
	var transitions:=0
	for action in ["Turn","Ascend","Dive","Swim"]:
		for item in [entry,direct]:assert(item.controller.set_action(action,false))
		for i in 90:
			for item in [entry,direct]:item.controller.step(1./60.)
			max_delta=maxf(max_delta,delta());transitions+=1
		assert(entry.controller.snapshot().action==action and entry.controller.snapshot().inside_envelope)
	assert(max_delta<.000002)
	var captures:=[]
	for item in [entry,direct]:item.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
	for action in ["Swim","Turn","Ascend","Dive"]:
		for item in [entry,direct]:pose(item,action,1.17)
		carrier.transform = entry.carrier.transform
		camera.position=entry.carrier.global_position+Vector3(.18,.10,.65);camera.look_at(entry.carrier.global_position,Vector3.UP)
		for name in ["canonical","approved"]:
			entry.carrier.visible=name=="canonical";carrier.visible=name=="approved"
			await process_frame;await process_frame;await RenderingServer.frame_post_draw
			var path: String=out.path_join(action+"-"+name+".png");assert(viewport.get_texture().get_image().save_png(path)==OK);captures.append(path)
	exhibit._add_fish(world,species,float(row.real_length_cm)/100.,cfg);assert(exhibit.loading_metrics[1].reused_appearance);parity(exhibit.fish[1].model,model,true);exhibit.fish[1].carrier.hide()
	var lods := 0
	for mesh in entry.model.find_children("*", "MeshInstance3D", true, false):
		for surface in mesh.mesh.get("_surfaces"):
			lods += surface.get("lods", []).size()
	assert(lods==0)
	var deps: Dictionary={}
	for path in ["res://scripts/aquarium/VolumeFishExhibit.gd","res://scripts/aquarium/FishSurfaceOwnership.gd","res://scripts/aquarium/FinalizedElevenFish20261105.gd",FINAL.TABLE,"res://scripts/aquarium/FoundryFishMotion.gd",row.motion_profile]:deps[ProjectSettings.globalize_path(path)]=FileAccess.get_sha256(path)
	var report: Dictionary={"ok":true,"kind":"eleven_fish_canonical_motion_and_render_comparison","species":species,"model_sha256":FileAccess.get_sha256(route),"fresh_process":true,"actual_entry":"VolumeFishExhibit._add_fish","first_and_cache_load_equal":true,"all_static_arrays_and_RGBA_equal":true,"static_builders_disabled":true,"runtime_static_build_calls":0,"cached_material_scope":"Existing per-instance duplicated surface handle; same pixels and material properties verified, no shape/color patch.","serialized_lod_entries":lods,"triangles":row.triangles,"meshes":row.mesh_count,"surfaces":row.surface_count,"model_scale":entry.model.scale.x,"controller_comparisons":phases,"transition_comparisons":transitions,"maximum_actual_skeleton_delta":max_delta,"captures":captures,"dependencies":deps,"scope":"Canonical/cache entry against independent accepted raw GLB; original same-byte full490 and body/GPU reports separately retained. Pixel pairs compared independently."}
	FileAccess.open(out.path_join("canonical-motion.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
	preload("res://scripts/aquarium/FishAppearanceCache.gd").clear();exhibit.fish.clear();exhibit.free();entry.clear();direct.clear();viewport.queue_free();await process_frame;print("ELEVEN_CANONICAL_MOTION_OK ",species);quit()
