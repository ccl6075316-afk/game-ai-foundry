extends SceneTree
func _initialize():
    create_timer(30.).timeout.connect(func():quit(2))
    call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();assert(args.size()==1)
    var out=str(args[0]);assert(out.is_absolute_path() and out.contains("/work/clean-pixel-rainbow-trout-20261110"))
    var path="res://assets/models/fish/rainbow_trout.glb"
    var doc=GLTFDocument.new();var state=GLTFState.new();assert(doc.append_from_file(path,state)==OK)
    var viewport=SubViewport.new();viewport.size=Vector2i(1512,1040);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewport.mesh_lod_threshold=0.;root.add_child(viewport)
    var world=Node3D.new();viewport.add_child(world)
    var model=doc.generate_scene(state);world.add_child(model)
    var first=true;var bounds=AABB()
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        var box=mesh.global_transform*mesh.mesh.get_aabb()
        bounds=box if first else bounds.merge(box);first=false
    assert(not first and bounds.size.x>0.)
    var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("25343c");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.65;world.add_child(env)
    var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.65;world.add_child(light)
    var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=maxf(bounds.size.y*1.35,bounds.size.x*1040./1512.*1.14);camera.near=.001;camera.far=50.;world.add_child(camera)
    var center=bounds.get_center();camera.position=center+Vector3(0.,0.,bounds.size.x*2.);camera.look_at(center)
    for i in 4:await process_frame
    await RenderingServer.frame_post_draw
    var image=viewport.get_texture().get_image();assert(image.save_png(out.path_join("current-side.png"))==OK)
    var receipt={"ok":true,"species":"rainbow_trout","model_sha256":FileAccess.get_sha256(path),"image_sha256":FileAccess.get_sha256(out.path_join("current-side.png")),"scope":"Current canonical static GLB rest pose; no material or geometry changes, reference for style concept only.","camera_size":camera.size,"bounds":{"position":[bounds.position.x,bounds.position.y,bounds.position.z],"size":[bounds.size.x,bounds.size.y,bounds.size.z]}}
    var f=FileAccess.open(out.path_join("capture.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(receipt,"  "));f.close();quit()
