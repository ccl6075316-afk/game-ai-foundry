extends Node3D
## Deterministic original/low-poly comparison and isolated instancing trial.
var camera: Camera3D
var stage: Node3D
var hud: Label
var directory := ""
var auto_review := false
var catalogs: Array=[]
var shader_rows: Dictionary={}
var materials: Array=[]
var native_players: Array=[]
var clock := 0.0
var paused := false
var mode := "shader"
var review_running := false

func _ready() -> void:
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    Engine.max_fps=0
    RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(),true)
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--capture-dir="):directory=arg.trim_prefix("--capture-dir=");auto_review=true
    var env := WorldEnvironment.new();var e := Environment.new()
    e.background_mode=Environment.BG_COLOR;e.background_color=Color("1b2b31");e.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;e.ambient_light_color=Color.WHITE;e.ambient_light_energy=1
    env.environment=e;add_child(env)
    camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=1.0;add_child(camera)
    stage=Node3D.new();add_child(stage)
    var layer := CanvasLayer.new();add_child(layer);hud=Label.new();hud.position=Vector2(20,12);hud.add_theme_font_size_override("font_size",21);layer.add_child(hud)
    var plant_catalog := "res://assets/aquascape-v5/catalog.json"
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--plant-catalog="):plant_catalog=arg.trim_prefix("--plant-catalog=")
    for path in [plant_catalog,"res://assets/aquascape-decor-v1/catalog.json"]:
        catalogs.append_array(JSON.parse_string(FileAccess.get_file_as_string(path)).assets)
    if "--plants-only" in OS.get_cmdline_user_args():catalogs=catalogs.filter(func(r):return r.get("animated",false))
    var metadata_files: Dictionary={}
    for plant in catalogs.filter(func(r):return r.get("animated",false)):
        var path: String=plant.get("shader_metadata","res://assets/aquascape-v9/shader-plants/shader-plants.validation.json")
        if metadata_files.has(path):continue
        metadata_files[path]=true
        for row in JSON.parse_string(FileAccess.get_file_as_string(path)).outputs:shader_rows[row.id]=row
    if auto_review:call_deferred("_review")
    else:_stress(1000,"shader")

func _process(delta: float) -> void:
    if not paused:clock+=delta
    for mat in materials:mat.set_shader_parameter("clock",clock)

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo or review_running:return
    match event.keycode:
        KEY_1:_stress(100,"shader")
        KEY_2:_stress(1000,"shader")
        KEY_3:_stress(1000,"static")
        KEY_4:_stress(1000,"skeletal")
        KEY_SPACE:paused=not paused
        KEY_R:_stress(1000,"shader")

func _clear() -> void:
    for child in stage.get_children():child.free()
    materials.clear();native_players.clear()

func _bounds(model: Node3D) -> AABB:
    var result := AABB();var first := true
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        var box: AABB=model.global_transform.affine_inverse()*mesh.global_transform*mesh.get_aabb()
        result=box if first else result.merge(box);first=false
    return result

func _paint(model: Node3D,row: Dictionary) -> void:
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        for s in mesh.mesh.get_surface_count():
            if row.get("animated",false):
                var mat: StandardMaterial3D=mesh.get_active_material(s).duplicate();mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;mat.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
                mesh.set_surface_override_material(s,mat)
            else:
                var mat := ShaderMaterial.new();mat.shader=load("res://scripts/aquarium/DecorThreeViewArtwork.gdshader")
                for view in ["front","right","top"]:mat.set_shader_parameter(view+"_art",load(row.material_dir+"/"+row.id+"-"+view+".png"))
                var b: Dictionary=row.projection_bounds;mat.set_shader_parameter("projection_size",Vector3(b.width,b.height,b.depth));mat.set_shader_parameter("radial_jar",row.id=="terracotta_jar");mat.set_shader_parameter("right_art_on_rear",row.id=="coconut_shelter")
                mesh.set_surface_override_material(s,mat)

