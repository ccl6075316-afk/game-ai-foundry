extends SceneTree
var output=""
func _initialize():
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    assert(output.is_absolute_path() and output.simplify_path().begins_with(ProjectSettings.globalize_path("res://../plans/reviews/").simplify_path()))
    call_deferred("run")
func run():
    var path=output.path_join("fish-3000.scn")
    var packed=load(path) as PackedScene;assert(packed!=null)
    var carrier=Node3D.new();root.add_child(carrier)
    var model=packed.instantiate() as Node3D;carrier.add_child(model)
    var total=0;var vertices=0;var surfaces=0;var errors=0;var lookups=0
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        if not mesh.visible:continue
        for si in mesh.mesh.get_surface_count():
            var a=mesh.mesh.surface_get_arrays(si);total+=a[Mesh.ARRAY_INDEX].size()/3;vertices+=a[Mesh.ARRAY_VERTEX].size();surfaces+=1
            var material=mesh.get_active_material(si)
            if material is ShaderMaterial:
                for key in ["rest114_uvs","eye_uv_lookup"]:
                    var tex=material.get_shader_parameter(key)
                    if not tex is Texture2D:continue
                    lookups+=1;var image=tex.get_image()
                    for i in a[Mesh.ARRAY_VERTEX].size():
                        var uv=a[Mesh.ARRAY_TEX_UV][i];var value=image.get_pixel(i%image.get_width(),i/image.get_width())
                        if absf(uv.x-value.r)>1e-6 or absf(uv.y-value.g)>1e-6 or value.a<.5:errors+=1
    assert(total==2991 and errors==0)
    var profiles=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();profiles._load_profiles()
    var controller=load("res://scripts/aquarium/FoundryFishMotion.gd").new()
    var player=model.find_children("*","AnimationPlayer",true,false)[0]
    var skeleton=model.find_children("*","Skeleton3D",true,false)[0]
    var configured=controller.configure(carrier,model,player,skeleton,profiles.profiles.zander,Vector3.ZERO);assert(configured.ok)
    var pose_checks=[]
    for action in ["Swim","Turn","Ascend","Dive"]:
        assert(controller.set_action(action,true));controller.step(0);controller.seek(0)
        var before=[];var after=[]
        for bi in skeleton.get_bone_count():before.append(skeleton.get_bone_pose(bi))
        controller.seek(1.25)
        for bi in skeleton.get_bone_count():after.append(skeleton.get_bone_pose(bi))
        pose_checks.append({"action":action,"bone_pose_changed":var_to_bytes(before)!=var_to_bytes(after),"scope":"Two sampled times only; no complete action/contact gate."})
    controller.set_action("Swim",true);controller.step(0);controller.seek(1.25);carrier.transform=Transform3D.IDENTITY
    var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("183b4a");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.8;root.add_child(env)
    var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-35,-30,0);root.add_child(light)
    var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=.75;camera.position=Vector3(0,0,3);root.add_child(camera);camera.look_at(Vector3.ZERO);camera.current=true
    root.size=Vector2i(1024,600)
    for i in 8:await process_frame
    await RenderingServer.frame_post_draw
    root.get_texture().get_image().save_png(output.path_join("cold-3000.png"))
    var report={"fresh_process":true,"species":"zander","visible_triangles":total,"vertices":vertices,"surfaces":surfaces,"uv_lookup_tables_checked":lookups,"uv_lookup_errors":errors,"scene_sha256":FileAccess.get_sha256(path),"dependencies":ResourceLoader.get_dependencies(path),"builder_calls":0,"pose_checks":pose_checks,"accepted":false,"scope":"Standalone candidate cold-load and actual arrays/UV lookup correspondence; not a finalization or full fish gate."}
    var f=FileAccess.open(output.path_join("cold.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report,"  "));f.close()
    carrier.queue_free();await process_frame;profiles.free();quit()
