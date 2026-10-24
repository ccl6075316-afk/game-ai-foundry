extends Control
## Isolated interaction trial; its save file never touches the aquarium save.
const BED = preload("res://scripts/aquarium/EditableSandBed.gd")
const ROCK_IDS := ["rock","river_boulder"]
const SAVE_PATH := "user://aquascape-sand-trial-v1.json"
var viewport: SubViewport
var world: Node3D
var camera: Camera3D
var bed
var tool := "pour"
var radius := .075
var yaw := .18
var pitch := .64
var view_size := 1.30
var pointer := Vector2(-100,-100)
var hit: Variant=null
var painting := false
var orbiting := false
var moving := false
var stroke_clock := 0.0
var last_stamp: Variant=null
var selected := -1
var rocks: Array=[]
var rock_specs: Dictionary={}
var rock_paints: Dictionary={}
var ghost: Node3D
var ghost_id := ""
var ghost_scale := 1.0
var ghost_yaw := 0.0
var ghost_bounds := AABB()
var ring: MeshInstance3D
var history: Array=[]
var future: Array=[]
var tool_buttons: Dictionary={}
var status_label: Label
var detail_label: Label
var size_label: Label
var selected_label: Label
var notice := "左键按住铺沙，试着堆出一个小坡。"
var notice_time := 0.0
var capture_active := false
var statistics_clock := 0.0
var canvas: TextureRect

func _ready() -> void:
    get_window().content_scale_size=Vector2i(1440,900)
    DisplayServer.window_set_title("潮汐馆 · 铺沙与摆石实验")
    viewport=SubViewport.new()
    viewport.size=Vector2i(1440,900)
    viewport.own_world_3d=true
    viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    add_child(viewport)
    world=Node3D.new()
    viewport.add_child(world)
    canvas=TextureRect.new()
    canvas.texture=viewport.get_texture()
    canvas.expand_mode=TextureRect.EXPAND_IGNORE_SIZE
    canvas.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST
    canvas.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    canvas.gui_input.connect(_input_canvas)
    canvas.mouse_exited.connect(func():painting=false;moving=false;last_stamp=null;pointer=Vector2(-100,-100);_update_cursor())
    add_child(canvas)
    var environment := WorldEnvironment.new()
    environment.environment=Environment.new()
    environment.environment.background_mode=Environment.BG_COLOR
    environment.environment.background_color=Color("10272d")
    environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color=Color("dce5e0")
    environment.environment.ambient_light_energy=.35
    world.add_child(environment)
    var light := DirectionalLight3D.new()
    light.rotation_degrees=Vector3(-58,-30,0)
    light.light_energy=.65
    light.light_color=Color("ffffff")
    light.shadow_enabled=true
    light.shadow_bias=.015
    light.directional_shadow_max_distance=4.0
    world.add_child(light)
    camera=Camera3D.new()
    camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    camera.near=.01
    camera.far=10
    world.add_child(camera)
    camera.current=true
    _box(Vector3(0,-.020,0),Vector3(1.24,.038,.64),Color("213c40"))
    _box(Vector3(0,-.001,-.312),Vector3(1.24,.01,.012),Color("739394"))
    _box(Vector3(0,-.001,.312),Vector3(1.24,.01,.012),Color("739394"))
    _box(Vector3(-.612,-.001,0),Vector3(.012,.01,.62),Color("739394"))
    _box(Vector3(.612,-.001,0),Vector3(.012,.01,.62),Color("739394"))
    bed=BED.new()
    bed.name="EditableSubstrate"
    world.add_child(bed)
    bed.setup(load("res://assets/aquascape-sand-v1/fine-sand.png"))
    for row in JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquascape-v5/catalog.json")).assets:
        if row.id in ROCK_IDS:rock_specs[row.id]=row
    ring=MeshInstance3D.new()
    ring.name="BrushFootprint"
    var ring_paint := StandardMaterial3D.new()
    ring_paint.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    ring_paint.albedo_color=Color("e6d4a2")
    ring.material_override=ring_paint
    ring.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    world.add_child(ring)
    _ui()
    _camera()
    _add_rock("rock",Vector3(-.20,0,-.025),.85,-.18)
    _add_rock("river_boulder",Vector3(.20,0,.055),.85,.25)
    _set_tool("pour")
    for arg in OS.get_cmdline_user_args():
        if arg=="--demo":_demo(false)
        if arg.begins_with("--capture-dir="):call_deferred("_capture",arg.trim_prefix("--capture-dir="))

