extends SceneTree
var entries: Array=[]
var gray:=false
var load_plan: Dictionary
var report: Dictionary={"models":[],"captures":[]}
func _load(route: String, container: SubViewportContainer) -> Dictionary:
	var view := SubViewport.new();view.size=Vector2i(900,620);view.own_world_3d=true;view.render_target_update_mode=SubViewport.UPDATE_ALWAYS;container.add_child(view)
	var world := Node3D.new();view.add_child(world)
	var environment := WorldEnvironment.new();environment.environment=Environment.new()
	environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color("25343c")
	environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=.65;world.add_child(environment)
	var light := DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.65;world.add_child(light)
	var camera := Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=10;camera.current=true;world.add_child(camera)
	var path: String = load_plan.model
	var doc := GLTFDocument.new();var state := GLTFState.new();assert(doc.append_from_file(path,state)==OK)
	var model := doc.generate_scene(state);assert(model!=null)
	var carrier := Node3D.new();world.add_child(carrier);carrier.add_child(model);model.scale=Vector3.ONE*float(load_plan.model_scale)
	var skeleton: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]
	var player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
	var count := 0;var materials := [];var names := []
	for mesh in model.find_children("*","MeshInstance3D",true,false):
		names.append(str(mesh.name))
		for surface in mesh.mesh.get_surface_count():
			count+=(mesh.mesh.surface_get_arrays(surface)[Mesh.ARRAY_INDEX] as PackedInt32Array).size()/3
			var mat: StandardMaterial3D=mesh.mesh.surface_get_material(surface)
			assert(mat!=null)
			assert(mat.texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST)
			materials.append({"name":mat.resource_name,"texture":mat.albedo_texture!=null,"alpha":mat.transparency})
	var controller=load(load_plan.motion_runtime).new()
	var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(str(load_plan.motion_profile)))
	var configured: Dictionary=controller.configure(carrier,model,player,skeleton,profile)
	assert(configured.ok,JSON.stringify(configured))
	report.models.append({"route":route,"model_sha256":FileAccess.get_sha256(path),"triangles":count,"meshes":names,"materials":materials,"motion_configure":configured,"animations":player.get_animation_list()})
	return {"route":route,"model":model,"carrier":carrier,"view":view,"camera":camera,"controller":controller,"skeleton":skeleton,"player":player}

func _set_gray(value: bool) -> void:
	gray=value
	var mat := StandardMaterial3D.new();mat.albedo_color=Color(.65,.68,.7);mat.roughness=1;mat.metallic_specular=0
	for entry in entries:
		for mesh in entry.model.find_children("*","MeshInstance3D",true,false):mesh.material_override=mat if gray else null

func _view_image(entry: Dictionary) -> Image:
	var original: Image=entry.view.get_texture().get_image()
	var width := mini(900,original.get_width());var height := mini(620,original.get_height())
	return original.get_region(Rect2i((original.get_width()-width)/2,(original.get_height()-height)/2,width,height))

