extends Control
## Independent review scene. No mutation of existing aquarium, fish or save data.
const KIT = preload("res://scripts/aquarium/AquascapeKit.gd")
var kit = KIT.new()
var viewport: SubViewport
var world: Node3D
var camera: Camera3D
var scenery: Node3D
var fish_stock
var yaw := 0.30
var pitch := 0.35
var view_size := 1.70
var target := Vector3(0,.30,0)
var dragging := false
var mode := 0
var mode_label: Label
var report := {}
var export_errors: Array=[]
var export_requested := false
var reload_checks: Array=[]

func _ready() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg=="--export-assets" or arg.begins_with("--capture-dir="):export_requested=true
    DisplayServer.window_set_title("潮汐馆 · 缸底置景试作")
    viewport=SubViewport.new()
    viewport.size=Vector2i(1440,900)
    viewport.own_world_3d=true
    viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    add_child(viewport)
    world=Node3D.new()
    viewport.add_child(world)
    var screen := TextureRect.new()
    screen.texture=viewport.get_texture()
    screen.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
    screen.expand_mode=TextureRect.EXPAND_IGNORE_SIZE
    screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    screen.gui_input.connect(_input_view)
    add_child(screen)
    var env := WorldEnvironment.new()
    env.environment=Environment.new()
    env.environment.background_mode=Environment.BG_COLOR
    env.environment.background_color=Color("122d32")
    env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    env.environment.ambient_light_color=Color("d2e0d6")
    env.environment.ambient_light_energy=.63
    env.environment.tonemap_mode=Environment.TONE_MAPPER_LINEAR
    world.add_child(env)
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees=Vector3(-52,-32,0)
    sun.light_color=Color("ffecd4")
    sun.light_energy=.72
    sun.shadow_enabled=true
    sun.directional_shadow_max_distance=8.0
    sun.shadow_bias=.015
    world.add_child(sun)
    camera=Camera3D.new()
    camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    camera.near=.01
    camera.far=20.0
    world.add_child(camera)
    camera.current=true
    _build()
    _ui()
    _camera()
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--capture-dir="):
            call_deferred("_capture",arg.trim_prefix("--capture-dir="))

func _solid(color: Color) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color=color
    m.roughness=1
    m.metallic_specular=0
    return m

func _box(at: Vector3, size: Vector3, mat: Material) -> MeshInstance3D:
    var n := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size=size
    n.mesh=mesh
    n.position=at
    n.material_override=mat
    world.add_child(n)
    return n

func _build() -> void:
    _box(Vector3(0,-.07,0),Vector3(1.75,.12,.9),_solid(Color("203b3e")))
    var sand := ShaderMaterial.new()
    var sh := Shader.new()
    sh.code="""shader_type spatial;
    varying vec3 p;
    void vertex(){p=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;}
    float hash(vec2 q){return fract(sin(dot(q,vec2(127.1,311.7)))*43758.5453);}
    void fragment(){float a=floor(hash(floor(p.xz*700.0))*5.0)/5.0;float b=hash(floor(p.xz*130.0));ALBEDO=mix(vec3(.29,.25,.17),vec3(.61,.53,.36),a*.6+b*.4);ROUGHNESS=1.0;SPECULAR=0.0;}"""
    sand.shader=sh
    _box(Vector3(0,-.006,0),Vector3(1.70,.028,.86),sand)
    scenery=Node3D.new()
    scenery.name="Aquascape"
    world.add_child(scenery)
    var rocks := [Vector3(-.40,.007,-.11),Vector3(-.60,.008,.09),Vector3(-.25,.008,-.23)]
    var sizes := [Vector3(.34,.26,.27),Vector3(.25,.14,.20),Vector3(.23,.17,.23)]
    for i in rocks.size():
        var r: Node3D=kit.rock(2401+i,sizes[i])
        scenery.add_child(r)
        r.position=rocks[i]
        r.rotation.y=i*.64
        if i==0:_export(r,"river_rock")
    var wood: Node3D=kit.wood()
    scenery.add_child(wood)
    wood.position=Vector3(.02,.006,.03)
    wood.rotation.y=-.18
    _export(wood,"forked_driftwood")
    # Horizontal rhizomes rest on the upper wood surface. Roots enter the wood.
    for spec in [[false,Vector3(-.18,.15,.044),0.12,2405],[false,Vector3(-.35,.265,-.10),.8,2410],[true,Vector3(-.12,.14,-.02),.2,2406],[true,Vector3(-.26,.17,-.23),1.1,2407]]:
        var p: Node3D=kit.plant(spec[0],spec[3])
        scenery.add_child(p)
        p.position=spec[1]
        p.rotation.y=spec[2]
        if spec[3] in [2405,2406]:_export(p,"java_fern" if spec[0] else "anubias_nana")
    for i in 36:
        var angle := i*2.399
        var loc := Vector3(cos(angle)*(.14+fmod(i*.031,.56)),.003,sin(angle)*.35)
        var pebble: Node3D=kit.rock(2600+i,Vector3(.020,.009,.015)*(1.0+(i%4)*.23))
        scenery.add_child(pebble)
        pebble.position=loc
    fish_stock=preload("res://scripts/aquarium/AquariumFishStock.gd").new()
    add_child(fish_stock)
    # Fixed existing pose for same-light style comparison; no new fish motion/profile.
    var entry: Dictionary=fish_stock.add_stock(world,"bluegill",Vector3(.38,.52,-.03),0.0)
    entry.carrier.position=Vector3(.38,.52,-.03)
    entry.carrier.rotation=Vector3.ZERO
    entry.player.pause()

