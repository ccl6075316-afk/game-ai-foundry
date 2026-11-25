extends PanelContainer
## Tank-instance properties. Only JSON patches enter the hall's edit history.
var hall: Control
var bound_data: Dictionary={}
const Design = preload("ShellDesign.gd")
var height_field: SpinBox
var title := Label.new()
var dimensions := Label.new()
var diagram := Control.new()
var outline := PackedVector2Array()
var hint := Label.new()
var corners := VBoxContainer.new()
var radius_fields: Array[SpinBox]=[]
var sliders: Array[HSlider]=[]
var shape_tools := VBoxContainer.new()
var placement_tools := VBoxContainer.new()
var interior_tools := preload("ShellInteriorPanel.gd").new()
var edits := HBoxContainer.new()
var overview := HBoxContainer.new()
var apply_button := Button.new()
var passage_button := Button.new()
var substrate := OptionButton.new()
var depth := SpinBox.new()
var bound_mode := "none"
var session: RefCounted
const Finished=preload("FinishedShell.gd")
var coordinates: Array[SpinBox]=[]
var syncing := false

func setup(owner_hall: Control) -> void:
    hall=owner_hall
    session=hall.build_editor.shells.session
    var body := VBoxContainer.new()
    body.add_theme_constant_override("separation",12)
    add_child(body)
    var banner := PanelContainer.new()
    var style := preload("../hall/HallInterfaceStyle.gd")
    banner.add_theme_stylebox_override("panel",style.box(style.INK,style.INK,8,12,10))
    body.add_child(banner)
    var header := HBoxContainer.new()
    header.add_theme_constant_override("separation",12)
    banner.add_child(header)
    diagram.custom_minimum_size=Vector2(75,55)
    diagram.draw.connect(_draw_plan)
    header.add_child(diagram)
    var text := VBoxContainer.new()
    header.add_child(text)
    title.add_theme_font_size_override("font_size",23)
    title.add_theme_color_override("font_color",Color.WHITE)
    text.add_child(title)
    dimensions.add_theme_font_size_override("font_size",15)
    dimensions.add_theme_color_override("font_color",Color("#b6e3d3"))
    text.add_child(dimensions)
    hint.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
    hint.add_theme_font_size_override("font_size",15)
    hint.add_theme_color_override("font_color",Color("#486264"))
    body.add_child(hint)
    body.add_child(shape_tools)
    shape_tools.add_theme_constant_override("separation",9)
    height_field=add_field(shape_tools,"缸高（米）",Design.MIN_HEIGHT,100,.05)
    height_field.allow_greater=true
    height_field.value_changed.connect(change_height)
    shape_tools.add_child(corners)
    corners.add_theme_constant_override("separation",7)
    var heading := Label.new()
    heading.text="圆角半径（米）"
    heading.add_theme_font_size_override("font_size",19)
    corners.add_child(heading)
    for corner in ["左上","右上","右下","左下"]:
        var index := radius_fields.size()
        var field := add_field(corners,corner,0,8,.01)
        var line := field.get_parent()
        var slider := HSlider.new()
        slider.min_value=0
        slider.step=.01
        slider.custom_minimum_size=Vector2(115,30)
        slider.size_flags_horizontal=Control.SIZE_EXPAND_FILL
        line.add_child(slider);line.move_child(slider,1)
        sliders.append(slider)
        slider.value_changed.connect(change_radius.bind(index))
        radius_fields.append(field)
        field.value_changed.connect(change_radius.bind(index))
    body.add_child(interior_tools)
    var bed_page:=VBoxContainer.new()
    interior_tools.setup(session,bed_page)
    body.add_child(interior_tools.status)
    var substrate_title:=Label.new();substrate_title.text="底床材料";bed_page.add_child(substrate_title)
    bed_page.add_child(substrate)
    for id in Finished.BEDS:substrate.add_item(Finished.BEDS[id][0])
    substrate.item_selected.connect(func(_index):change_interior())
    depth=add_field(bed_page,"厚度（厘米）",0,20,.5)
    depth.value_changed.connect(func(_v):change_interior())
    body.add_child(edits)
    edits.add_child(apply_button)
    style.primary(apply_button)
    apply_button.pressed.connect(session.save)
    var discard:=Button.new();discard.text="取消";edits.add_child(discard);discard.pressed.connect(session.cancel)
    body.add_child(overview)
    for kind in ["shape","interior"]:
        var edit:=Button.new()
        edit.text="编辑缸形" if kind=="shape" else "编辑内部"
        overview.add_child(edit)
        edit.pressed.connect(func():
            if hall.selected>=0:
                var row:Dictionary=hall.objects[hall.selected]
                session.begin(kind,row.data,row))
    passage_button.text="观景通道"
    overview.add_child(passage_button)
    passage_button.pressed.connect(edit_passage)
    body.add_child(placement_tools)
    placement_tools.add_theme_constant_override("separation",8)
    var placement := Label.new()
    placement_tools.add_child(HSeparator.new())
    placement.text="摆放位置（米）"
    placement_tools.add_child(placement)
    for axis in ["X","Z"]:
        var index := coordinates.size()
        var field := add_field(placement_tools,axis,-100,100,.05)
        field.allow_greater=true;field.allow_lesser=true
        coordinates.append(field)
        field.value_changed.connect(change_position.bind(index))

    var actions := HBoxContainer.new()
    placement_tools.add_child(actions)
    for direction in [-1,1]:
        var turn := Button.new()
        turn.text="左转" if direction<0 else "右转"
        turn.pressed.connect(hall.editor._rotate_selected.bind(direction))
        actions.add_child(turn)
    var remove := Button.new()
    remove.text="删除展缸"
    remove.add_theme_color_override("font_color",Color("#954639"))
    remove.pressed.connect(hall.editor._delete_selected)
    actions.add_child(remove)
    hide()