func _capture(name: String) -> String:
    for i in 4:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var path := directory+"/"+name+".png";get_viewport().get_texture().get_image().save_png(path);return path

func _pair(row: Dictionary,gray: bool=false) -> void:
    _clear()
    for side in 2:
        var path: String=row.pre_budget_model if side==0 else row.model
        var model: Node3D=(load(path) as PackedScene).instantiate();stage.add_child(model)
        _paint(model,row)
        if gray:
            var mat := StandardMaterial3D.new();mat.albedo_color=Color("a1b2b7");mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
            for m in model.find_children("*","MeshInstance3D",true,false):m.material_override=mat
        var box := _bounds(model);var scale_value: float=.78/maxf(box.size.x,maxf(box.size.y,box.size.z));model.scale=Vector3.ONE*scale_value
        model.position=Vector3(-.55 if side==0 else .55,0,0)-box.get_center()*scale_value
    camera.size=1.12;camera.position=Vector3(0,.32,2.4);camera.look_at(Vector3.ZERO)
    hud.text=row.id+"   ORIGINAL (left) / LOW-POLY (right)"+("   silhouette" if gray else "   original artwork")
    if row.pre_budget_model==row.model:hud.text=row.id+"   BUDGETED FROM FIRST BUILD / CURRENT EXPORT"

func _shader_material(id: String,enabled: bool,texture: Texture2D) -> ShaderMaterial:
    var data: Dictionary=shader_rows[id];var mat := ShaderMaterial.new();mat.shader=load("res://scripts/aquarium/PlantSway.gdshader")
    var a: Array=data.anchor_min;var b: Array=data.anchor_size
    mat.set_shader_parameter("anchor_min",Vector3(a[0],a[1],a[2]));mat.set_shader_parameter("anchor_size",Vector3(b[0],b[1],b[2]));mat.set_shader_parameter("artwork",texture);mat.set_shader_parameter("enabled",1.0 if enabled else 0.0)
    materials.append(mat);return mat

func _stress(count: int,kind: String) -> void:
    _clear();mode=kind;clock=0;paused=false
    var plants: Array=catalogs.filter(func(r):return r.get("animated",false))
    if kind=="skeletal":plants=plants.filter(func(r):return r.get("deformation","")!="shader")
    if plants.is_empty():hud.text="No skeletal assets in this selection";return
    var cols: int=ceili(sqrt(count));var spacing := .11
    var shader_meshes: Dictionary={}
    if kind!="skeletal":
        for row in plants:
            var scene: Node3D=(load(row.get("shader_model","res://assets/aquascape-v9/shader-plants/"+row.id+".glb")) as PackedScene).instantiate()
            var meshes: Array=scene.find_children("*","MeshInstance3D",true,false);shader_meshes[row.id]=meshes[0].mesh;scene.free()
        # One batch per species for this isolated fixed-camera trial.
        for species in plants.size():
            var row: Dictionary=plants[species];var mm := MultiMesh.new();mm.transform_format=MultiMesh.TRANSFORM_3D;mm.use_custom_data=true;mm.use_colors=true;mm.mesh=shader_meshes[row.id]
            var indices: Array=[]
            for i in count:
                if i%plants.size()==species:indices.append(i)
            mm.instance_count=indices.size()
            for j in indices.size():
                var i: int=indices[j];var plant_size: float=_bounds_from_mesh(mm.mesh).size.length();var scale_value: float=.16/maxf(plant_size,.001)
                var basis := Basis(Vector3.UP,float(i)*2.399).scaled(Vector3.ONE*scale_value)
                mm.set_instance_transform(j,Transform3D(basis,Vector3((i%cols-cols*.5)*spacing,0,(i/cols-cols*.5)*spacing)))
                mm.set_instance_custom_data(j,Color(fposmod(i*.618,1),fposmod(i*.372,1),0,0))
                mm.set_instance_color(j,Color.WHITE)
            var native_material: StandardMaterial3D=mm.mesh.surface_get_material(0)
            var node := MultiMeshInstance3D.new();node.multimesh=mm
            if kind=="static":
                var paint: StandardMaterial3D=native_material.duplicate();paint.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST;paint.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;node.material_override=paint
            else:node.material_override=_shader_material(row.id,true,native_material.albedo_texture)
            stage.add_child(node)
    else:
        for i in count:
            var row: Dictionary=plants[i%plants.size()];var model: Node3D=(load(row.model) as PackedScene).instantiate();stage.add_child(model);_paint(model,row)
            var scale_value: float=.16/maxf(_bounds(model).size.length(),.001);model.scale=Vector3.ONE*scale_value;model.rotation.y=float(i)*2.399;model.position=Vector3((i%cols-cols*.5)*spacing,0,(i/cols-cols*.5)*spacing)
            for player in model.find_children("*","AnimationPlayer",true,false):
                for clip in player.get_animation_list():
                    if String(clip).ends_with("WaterSway"):player.play(clip);player.seek(fposmod(i*.137,10));native_players.append(player)
    camera.size=maxf(.8,cols*spacing);camera.position=Vector3(0,cols*spacing*.85,cols*spacing*.85);camera.look_at(Vector3(0,.04,0))
    hud.text="PLANTS  %d   /   %s\n1:100 shader  2:1000 shader  3:1000 static  4:1000 skeletal  SPACE:pause" % [count,kind]

