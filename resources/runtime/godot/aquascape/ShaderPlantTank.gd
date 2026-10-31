extends Control
## A small planted tank for inspecting procedural water sway, not a stress grid.
var viewport: SubViewport
var world: Node3D
var plants: Node3D
var camera: Camera3D
var entries: Array=[]
var shader_rows: Dictionary={}
var paints: Array=[]
var water: ShaderMaterial
var selected := 0
var clock := 0.0
var paused := false
var strength := 1.0
var flow_speed := 1.65
var sway_amplitude := .18
var clumps := 3
var yaw := .16
var pitch := .16
var zoom := 1.02
var dragging := false
var caption: Label
var pause_button: Button
var count_button: Button
var strength_label: Label
var rest_bounds_inside := true
var species_scroll: ScrollContainer
var species_buttons: Array=[]

func _ready() -> void:
    DisplayServer.window_set_title("水草鱼缸 · Shader 水流摆动 · 可交互预览")
    get_window().content_scale_size=Vector2i(1440,900)
    Engine.max_fps=60
    var catalog_path := "res://assets/aquascape-v5/catalog.json"
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--plant-catalog="):catalog_path=arg.trim_prefix("--plant-catalog=")
    entries=JSON.parse_string(FileAccess.get_file_as_string(catalog_path)).assets.filter(func(r):return r.get("animated",false))
    var metadata_files: Dictionary={}
    for plant in entries:
        var path: String=plant.get("shader_metadata","res://assets/aquascape-v9/shader-plants/shader-plants.validation.json")
        if metadata_files.has(path):continue
        metadata_files[path]=true
        for row in JSON.parse_string(FileAccess.get_file_as_string(path)).outputs:shader_rows[row.id]=row
    viewport=SubViewport.new();viewport.size=Vector2i(1150,720);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;add_child(viewport)
    world=Node3D.new();viewport.add_child(world)
    var screen := TextureRect.new();screen.texture=viewport.get_texture();screen.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST;screen.expand_mode=TextureRect.EXPAND_IGNORE_SIZE
    screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);screen.offset_top=90;screen.offset_right=-280;screen.offset_bottom=-75;screen.gui_input.connect(_view_input);add_child(screen)
    var env := WorldEnvironment.new();var e := Environment.new();e.background_mode=Environment.BG_COLOR;e.background_color=Color("081c26");e.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;e.ambient_light_color=Color("c9e2dc");e.ambient_light_energy=.8;env.environment=e;world.add_child(env)
    var light := DirectionalLight3D.new();light.rotation_degrees=Vector3(-55,-25,0);light.light_energy=.75;world.add_child(light)
    camera=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.01;camera.far=15;world.add_child(camera)
    _tank();plants=Node3D.new();world.add_child(plants);_ui()
    for i in entries.size():
        if entries[i].id=="vallisneria":selected=i
    for i in entries.size():
        if entries[i].id=="bacopa_round":selected=i
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--plant="):
            for i in entries.size():
                if entries[i].id==arg.trim_prefix("--plant="):selected=i
    _select(selected);_camera()
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--tank-capture-dir="):call_deferred("_capture",arg.trim_prefix("--tank-capture-dir="))
        if arg.begins_with("--motion-check-dir="):call_deferred("_motion_check",arg.trim_prefix("--motion-check-dir="))

func _solid(color: Color) -> StandardMaterial3D:
    var m := StandardMaterial3D.new();m.albedo_color=color;m.roughness=.9;m.metallic_specular=0
    return m

func _box(at: Vector3,size: Vector3,material: Material) -> MeshInstance3D:
    var node := MeshInstance3D.new();var mesh := BoxMesh.new();mesh.size=size;node.mesh=mesh;node.position=at;node.material_override=material;world.add_child(node);return node

