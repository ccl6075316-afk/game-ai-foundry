extends "res://scripts/aquarium/DecorPlacementLab.gd"
signal apply_requested(state: Dictionary)
signal cancel_requested
var initial_state: Dictionary={}
var build_editor: RefCounted
var metric_scale := 5.0

func _ready() -> void:
    super._ready()
    # The standalone lab assumes a 1440x900 local canvas. Embed that exact
    # workspace, scaled uniformly inside the hall, without resizing its window.
    get_window().content_scale_size=Vector2i(1920,1080)
    size=Vector2(1440,900);position=Vector2(96,0);scale=Vector2.ONE*1.2
    for row in JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquascape-v5/catalog.json")).assets:
        if not row.animated:rock_specs[row.id]=row
    if not initial_state.is_empty():_restore(initial_state)
    build_editor=preload("res://scripts/aquarium/editor/BuildEditorBridge.gd").new();build_editor.setup(self,true)
    _set_tool("select")
    # The hall owns persistence. Reuse sculpt/placement behavior, with explicit
    # Apply/Cancel instead of writing the standalone trial save accidentally.
    for b in find_children("*","Button",true,false):
        if b.text in ["保存实验","读取实验"]:b.hide()
    _button(self,"应用并回大厅",Vector2(990,20),210,func():apply_requested.emit(_state()))
    _button(self,"取消本次修改",Vector2(1210,20),210,func():cancel_requested.emit())
    notice="正在编辑这个展缸 · 应用后回到大厅 · 尺度为大缸的 1/5 工作空间"

func _save_user() -> void:apply_requested.emit(_state())
func _load_user() -> void:notice="由大厅统一保存；取消可放弃本次缸内修改。"

# The parent lab sees process-wide capture arguments; the hall review owns
# capture, so embedded editors must not launch a second review or quit the game.
func _capture(_directory: String) -> void:pass

func _ui() -> void:
    super._ui()
    for child in get_children():
        if child is Control and child!=canvas:child.hide()
    var title := Label.new();title.text="潮汐馆 / 缸内布置"
    title.position=Vector2(24,20);title.add_theme_font_size_override("font_size",23);add_child(title)
    _button(self,"撤销",Vector2(760,20),100,_undo)
    _button(self,"重做",Vector2(870,20),100,_redo)
    _button(self,"删除选中物件",Vector2(1135,650),285,func():
        if selected>=0:_remember();rocks[selected].node.queue_free();rocks.remove_at(selected);selected=-1)
    var footer := Label.new();footer.position=Vector2(24,62);footer.size=Vector2(1080,26);footer.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS;footer.add_theme_font_size_override("font_size",17);footer.name="BuildStatus";add_child(footer)

func _input_canvas(event: InputEvent) -> void:
    if build_editor!=null and build_editor.input_event(event):return
    if tool=="select" and event is InputEventMouseButton:
        if event.button_index==MOUSE_BUTTON_LEFT:
            moving=false
            if event.pressed:selected=_pick_rock(event.position)
            return
        if event.pressed and event.shift_pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN] and selected>=0:
            build_editor.start()
            var value: Transform3D=rocks[selected].node.transform
            value.basis=value.basis.scaled_local(Vector3.ONE*(1.08 if event.button_index==MOUSE_BUTTON_WHEEL_UP else .92))
            build_editor.change(value);build_editor.finish(false);return
    super._input_canvas(event)

func _set_tool(value: String) -> void:
    super._set_tool(value)
    if value=="select":notice="点击选中造景；W 移动箭头，E 旋转圆环，R 缩放方块；Esc 取消本次拖动。"

func _unhandled_key_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and event.keycode==KEY_Q:return
    super._unhandled_key_input(event)

func _input(event: InputEvent) -> void:
    if build_editor!=null and build_editor.gizmo.dragging and (event is InputEventMouseMotion or event is InputEventMouseButton):
        var local_event: InputEvent=event.duplicate()
        local_event.position=get_global_transform_with_canvas().affine_inverse()*event.position
        if build_editor.input_event(local_event):get_viewport().set_input_as_handled();return
    if build_editor!=null and build_editor.key(event):get_viewport().set_input_as_handled()

func _process(delta: float) -> void:
    super._process(delta)
    if build_editor!=null:build_editor.tick()
    if has_node("BuildStatus"):get_node("BuildStatus").text=notice

func _state() -> Dictionary:
    var state := super._state()
    for i in rocks.size():
        var node: Node3D=rocks[i].node
        if node.has_meta("free_transform"):
            state.rocks[i].rotation=preload("res://scripts/aquarium/editor/PropTransform.gd").array(node.rotation)
            state.rocks[i].stretch=preload("res://scripts/aquarium/editor/PropTransform.gd").array(node.scale)
    return state

func _restore(data: Dictionary) -> void:
    super._restore(data)
    for i in data.rocks.size():
        var row: Dictionary=data.rocks[i]
        if row.has("rotation") or row.has("stretch"):
            preload("res://scripts/aquarium/editor/PropTransform.gd").apply(rocks[i].node,row)
            rocks[i].node.set_meta("free_transform",true)
    if build_editor!=null:_set_tool("select")

func _settle_rocks() -> void:
    for row in rocks:
        if not row.node.has_meta("free_transform"):row.node.position.y=minf(row.node.position.y,_support(row.node.position,row.bounds,row.factor))
