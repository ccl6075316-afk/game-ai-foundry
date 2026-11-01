extends PanelContainer
## Right-side information and controls for the selected scene object.
signal mode_changed(value: String)
var title: Label
var details: Label
var measurements: Label
var hint: Label
var modes: Dictionary={}

func setup() -> void:
    var style := StyleBoxFlat.new();style.bg_color=Color("14313b");style.border_color=Color("355563");style.set_border_width_all(1)
    style.content_margin_left=14;style.content_margin_right=14;style.content_margin_top=12;style.content_margin_bottom=10;add_theme_stylebox_override("panel",style)
    var body := VBoxContainer.new();body.add_theme_constant_override("separation",6);add_child(body)
    var header := Label.new();header.text="物件属性";header.add_theme_font_size_override("font_size",22);body.add_child(header)
    title=Label.new();title.add_theme_font_size_override("font_size",19);body.add_child(title)
    details=Label.new();details.add_theme_color_override("font_color",Color("acc8d1"));body.add_child(details)
    var tools := HBoxContainer.new();body.add_child(tools)
    for pair in [["move","移动 W"],["rotate","旋转 E"],["scale","缩放 R"]]:
        var b := Button.new();b.text=pair[1];b.toggle_mode=true;b.focus_mode=Control.FOCUS_NONE;b.size_flags_horizontal=Control.SIZE_EXPAND_FILL
        tools.add_child(b);modes[pair[0]]=b;b.pressed.connect(func():set_mode(pair[0]);mode_changed.emit(pair[0]))
    measurements=Label.new();measurements.add_theme_font_size_override("font_size",15);body.add_child(measurements)
    hint=Label.new();hint.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;hint.add_theme_font_size_override("font_size",14);body.add_child(hint)
    set_mode("move")

func set_mode(value: String) -> void:
    for key in modes:modes[key].button_pressed=key==value

func bind_object(name_value: String,type_value: String,node: Node3D,box: AABB,planar: bool,metric_scale:=1.0) -> void:
    title.text=name_value if node!=null else "未选中物件"
    details.text=type_value if node!=null else "从场景中选择物件，查看和调整属性。"
    for button in modes.values():button.disabled=node==null
    if node==null:measurements.text="";hint.text="底部选择素材，右侧调整选中物件。";return
    var p := node.position*metric_scale;var r := node.rotation_degrees;var s := node.scale
    for axis in 3:
        if absf(r[axis])<.5:r[axis]=0
    measurements.text="位置  X %.2f   Y %.2f   Z %.2f\n旋转  X %.0f°   Y %.0f°   Z %.0f°\n缩放  X %.2f   Y %.2f   Z %.2f" % [p.x,p.y,p.z,r.x,r.y,r.z,s.x,s.y,s.z]
    var dimensions := (node.transform*box).size*metric_scale
    hint.text="占用尺寸  %.2f × %.2f × %.2f m\n" % [dimensions.x,dimensions.y,dimensions.z]
    hint.text+="落地移动 X/Z · 绕 Y 旋转 · 整体缩放" if planar else "世界轴移动与旋转 · 局部轴缩放\nEsc 取消拖动；完成后应用回大厅。"