func _tank() -> void:
    _box(Vector3(0,-.045,0),Vector3(1.25,.10,.65),_solid(Color("142e35")))
    var sand := _solid(Color("e0d3ac"));sand.albedo_texture=load("res://assets/aquascape-sand-v1/fine-sand.png");sand.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST;sand.uv1_scale=Vector3(3,2,1)
    _box(Vector3(0,.015,0),Vector3(1.2,.04,.60),sand)
    _box(Vector3(0,.325,-.305),Vector3(1.21,.65,.014),_solid(Color("17404a")))
    var rim := _solid(Color("507a80"))
    for y in [0.0,.65]:
        for z in [-.30,.30]:_box(Vector3(0,y,z),Vector3(1.22,.014,.014),rim)
        for x in [-.60,.60]:_box(Vector3(x,y,0),Vector3(.014,.014,.61),rim)
    for x in [-.60,.60]:
        for z in [-.30,.30]:_box(Vector3(x,.325,z),Vector3(.012,.65,.012),rim)
    var glass := _solid(Color(.24,.61,.68,.055));glass.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA;glass.cull_mode=BaseMaterial3D.CULL_DISABLED;glass.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    _box(Vector3(0,.325,.302),Vector3(1.2,.65,.004),glass)
    for x in [-.602,.602]:_box(Vector3(x,.325,0),Vector3(.004,.65,.60),glass)
    var plane := MeshInstance3D.new();var mesh := PlaneMesh.new();mesh.size=Vector2(1.19,.59);plane.mesh=mesh;plane.position.y=.58
    water=ShaderMaterial.new();water.shader=load("res://shaders/aquarium_lab_surface.gdshader");water.set_shader_parameter("strength",.17);water.set_shader_parameter("pixel_size",.018);plane.material_override=water;world.add_child(plane)

func _label(parent: Node,text: String,at: Vector2,size: int=20) -> Label:
    var label := Label.new();label.text=text;label.position=at;label.add_theme_font_size_override("font_size",size);label.modulate=Color("d6e8dd");parent.add_child(label);return label

func _ui() -> void:
    var back := ColorRect.new();back.color=Color("0c242d");back.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);back.mouse_filter=Control.MOUSE_FILTER_IGNORE;add_child(back);move_child(back,0)
    _label(self,"水草在缸里 · Shader 水流摆动",Vector2(24,16),27)
    caption=_label(self,"",Vector2(25,56),19)
    _label(self,"选择水草",Vector2(1180,101),23)
    species_scroll=ScrollContainer.new();species_scroll.position=Vector2(1175,143);species_scroll.size=Vector2(255,425);add_child(species_scroll)
    var list := VBoxContainer.new();list.add_theme_constant_override("separation",6);species_scroll.add_child(list)
    for i in entries.size():
        var button := Button.new();button.text=entries[i].name_zh+(" · 新增" if entries[i].get("deformation","")=="shader" else "");button.custom_minimum_size=Vector2(235,37);button.focus_mode=Control.FOCUS_NONE;button.toggle_mode=true;button.pressed.connect(func():_select(i));list.add_child(button);species_buttons.append(button)
    pause_button=Button.new();pause_button.text="暂停摆动";pause_button.position=Vector2(1175,590);pause_button.size=Vector2(115,40);pause_button.focus_mode=Control.FOCUS_NONE;pause_button.pressed.connect(_pause);add_child(pause_button)
    count_button=Button.new();count_button.text="看单丛";count_button.position=Vector2(1300,590);count_button.size=Vector2(120,40);count_button.focus_mode=Control.FOCUS_NONE;count_button.pressed.connect(func():clumps=1 if clumps==3 else 3;count_button.text="看三丛" if clumps==1 else "看单丛";_select(selected));add_child(count_button)
    strength_label=_label(self,"水流强度：1.0 倍",Vector2(1175,650),19)
    var slider := HSlider.new();slider.min_value=0;slider.max_value=1.5;slider.step=.05;slider.value=1;slider.position=Vector2(1175,688);slider.size=Vector2(240,28);slider.focus_mode=Control.FOCUS_NONE
    slider.value_changed.connect(func(v):strength=v;strength_label.text="水流强度：%.2f 倍" % v;_set_strength());add_child(slider)
    _label(self,"拖动转动鱼缸 · 滚轮拉近看叶片 · ← → 换水草 · 空格暂停 · R 回到正面",Vector2(25,842),20)

