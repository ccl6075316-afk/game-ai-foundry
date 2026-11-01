extends SceneTree
## Read-only local GLB capture. Static preview, not motion/whole-fish acceptance.
func _initialize() -> void:
	call_deferred("capture")

func capture() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	assert(args.size()==1 and DisplayServer.get_name()!="headless")
	var cfg: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var output: String = cfg.output.replace("\\","/")
	assert(output.contains("/experiments/") and output.is_absolute_path())
	assert(FileAccess.get_sha256(cfg.model)==cfg.model_sha256)
	assert(not DirAccess.dir_exists_absolute(output),"Fresh capture directory required")
	DirAccess.make_dir_recursive_absolute(output)
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	assert(document.append_from_file(cfg.model,state)==OK)
	var model: Node3D = document.generate_scene(state)
	assert(model!=null)
	var viewport := SubViewport.new()
	viewport.size=Vector2i(900,600); viewport.own_world_3d=true
	viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
	viewport.mesh_lod_threshold=0.0
	root.add_child(viewport)
	var world := Node3D.new(); viewport.add_child(world)
	var carrier := Node3D.new(); world.add_child(carrier); carrier.add_child(model)
	carrier.scale=Vector3.ONE*float(cfg.model_scale)
	var meshes := model.find_children("*","MeshInstance3D",true,false)
	var triangles: int=0
	for node in meshes:
		var mesh := node as MeshInstance3D
		assert(mesh.mesh!=null and mesh.material_override==null)
		for surface in mesh.mesh.get_surface_count():
			var arrays: Array=mesh.mesh.surface_get_arrays(surface)
			triangles+=(arrays[Mesh.ARRAY_INDEX] as PackedInt32Array).size()/3
			var material := mesh.get_active_material(surface) as StandardMaterial3D
			assert(material!=null)
			if material.albedo_texture!=null:assert(material.texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST)
	assert(triangles==int(cfg.triangles) and triangles<=int(cfg.hard_triangles))
	var environment := Environment.new()
	environment.background_mode=Environment.BG_COLOR; environment.background_color=Color(.12,.16,.2)
	environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color=Color.WHITE; environment.ambient_light_energy=.7
	var world_environment := WorldEnvironment.new(); world_environment.environment=environment; world.add_child(world_environment)
	var light := DirectionalLight3D.new(); light.rotation_degrees=Vector3(-45,-35,0); light.light_energy=.8; world.add_child(light)
	var camera := Camera3D.new(); camera.projection=Camera3D.PROJECTION_ORTHOGONAL
	camera.keep_aspect=Camera3D.KEEP_WIDTH; camera.near=.001; camera.far=5
	world.add_child(camera); camera.current=true
	var clay := StandardMaterial3D.new(); clay.albedo_color=Color(.55,.58,.6); clay.roughness=1
	var rows: Array=[]
	for view in cfg.views:
		var point := Vector3(view.focus[0],view.focus[1],view.focus[2])*float(cfg.model_scale)
		var direction := Vector3(view.direction[0],view.direction[1],view.direction[2]).normalized()
		camera.position=point+direction*.5; camera.size=float(view.width_m)
		camera.look_at(point,Vector3.FORWARD if absf(direction.y)>.99 else Vector3.UP)
		for gray in [false,true]:
			for node in meshes:(node as MeshInstance3D).material_override=clay if gray else null
			for frame in 3:await process_frame; RenderingServer.force_draw(false)
			var path: String=output.path_join(str(view.name)+("-clay.png"if gray else"-texture.png"))
			assert(viewport.get_texture().get_image().save_png(path)==OK)
			rows.append({"path":path,"sha256":FileAccess.get_sha256(path)})
	assert(FileAccess.get_sha256(cfg.model)==cfg.model_sha256)
	var report := {"ok":true,"kind":"direct_static_fish_glb_review","model":cfg.model,"model_sha256":cfg.model_sha256,"config_sha256":FileAccess.get_sha256(args[0]),"script_sha256":FileAccess.get_sha256(get_script().resource_path),"direct_GLTFDocument":true,"runtime_static_build_calls":0,"triangles":triangles,"engine":Engine.get_version_info().string,"captures":rows,"scope":"Fresh actual GPU, rest pose only. No motion/root/body-coverage/SOP or visual approval."}
	var file := FileAccess.open(output.path_join("capture.validation.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t")); file.close()
	print(JSON.stringify({"ok":true,"triangles":triangles,"captures":rows.size()})); quit()
