extends TabContainer
const Interior=preload("ShellInterior.gd")
const Fish=preload("../FishDisplayCatalog.gd")
var session: RefCounted
var decor:=OptionButton.new()
var prop_modes:=HBoxContainer.new()
var prop_mode_buttons: Dictionary={}
var prop_label:=Label.new()
var algae_toggle:=CheckButton.new()
var species:=OptionButton.new()
var stock_button:=Button.new()
var retrieve_button:=Button.new()
var brightness:=HSlider.new()
var tint:=OptionButton.new()
var brush:=HSlider.new()
var status:=Label.new()
var tool:="raise"
var modes:=["raise","place","fish_idle",""]
var last_stock: Dictionary={}

func setup(owner_session: RefCounted,bed_page: VBoxContainer) -> void:
    session=owner_session
    var style=preload("../hall/HallInterfaceStyle.gd")
    add_theme_stylebox_override("panel",style.box(style.PAPER,style.PAPER,6,2,8))
    add_theme_stylebox_override("tab_selected",style.box(style.TEAL,style.TEAL,6,10,6))
    add_theme_stylebox_override("tab_unselected",style.box(style.PAPER,style.PAPER,6,10,6))
    add_theme_color_override("font_selected_color",Color.WHITE)
    add_theme_color_override("font_unselected_color",style.MUTED)
    add_theme_color_override("font_hovered_color",style.INK)
    for label in ["底床","布景","鱼只","灯光"]:
        var page:=bed_page if get_child_count()==0 else VBoxContainer.new()
        page.name=label
        add_child(page)
    add_modes(bed_page,{"堆沙":"raise","挖沙":"lower"},0)
    slider(bed_page,"笔刷半径（米）",brush,.1,1.5,.05)
    brush.value=.4
    var props:=get_child(1)
    props.add_child(decor)
    for id in Interior.assets():
        decor.add_item(Interior.assets()[id].name_zh)
        decor.set_item_metadata(decor.item_count-1,id)
    add_modes(props,{"摆放":"place","变换":"move_prop","移除":"remove_prop"},1)
    props.add_child(prop_label)
    props.add_child(prop_modes)
    algae_toggle.text="藻覆盖"
    algae_toggle.hide()
    algae_toggle.toggled.connect(func(enabled: bool):
        if not session.prop_editor.set_selected_algae(enabled):
            algae_toggle.set_pressed_no_signal(not enabled)
    )
    props.add_child(algae_toggle)
    var group:=ButtonGroup.new()
    for spec in [["move","移动 W"],["rotate","旋转 E"],["scale","缩放 R"]]:
        var mode:String=spec[0]
        var button:=Button.new()
        button.text=spec[1]
        button.toggle_mode=true
        button.button_group=group
        button.focus_mode=Control.FOCUS_NONE
        button.size_flags_horizontal=Control.SIZE_EXPAND_FILL
        button.pressed.connect(func():set_prop_mode(mode))
        prop_modes.add_child(button)
        prop_mode_buttons[mode]=button
    prop_label.hide()
    prop_modes.hide()
    var fish:=get_child(2)
    fish.add_child(species)
    var actions:=HBoxContainer.new()
    fish.add_child(actions)
    actions.add_child(stock_button)
    stock_button.text="放鱼"
    style.primary(stock_button)
    stock_button.pressed.connect(stock_fish)
    actions.add_child(retrieve_button)
    retrieve_button.text="收回"
    retrieve_button.toggle_mode=true
    retrieve_button.toggled.connect(func(active):
        modes[2]="remove_fish" if active else "fish_idle"
        set_tool(modes[2]))
    var lights:=get_child(3)
    for color in ["自然白","暖光","冷光"]:tint.add_item(color)
    lights.add_child(tint)
    slider(lights,"亮度",brightness,0,3,.05)
    brightness.value_changed.connect(func(v):session.update_bed({"brightness":v}))
    tint.item_selected.connect(func(i):session.update_bed({"tint":["neutral","warm","cool"][i]}))
    tab_changed.connect(func(i):set_tool(modes[i]))
    status.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART

func slider(page: Control,label: String,control: HSlider,low: float,high: float,step: float) -> void:
    var text:=Label.new()
    text.text=label
    page.add_child(text)
    control.min_value=low;control.max_value=high;control.step=step
    page.add_child(control)

func add_modes(page: Control,options: Dictionary,index: int) -> void:
    var line:=HBoxContainer.new()
    page.add_child(line)
    var group:=ButtonGroup.new()
    for label in options:
        var button:=Button.new()
        var id:String=options[label]
        button.text=label;button.toggle_mode=true;button.button_group=group
        button.button_pressed=id==modes[index]
        button.pressed.connect(func():modes[index]=id;set_tool(id))
        line.add_child(button)