func _select(index: int) -> void:
    selected=posmod(index,entries.size());clock=0;rest_bounds_inside=true
    for child in plants.get_children():child.free()
    paints.clear()
    var row: Dictionary=entries[selected];var data: Dictionary=shader_rows[row.id]
    var original: Node3D=(load(row.get("shader_model","res://assets/aquascape-v9/shader-plants/"+row.id+".glb")) as PackedScene).instantiate()
    var meshes: Array=original.find_children("*","MeshInstance3D",true,false);var mesh: Mesh=meshes[0].mesh;var native: StandardMaterial3D=mesh.surface_get_material(0);original.free()
    var paint := ShaderMaterial.new();paint.shader=load("res://scripts/aquarium/PlantSway.gdshader");var low: Array=data.anchor_min;var size_data: Array=data.anchor_size
    paint.set_shader_parameter("anchor_min",Vector3(low[0],low[1],low[2]));paint.set_shader_parameter("anchor_size",Vector3(size_data[0],size_data[1],size_data[2]));paint.set_shader_parameter("artwork",native.albedo_texture);paint.set_shader_parameter("enabled",1.0);paints.append(paint);_set_strength()
    var box := mesh.get_aabb();var factor: float=minf(.47/maxf(box.size.y,.001),minf(.78/maxf(box.size.x,.001),.48/maxf(box.size.z,.001)))
    var mm := MultiMesh.new();mm.transform_format=MultiMesh.TRANSFORM_3D;mm.use_custom_data=true;mm.use_colors=true;mm.mesh=mesh;mm.instance_count=clumps
    for i in clumps:
        var scale_value: float=factor if i==0 else factor*.52
        var x := 0.0 if i==0 else (-.32 if i==1 else .32);var z := .04 if i==0 else -.10
        var basis := Basis.IDENTITY.scaled(Vector3.ONE*scale_value)
        # Alpha carriers may have invisible corners below the real root.
        # Place the authored root, rather than lifting it by those empty corners.
        var base_y: float=.025 if row.get("deformation","")=="shader" else .025-box.position.y*scale_value
        var transform_value := Transform3D(basis,Vector3(x-box.get_center().x*scale_value,base_y,z-box.get_center().z*scale_value))
        var occupied: AABB=transform_value*box
        rest_bounds_inside=rest_bounds_inside and occupied.position.x>=-.60 and occupied.end.x<=.60 and occupied.position.z>=-.30 and occupied.end.z<=.30 and occupied.end.y<.58
        mm.set_instance_transform(i,transform_value)
        mm.set_instance_custom_data(i,Color(i*.31,.5,0,0))
        mm.set_instance_color(i,Color.WHITE)
    var node := MultiMeshInstance3D.new();node.multimesh=mm;node.material_override=paint;plants.add_child(node)
    for i in species_buttons.size():species_buttons[i].button_pressed=i==selected
    species_scroll.call_deferred("ensure_control_visible",species_buttons[selected])
    _refresh_caption()

func _refresh_caption() -> void:
    caption.text="%s   ·   整丛 %d 三角面   ·   水下 %d 丛   ·   %s" % [entries[selected].name_zh,int(shader_rows[entries[selected].id].triangles),clumps,"已暂停" if paused else "水流摆动中"]

func _set_strength() -> void:
    for paint in paints:paint.set_shader_parameter("amplitude",sway_amplitude*strength)

func _pause() -> void:
    paused=not paused;pause_button.text="继续摆动" if paused else "暂停摆动"
    _refresh_caption()

func _camera() -> void:
    var target := Vector3(0,.30,0);camera.size=zoom;camera.position=target+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*2;camera.look_at(target)

func _process(delta: float) -> void:
    if not paused:clock+=delta*flow_speed
    for paint in paints:paint.set_shader_parameter("clock",clock)
    if water:water.set_shader_parameter("clock",clock)