func _bounds_from_mesh(mesh: Mesh) -> AABB:return mesh.get_aabb()

func _measure(count: int,kind: String) -> Dictionary:
    if kind=="skeletal" and catalogs.filter(func(r):return r.get("animated",false) and r.get("deformation","")!="shader").is_empty():
        return {"kind":kind,"count":0,"skipped":true,"reason":"Selected species use shaders; no skeletal version was produced."}
    _stress(count,kind)
    for i in 60:await get_tree().process_frame
    var wall: Array=[];var gpu: Array=[];var cpu: Array=[];var calls: Array=[];var primitive_counts: Array=[];var last := Time.get_ticks_usec()
    for i in 120:
        await get_tree().process_frame
        var now := Time.get_ticks_usec();wall.append((now-last)/1000.0);last=now
        gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid()));cpu.append(RenderingServer.viewport_get_measured_render_time_cpu(get_viewport().get_viewport_rid()))
        calls.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME));primitive_counts.append(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
    wall.sort();gpu.sort();cpu.sort();calls.sort();primitive_counts.sort()
    var screenshot: String=await _capture("stress-%s-%d" % [kind,count])
    var weighted_triangles := 0
    var plants: Array=catalogs.filter(func(r):return r.get("animated",false))
    if kind=="skeletal":plants=plants.filter(func(r):return r.get("deformation","")!="shader")
    for i in count:weighted_triangles+=int(shader_rows[plants[i%plants.size()].id].triangles)
    return {"kind":kind,"count":count,"submitted_instance_triangles":weighted_triangles,"wall_frame_ms_median":wall[60],"wall_frame_ms_p95":wall[114],"viewport_gpu_ms_median":gpu[60],"viewport_cpu_ms_median":cpu[60],"draw_calls_median":calls[60],"engine_primitive_counter_median":primitive_counts[60],"godot_tracked_static_memory_bytes":OS.get_static_memory_usage(),"renderer_tracked_video_memory_bytes":Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED),"native_players":native_players.size(),"screenshot":screenshot}

