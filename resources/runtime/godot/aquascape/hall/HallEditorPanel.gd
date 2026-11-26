extends Control
## The hall chrome owns global commands; the object controls follow selection.
const Style = preload("HallInterfaceStyle.gd")
var architecture_ui: RefCounted
var wall_finish_picker: OptionButton
var exterior_picker: OptionButton
var exterior_material: OptionButton
var exterior_fields: VBoxContainer
var exterior_controls := {}
var exterior_dragging := false
var exterior_remembered := false
var water_panel
var side: PanelContainer
var status: Label
var mode_button: Button
var size_spin: SpinBox
var fish_spin: SpinBox
var visitor_spin: SpinBox
var parcel_label: Label
var floor_panel: HBoxContainer
var floor_label: Label
var floor_up: Button
var floor_down: Button
var lower_life_tools: Button
var catalog_button: Button
var settings: PanelContainer
var inspection_tools: HBoxContainer
var walk_observe: Button
var tank_tools: VBoxContainer
var size_row: HBoxContainer
var size_caption: Label
var feedback: Label
var undo: Button
var redo: Button
var panel_sync := false
var statistics_clock := 0.0
var catalog_open := true

func label(parent: Control, caption: String, points:=17) -> Label:
    var item := Label.new()
    item.text=caption
    item.add_theme_font_size_override("font_size",points)
    parent.add_child(item)
    return item

func button(parent: Control, caption: String, action: Callable) -> Button:
    var item := Button.new()
    item.text=caption
    item.focus_mode=Control.FOCUS_NONE
    parent.add_child(item)
    item.pressed.connect(action)
    return item

func build(host: Control) -> void:
    name="HallEditorPanel"
    theme=Style.create()
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    mouse_filter=Control.MOUSE_FILTER_IGNORE
    var header := PanelContainer.new()
    header.name="HallHeader"
    header.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
    header.offset_left=22;header.offset_top=16;header.offset_right=-22
    add_child(header)
    var row := HBoxContainer.new()
    row.add_theme_constant_override("separation",12)
    header.add_child(row)
    var emblem := Control.new()
    emblem.custom_minimum_size=Vector2(42,42)
    emblem.mouse_filter=Control.MOUSE_FILTER_IGNORE
    row.add_child(emblem)
    emblem.draw.connect(func():
        var mid := emblem.size*.5
        emblem.draw_circle(mid,19,Style.TEAL,true,-1,true)
        for j in 2:
            var wave := PackedVector2Array()
            for x in range(-13,14):
                wave.append(mid+Vector2(x,j*6-3+sin(x*.19)*2.8))
            emblem.draw_polyline(wave,Color("#d3eee0"),2.4,true)
    )
    label(row,"潮汐馆",30)
    parcel_label=label(row,"",16)
    parcel_label.add_theme_color_override("font_color",Style.MUTED)
    parcel_label.size_flags_horizontal=Control.SIZE_EXPAND_FILL
    catalog_button=button(row,"建造目录",func():catalog_open=not catalog_open)
    catalog_button.toggle_mode=true;catalog_button.button_pressed=true
    button(row,"场馆设置",func():settings.visible=not settings.visible)
    walk_observe=button(row,"观察选中缸",host.tank_session._start_inspection)
    undo=button(row,"撤销",host._undo)
    redo=button(row,"重做",host._redo)
    var menu := MenuButton.new()
    menu.text="大厅菜单 ▾";row.add_child(menu)
    for title in ["保存大厅","读取大厅","返回海岸"]:menu.get_popup().add_item(title)
    menu.get_popup().id_pressed.connect(func(id):
        if id==0:host._save_layout()
        elif id==1:host._load_layout(host.save_path)
        else:host._request_return()
    )
    mode_button=button(row,"进入逛馆",func():host._mode(not host.editing))
    Style.primary(mode_button)
    var views := PanelContainer.new()
    views.position=Vector2(22,105);add_child(views)
    floor_panel=HBoxContainer.new();views.add_child(floor_panel)
    floor_down=button(floor_panel,"−",func():host.editor._change_level(-1))
    floor_label=label(floor_panel,"1 层",19)
    floor_up=button(floor_panel,"＋",func():host.editor._change_level(1))
    button(floor_panel,"正俯视",func():host.pitch=PI/2;host.yaw=0;host.editor._fit_hall())
    button(floor_panel,"斜视",func():host.pitch=.83;host.yaw=.48;host.editor._fit_hall())
    lower_life_tools=button(floor_panel,"显示楼下",func():host.editor._set_lower_life(lower_life_tools.button_pressed))
    lower_life_tools.toggle_mode=true
    _build_settings(host)
    _build_object_actions(host)
    architecture_ui=preload("HallArchitecturePanel.gd").new()
    architecture_ui.setup(host)
    inspection_tools=HBoxContainer.new()
    inspection_tools.position=Vector2(24,185);add_child(inspection_tools)
    button(inspection_tools,"下一条鱼",host.tank_session.next_fish)
    button(inspection_tools,"返回大厅视角",host.tank_session._stop_inspection)
    var footer := HBoxContainer.new()
    footer.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
    footer.offset_left=30;footer.offset_top=-42;footer.offset_right=-30;footer.offset_bottom=-8
    footer.mouse_filter=Control.MOUSE_FILTER_IGNORE;add_child(footer)
    status=label(footer,"",17);status.size_flags_horizontal=Control.SIZE_EXPAND_FILL
    status.add_theme_color_override("font_color",Color("#e5ebe6"))
    status.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS
    feedback=label(footer,"",16)
    feedback.add_theme_color_override("font_color",Color("#a9d7c7"))
    water_panel=preload("../TankWaterPanel.gd").new()
    add_child(water_panel);water_panel.hide()
    water_panel.position=Vector2(1500,105);water_panel.size=Vector2(398,650)
    water_panel.add_theme_stylebox_override("panel",theme.get_stylebox("panel","PanelContainer"))
    water_panel.changed.connect(host.tank_session._water_changed)
    water_panel.preset_selected.connect(host.tank_session._water_preset)
    water_panel.interaction_started.connect(func():if not host.tank_session.water_drag:host._remember();host.tank_session.water_drag=true)
    water_panel.interaction_ended.connect(func():host.tank_session.water_drag=false)