func _box(at: Vector3,dimensions: Vector3,color: Color) -> void:
    var node := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size=dimensions
    node.mesh=mesh
    var material := StandardMaterial3D.new()
    material.albedo_color=color
    material.roughness=1.0
    node.material_override=material
    node.position=at
    world.add_child(node)

func _text(parent: Node,text: String,at: Vector2,font_size: int,color:=Color("e7e2cc")) -> Label:
    var label := Label.new()
    label.text=text
    label.position=at
    label.add_theme_font_size_override("font_size",font_size)
    label.add_theme_color_override("font_color",color)
    parent.add_child(label)
    return label

func _button(parent: Node,text: String,at: Vector2,width: float,action: Callable) -> Button:
    var b := Button.new()
    b.text=text
    b.position=at
    b.custom_minimum_size=Vector2(width,38)
    b.focus_mode=Control.FOCUS_NONE
    b.pressed.connect(action)
    parent.add_child(b)
    return b

func _ui() -> void:
    var header := ColorRect.new()
    header.color=Color("0c2228")
    header.size=Vector2(1440,90)
    add_child(header)
    _text(header,"A Q U A S C A P E   /   铺沙实验",Vector2(26,13),27)
    _text(header,"一种细沙 · 两种原画石头 · 可以堆坡、挖沙、摆石和掩埋石脚",Vector2(26,53),17,Color("afc6ba"))
    var panel := ColorRect.new()
    panel.color=Color("132c31")
    panel.position=Vector2(1130,94)
    panel.size=Vector2(302,708)
    add_child(panel)
    _text(panel,"底床工具",Vector2(18,10),22)
    var row := 0
    for spec in [["pour","1  倒沙"],["remove","2  吸沙"],["smooth","3  整平"],["select","4  选取 / 移动石头"],["rock","5  摆放阶台灰岩"],["river_boulder","6  摆放圆卵溪石"]]:
        var id: String=spec[0]
        var b := _button(panel,spec[1],Vector2(18,45+row*43),266,func():_set_tool(id))
        b.toggle_mode=true
        tool_buttons[id]=b
        row+=1
    size_label=_text(panel,"笔刷直径 15 cm",Vector2(18,312),17)
    var slider := HSlider.new()
    slider.position=Vector2(18,346)
    slider.size=Vector2(265,28)
    slider.min_value=3
    slider.max_value=30
    slider.value=15
    slider.step=1
    slider.focus_mode=Control.FOCUS_NONE
    slider.value_changed.connect(func(value: float):radius=value/200.0;size_label.text="笔刷直径 %d cm" % value)
    panel.add_child(slider)
    selected_label=_text(panel,"石头：点击选取后可移动",Vector2(18,381),16,Color("afc6ba"))
    _text(panel,"Q / E 旋转 · Shift＋滚轮缩放\nDelete 删除选中石头",Vector2(18,411),15,Color("afc6ba"))
    _button(panel,"撤销",Vector2(18,467),128,_undo)
    _button(panel,"重做",Vector2(156,467),128,_redo)
    _button(panel,"保存实验",Vector2(18,512),128,_save_user)
    _button(panel,"读取实验",Vector2(156,512),128,_load_user)
    _button(panel,"示例坡景",Vector2(18,557),128,func():_demo(true))
    _button(panel,"清空重铺",Vector2(156,557),128,_clear)
    _button(panel,"俯视",Vector2(18,602),128,func():pitch=1.45;_camera())
    _button(panel,"斜视",Vector2(156,602),128,func():pitch=.64;yaw=.18;_camera())
    _text(panel,"范围：120 × 60 cm\n底床厚度上限：24 cm",Vector2(18,651),15,Color("afc6ba"))
    var footer := ColorRect.new()
    footer.color=Color("0c2228")
    footer.position=Vector2(0,810)
    footer.size=Vector2(1440,90)
    add_child(footer)
    status_label=_text(footer,notice,Vector2(26,8),18)
    detail_label=_text(footer,"左键操作 · 右键拖动旋转 · 滚轮拉近 · Ctrl+Z 撤销",Vector2(26,41),16,Color("afc6ba"))