func _shader_closeup(id: String) -> void:
    _clear();clock=0;paused=true
    var row: Dictionary=catalogs.filter(func(r):return r.id==id)[0]
    var model: Node3D=(load(row.get("shader_model","res://assets/aquascape-v9/shader-plants/"+id+".glb")) as PackedScene).instantiate();stage.add_child(model)
    var meshes: Array=model.find_children("*","MeshInstance3D",true,false);var mesh: MeshInstance3D=meshes[0];var paint: StandardMaterial3D=mesh.mesh.surface_get_material(0)
    mesh.material_override=_shader_material(id,true,paint.albedo_texture)
    var box := _bounds(model);var scale_value: float=.78/maxf(box.size.x,maxf(box.size.y,box.size.z));model.scale=Vector3.ONE*scale_value;model.position=-box.get_center()*scale_value
    camera.size=1.02;camera.position=Vector3(0,.32,2.4);camera.look_at(Vector3.ZERO);hud.text=id+" / shader sway / native-resolution atlas / fixed roots"

func _review() -> void:
    review_running=true;DirAccess.make_dir_recursive_absolute(directory)
    var captures: Array=[]
    for row in catalogs:
        _pair(row);captures.append(await _capture("compare-"+row.id))
    # Different viewing directions are needed to assess closed leaf shells and apertures.
    for id in ["java_fern","vallisneria","pale_limestone","shipwreck","terracotta_jar","iron_anchor"]:
        var matched: Array=catalogs.filter(func(r):return r.id==id)
        if matched.is_empty():continue
        var row: Dictionary=matched[0];_pair(row)
        camera.position=Vector3(0,2.4,.08);camera.look_at(Vector3.ZERO,Vector3.FORWARD);captures.append(await _capture("top-"+id))
        camera.position=Vector3(0,.28,-2.4);camera.look_at(Vector3.ZERO);captures.append(await _capture("rear-"+id))
        _pair(row,true);captures.append(await _capture("gray-"+id))
    var samples: Array=[]
    for kind in ["static","shader","skeletal"]:samples.append(await _measure(1000,kind))
    var closeup_ids: Array=[]
    for id in ["anubias","vallisneria","aponogeton","bacopa_round","cabomba","hornwort"]:
        if not catalogs.filter(func(r):return r.id==id).is_empty():closeup_ids.append(id)
    for id in closeup_ids:
        _shader_closeup(id)
        for phase in [0.0,2.5,5.0,7.5,10.0]:
            clock=phase;captures.append(await _capture("closeup-"+id+"-"+str(phase)))
    _shader_closeup("vallisneria" if closeup_ids.has("vallisneria") else closeup_ids[0])
    DirAccess.make_dir_recursive_absolute(directory+"/motion-frames")
    for frame in 120:
        clock=frame/12.0
        for i in 2:await get_tree().process_frame
        await RenderingServer.frame_post_draw
        var image := get_viewport().get_texture().get_image();image.resize(640,360,Image.INTERPOLATE_NEAREST);image.save_png(directory+"/motion-frames/%04d.png" % frame)
    _stress(1000,"shader");paused=true;clock=0
    for phase in [0.0,2.5,5.0,7.5]:
        clock=phase;captures.append(await _capture("shader-phase-"+str(phase)))
    var report := {"schema_version":1,"command":"aquascape.budget-native-review","ok":true,"status":"done","next_action":"human_review","outputs":captures,"performance":samples,"gpu":RenderingServer.get_video_adapter_name(),"renderer":RenderingServer.get_current_rendering_method(),"resolution":[get_viewport().size.x,get_viewport().size.y],"vsync":false,"failures":[],"visual_review":"pending","user_acceptance":"pending","limitations":["Isolated plants at one fixed camera; no fish, water or full-tank performance claim.","CPU/GPU timings and video-memory availability depend on renderer/driver; zero GPU time is unavailable, not zero cost.","Godot tracked memory is not total process resident memory; sequential cases are not clean-process peak-memory comparisons.","Engine primitive counters may exclude MultiMesh instance multipliers; use submitted_instance_triangles for the asset budget.","Skeletal/static comparisons also differ in batching and atlas layout; this is a comparison of complete runtime paths, not a pure shader instruction benchmark."]}
    var file := FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();get_tree().quit()