func _draw_plan() -> void:
    if outline.size()<3:return
    var bounds := preload("Footprint.gd").bounds(outline)
    var factor := minf((diagram.size.x-8)/bounds.size.x,(diagram.size.y-8)/bounds.size.y)
    var points := PackedVector2Array()
    for point in outline:points.append((point-bounds.get_center())*factor+diagram.size*.5)
    diagram.draw_colored_polygon(points,Color("#458d85"))
    points.append(points[0])
    diagram.draw_polyline(points,Color("#b4eed9"),2,true)

func add_field(parent: Control,caption: String,minimum: float,maximum: float,step_value: float) -> SpinBox:
    var line := HBoxContainer.new()
    parent.add_child(line)
    var label := Label.new()
    label.text=caption
    label.custom_minimum_size.x=72
    line.add_child(label)
    var field := SpinBox.new()
    field.min_value=minimum
    field.max_value=maximum
    field.step=step_value
    field.size_flags_horizontal=Control.SIZE_EXPAND_FILL
    line.add_child(field)
    return field

func bind_row(row: Dictionary) -> void:
    visible=not row.is_empty()
    if row.is_empty():
        bound_data={}
        return
    var data: Dictionary=row.data
    if bound_data==data and bound_mode==session.mode:return
    var entering:bool=bound_mode!=session.mode
    bound_mode=session.mode
    shape_tools.visible=bound_mode=="shape"
    interior_tools.visible=bound_mode=="interior"
    interior_tools.status.visible=interior_tools.visible
    edits.visible=bound_mode!=""
    overview.visible=bound_mode==""
    placement_tools.visible=bound_mode==""
    apply_button.text="保存缸形" if bound_mode=="shape" else "保存内部"
    syncing=true
    bound_data=data
    passage_button.text="新建通道" if data.get("interior",{}).get("passage",{}).is_empty() else "编辑通道"
    title.text=data.name+"缸" if data.design.kind in ["rect","ellipse"] and not data.name.ends_with("缸") else data.name
    outline=Design.contour(data.design)
    diagram.queue_redraw()
    var extent: Vector3=hall._bounds(data).size*float(data.scale)
    dimensions.text="长 %.2f　宽 %.2f　高 %.2f 米" % [extent.x,extent.z,extent.y]
    hint.text="拖外框边线或顶点等比缩放，拖蓝点调高。" if data.design.kind=="custom" else "拖边线调长或宽，拖顶点同时调长宽。拖蓝点调高。"
    if bound_mode=="interior":
        hint.text="调整这个展缸的底床。"
        var interior:Dictionary=data.get("interior",Finished.DEFAULT_BED)
        substrate.select(Finished.BEDS.keys().find(interior.substrate))
        depth.set_value_no_signal(interior.depth_cm)
        interior_tools.sync(interior,entering)
    hint.visible=bound_mode=="shape"
    height_field.min_value=Design.MIN_HEIGHT*data.scale
    height_field.set_value_no_signal(extent.y)
    corners.visible=data.design.kind=="rect"
    if corners.visible:
        for i in radius_fields.size():
            var field := radius_fields[i]
            field.max_value=minf(extent.x,extent.z)*.5
            sliders[i].max_value=field.max_value
            sliders[i].set_value_no_signal(data.design.radii[i]*data.scale)
            field.set_value_no_signal(data.design.radii[i]*data.scale)
    for i in coordinates.size(): coordinates[i].set_value_no_signal(data.at[i])
    syncing=false

func current() -> Dictionary:
    if syncing or not visible:return {}
    if session.mode!="":return session.draft
    if hall.selected<0:return {}
    var data: Dictionary=hall.objects[hall.selected].data
    return data if data.id==bound_data.get("id","") and data.kind=="shell" else {}

func change_height(value: float) -> void:
    var data := current()
    if data.is_empty(): return
    var design: Dictionary=data.design.duplicate(true)
    design.height=value/data.scale
    if session.mode=="shape" and session.change({"design":design}):
        session.frame_height()
    else:
        bound_data={}

func change_radius(value: float,index: int) -> void:
    var data := current()
    if data.is_empty() or data.design.kind!="rect": return
    var design: Dictionary=data.design.duplicate(true)
    design.radii[index]=minf(value/data.scale,minf(design.width,design.depth)*.5)
    if is_equal_approx(design.radii[index],data.design.radii[index]):return
    if session.mode=="shape" and not session.change({"design":design}):bound_data={}

func change_interior() -> void:
    if syncing or session.mode!="interior":return
    var id: String=Finished.BEDS.keys()[substrate.selected]
    var fields: Dictionary={"substrate":id,"depth_cm":depth.value}
    if id=="bare":fields.merge({"depth_cm":0,"heights":[]},true)
    session.update_bed(fields)

func change_position(value: float,index: int) -> void:
    var data := current()
    if data.is_empty(): return
    var at: Array=data.at.duplicate()
    at[index]=value
    if not hall._execute_build("patch",{"id":data.id,"patch":{"at":at}}):
        bound_data={}

func edit_passage() -> void:
    if session.mode!="" or hall.selected<0 or hall.selected>=hall.objects.size():return
    var row:Dictionary=hall.objects[hall.selected]
    if row.data.kind!="shell" or row.data.id!=bound_data.get("id"):return
    var id:String=row.data.id
    if not session.begin("interior",row.data,row):return
    await get_tree().process_frame
    await get_tree().process_frame
    if session.mode!="interior" or session.draft.get("id")!=id:return
    interior_tools.current_tab=4
    interior_tools.set_tool("passage")
    interior_tools.status.text="编辑当前选中展缸的通道。点击节点选中后调整，完成后保存内部。"
