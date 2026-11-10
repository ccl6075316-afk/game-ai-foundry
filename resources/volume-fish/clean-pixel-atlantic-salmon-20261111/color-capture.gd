extends SceneTree
func _initialize():
    root.hide();create_timer(45.).timeout.connect(func():quit(2));call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var out=args[0];var plan=JSON.parse_string(FileAccess.get_file_as_string(out.path_join("plan.json")));assert(FileAccess.get_sha256(plan.model)==plan.model_sha256)
    var viewport=SubViewport.new();viewport.size=Vector2i(1512,1040);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewport.mesh_lod_threshold=0.;root.add_child(viewport)
    var world=Node3D.new();viewport.add_child(world)
    var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("25343c");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.65;world.add_child(env)
    var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.65;world.add_child(light)
    var doc=GLTFDocument.new();var state=GLTFState.new();assert(doc.append_from_file(plan.model,state)==OK);var model=doc.generate_scene(state);world.add_child(model);model.scale=Vector3.ONE*float(plan.scale)
    for player in model.find_children("*","AnimationPlayer",true,false):player.stop()
    for skeleton in model.find_children("*","Skeleton3D",true,false):skeleton.reset_bone_poses()
    var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.keep_aspect=Camera3D.KEEP_WIDTH;camera.size=float(plan.projection.width)*float(plan.scale);camera.near=.001;camera.far=10.;world.add_child(camera);var center=Vector3(plan.projection.cx,plan.projection.cy,0.)*float(plan.scale);camera.position=center+Vector3(0,0,2.);camera.look_at(center)
    var saved=[];var materials=[]
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        for surface in mesh.mesh.get_surface_count():
            var mat=mesh.get_active_material(surface);saved.append([mat,mat.shading_mode]);materials.append({"roughness":mat.roughness,"metallic":mat.metallic,"specular":mat.metallic_specular,"emission":mat.emission_enabled,"albedo":str(mat.albedo_color)})
    for label in ["albedo","reference-light","viewer-light"]:
        for item in saved:item[0].shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED if label=="albedo" else item[1]
        light.light_energy=1.1 if label=="viewer-light" else .65
        for i in 4:await process_frame
        await RenderingServer.frame_post_draw
        assert(viewport.get_texture().get_image().save_png(out.path_join(label+".png"))==OK)
    FileAccess.open(out.path_join("diagnosis.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"ok":true,"model_sha256":plan.model_sha256,"ambient_energy":.65,"reference_light":.65,"viewer_light":1.1,"materials":materials,"scope":"Same model, camera, pose and ambient; only diagnostic light or unshaded pass differs. No saved asset changes."},"  "));quit()
