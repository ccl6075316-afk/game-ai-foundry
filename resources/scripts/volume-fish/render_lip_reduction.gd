extends SceneTree
## Cold-load a diagnostic candidate beside the unchanged production factory.
var output := ""
var factory
var cameras: Array[Camera3D]=[]
var entries: Array=[]
var views: Array[SubViewport]=[]
var bindings:Dictionary={}

func bind_tree(path:String,extensions:Array) -> void:
    var dir=DirAccess.open(path)
    if dir==null:return
    for name in dir.get_files():
        if name.get_extension() in extensions:
            var file=path.path_join(name);bindings[file]=FileAccess.get_sha256(file)
    for name in dir.get_directories():bind_tree(path.path_join(name),extensions)

func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    assert(output.is_absolute_path() and output.simplify_path().begins_with(ProjectSettings.globalize_path("res://../plans/reviews/").simplify_path()))
    call_deferred("run")

func run() -> void:
    bind_tree("res://scripts/aquarium",["gd","gdshader","gdshaderinc"])
    bind_tree("res://assets/models/fish/motion",["json"])
    for file in [get_script().resource_path,"res://assets/models/fish/zander.glb"]:bindings[file]=FileAccess.get_sha256(file)
    root.size=Vector2i(1536,768);root.title="Zander lips · original / experimental 75% reduction"
    var layout=HBoxContainer.new();layout.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);root.add_child(layout)
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    var path=output.path_join("lips-25.res")
    var candidate=load(path) as ArrayMesh;assert(candidate!=null)
    var config=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles.zander
    for file in [config.body.path,config.lips.path]:bindings[file]=FileAccess.get_sha256(file)
    var baseline=load(config.lips.path) as ArrayMesh
    var receipt={"fresh_process":true,"candidate_sha256":FileAccess.get_sha256(path),"candidate_surface_count":candidate.get_surface_count(),"checks":[],"images":[],"scope":"Diagnostic A/B, not final asset cold-load/finalization gate. Production factory still assembles the original body/fins/eyes.","accepted":false}
    for si in candidate.get_surface_count():
        var a=candidate.surface_get_arrays(si);var n=a[Mesh.ARRAY_VERTEX].size()
        assert(a[Mesh.ARRAY_BONES].size()==n*4 and a[Mesh.ARRAY_WEIGHTS].size()==n*4)
        var max_error=0.0;var baseline_error=0.0
        var original=baseline.surface_get_arrays(si)
        for vi in original[Mesh.ARRAY_VERTEX].size():
            var total=0.0
            for j in 4:total+=original[Mesh.ARRAY_WEIGHTS][vi*4+j]
            baseline_error=maxf(baseline_error,absf(total-1.0))
        for vi in n:
            var total=0.0
            for j in 4:
                assert(a[Mesh.ARRAY_WEIGHTS][vi*4+j]>=0)
                total+=a[Mesh.ARRAY_WEIGHTS][vi*4+j]
            max_error=maxf(max_error,absf(total-1.0))
        receipt.checks.append({"surface":si,"vertices":n,"triangles":a[Mesh.ARRAY_INDEX].size()/3,"max_stored_weight_sum_error":max_error,"baseline_max_stored_weight_sum_error":baseline_error,"normalization_not_finally_accepted":true})
    for i in 2:
        var column=VBoxContainer.new();column.size_flags_horizontal=Control.SIZE_EXPAND_FILL;layout.add_child(column)
        var label=Label.new();label.text="ORIGINAL · lips 138,720 triangles" if i==0 else "CANDIDATE · lips 34,680 triangles · not accepted";column.add_child(label)
        var container=SubViewportContainer.new();container.stretch=true;container.size_flags_vertical=Control.SIZE_EXPAND_FILL;column.add_child(container)
        var viewport=SubViewport.new();viewport.size=Vector2i(768,730);viewport.own_world_3d=true;container.add_child(viewport);views.append(viewport)
        var world=Node3D.new();viewport.add_child(world)
        var environment=WorldEnvironment.new();environment.environment=Environment.new()
        environment.environment.background_mode=Environment.BG_COLOR;environment.environment.background_color=Color("183b4a")
        environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;environment.environment.ambient_light_color=Color.WHITE;environment.environment.ambient_light_energy=.8;world.add_child(environment)
        var light=DirectionalLight3D.new();light.rotation_degrees=Vector3(-35,-30,0);world.add_child(light)
        var camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.001;camera.far=100;camera.current=true;world.add_child(camera);cameras.append(camera)
        var profile:Dictionary=factory.profiles.zander
        factory._add_fish(world,"zander",float(profile.real_length_cm)/100.,profile)
        var entry:Dictionary=factory.fish[-1];entries.append(entry)
        entry.player.pause();entry.carrier.transform=Transform3D.IDENTITY
        if i==1:
            var lip=entry.model.find_child("Source_lips139",true,false) as MeshInstance3D
            lip.mesh=candidate
    for shot in ["whole","side","front","oblique","moving_oblique"]:
        var baseline_lip=entries[0].model.find_child("Source_lips139",true,false) as MeshInstance3D
        var baseline_box=baseline_lip.global_transform*baseline_lip.get_aabb()
        for i in 2:
            var entry=entries[i]
            if shot=="moving_oblique":
                entry.controller.seek(.75)
                entry.controller.step(1.0/60.0)
                entry.carrier.transform=Transform3D.IDENTITY
            var lip=entry.model.find_child("Source_lips139",true,false) as MeshInstance3D
            var box=baseline_box
            var center=box.get_center()
            var direction=Vector3(0,0,1)
            if shot=="whole":center=Vector3.ZERO
            if shot=="front":direction=Vector3(1,0,0)
            if shot in ["oblique","moving_oblique"]:direction=Vector3(1,.35,1).normalized()
            var camera=cameras[i]
            camera.size=float(entry.length_m)*1.35 if shot=="whole" else box.size.length()*1.6
            camera.position=center+direction*2.0
            camera.look_at(center)
        for frame in 8:await process_frame
        await RenderingServer.frame_post_draw
        var image_path=output.path_join(shot+".png")
        assert(root.get_texture().get_image().save_png(image_path)==OK)
        receipt.images.append({"path":image_path,"sha256":FileAccess.get_sha256(image_path)})
    var changed=[]
    for file in bindings:
        if FileAccess.get_sha256(file)!=bindings[file]:changed.append(file)
    receipt.inputs=bindings;receipt.input_changes=changed;assert(changed.is_empty())
    var f=FileAccess.open(output.path_join("cold-load-render.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify(receipt,"  "));f.close()
    factory.free();preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    quit()