func _view_input(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        if event.button_index==MOUSE_BUTTON_LEFT:dragging=event.pressed
        if event.pressed and event.button_index==MOUSE_BUTTON_WHEEL_UP:zoom=maxf(.48,zoom*.9)
        if event.pressed and event.button_index==MOUSE_BUTTON_WHEEL_DOWN:zoom=minf(2.1,zoom*1.1)
    if event is InputEventMouseMotion and dragging:yaw-=event.relative.x*.006;pitch=clampf(pitch+event.relative.y*.005,-.08,1.2)
    _camera()

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo:return
    match event.keycode:
        KEY_LEFT:_select(selected-1)
        KEY_RIGHT:_select(selected+1)
        KEY_SPACE:_pause()
        KEY_R:yaw=.16;pitch=.16;zoom=1.02;_camera()

func _capture(directory: String) -> void:
    DirAccess.make_dir_recursive_absolute(directory);paused=true
    var outputs: Array=[];var all_inside := true
    for i in entries.size():_select(i);all_inside=all_inside and rest_bounds_inside
    for entry in entries:
        var id: String=entry.id
        for i in entries.size():
            if entries[i].id==id:_select(i);break
        for phase in [0.0,2.5]:
            clock=phase
            for i in 5:await get_tree().process_frame
            await RenderingServer.frame_post_draw
            var path: String=directory+"/"+id+"-"+str(phase)+".png";get_viewport().get_texture().get_image().save_png(path);outputs.append(path)
    var report := {"schema_version":1,"command":"aquascape.shader-plant-tank","ok":all_inside,"status":"done" if all_inside else "failed","next_action":"human_review" if all_inside else "fix_input","outputs":outputs,"failures":[] if all_inside else ["Rest plant bounds exceed tank"],"summary":{"species":entries.size(),"clumps":3,"all_species_rest_bounds_inside_tank":all_inside,"native_skeletons":plants.find_children("*","Skeleton3D",true,false).size(),"animation_players":plants.find_children("*","AnimationPlayer",true,false).size(),"deformation":"PlantSway.gdshader","water_height_m":.58,"tank_size_m":[1.2,.65,.6]},"user_acceptance":"pending","limitations":["Rest bounds and prior shader-root/loop checks supplement visual review; no continuous plant/glass collision simulation."]}
    var file := FileAccess.open(directory+"/tank.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();get_tree().quit()

func _motion_check(directory: String) -> void:
    DirAccess.make_dir_recursive_absolute(directory)
    for i in entries.size():
        if entries[i].id=="vallisneria":_select(i);break
    paused=false;_refresh_caption()
    for i in 5:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var start_clock := clock
    var start_uniform: Variant=paints[0].get_shader_parameter("clock")
    viewport.get_texture().get_image().save_png(directory+"/playing-start.png")
    await get_tree().create_timer(2.0).timeout
    await RenderingServer.frame_post_draw
    viewport.get_texture().get_image().save_png(directory+"/playing-later.png")
    var advanced: bool=clock>start_clock+2.5
    var later_uniform: Variant=paints[0].get_shader_parameter("clock")
    _pause()
    for i in 4:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var stopped_clock := clock
    viewport.get_texture().get_image().save_png(directory+"/paused-start.png")
    await get_tree().create_timer(.5).timeout
    await RenderingServer.frame_post_draw
    viewport.get_texture().get_image().save_png(directory+"/paused-later.png")
    var pause_ok: bool=clock==stopped_clock
    _pause();await get_tree().create_timer(.5).timeout
    var resume_ok: bool=clock>stopped_clock+.5
    for i in 4:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    get_viewport().get_texture().get_image().save_png(directory+"/interactive-view.png")
    var okay: bool=advanced and pause_ok and resume_ok
    var report := {"schema_version":1,"command":"aquascape.live-shader-motion","ok":okay,"status":"done" if okay else "failed","next_action":"human_review" if okay else "fix_input","outputs":[directory+"/playing-start.png",directory+"/playing-later.png",directory+"/paused-start.png",directory+"/paused-later.png",directory+"/interactive-view.png"],"checks":{"clock_advances_in_real_time":advanced,"pause_freezes_clock":pause_ok,"resume_advances_clock":resume_ok},"parameters":{"amplitude":sway_amplitude,"flow_speed":flow_speed,"default_cycle_seconds":10.0/flow_speed,"strength_max":1.5,"start_uniform":start_uniform,"later_uniform":later_uniform,"enabled":paints[0].get_shader_parameter("enabled")},"failures":[] if okay else ["Live playback/pause/resume failed"],"user_acceptance":"pending"}
    var file := FileAccess.open(directory+"/motion.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();get_tree().quit(0 if okay else 1)