func _build_settings(host: Control) -> void:
    settings=PanelContainer.new();settings.position=Vector2(22,182)
    settings.z_index=3;add_child(settings);settings.hide()
    var body := VBoxContainer.new();body.add_theme_constant_override("separation",10);settings.add_child(body)
    label(body,"场馆设置",23)
    var finishes := HBoxContainer.new();body.add_child(finishes)
    button(finishes,"全馆地面配色",func():host.editor._change_finish("floor_style"))
    button(finishes,"原有墙面配色",func():host.editor._change_finish("wall_style"))
    var wall_row := HBoxContainer.new();body.add_child(wall_row)
    label(wall_row,"全馆墙面材质")
    wall_finish_picker=OptionButton.new();wall_row.add_child(wall_finish_picker)
    for entry in preload("HallArchitecture.gd").WALL_NAMES:wall_finish_picker.add_item(entry)
    wall_finish_picker.item_selected.connect(func(index):host._execute_build("style",{"key":"wall_finish","value":index}))
    _build_exterior_settings(body,host)
    button(body,"分区铺地材…",func():
        settings.hide();catalog_open=true;host.build_editor.palette.show_category("地面");host.build_editor.choose("finish"))
    button(body,"建造墙、门洞、窗洞和柱子…",func():
        settings.hide();catalog_open=true;host.editor._set_tool("");host.build_editor.palette.show_category("墙和柱"))
    label(body,"选中自建墙：独立选择材质、造型、厚度和洞口。",15)
    var visitors := HBoxContainer.new();body.add_child(visitors)
    label(visitors,"预览游客人数")
    visitor_spin=SpinBox.new();visitor_spin.max_value=200;visitor_spin.value=24
    visitors.add_child(visitor_spin)
    visitor_spin.value_changed.connect(func(v):if is_instance_valid(host.visitor_crowd):host.visitor_crowd.set_visitor_count(int(v)))
    button(visitors,"清零",func():visitor_spin.value=0)
    button(body,"收起设置",settings.hide)

func _build_exterior_settings(body: VBoxContainer,host: Control) -> void:
    var row := HBoxContainer.new();body.add_child(row);label(row,"自动外墙造型")
    exterior_picker=OptionButton.new();row.add_child(exterior_picker)
    exterior_picker.add_item("普通平墙");exterior_picker.add_item("凹凸岩壁")
    exterior_picker.item_selected.connect(func(index):_patch_exterior(host,{"profile":"rock" if index==1 else "plain"}))
    exterior_fields=VBoxContainer.new();body.add_child(exterior_fields)
    var material_row := HBoxContainer.new();exterior_fields.add_child(material_row);label(material_row,"外墙岩面材质")
    exterior_material=OptionButton.new();material_row.add_child(exterior_material)
    for entry in preload("HallArchitecture.gd").WALL_NAMES:exterior_material.add_item(entry)
    exterior_material.item_selected.connect(func(index):_patch_exterior(host,{"finish":index}))
    for spec in [["depth","单侧凸出上限",.1,1.2,.05],["relief","起伏程度",0,1,.05],["size","岩块大小",.6,2,.1]]:
        var line := HBoxContainer.new();exterior_fields.add_child(line)
        var title := label(line,spec[1],15);title.custom_minimum_size.x=150
        var slider := HSlider.new();slider.min_value=spec[2];slider.max_value=spec[3];slider.step=spec[4];slider.custom_minimum_size=Vector2(160,24);line.add_child(slider)
        var number := label(line,"",15);number.custom_minimum_size.x=64
        exterior_controls[spec[0]]={"slider":slider,"label":number}
        slider.drag_started.connect(func():exterior_dragging=true;exterior_remembered=false)
        slider.drag_ended.connect(func(_changed):exterior_dragging=false;exterior_remembered=false)
        slider.value_changed.connect(func(value):_patch_exterior(host,{spec[0]:value}))
    label(exterior_fields,"凸出会占用馆内空间，游客自动绕开。",15)