func _camera() -> void:
    camera.size=view_size
    var target := Vector3(.19,.035,0)
    camera.position=target+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*3
    camera.look_at(target)

func _set_tool(value: String) -> void:
    painting=false
    moving=false
    last_stamp=null
    tool=value
    for key in tool_buttons:tool_buttons[key].button_pressed=key==value
    if is_instance_valid(ghost):ghost.hide();ghost.queue_free()
    ghost=null
    if tool in ROCK_IDS:
        var built := _rock_model(tool)
        ghost=built.node
        ghost_bounds=built.bounds
        ghost_id=tool
        ghost_scale=.85
        ghost_yaw=0
        world.add_child(ghost)
        for mesh in ghost.find_children("*","MeshInstance3D",true,false):mesh.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        notice="移动鼠标预览落点，左键摆放；Q/E 旋转，Shift＋滚轮缩放。"
    else:
        notice={"pour":"按住左键倒沙，停留越久堆得越高。","remove":"按住左键吸沙，石头露出后会下落贴住底床。","smooth":"按住左键整平，拖动修出柔和的坡面。","select":"点击石头并拖动；Q/E 旋转，Shift＋滚轮缩放。"}.get(tool,"")
    _update_cursor()

func _rock_model(id: String) -> Dictionary:
    var spec: Dictionary=rock_specs[id]
    # Retain shared paint for the lifetime of the lab, including deletion and
    # undo; GLES must not lose a material while retired instances still use it.
    if not rock_paints.has(id):
        var paint := ShaderMaterial.new()
        paint.shader=load("res://scripts/aquarium/ThreeViewArtwork.gdshader")
        for view in ["front","right","top"]:paint.set_shader_parameter(view+"_art",load(spec.material_dir+"/"+id+"-"+view+".png"))
        var d: Dictionary=spec.projection_bounds
        paint.set_shader_parameter("projection_size",Vector3(d.width,d.height,d.depth))
        rock_paints[id]=paint
    var node: Node3D=(load(spec.model) as PackedScene).instantiate()
    var box := AABB()
    var first := true
    for mesh in node.find_children("*","MeshInstance3D",true,false):
        var local: AABB=mesh.transform*mesh.get_aabb()
        box=local if first else box.merge(local)
        first=false
        for surface in mesh.mesh.get_surface_count():
            mesh.set_surface_override_material(surface,rock_paints[id])
    return {"node":node,"bounds":box}

func _support(at: Vector3,box: AABB,factor: float) -> float:
    var height: float=bed.sample(at.x,at.z)
    for delta in [Vector2(-1,-1),Vector2(1,-1),Vector2(-1,1),Vector2(1,1)]:
        height=minf(height,bed.sample(at.x+delta.x*box.size.x*factor*.22,at.z+delta.y*box.size.z*factor*.22))
    return height-.012-box.position.y*factor

func _inside_tank(at: Vector3,box: AABB,factor: float,angle: float) -> Vector3:
    var extent_x: float=(absf(cos(angle))*box.size.x+absf(sin(angle))*box.size.z)*factor*.5
    var extent_z: float=(absf(sin(angle))*box.size.x+absf(cos(angle))*box.size.z)*factor*.5
    return Vector3(clampf(at.x,-BED.WIDTH*.5+extent_x,BED.WIDTH*.5-extent_x),at.y,clampf(at.z,-BED.DEPTH*.5+extent_z,BED.DEPTH*.5-extent_z))

func _add_rock(id: String,at: Vector3,factor: float,angle: float,saved_y: Variant=null) -> void:
    var built := _rock_model(id)
    var node: Node3D=built.node
    world.add_child(node)
    at=_inside_tank(at,built.bounds,factor,angle)
    node.scale=Vector3.ONE*factor
    node.rotation.y=angle
    node.position=Vector3(at.x,_support(at,built.bounds,factor) if saved_y==null else float(saved_y),at.z)
    rocks.append({"id":id,"node":node,"bounds":built.bounds,"factor":factor})
    selected=rocks.size()-1

