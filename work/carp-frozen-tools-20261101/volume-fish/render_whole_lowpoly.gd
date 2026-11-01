extends SceneTree
var output=""
var entries=[];var cameras=[];var factory
func _initialize():
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    assert(output.is_absolute_path() and output.simplify_path().begins_with(ProjectSettings.globalize_path("res://../plans/reviews/").simplify_path()))
    call_deferred("run")
func run():
    root.size=Vector2i(2048,600);root.title="Whole-fish low-poly study · original / 992 / 2991 / 6000"
    var layout=HBoxContainer.new();layout.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.add_child(layout)
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    var transport=load("E:/game-ai-foundry/resources/scripts/volume-fish/LowPolyFishTransport.gd").new()
    var report={"production_changed":false,"accepted":false,"candidates":[],"images":[],"pose_probes":[]}
    var budgets=[0,1000,3000,6000]
    for budget in budgets:
        var column=VBoxContainer.new();column.size_flags_horizontal=Control.SIZE_EXPAND_FILL;layout.add_child(column)
        var label=Label.new();label.text="ORIGINAL · 212,360 tris" if budget==0 else "TARGET "+str(budget)+" · EXPERIMENT";column.add_child(label)
        var container=SubViewportContainer.new();container.stretch=true;container.size_flags_vertical=Control.SIZE_EXPAND_FILL;column.add_child(container)
        var viewport=SubViewport.new();viewport.own_world_3d=true;viewport.size=Vector2i(512,570);container.add_child(viewport)
        var world=Node3D.new();viewport.add_child(world)
        var env=WorldEnvironment.new();env.environment=Environment.new();env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("183b4a");env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.environment.ambient_light_color=Color.WHITE;env.environment.ambient_light_energy=.8;world.add_child(env)
        var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-35,-30,0);world.add_child(light)
        var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=100;camera.current=true;world.add_child(camera);cameras.append(camera)
        factory._add_fish(world,"zander",float(factory.profiles.zander.real_length_cm)/100.,factory.profiles.zander)
        var entry=factory.fish[-1];entries.append(entry);entry.player.pause();entry.carrier.transform=Transform3D.IDENTITY
        if budget>0:
            var json_path=output.path_join("low-"+str(budget)+".json")
            var data=JSON.parse_string(FileAccess.get_file_as_string(json_path))
            transport.apply(entry.model,data)
            label.text=str(data.actual_triangles)+" tris · EXPERIMENT"
            for node in entry.model.find_children("*","Node",true,false):node.owner=entry.model
            var packed=PackedScene.new();assert(packed.pack(entry.model)==OK)
            var scene_path=output.path_join("fish-"+str(budget)+".scn")
            assert(ResourceSaver.save(packed,scene_path,ResourceSaver.FLAG_COMPRESS)==OK)
            report.candidates.append({"budget":budget,"actual_triangles":data.actual_triangles,"scene":scene_path,"sha256":FileAccess.get_sha256(scene_path),"geometry_sha256":FileAccess.get_sha256(json_path)})
    for shot in ["whole","head-side","head-front","head-oblique","Turn","Ascend","Dive"]:
        var head=entries[0].model.find_child("Source_lips139",true,false) as MeshInstance3D
        var box=head.global_transform*head.get_aabb()
        for i in entries.size():
            var entry=entries[i]
            if shot in ["Turn","Ascend","Dive"]:
                entry.controller.set_action(shot,true);entry.controller.step(0);entry.controller.seek(1.25)
                entry.carrier.transform=Transform3D.IDENTITY
                var finite=true
                for bi in entry.skeleton.get_bone_count():finite=finite and entry.skeleton.get_bone_global_pose(bi).origin.is_finite()
                report.pose_probes.append({"budget":budgets[i],"action":shot,"time":1.25,"finite_bone_origins":finite})
            var direction=Vector3(0,0,1);var center=Vector3.ZERO;var size=float(entry.length_m)*1.35
            if shot.begins_with("head"):
                center=box.get_center();size=box.size.length()*1.6
                if shot=="head-front":direction=Vector3(1,0,0)
                if shot=="head-oblique":direction=Vector3(1,.35,1).normalized()
            cameras[i].size=size;cameras[i].position=center+direction*2;cameras[i].look_at(center)
        for frame in 8:await process_frame
        await RenderingServer.frame_post_draw
        var path=output.path_join(shot+".png");assert(root.get_texture().get_image().save_png(path)==OK)
        report.images.append({"path":path,"sha256":FileAccess.get_sha256(path)})
    var f=FileAccess.open(output.path_join("render.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report,"  "));f.close()
    layout.queue_free();await process_frame;factory.free();preload("res://scripts/aquarium/FishAppearanceCache.gd").clear();quit()
