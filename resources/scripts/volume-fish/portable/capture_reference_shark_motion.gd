extends SceneTree
## Actual standalone GLB/native/controller GPU poses. No static model edits.
var spec: Dictionary
var output: String
func _initialize() -> void:
    var args=OS.get_cmdline_user_args();assert(args.size()==2)
    spec=JSON.parse_string(FileAccess.get_file_as_string(args[0])).items[0];output=args[1]
    assert(output.contains("/experiments/") and FileAccess.get_sha256(spec.model)==spec.model_sha256)
    DirAccess.make_dir_recursive_absolute(output);call_deferred("run")
func run() -> void:
    root.size=Vector2i(900,620);root.position=Vector2i(-3000,-3000)
    var viewport:=SubViewport.new();viewport.size=Vector2i(900,620);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;root.add_child(viewport)
    var world:=Node3D.new();viewport.add_child(world)
    var environment:=WorldEnvironment.new();environment.environment=Environment.new();environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color("25343c");environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=.65;world.add_child(environment)
    var light:=DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-35,0);light.light_energy=.65;world.add_child(light)
    var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_file(spec.model,state)==OK)
    var carrier:=Node3D.new();world.add_child(carrier);var model=document.generate_scene(state);carrier.add_child(model)
    var skeleton: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]
    var player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
    player.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL;player.stop();skeleton.reset_bone_poses()
    var profile: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(spec.motion_profile));assert(FileAccess.get_sha256(spec.motion_profile)==spec.motion_profile_sha256)
    model.scale=Vector3.ONE*float(profile.real_length_cm)/100./float(spec.length_native)
    var camera:=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.current=true;camera.near=.001;camera.far=4;camera.keep_aspect=Camera3D.KEEP_WIDTH;world.add_child(camera)
    var captures: Array=[];var controller=load(spec.motion_runtime).new()
    assert(FileAccess.get_sha256(spec.motion_runtime)==spec.motion_runtime_sha256)
    var configured: Dictionary=controller.configure(carrier,model,player,skeleton,profile);assert(configured.ok,str(configured))
    var cases: Array=[{"name":"rest","mode":"rest","time":0.}]
    for phase in 12:cases.append({"name":"native-%02d"%phase,"mode":"native","time":player.get_animation(profile.base_clip).length*float(phase)/12.})
    for action in ["Swim","Turn","Ascend","Dive"]:cases.append({"name":action,"mode":action,"time":3.5})
    cases.append({"name":"wide-fast","mode":"Turn","time":7.65625,"controls":{"body_amplitude":2.5,"body_frequency":3.,"fin_amplitude":2.5,"fin_frequency":3.}})
    for item in cases:
        if item.mode=="rest":player.stop();skeleton.reset_bone_poses()
        elif item.mode=="native":player.play(profile.base_clip);player.seek(item.time,true);player.advance(0.)
        else:
            controller.set_motion_controls(item.get("controls",{"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.}),true)
            controller.set_action(item.mode,true);controller.step(0.);controller.seek(item.time)
        skeleton.force_update_all_bone_transforms()
        # Camera isolation only: strip carrier path transform after the real
        # controller has posed the skeleton; static geometry/material untouched.
        carrier.transform=Transform3D.IDENTITY
        var regions: Array=[{"name":"whole","at":[0.,0.,0.],"size":.68}]
        if item.mode=="rest":regions.append_array([{"name":"mouth","at":[.232,.001,0.],"size":.19},{"name":"head","at":[.24,.007,0.],"size":.30},{"name":"tail","at":[-.20,.006,0.],"size":.27}])
        for region in regions:
            var target:=Vector3(region.at[0],region.at[1],region.at[2]);camera.size=region.size
            var views: Array=[{"name":"side","dir":Vector3(0,0,1)},{"name":"top","dir":Vector3(0,1,.001)},{"name":"oblique","dir":Vector3(.7,.4,1)}]
            if item.mode=="rest":views.append_array([{"name":"bottom","dir":Vector3(0,-1,.001)},{"name":"front","dir":Vector3(1,0,0)},{"name":"other-side","dir":Vector3(0,0,-1)}])
            if item.mode=="native" and region.name=="whole":views=views.slice(0,2)
            for view in views:
                camera.position=target+view.dir.normalized();camera.look_at(target,Vector3.UP if absf(view.dir.y)<.99 else Vector3(0,0,-1))
                for frame in 3:await process_frame;RenderingServer.force_draw(true)
                var path=output.path_join(item.name+"-"+region.name+"-"+view.name+".png");assert(viewport.get_texture().get_image().save_png(path)==OK)
                captures.append({"path":path,"sha256":FileAccess.get_sha256(path),"case":item,"region":region.name,"view":view.name})
    var report={"ok":true,"model_sha256":spec.model_sha256,"motion_profile_sha256":spec.motion_profile_sha256,"controller_sha256":spec.motion_runtime_sha256,"script_sha256":FileAccess.get_sha256(get_script().resource_path),"bones":skeleton.get_bone_count(),"captures":captures,"actual_gpu":true,"rigged":true,"runtime_static_build_calls":0,"scope":"12 native phases, four actual controller actions and one extreme; carrier path removed for fixed local camera only. Visual review remains separate.","formal_acceptance":false}
    FileAccess.open(output.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n")
    print("REFERENCE_SHARK_MOTION_CAPTURE_OK ",captures.size());quit()