func _settle_rocks() -> void:
    for row in rocks:
        var node: Node3D=row.node
        node.position.y=minf(node.position.y,_support(node.position,row.bounds,row.factor))

func _ray_bed(screen: Vector2) -> Variant:
    var origin := camera.project_ray_origin(screen)
    var direction := camera.project_ray_normal(screen)
    if direction.y>-.03:return null
    var begin: float=maxf(0,(BED.MAX_HEIGHT+.01-origin.y)/direction.y)
    var end: float=(0-origin.y)/direction.y
    var previous: float=begin
    for i in range(129):
        var t: float=lerpf(begin,end,i/128.0)
        var p: Vector3=origin+direction*t
        if absf(p.x)<=BED.WIDTH*.5 and absf(p.z)<=BED.DEPTH*.5 and p.y<=bed.sample(p.x,p.z):
            var lo := previous
            var hi := t
            for j in 12:
                var mid := (lo+hi)*.5
                var q: Vector3=origin+direction*mid
                if q.y>bed.sample(q.x,q.z):lo=mid
                else:hi=mid
            var result: Vector3=origin+direction*hi
            result.y=bed.sample(result.x,result.z)
            return result
        previous=t
    return null

func _pick_rock(screen: Vector2) -> int:
    var origin := camera.project_ray_origin(screen)
    var direction := camera.project_ray_normal(screen)
    var best := -1
    var nearest := INF
    for i in rocks.size():
        var row: Dictionary=rocks[i]
        var inverse: Transform3D=row.node.global_transform.affine_inverse()
        var point: Variant=row.bounds.intersects_ray(inverse*origin,inverse.basis*direction)
        if point==null:continue
        var distance: float=origin.distance_to(row.node.global_transform*point)
        if distance<nearest:nearest=distance;best=i
    return best

func _update_cursor() -> void:
    hit=_ray_bed(pointer)
    ring.visible=hit!=null and tool in ["pour","remove","smooth"]
    if ring.visible:
        var mesh := ImmediateMesh.new()
        mesh.surface_begin(Mesh.PRIMITIVE_LINES)
        for i in 64:
            for k in [i,i+1]:
                var a: float=k*TAU/64.0
                var x: float=clampf(hit.x+cos(a)*radius,-BED.WIDTH*.5,BED.WIDTH*.5)
                var z: float=clampf(hit.z+sin(a)*radius,-BED.DEPTH*.5,BED.DEPTH*.5)
                mesh.surface_add_vertex(Vector3(x,bed.sample(x,z)+.0015,z))
        mesh.surface_end()
        ring.mesh=mesh
    if is_instance_valid(ghost):
        ghost.visible=hit!=null
        if hit!=null:
            ghost.scale=Vector3.ONE*ghost_scale
            ghost.rotation.y=ghost_yaw
            var at: Vector3=_inside_tank(hit,ghost_bounds,ghost_scale,ghost_yaw)
            ghost.position=Vector3(at.x,_support(at,ghost_bounds,ghost_scale),at.z)

func _input_canvas(event: InputEvent) -> void:
    if event is InputEventMouseMotion:
        pointer=event.position
        if orbiting:
            yaw-=event.relative.x*.007
            pitch=clampf(pitch+event.relative.y*.005,.22,1.5)
            _camera()
        _update_cursor()
        if moving and selected>=0 and hit!=null:
            var row: Dictionary=rocks[selected]
            var at: Vector3=_inside_tank(hit,row.bounds,row.factor,row.node.rotation.y)
            row.node.position=Vector3(at.x,_support(at,row.bounds,row.factor),at.z)
    if not event is InputEventMouseButton:return
    pointer=event.position
    _update_cursor()
    if event.button_index==MOUSE_BUTTON_RIGHT:orbiting=event.pressed
    if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
        var direction: float=1 if event.button_index==MOUSE_BUTTON_WHEEL_UP else -1
        if event.shift_pressed:_resize_rock(direction)
        else:view_size=clampf(view_size*pow(.9,direction),.45,2.3);_camera()
        _update_cursor()
    if event.button_index!=MOUSE_BUTTON_LEFT:return
    if not event.pressed:
        painting=false;moving=false;last_stamp=null
        return
    if tool=="select":
        selected=_pick_rock(pointer)
        if selected>=0:_remember();moving=true
    elif hit!=null:
        if tool in ROCK_IDS:
            if rocks.size()>=80:notice="本实验最多放置 80 块石头。";return
            _remember()
            _add_rock(tool,hit,ghost_scale,ghost_yaw)
        else:
            _remember()
            painting=true
            stroke_clock=0
            last_stamp=hit
            _stamp(.033)

