extends RefCounted
const Architecture=preload("HallArchitecture.gd")
var host: Control
var object_fields: VBoxContainer
var object_scroll: ScrollContainer
var rock_controls := {}
var rock_labels := {}
var region_panel: PanelContainer
var finish: OptionButton
var ceiling: SpinBox
var controls := {}
var labels := {}
var opening: OptionButton
var wall_finish: OptionButton
var trim_finish: OptionButton
var wall_profile: OptionButton
var round_column: CheckBox
var region_help: Label
var syncing := false
var sculpt_dragging := false
var sculpt_remembered := false

func setup(owner: Control) -> void:
    host=owner
    object_scroll=ScrollContainer.new();object_scroll.custom_minimum_size=Vector2(0,340);object_scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
    host.panel.side.get_child(0).add_child(object_scroll)
    object_fields=VBoxContainer.new();object_fields.size_flags_horizontal=Control.SIZE_EXPAND_FILL;object_scroll.add_child(object_fields)
    for spec in [["height","高度（米）",.8,20,.1],["thickness","墙体厚度（米）",.12,1.2,.02],["width","柱宽 / 直径",.3,2,.1],
        ["opening_width","洞口宽度",.8,12,.1],["opening_height","洞口高度",.6,15,.1],
        ["opening_offset","洞口左右偏移",-9,9,.1],["sill","窗台高度",.3,5,.1]]:
        var row := HBoxContainer.new();object_fields.add_child(row)
        var label := Label.new();label.text=spec[1];label.size_flags_horizontal=Control.SIZE_EXPAND_FILL;row.add_child(label)
        var spin := SpinBox.new();spin.min_value=spec[2];spin.max_value=spec[3];spin.step=spec[4];row.add_child(spin)
        controls[spec[0]]=spin;labels[spec[0]]=row
        spin.value_changed.connect(func(v):patch({spec[0]:v}))
    wall_profile=_choice("墙体造型",Architecture.WALL_PROFILE_NAMES)
    object_fields.move_child(wall_profile.get_parent(),0)
    wall_profile.item_selected.connect(func(index):
        var values := {"wall_profile":Architecture.WALL_PROFILES[index]}
        if Architecture.WALL_PROFILES[index]=="rock":values.wall_finish=5
        patch(values))
    for spec in [["rock_depth","单侧凸出",.1,1.2,.05],["rock_relief","起伏程度",0,1,.05],["rock_size","岩块大小",.6,2,.1]]:
        var row := VBoxContainer.new();object_fields.add_child(row);object_fields.move_child(row,rock_controls.size()+1)
        var label := Label.new();row.add_child(label);rock_labels[spec[0]]=label
        var slider := HSlider.new();slider.min_value=spec[2];slider.max_value=spec[3];slider.step=spec[4];slider.custom_minimum_size.y=24;row.add_child(slider)
        rock_controls[spec[0]]=slider
        slider.drag_started.connect(func():sculpt_dragging=true;sculpt_remembered=false)
        slider.drag_ended.connect(func(_changed):sculpt_dragging=false;sculpt_remembered=false)
        slider.value_changed.connect(func(value):_sculpt(spec[0],value))
    wall_finish=_choice("墙面材质",["跟随全馆墙面"]+Architecture.WALL_NAMES)
    wall_finish.item_selected.connect(func(index):patch({"wall_finish":index-1}))
    trim_finish=_choice("墙裙 / 饰边",["同墙面材质"]+Architecture.WALL_NAMES)
    trim_finish.item_selected.connect(func(index):patch({"trim_finish":index-1}))
    opening=OptionButton.new();object_fields.add_child(opening)
    for title in ["实心墙","通行门洞","观景窗洞"]:opening.add_item(title)
    opening.item_selected.connect(func(index):patch({"opening":["none","door","window"][index],"door":index==1}))
    round_column=CheckBox.new();round_column.text="圆柱";object_fields.add_child(round_column)
    round_column.toggled.connect(func(v):patch({"round":v}))
    region_panel=PanelContainer.new();region_panel.position=Vector2(22,170);host.add_child(region_panel)
    region_panel.theme=host.panel.theme
    var box := VBoxContainer.new();region_panel.add_child(box)
    var title := Label.new();title.text="区域设置 · 点击或拖动矩形";box.add_child(title)
    finish=OptionButton.new();box.add_child(finish)
    for name in Architecture.FINISH_NAMES:finish.add_item(name)
    finish.item_selected.connect(func(index):host.editor.region_finish=index;host.editor.floor_preview_key=[])
    var row := HBoxContainer.new();box.add_child(row)
    var label := Label.new();label.text="天花净高（米）";row.add_child(label)
    ceiling=SpinBox.new();ceiling.min_value=2.4;ceiling.max_value=20;ceiling.step=.1;ceiling.value=6.6;row.add_child(ceiling)
    ceiling.value_changed.connect(func(v):host.editor.ceiling_height=v;host.editor.floor_preview_key=[])
    region_help=Label.new();region_help.text="天花在布展时隐藏，逛馆时显示。