func _export(n: Node3D, id: String) -> void:
    if not export_requested:return
    var transform_before := n.transform
    n.transform=Transform3D.IDENTITY
    var err: int=kit.save_asset(n,"res://assets/aquascape/"+id+".tscn")
    if err!=OK:export_errors.append({"asset":id,"error":err})
    n.transform=transform_before
    var saved: PackedScene=ResourceLoader.load("res://assets/aquascape/"+id+".tscn","PackedScene",ResourceLoader.CACHE_MODE_IGNORE)
    if saved==null:
        export_errors.append({"asset":id,"error":"reload_failed"})
    else:
        var instance := saved.instantiate()
        var expected := n.find_children("*","MeshInstance3D",true,false).size() + (1 if n is MeshInstance3D else 0)
        var actual := instance.find_children("*","MeshInstance3D",true,false).size() + (1 if instance is MeshInstance3D else 0)
        reload_checks.append({"asset":id,"expected_meshes":expected,"reloaded_meshes":actual,"ok":expected==actual})
        if expected!=actual:export_errors.append({"asset":id,"error":"reload_mesh_count_mismatch"})
        instance.free()

func _label(parent: Node, value: String, pos: Vector2, size_value: int, color: Color) -> Label:
    var l := Label.new()
    l.text=value
    l.position=pos
    l.add_theme_font_size_override("font_size",size_value)
    l.add_theme_color_override("font_color",color)
    l.mouse_filter=Control.MOUSE_FILTER_IGNORE
    parent.add_child(l)
    return l

func _ui() -> void:
    var top := ColorRect.new()
    top.color=Color("0c2329")
    top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
    top.offset_bottom=104
    top.mouse_filter=Control.MOUSE_FILTER_IGNORE
    add_child(top)
    _label(top,"A Q U A S C A P E    /    缸 底 置 景",Vector2(34,18),26,Color("e9dfc2"))
    _label(top,"01  灰岩与砂砾     02  分叉沉木     03  小水榕     04  爪哇蕨（铁皇冠）",Vector2(34,61),17,Color("9fbcb1"))
    var panel := ColorRect.new()
    panel.color=Color("0c2329")
    panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
    panel.offset_top=-112
    panel.mouse_filter=Control.MOUSE_FILTER_IGNORE
    add_child(panel)
    _label(panel,"小水榕 · Anubias barteri var. nana       |       爪哇蕨 · Microsorum pteropus",Vector2(34,12),19,Color("d5dfc5"))
    _label(panel,"拖动旋转 · 滚轮缩放 · R 复位      1 材质   2 灰模   3 格纹   4 俯视   5 背面",Vector2(34,45),17,Color("9ab5ad"))
    mode_label=_label(panel,"材质预览 · 试作 / 待视觉验收",Vector2(34,76),15,Color("d6b77c"))
    var buttons := HBoxContainer.new()
    buttons.position=Vector2(1070,30)
    top.add_child(buttons)
    for i in 3:
        var b := Button.new()
        b.text=["材质","灰模","格纹"][i]
        b.custom_minimum_size=Vector2(88,40)
        b.pressed.connect(func():_mode(i))
        buttons.add_child(b)