func _stamp(seconds: float) -> void:
    if hit==null:return
    var previous: Vector3=hit if last_stamp==null else last_stamp
    var count: int=clampi(int(ceil(previous.distance_to(hit)/(radius*.3))),1,12)
    for i in range(1,count+1):bed.brush(previous.lerp(hit,i/float(count)),radius,seconds/count,tool)
    last_stamp=hit
    _settle_rocks()
    _update_cursor()

func _resize_rock(direction: float) -> void:
    if is_instance_valid(ghost):ghost_scale=clampf(ghost_scale+direction*.08,.4,1.6)
    elif selected>=0:
        _remember()
        var row: Dictionary=rocks[selected]
        row.factor=clampf(row.factor+direction*.08,.4,1.6)
        row.node.scale=Vector3.ONE*row.factor
        row.node.position=_inside_tank(row.node.position,row.bounds,row.factor,row.node.rotation.y)
        row.node.position.y=_support(row.node.position,row.bounds,row.factor)

func _unhandled_key_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo:return
    if event.ctrl_pressed:
        if event.keycode==KEY_Z:_undo()
        if event.keycode==KEY_Y:_redo()
        return
    match event.keycode:
        KEY_1:_set_tool("pour")
        KEY_2:_set_tool("remove")
        KEY_3:_set_tool("smooth")
        KEY_4:_set_tool("select")
        KEY_5:_set_tool("rock")
        KEY_6:_set_tool("river_boulder")
        KEY_Q,KEY_E:
            var angle: float=deg_to_rad(-15 if event.keycode==KEY_Q else 15)
            if is_instance_valid(ghost):ghost_yaw+=angle;_update_cursor()
            elif selected>=0:
                _remember()
                var row: Dictionary=rocks[selected]
                row.node.rotation.y+=angle
                row.node.position=_inside_tank(row.node.position,row.bounds,row.factor,row.node.rotation.y)
        KEY_DELETE:
            if selected>=0:
                _remember();rocks[selected].node.hide();rocks[selected].node.queue_free();rocks.remove_at(selected);selected=-1

func _process(delta: float) -> void:
    if capture_active:return
    if painting:
        if not Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):painting=false
        elif pointer.x<1128 and pointer.y>90 and pointer.y<810:
            stroke_clock+=delta
            if stroke_clock>=.033:_stamp(minf(stroke_clock,.07));stroke_clock=0
    if moving and not Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):moving=false
    statistics_clock+=delta
    if statistics_clock>.25:
        statistics_clock=0
        status_label.text=notice
        detail_label.text="右键拖动旋转 · 滚轮拉近 · 底沙 %.1f L · %d 块石头 · 地形 %d 块 · 最近笔刷 %.1f ms" % [bed.volume()*1000,rocks.size(),bed.chunks.size(),bed.last_brush_ms]
        selected_label.text="石头："+(rock_specs[rocks[selected].id].name_zh+"  %.2f×" % rocks[selected].factor if selected>=0 else "点击选取后可移动")

func _state() -> Dictionary:
    var saved_rocks: Array=[]
    for row in rocks:
        var p: Vector3=row.node.position
        saved_rocks.append({"id":row.id,"position":[p.x,p.y,p.z],"scale":row.factor,"yaw":row.node.rotation.y})
    return {"schema_version":1,"grid":[BED.NX,BED.NZ],"sand":"fine_sand","heights":Array(bed.heights),"rocks":saved_rocks}