func _patch_exterior(host: Control,fields: Dictionary) -> void:
    if panel_sync:return
    if host._execute_build("exterior",{"patch":fields},not exterior_dragging or not exterior_remembered):
        if exterior_dragging:exterior_remembered=true
    else:host._sync_panel()

func _build_object_actions(host: Control) -> void:
    side=PanelContainer.new();add_child(side)
    side.position=Vector2(1500,372);side.size.x=398
    var body := VBoxContainer.new();side.add_child(body);body.add_theme_constant_override("separation",9)
    var actions := HBoxContainer.new();body.add_child(actions)
    button(actions,"左转",func():host.editor._rotate_selected(-1))
    button(actions,"右转",func():host.editor._rotate_selected(1))
    button(actions,"删除物件",host.editor._delete_selected)
    size_row=HBoxContainer.new();body.add_child(size_row)
    size_caption=label(size_row,"缩放倍率");size_caption.size_flags_horizontal=Control.SIZE_EXPAND_FILL
    size_spin=SpinBox.new();size_row.add_child(size_spin)
    size_spin.value_changed.connect(func(v):if not panel_sync:host.editor._resize_selected(v))
    tank_tools=VBoxContainer.new();body.add_child(tank_tools)
    var stock := HBoxContainer.new();tank_tools.add_child(stock)
    label(stock,"展示鱼数").size_flags_horizontal=Control.SIZE_EXPAND_FILL
    fish_spin=SpinBox.new();fish_spin.max_value=15;stock.add_child(fish_spin)
    fish_spin.value_changed.connect(func(v):if not panel_sync:host.editor._fish_count_changed(v))
    var tank_actions := HBoxContainer.new();tank_tools.add_child(tank_actions)
    button(tank_actions,"编辑造景",host.tank_session._open_content_editor)
    button(tank_actions,"水体",host.tank_session._open_water_panel)
    button(tank_actions,"观察",host.tank_session._start_inspection)

func sync(host: Control) -> void:
    if not is_instance_valid(side):return
    panel_sync=true
    wall_finish_picker.select(int(host._state().get("wall_finish",0)))
    var exterior := preload("HallExteriorWall.gd").settings(host._state())
    exterior_picker.select(1 if exterior.profile=="rock" else 0);exterior_fields.visible=exterior.profile=="rock"
    exterior_material.select(int(exterior.finish))
    for key in exterior_controls:
        exterior_controls[key].slider.set_value_no_signal(float(exterior[key]))
        exterior_controls[key].label.text="%.2f%s" % [exterior[key],"" if key=="relief" else " m"]
    parcel_label.text="  /  %s    ·    %s m²" % ["布展" if host.editing else "逛馆",host.parcels.size()*42]
    mode_button.text="进入逛馆" if host.editing else "返回布展"
    floor_panel.get_parent().visible=host.editing and not host.tank_session.inspecting
    floor_panel.visible=floor_panel.get_parent().visible
    floor_label.text=" %d 层 " % (host.active_level+1)
    floor_up.disabled=host.active_level>=host.highest_level
    floor_down.disabled=host.active_level==0
    lower_life_tools.visible=host.active_level>0
    walk_observe.visible=not host.editing and not host.tank_session.inspecting and host.selected>=0 and host.objects[host.selected].tank!=null
    undo.disabled=host.history.is_empty();redo.disabled=host.future.is_empty()
    catalog_button.visible=host.editing and not host.tank_session.inspecting
    if not host.editing:water_panel.hide()
    if host.selected>=0 and host.selected<host.objects.size():
        var data: Dictionary=host.objects[host.selected].data
        size_row.visible=data.kind!="stair"
        size_caption.text="墙段长度（米）" if data.kind=="wall" else "缩放倍率"
        size_spin.min_value=3 if data.kind=="wall" and data.get("door",false) else (.5 if data.kind=="wall" else .4)
        size_spin.max_value=18 if data.kind=="wall" else 1.3
        size_spin.step=.5 if data.kind=="wall" else .05
        size_spin.set_value_no_signal(float(data.length) if data.kind=="wall" else float(data.scale))
        tank_tools.visible=data.kind=="tank"
        fish_spin.set_value_no_signal(float(data.get("fish_count",0)))
        if data.kind=="tank":water_panel.bind(data.water,data.name)
        else:water_panel.hide()
    else:water_panel.hide()
    panel_sync=false
    architecture_ui.sync()

func tick(delta: float, notice: String) -> void:
    statistics_clock+=delta
    if statistics_clock>.12:
        statistics_clock=0
        status.text=notice

func choose_tank_size(host: Control, index: int) -> void:
    host.editor.set_tank_size(index)

func set_tool_feedback(_kind: String, allowed: bool) -> void:
    feedback.text="可放置" if allowed else "不可放置"
