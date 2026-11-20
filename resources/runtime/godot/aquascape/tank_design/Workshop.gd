extends PanelContainer
const Shape = preload("Footprint.gd")
const Canvas = preload("PlanCanvas.gd")
const Preview = preload("TankPreview.gd")
signal finished
const LIBRARY_PATH := "user://tank-design-prototype-v1.cfg"
var library_path := LIBRARY_PATH
var plan := Canvas.new()
var preview := Preview.new()
var library := ConfigFile.new()
var design_tools := VBoxContainer.new()
var inspector := VBoxContainer.new()
var title := Label.new()
var hint := Label.new()
var stats := Label.new()
var name_field := LineEdit.new()
var finish := Button.new()
const Design = preload("ShellDesign.gd")
var height_field := SpinBox.new()

func section(parent: Container, caption: String) -> Label:
    var label := Label.new()
    label.text=caption
    label.add_theme_font_size_override("font_size",18)
    label.modulate=Color("#b4e8dd")
    parent.add_child(label)
    return label

func button(parent: Container, caption: String, action: Callable) -> Button:
    var control := Button.new()
    control.text=caption
    control.pressed.connect(action)
    parent.add_child(control)
    return control

func _ready() -> void:
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    library.load(library_path)
    var margin := MarginContainer.new()
    add_child(margin)
    for side in ["left","right","top","bottom"]:
        margin.add_theme_constant_override("margin_"+side,16)
    var layout := VBoxContainer.new()
    margin.add_child(layout)
    title.add_theme_font_size_override("font_size",25)
    layout.add_child(title)
    var body := HBoxContainer.new()
    body.size_flags_vertical=Control.SIZE_EXPAND_FILL
    body.add_theme_constant_override("separation",16)
    layout.add_child(body)
    plan.size_flags_horizontal=Control.SIZE_EXPAND_FILL
    plan.clip_contents=true
    body.add_child(plan)
    var rail := VBoxContainer.new()
    rail.custom_minimum_size.x=255
    body.add_child(rail)
    rail.add_child(preview)
    rail.add_child(design_tools)
    section(design_tools,"轮廓工具")
    var grid := CheckButton.new()
    grid.text="吸附点阵 · 0.5 米"
    grid.button_pressed=plan.snap
    grid.toggled.connect(func(value): plan.snap=value)
    design_tools.add_child(grid)
    button(design_tools,"撤回末点",undo_point)
    name_field.max_length=60
    name_field.placeholder_text="模板名称"
    design_tools.add_child(name_field)
    finish.text="保存并回大厅"
    finish.pressed.connect(save_template)
    design_tools.add_child(finish)
    button(design_tools,"返回大厅",close_design)
    rail.add_child(inspector)
    inspector.add_child(stats)
    section(inspector,"缸高（米）")
    height_field.min_value=Design.MIN_HEIGHT
    height_field.allow_greater=true
    height_field.step=.05
    height_field.value_changed.connect(set_height)
    inspector.add_child(height_field)
    hint.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
    layout.add_child(hint)
    plan.changed.connect(refresh)
    refresh()

func close_design() -> void:
    finished.emit()

func undo_point() -> void:
    var count: int=plan.draft.nodes.size()
    if plan.closed: plan.closed=false
    elif count>0:
        plan.draft.nodes.resize(count-1)
        plan.draft.bends.pop_back()
    plan.update_view()

func save_template() -> void:
    var tank: Dictionary=plan.draft.duplicate(true)
    var path := Shape.contour(tank)
    if not plan.closed or not Shape.valid(path): return
    var center := Shape.bounds(path).get_center()
    for i in tank.nodes.size(): tank.nodes[i]-=center
    var id := str(Time.get_unix_time_from_system())+"-"+str(Time.get_ticks_usec())
    tank.name=name_field.text.strip_edges()
    if tank.name=="": tank.name="异形缸 %d" % (library.get_section_keys("templates").size()+1 if library.has_section("templates") else 1)
    library.set_value("templates",id,tank)
    var temp_path := library_path + ".tmp"
    if library.save(temp_path)!=OK or DirAccess.rename_absolute(temp_path,library_path)!=OK:
        library.erase_section_key("templates",id)
        hint.text="模板写入失败，可保留轮廓并重试。"
        return
    close_design()

func set_height(value: float) -> void:
    if Design.valid_height(value): plan.draft.height=value
    refresh()

func refresh() -> void:
    title.text="定制异形缸  /  俯视轮廓"
    var path := Shape.contour(plan.draft)
    finish.disabled=not plan.closed or not Shape.valid(path)
    preview.display(plan.draft if not finish.disabled else {})
    hint.text="点击落点，点回首点闭合。拖顶点移动，拖边线或白点调弧度。"
    if plan.closed and finish.disabled: hint.text="轮廓有交叉或重合，请移动节点或调整弧线。"
    height_field.set_value_no_signal(plan.draft.height)
    var extent := Shape.bounds(path).size if path.size()>0 else Vector2.ZERO
    stats.text="%.2f × %.2f 米　高 %.2f 米" % [extent.x,extent.y,plan.draft.height]