上层楼板已作为天花的区域无需另铺。";box.add_child(region_help)
    sync()

func _choice(title: String,names: Array) -> OptionButton:
    var row := HBoxContainer.new();object_fields.add_child(row)
    var label := Label.new();label.text=title;label.size_flags_horizontal=Control.SIZE_EXPAND_FILL;row.add_child(label)
    var choice := OptionButton.new();row.add_child(choice)
    for entry in names:choice.add_item(entry)
    return choice

func patch(fields: Dictionary) -> void:
    if syncing or host.selected<0:return
    var data: Dictionary=host.objects[host.selected].data
    if not host._execute_build("patch",{"id":data.id,"patch":fields}):host._sync_panel()

func _sculpt(key: String,value: float) -> void:
    if syncing or host.selected<0:return
    var data: Dictionary=host.objects[host.selected].data
    var remember := not sculpt_dragging or not sculpt_remembered
    if host._execute_build("patch",{"id":data.id,"patch":{key:value}},remember):
        if sculpt_dragging:sculpt_remembered=true
    else:host._sync_panel()

func sync() -> void:
    syncing=true
    var tool: String=host.editor.pending_kind
    region_panel.visible=host.editing and tool in Architecture.REGION_TOOLS
    region_help.visible=tool.begins_with("ceiling")
    finish.visible=tool=="finish"
    finish.select(host.editor.region_finish)
    ceiling.get_parent().visible=tool=="ceiling"
    var data: Dictionary={}
    if host.selected>=0 and host.selected<host.objects.size():data=host.objects[host.selected].data
    object_fields.visible=host.editing and tool=="" and data.get("kind","") in ["wall","column"]
    object_scroll.visible=object_fields.visible
    if object_fields.visible:
        var wall: bool=data.kind=="wall"
        for key in rock_controls:
            rock_controls[key].get_parent().visible=wall and data.get("wall_profile", "plain")=="rock"
            var value := float(data.get(key,{"rock_depth":.65,"rock_relief":.75,"rock_size":1.1}[key]))
            rock_controls[key].set_value_no_signal(value)
            rock_labels[key].text={"rock_depth":"单侧凸出上限  %.2f 米","rock_relief":"起伏程度  %.2f","rock_size":"岩块大小  %.2f 米"}[key] % value
        var hole := Architecture.aperture(data)
        var defaults := {"height":Architecture.height(data),"thickness":.18,"width":.6,"opening_width":hole.size.x,"opening_height":hole.size.y,"opening_offset":hole.get_center().x,"sill":1.0}
        controls.height.min_value=.8 if wall else 2.4
        for key in controls:
            controls[key].set_value_no_signal(float(data.get(key,defaults[key])))
            labels[key].visible=key=="height" or (key=="thickness" and wall) or (key=="width" and not wall) or (wall and key.begins_with("opening_") and Architecture.opening(data)!="none") or (wall and key=="sill" and Architecture.opening(data)=="window")
        wall_profile.get_parent().visible=wall;wall_finish.get_parent().visible=wall
        trim_finish.get_parent().visible=wall and data.get("wall_profile", "plain")!="rock"
        wall_profile.select(Architecture.WALL_PROFILES.find(data.get("wall_profile","plain")))
        wall_finish.select(int(data.get("wall_finish",-1))+1);trim_finish.select(int(data.get("trim_finish",-1))+1)
        opening.visible=wall;opening.select(["none","door","window"].find(Architecture.opening(data)))
        round_column.visible=not wall;round_column.set_pressed_no_signal(data.get("round",false))
    syncing=false
