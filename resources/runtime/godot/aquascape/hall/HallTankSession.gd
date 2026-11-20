extends RefCounted
## Opens the independent tank editor and applies its document back to one tank.
## Water controls and inspection use the same selected tank.
var host: Control
const WaterProfile := preload("res://scripts/aquarium/TankWaterProfile.gd")
var inspecting := false
var inspection_camera: Camera3D
var inspection_tank_id := ""
var inspection_fish := 0
var inspection_distance := 2.4
var inspection_yaw := 0.0
var inspection_pitch := .08
var water_drag := false
var active_editor
var editor_object_id := ""
var editor_backdrop: ColorRect
var editor_hidden: Array=[]

func _init(hall: Control) -> void:
    host = hall

func create_camera(world: Node3D) -> void:
    inspection_camera = Camera3D.new()
    inspection_camera.near = .025
    inspection_camera.far = 100
    inspection_camera.fov = 62
    world.add_child(inspection_camera)

func _open_content_editor() -> bool:
    _stop_inspection()
    if host.selected<0 or host.objects[host.selected].data.kind!="tank":host.notice="先选择一个展缸。";return false
    editor_object_id=host.objects[host.selected].data.id
    active_editor=load("res://scripts/aquarium/HallTankEditor.gd").new()
    active_editor.metric_scale=float(host.objects[host.selected].data.scale)*5.0
    active_editor.initial_state=host.objects[host.selected].tank.content_state()
    active_editor.apply_requested.connect(_apply_content_editor)
    active_editor.cancel_requested.connect(_close_content_editor)
    editor_hidden.clear()
    for child in host.get_children():
        if child is CanvasItem and child.visible:editor_hidden.append(child);child.hide()
    editor_backdrop=ColorRect.new();editor_backdrop.color=Color("0c2028");editor_backdrop.size=Vector2(1920,1080);host.add_child(editor_backdrop)
    host.viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED
    host.visitor_crowd.set_paused(true)
    host.add_child(active_editor);Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    return true

func _apply_content_editor(state: Dictionary) -> void:
    if not host._execute_build("patch",{"id":editor_object_id,"patch":{"content":state}}):return
    _close_content_editor();host.notice="缸内布景已应用；保存大厅可一起保存。"

func _close_content_editor() -> void:
    if is_instance_valid(active_editor):active_editor.hide();active_editor.queue_free()
    active_editor=null
    host.visitor_crowd.set_paused(false)
    if is_instance_valid(editor_backdrop):editor_backdrop.hide();editor_backdrop.queue_free()
    for child in editor_hidden:
        if is_instance_valid(child):child.show()
    editor_hidden.clear();host.panel.side.visible=host.editing;host.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    host.get_window().content_scale_size=Vector2i(1920,1080)
    DisplayServer.window_set_title("潮汐馆 · 可编辑 3D 大厅")
    host.editor_camera.current=host.editing;host.eye.current=not host.editing
    host.editor._refresh_floor_view(false)

func _open_water_panel() -> void:
    if host.selected<0 or host.objects[host.selected].tank==null:host.notice="先放置一个展缸，再调整水体。";return
    host.editor._set_tool("");host.editor.dragging=false;host._sync_panel();host.panel.water_panel.show()

func _water_changed(key: String,value: Variant) -> void:
    if host.selected<0 or host.objects[host.selected].tank==null:return
    var config: Dictionary=host.objects[host.selected].data.water.duplicate(true);config[key]=value
    if host._execute_build("patch",{"id":host.objects[host.selected].data.id,"patch":{"water":config}},not water_drag):
        host.notice="已调整这个展缸的水体外观；可撤销并保存。"

func _water_preset(index: int) -> void:
    if host.selected<0 or host.objects[host.selected].tank==null:return
    host._execute_build("patch",{"id":host.objects[host.selected].data.id,"patch":{"water":WaterProfile.preset(index)}})

func _start_inspection(reset: bool=true) -> void:
    if host.selected<0 or host.objects[host.selected].tank==null:_open_water_panel()
    if host.selected<0 or host.objects[host.selected].tank==null:return
    host.panel.water_panel.hide()
    inspection_tank_id=host.objects[host.selected].data.id;inspecting=true;host.looking=false;host.editor.dragging=false
    if reset:inspection_distance=2.4*host.objects[host.selected].node.scale.x;inspection_yaw=0;inspection_pitch=.08;inspection_fish=0
    host.panel.side.hide();host.panel.floor_panel.hide();host.editor_camera.current=false;host.eye.current=false;inspection_camera.current=true
    Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    host._sync_panel()
    host.notice="近景观察：滚轮推进缸内，右键环绕，Esc 返回。"
    _update_inspection()

func _update_inspection() -> void:
    for row in host.objects:
        if row.data.id!=inspection_tank_id or row.tank==null:continue
        var target: Vector3=row.tank.global_transform*Vector3(0,1.4,0)
        if not row.tank.fish.is_empty():target=row.tank.fish[posmod(inspection_fish,row.tank.fish.size())].carrier.global_position
        var axis := Vector3(sin(inspection_yaw)*cos(inspection_pitch),sin(inspection_pitch),cos(inspection_yaw)*cos(inspection_pitch))
        axis=row.node.global_basis.orthonormalized()*axis
        inspection_camera.global_position=target+axis*inspection_distance
        inspection_camera.look_at(target);return
    _stop_inspection()

func _stop_inspection() -> void:
    if not inspecting:return
    inspecting=false;host.looking=false;Input.mouse_mode=Input.MOUSE_MODE_VISIBLE
    inspection_camera.current=false;host.editor_camera.current=host.editing;host.eye.current=not host.editing;host.panel.side.visible=host.editing;host.panel.floor_panel.visible=host.editing
    host._sync_panel()
    host.notice="已返回大厅视角。"

func next_fish() -> void:
    inspection_fish += 1
    _start_inspection(false)

func handle_inspection_input(event: InputEvent) -> bool:
    if not inspecting or not host.looking or not event is InputEventMouseMotion:
        return false
    inspection_yaw -= event.relative.x * .004
    inspection_pitch = clampf(inspection_pitch + event.relative.y * .003, -.65, .85)
    _update_inspection()
    return true

func inspection_canvas_input(event: InputEvent) -> void:
    if not event is InputEventMouseButton:
        return
    if event.button_index == MOUSE_BUTTON_RIGHT:
        host.looking = event.pressed
        Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
    elif event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
        var factor := .88 if event.button_index == MOUSE_BUTTON_WHEEL_UP else 1.14
        inspection_distance = clampf(inspection_distance * factor, .22, 8.0)
        _update_inspection()