func set_tool(id: String) -> void:
    if tool=="move_prop" and id!=tool:session.prop_editor.clear_selection()
    tool=id
    status.text={"raise":"按住左键在缸底堆沙。","lower":"按住左键挖低底床。","place":"选择布景，再点缸底摆放。","move_prop":"点击选中要调整的布景或水草。","remove_prop":"点击要移除的布景。","fish_idle":"选择鱼种，点「放鱼」即可入缸。","remove_fish":"点击正在游动的鱼即可收回。","":"调节这只展缸的灯色和亮度。"}[id]
    if id=="fish_idle" and species.item_count==0:status.text="仓库里暂无可放入的鱼。"

func select_prop(item: Dictionary) -> void:
    prop_label.text=Interior.assets()[item.id].name_zh if not item.is_empty() else ""
    prop_label.visible=not item.is_empty()
    algae_toggle.visible=not item.is_empty() and Interior.supports_algae(item.id)
    algae_toggle.set_pressed_no_signal(item.get("algae",false))
    prop_modes.visible=prop_label.visible
    if prop_label.visible:set_prop_mode(session.prop_editor.gizmo.mode)
    else:status.text="点击选中要调整的布景或水草。"

func set_prop_mode(mode: String) -> void:
    session.prop_editor.set_mode(mode)
    for key in prop_mode_buttons:
        prop_mode_buttons[key].set_pressed_no_signal(key==mode)
    status.text={
        "move":"拖动轴箭头沿指定方向移动，也可直接拖物件贴着底床移动。",
        "rotate":"拖动圆环绕对应轴旋转。",
        "scale":"拖动轴端方块按轴缩放，拖动中心方块等比缩放。"
    }[mode]

func sync(bed: Dictionary, entering: bool) -> void:
    brightness.set_value_no_signal(bed.get("brightness",1.0))
    tint.select(["neutral","warm","cool"].find(bed.get("tint","neutral")))
    var available:Dictionary=session.available_fish()
    if available!=last_stock or entering:
        var previous = species.get_selected_metadata() if species.selected>=0 else ""
        species.clear()
        for id in Fish.SPECIES:
            if not available.has(id):continue
            var count:int=available[id].size()
            species.add_item(Fish.LABELS[id]+(" × %d"%count if session.hall.warehouse_linked else ""))
            species.set_item_metadata(species.item_count-1,id)
            if previous==id:species.select(species.item_count-1)
        last_stock=available
        stock_button.disabled=species.selected<0
    if entering:
        current_tab=0
        set_tool(modes[0])

func stock_fish() -> void:
    if session.mode!="interior" or species.selected<0:return
    retrieve_button.button_pressed=false
    var id:String=species.get_selected_metadata()
    var available:Dictionary=session.available_fish()
    if not available.has(id):return
    var bed:Dictionary=session.draft.get("interior",preload("FinishedShell.gd").DEFAULT_BED).duplicate()
    var uv:Variant=Interior.swim_position(session.draft.design,bed,id)
    if uv==null:
        status.text="这个缸的水深或转身空间不足，放不下%s。"%Fish.LABELS[id]
        return
    var item:={"id":id,"u":uv.x,"v":uv.y}
    if session.hall.warehouse_linked:item.stock=available[id][0]
    var fish:Array=bed.get("fish",[]).duplicate()
    fish.append(item)
    bed.fish=fish
    if session.change({"interior":bed}):
        sync(bed,false)
        status.text="已放入一条%s。"%Fish.LABELS[id]

func use_at(p: Vector2) -> void:
    if tool not in ["raise","lower","place"]:return
    var design:Dictionary=session.draft.design
    var bed:Dictionary=session.draft.get("interior",preload("FinishedShell.gd").DEFAULT_BED).duplicate(true)
    var bounds:=Interior.bounds(design)
    var uv:=(p-bounds.position)/bounds.size
    var gap:=Interior.clearance(p,preload("ShellDesign.gd").contour(design))
    if gap<=.001:status.text="请点展缸轮廓以内。";return
    if tool in ["raise","lower"]:
        Interior.sculpt(bed,uv,bounds.size,tool=="raise",maxf(brush.value,bounds.size[bounds.size.max_axis_index()]/Interior.GRID),design.height)
    else:
        var items:Array=bed.get("props",[])
        items.append({"id":decor.get_selected_metadata(),"u":uv.x,"v":uv.y})
        bed.props=items
    if not session.change({"interior":bed}):
        status.text="这里的水深或转身空间不足，请换个位置或调整缸形。"
    else:set_tool(tool)