func _mode(value: int) -> void:
    mode=value
    kit.set_mode(value)
    mode_label.text=["材质预览","灰模：轮廓与接触","格纹：UV 方向与拉伸"][value]+" · 试作 / 待视觉验收"

func _camera() -> void:
    camera.size=view_size
    camera.position=target+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*3
    camera.look_at(target)

func _input_view(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        if event.button_index==MOUSE_BUTTON_LEFT:dragging=event.pressed
        if event.pressed and event.button_index==MOUSE_BUTTON_WHEEL_UP:view_size=maxf(.25,view_size*.9)
        if event.pressed and event.button_index==MOUSE_BUTTON_WHEEL_DOWN:view_size=minf(3.4,view_size*1.1)
    if event is InputEventMouseMotion and dragging:
        yaw-=event.relative.x*.007
        pitch=clampf(pitch+event.relative.y*.005,-.05,1.52)
    _camera()

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed:return
    match event.keycode:
        KEY_1:_mode(0)
        KEY_2:_mode(1)
        KEY_3:_mode(2)
        KEY_4:pitch=1.48
        KEY_5:yaw=PI+.30;pitch=.35
        KEY_R:yaw=.30;pitch=.35;view_size=1.70;target=Vector3(0,.30,0);_mode(0)
    _camera()

func _capture(directory: String) -> void:
    DirAccess.make_dir_recursive_absolute(directory)
    for i in 8:await get_tree().process_frame
    var captures := []
    var views := [
        ["01-material",0,.30,.35,1.70,Vector3(0,.30,0)],
        ["02-gray",1,.30,.35,1.70,Vector3(0,.30,0)],
        ["03-checker",2,.30,.35,1.70,Vector3(0,.30,0)],
        ["04-back",0,PI+.30,.40,1.70,Vector3(0,.25,0)],
        ["05-top",0,0,1.48,1.70,Vector3(0,.2,0)],
        ["06-plants",0,.38,.38,.64,Vector3(-.23,.27,-.04)],
        ["07-wood",0,-.45,.48,.92,Vector3(.12,.19,.03)],
        ["08-leaf-side",1,1.45,.18,.64,Vector3(-.23,.27,-.04)]
    ]
    for row in views:
        _mode(row[1]);yaw=row[2];pitch=row[3];view_size=row[4];target=row[5];_camera()
        for i in 3:await get_tree().process_frame
        await RenderingServer.frame_post_draw
        var path: String = directory+"/"+row[0]+".png"
        var err := get_viewport().get_texture().get_image().save_png(path)
        captures.append({"path":path,"error":err})
    var mesh_count := 0
    var vertices := 0
    var invalid_values := 0
    for n in scenery.find_children("*","MeshInstance3D",true,false):
        mesh_count+=1
        for surface in n.mesh.get_surface_count():
            var arrays: Array=n.mesh.surface_get_arrays(surface)
            vertices+=arrays[Mesh.ARRAY_VERTEX].size()
            for v in arrays[Mesh.ARRAY_VERTEX]:
                if not v.is_finite():invalid_values+=1
            for uv in arrays[Mesh.ARRAY_TEX_UV]:
                if not uv.is_finite():invalid_values+=1
    var failed_capture := false
    for row in captures:
        if row.error!=OK:failed_capture=true
    report={"schema_version":1,"command":"aquascape.validate","status":"done","next_action":"human_review","ok":kit.failures.is_empty() and export_errors.is_empty() and invalid_values==0 and not failed_capture,"summary":{"meshes":mesh_count,"vertices":vertices,"triangles":kit.triangle_count,"invalid_values":invalid_values,"existing_fish":"bluegill, fixed original pose, original loader","source_resolution_preserved":true},"outputs":captures,"failures":kit.failures,"export_errors":export_errors,"visual_review":"pending","user_acceptance":"pending","scope":"Static scenery prototype. No fish changes or new fish acceptance. No interactive placement/collision or plant sway."}
    report["reload_checks"]=reload_checks
    var f := FileAccess.open(directory+"/validation-report.json",FileAccess.WRITE)
    f.store_string(JSON.stringify(report,"  "))
    print(JSON.stringify(report))
    get_tree().quit(0 if report.ok else 1)
