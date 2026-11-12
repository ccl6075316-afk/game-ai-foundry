extends SceneTree
var rows:Array=[]
func _initialize():
    create_timer(60).timeout.connect(func():quit(2))
    call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var path=args[0];var output=args[1];var hide_fins=args.size()<3 or args[2]=="body"
    DirAccess.make_dir_recursive_absolute(output)
    var viewport=SubViewport.new();viewport.size=Vector2i(1536,960);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewport.mesh_lod_threshold=0.;root.add_child(viewport)
    var world=Node3D.new();viewport.add_child(world)
    var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("1e2832");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.7;world.add_child(env)
    var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.7;world.add_child(light)
    var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.keep_aspect=Camera3D.KEEP_WIDTH;camera.near=.001;camera.far=15;camera.current=true;world.add_child(camera)
    var doc=GLTFDocument.new();var state=GLTFState.new();assert(doc.append_from_file(path,state)==OK);var model=doc.generate_scene(state);world.add_child(model)
    var meshes=model.find_children("*","MeshInstance3D",true,false)
    var bounds:AABB=meshes[0].global_transform*meshes[0].get_aabb()
    for mesh in meshes:
        bounds=bounds.merge(mesh.global_transform*mesh.get_aabb())
        if hide_fins and str(mesh.name)!="Closed_body" and not str(mesh.name).begins_with("Eye_support"):mesh.hide()
        for surface in mesh.mesh.get_surface_count():
            var material=mesh.get_active_material(surface).duplicate();material.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST;mesh.set_surface_override_material(surface,material)
    var center=bounds.get_center();var whole_size=bounds.size.x*1.18
    var sk=model.find_children("*","Skeleton3D",true,false)[0];sk.reset_bone_poses()
    var jaw=load("res://scripts/aquarium/FoundryJawMotion.gd").new();jaw.configure(sk,14.0);jaw.apply(0.0)
    var views=[{"name":"side","dir":Vector3(0,0,1)},{"name":"reverse","dir":Vector3(0,0,-1)},{"name":"top","dir":Vector3(0,1,0)},{"name":"bottom","dir":Vector3(0,-1,0)},{"name":"oblique","dir":Vector3(.6,.35,1)},{"name":"dorsal-oblique","dir":Vector3(.15,1,.6)},{"name":"front","dir":Vector3(1,.1,0)},{"name":"rear","dir":Vector3(-1,.1,0)}]
    for view in views:
        camera.size=whole_size;camera.position=center+view.dir.normalized()*3;camera.look_at(center,Vector3.UP if absf(view.dir.y)<.99 else Vector3(0,0,-1));await capture(viewport,output,view.name)
    for amount in [0.,.5,1.]:
        jaw.apply(amount);sk.force_update_all_bone_transforms();var focus=Vector3(.43,0,0);camera.size=.21;camera.position=focus+Vector3(.6,.2,1).normalized()*3;camera.look_at(focus,Vector3.UP);await capture(viewport,output,"mouth-%d"%int(amount*100))
    FileAccess.open(output.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify({"ok":true,"model":path,"model_sha256":FileAccess.get_sha256(path),"hide_fins":hide_fins,"captures":rows,"scope":"static GPU and independent mouth preview, not full SOP"},"  "));quit()
func capture(viewport,output,label):
    await process_frame;await process_frame;await RenderingServer.frame_post_draw
    var path=output.path_join(label+".png");assert(viewport.get_texture().get_image().save_png(path)==OK);rows.append({"name":label,"path":path,"sha256":FileAccess.get_sha256(path)})