func _restore(data: Dictionary) -> void:
    _set_tool("pour")
    for row in rocks:row.node.hide();row.node.queue_free()
    rocks.clear();selected=-1
    bed.heights=PackedFloat32Array(data.heights)
    bed.rebuild_all()
    for row in data.rocks:_add_rock(row.id,Vector3(row.position[0],row.position[1],row.position[2]),row.scale,row.yaw,row.position[1])
    _update_cursor()

func _remember() -> void:
    history.append(_state())
    if history.size()>30:history.pop_front()
    future.clear()

func _undo() -> void:
    if history.is_empty():return
    future.append(_state())
    _restore(history.pop_back())
    notice="已撤销。"

func _redo() -> void:
    if future.is_empty():return
    history.append(_state())
    _restore(future.pop_back())
    notice="已重做。"

func _write_save(path: String) -> bool:
    var file := FileAccess.open(path,FileAccess.WRITE)
    if file==null:return false
    file.store_string(JSON.stringify(_state()))
    return true

func _read_save(path: String) -> bool:
    if not FileAccess.file_exists(path):return false
    var data: Variant=JSON.parse_string(FileAccess.get_file_as_string(path))
    if not data is Dictionary or data.get("schema_version")!=1 or data.get("sand")!="fine_sand":return false
    # JSON numbers parse as floats; array equality against integer arrays is strict.
    if not data.get("grid") is Array or data.grid.size()!=2 or data.grid[0]!=BED.NX or data.grid[1]!=BED.NZ:return false
    if not data.get("heights") is Array or data.heights.size()!=BED.NX*BED.NZ or not data.get("rocks") is Array or data.rocks.size()>80:return false
    for h in data.heights:
        if not (h is float or h is int) or not is_finite(h) or h<0 or h>BED.MAX_HEIGHT:return false
    for row in data.rocks:
        if not row is Dictionary or not row.get("id") in ROCK_IDS:return false
        if not row.get("position") is Array or row.position.size()!=3:return false
        for p in row.position:
            if not (p is float or p is int) or not is_finite(p):return false
        if absf(row.position[0])>.61 or absf(row.position[2])>.31:return false
        if not (row.get("scale") is float or row.get("scale") is int) or not is_finite(row.scale) or row.scale<.4 or row.scale>1.6:return false
        if not (row.get("yaw") is float or row.get("yaw") is int) or not is_finite(row.yaw):return false
    _remember()
    _restore(data)
    return true

func _save_user() -> void:
    notice="实验已保存。" if _write_save(SAVE_PATH) else "保存失败。"

func _load_user() -> void:
    notice="已读取实验。" if _read_save(SAVE_PATH) else "没有可读取的有效实验存档。"

func _clear() -> void:
    _remember()
    for row in rocks:row.node.hide();row.node.queue_free()
    rocks.clear();selected=-1
    bed.reset(.008)
    _set_tool("pour")
    notice="已清空，保留薄底沙；可撤销。"

func _demo(record: bool) -> void:
    if record:_remember()
    for row in rocks:row.node.hide();row.node.queue_free()
    rocks.clear();selected=-1
    for z in BED.NZ:
        for x in BED.NX:
            var px: float=x*BED.DX-BED.WIDTH*.5
            var pz: float=z*BED.DZ-BED.DEPTH*.5
            var mound: float=.105*exp(-((px+.32)*(px+.32)/.025+(pz-.045)*(pz-.045)/.014))
            var ridge: float=.04*exp(-((px-.28)*(px-.28)/.06+(pz+.16)*(pz+.16)/.012))
            bed.heights[z*BED.NX+x]=.02+(.3-pz)*.06+mound+ridge
    bed.rebuild_all()
    _add_rock("rock",Vector3(-.23,0,-.05),.9,-.28)
    _add_rock("river_boulder",Vector3(.22,0,-.015),.9,.35)
    _set_tool("pour")
    notice="示例坡景已就绪，继续倒沙、挖沙或调整石头。"

func _capture(_directory: String) -> void:
    push_error("Use aquascape_sand_review.tscn for deterministic native review.")
    get_tree().quit(1)
