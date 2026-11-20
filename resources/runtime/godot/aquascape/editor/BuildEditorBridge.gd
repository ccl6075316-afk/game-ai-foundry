extends RefCounted
## Adapts shared editor controls to hall document commands or tank edit session.
var host: Control
var tank := false
var palette: Control
var gizmo: Control
var drag_asset := ""
var before: Dictionary={}
var selected_node: Node3D
var selection_key := ""
var inspector: Control
var thumbnails: Node
var shells: RefCounted
var shell_inspector: Control

func setup(owner_value: Control,in_tank: bool) -> void:
    host=owner_value;tank=in_tank
    palette=preload("res://scripts/aquarium/editor/BuildPalette.gd").new();host.add_child(palette)
    palette.position=Vector2(0,710) if tank else Vector2(22,814)
    palette.size=Vector2(1440,190) if tank else Vector2(1420,210)
    var items: Array=[]
    if tank:
        for row in host.decor_entries:
            var category: String={"rock":"石头","wood":"沉木","decor":"人工摆件"}.get(row.get("category","decor"),"人工摆件")
            var name_value: String=row.name_zh
            items.append({"id":row.id,"label":name_value,"category":category,"preview":load(row.material_dir+"/"+row.id+"-front.png")})
        for i in 5:
            var path: String="res://assets/aquascape-sand-v1/fine-sand.png" if i==0 else "res://assets/aquascape-substrates-v2/"+host.SUBSTRATE_BED.MATERIAL_IDS[i]+".png"
            items.append({"id":"substrate_"+str(i),"label":host.SUBSTRATE_NAMES[i],"category":"底床材料","preview":load(path)})
        for pair in [["pour","倒沙 / 堆高"],["remove","吸沙"],["smooth","整平"],["paint","局部换底材"],["select","选择物件"]]:items.append({"id":pair[0],"label":pair[1],"category":"底床工具","preview":preload("res://scripts/aquarium/editor/BuildThumbnailService.gd").tool_icon(pair[0])})
    else:
        shells=preload("../tank_design/HallShellCatalog.gd").new(host)
        items=shells.entries()
        for pair in [["tank_0","小型成品展缸","模块展缸"],["tank_1","中型成品展缸","模块展缸"],["tank_2","标准成品展缸","模块展缸"],["wall","实心隔墙","馆内建筑"],["door","门洞隔墙","馆内建筑"],["parcel","铺设地块","馆内建筑"],["stair","楼梯","馆内建筑"],["floor","铺楼板","馆内建筑"],["floor_erase","拆楼板","馆内建筑"],["bench","观赏长凳","家具"],["plinth","展示台","家具"]]:items.append({"id":pair[0],"label":pair[1],"category":pair[2]})
        palette.theme=host.panel.theme
    palette.setup("造景目录" if tank else "建造目录",items,"tank" if tank else "hall")
    palette.chosen.connect(choose);palette.drag_started.connect(func(id):drag_asset=id;choose(id))
    palette.drag_finished.connect(func(placed):
        drag_asset=""
        if not placed:_reset_tool())
    inspector=preload("res://scripts/aquarium/editor/BuildInspector.gd").new();host.add_child(inspector)
    inspector.position=Vector2(1126,96) if tank else Vector2(1500,105)
    inspector.size=Vector2(302,500) if tank else Vector2(398,255)
    inspector.setup();inspector.mode_changed.connect(set_mode)
    host.canvas.build_scope="tank" if tank else "hall";host.canvas.asset_dropped.connect(drop_asset)
    gizmo=preload("res://scripts/aquarium/editor/EditorGizmo.gd").new();host.add_child(gizmo)
    gizmo.planar=not tank;gizmo.started.connect(start);gizmo.changed.connect(change);gizmo.finished.connect(finish)
    if not tank:
        inspector.theme=host.panel.theme
        inspector.add_theme_stylebox_override("panel",host.panel.theme.get_stylebox("panel","PanelContainer"))
        inspector.details.add_theme_color_override("font_color",Color("#486264"))
        host.panel.side.reparent(inspector.get_child(0),false)
        host.panel.side.add_theme_stylebox_override("panel",StyleBoxEmpty.new())
        shell_inspector=preload("../tank_design/HallShellInspector.gd").new()
        host.add_child(shell_inspector)
        shell_inspector.position=inspector.position
        shell_inspector.size=Vector2(398,0)
        shell_inspector.theme=host.panel.theme
        shell_inspector.add_theme_stylebox_override("panel",inspector.get_theme_stylebox("panel"))
        shell_inspector.setup(host)
        palette.tabs.current_tab=0
        var custom := Button.new()
        custom.text="＋ 新建异形缸"
        palette.header.add_child(custom)
        palette.tabs.tab_changed.connect(func(index):custom.visible=index==0 or palette.tabs.get_tab_title(index)=="展缸")
        custom.pressed.connect(shells.open_workshop)
        thumbnails=preload("res://scripts/aquarium/editor/BuildThumbnailService.gd").new();host.add_child(thumbnails)
        thumbnails.preview_ready.connect(palette.set_preview);thumbnails.call_deferred("generate",host,items.filter(func(item):return not str(item.id).begins_with("shell_")))

func choose(id: String) -> void:
    gizmo.cancel()
    if tank:
        if id.begins_with("substrate_"):host._choose_substrate(int(id.trim_prefix("substrate_")))
        else:host._set_tool(id)
    else:
        host.panel.water_panel.hide()
        if shells.templates.has(id):shells.choose(id)
        elif id.begins_with("tank_"):host.panel.choose_tank_size(host, int(id.trim_prefix("tank_")));host.editor._set_tool("tank")
        elif id in ["wall","door"]:host.editor.wall_with_door=id=="door";host.editor._set_tool("wall")
        else:host.editor._set_tool(id)

func set_mode(value: String) -> void:
    gizmo.cancel();gizmo.mode=value;inspector.set_mode(value);_reset_tool()

func drop_asset(id: String,at: Vector2) -> void:
    choose(id)
    if tank:
        host.pointer=at;host._update_cursor()
        if host._is_decor(id) and host.hit!=null and host.rocks.size()<80:
            host._remember();host._add_rock(id,host.hit,host.ghost_scale,host.ghost_yaw);host._set_tool("select")
        elif id.begins_with("substrate_"):host.notice="已选底床材料，按住左键铺设。"
    else:
        var hit: Variant=host.editor._floor_hit(at*Vector2(host.viewport.size)/host.canvas.size)
        if hit!=null:
            if id in ["floor","floor_erase"] and host.editor.pending_kind!=id:return
            if host.editor.pending_kind in ["tank","shell","bench","plinth","stair"]:host.editor._add_at(host.editor.pending_kind,hit)
            elif host.editor.pending_kind in ["floor","floor_erase"]:
                host.editor.floor_anchor=hit;host.editor._commit_floor(hit)
            elif host.editor.pending_kind=="parcel":host.editor._expand_at(hit)
            elif host.editor.pending_kind=="wall":host.editor.wall_anchor=hit;host.notice="已放下墙起点，点击终点建墙。"

func tick() -> void:
    if not is_instance_valid(host):return
    var building: bool=tank or (host.editing and host.tank_session.active_editor==null and not host.tank_session.inspecting)
    var drafting: bool=not tank and shells.session.mode!=""
    if drafting and shells.session.mode=="interior":shells.session.tick_brush()
    palette.visible=building and not drafting and (tank or host.panel.catalog_open)
    host.canvas.accepts_assets=palette.visible
    if tank:
        inspector.visible=palette.visible
    else:
        var selected_shell: Dictionary={}
        if building and host.editor.pending_kind=="" and host.selected>=0 and host.selected<host.objects.size():
            if host.objects[host.selected].data.kind=="shell":
                selected_shell=host.objects[host.selected]
                host.panel.water_panel.hide()
        if drafting:selected_shell=shells.session.preview_row()
        shells.handles.sync(selected_shell if shells.session.mode=="shape" else {})
        shell_inspector.bind_row(selected_shell)
        host.panel.visible=not drafting and host.tank_session.active_editor==null
        inspector.visible=building and host.selected>=0 and host.editor.pending_kind=="" and selected_shell.is_empty() and not host.panel.water_panel.visible
        host.panel.side.visible=inspector.visible
        host.panel.inspection_tools.visible=host.tank_session.inspecting
        host.panel.floor_panel.get_parent().visible=building
        host.panel.catalog_button.visible=building
        host.panel.feedback.visible=building and host.editor.pending_kind!=""

    var current: Node3D=null;var key := "";var center := Vector3.ZERO
    if tank:
        if host.selected>=0 and host.selected<host.rocks.size() and host.tool=="select":
            var row: Dictionary=host.rocks[host.selected];current=row.node;center=current.global_transform*row.bounds.get_center();key=str(current.get_instance_id())
    elif building and not drafting and host.editor.pending_kind=="" and host.selected>=0 and host.selected<host.objects.size():
        var row: Dictionary=host.objects[host.selected]
        if row.data.kind not in ["wall","stair","shell"]:current=row.node;center=current.global_transform*host._bounds(row.data).get_center();key=row.data.id
    if gizmo.dragging and key!=selection_key:gizmo.cancel()
    selected_node=current;selection_key=key
    var show_gizmo := current!=null
    if not tank and gizmo.mode=="move":
        show_gizmo=show_gizmo and key==host.editor.move_selection_id
    gizmo.sync(host.camera if tank else host.editor_camera,current.global_transform if current!=null else Transform3D.IDENTITY,center,show_gizmo,host.canvas.size/Vector2(host.viewport.size))
    if not drag_asset.is_empty():
        if tank:host.pointer=host.canvas.get_local_mouse_position();host._update_cursor()
        else:host.pointer=host.canvas.get_local_mouse_position()*Vector2(host.viewport.size)/host.canvas.size;host.editor._preview(host.editor._floor_hit(host.pointer))
    var inspected: Node3D=current;var label := "";var type_value := "";var box := AABB()
    if tank and current!=null:
        var row: Dictionary=host.rocks[host.selected];label=host.rock_specs[row.id].name_zh;box=row.bounds
        type_value={"rock":"石头","wood":"沉木"}.get(host.rock_specs[row.id].get("category","decor"),"人工摆件")
    elif not tank and not drafting and host.editor.pending_kind=="" and host.selected>=0 and host.selected<host.objects.size():
        var row: Dictionary=host.objects[host.selected];inspected=row.node;label=row.data.name;box=host._bounds(row.data)
        type_value={"tank":"展缸","wall":"隔墙","bench":"家具","plinth":"展示台","stair":"楼梯"}.get(row.data.kind,"")
    inspector.bind_object(label,type_value,inspected,box,not tank,host.metric_scale if tank else 1.0)
    if not tank and inspected!=null and host.objects[host.selected].data.kind=="wall":
        for button in inspector.modes.values():button.disabled=true
        inspector.hint.text="可调整方向与墙长。"
    if not tank and inspected!=null and host.objects[host.selected].data.kind=="stair":
        for button in inspector.modes.values():button.disabled=true
        inspector.hint.text="先单击楼梯，再按住拖动。Q/E 转向，Delete 删除。"

func input_event(event: InputEvent) -> bool:
    if not tank and shells.session.mode!="":
        if shells.session.mode=="interior" and shells.session.interior_input(event):return true
        if shells.session.mode=="shape" and shells.handles.handle(event):return true
        if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:return true
    return gizmo.handle(event) if is_instance_valid(gizmo) else false

func key(event: InputEvent) -> bool:
    if not event is InputEventKey or not event.pressed or event.echo:return false
    if gizmo.dragging and event.keycode==KEY_ESCAPE:gizmo.cancel();return true
    if gizmo.dragging and event.ctrl_pressed:
        if event.keycode in [KEY_Z,KEY_Y]:gizmo.cancel();return true
        if event.keycode==KEY_S:gizmo.dragging=false;finish(false)
    if event.ctrl_pressed:return false
    if host.get_viewport().gui_get_focus_owner() is LineEdit:return false
    if event.keycode in [KEY_W,KEY_E,KEY_R]:
        set_mode({KEY_W:"move",KEY_E:"rotate",KEY_R:"scale"}[event.keycode]);return true
    return false

func start() -> void:before=host._state().duplicate(true)

func change(value: Transform3D) -> void:
    if not is_instance_valid(selected_node):return
    if tank:
        var row: Dictionary=host.rocks[host.selected];var scales := value.basis.get_scale()
        if scales.min_axis_index()<0 or scales.x<.04 or scales.y<.04 or scales.z<.04 or scales.x>3 or scales.y>3 or scales.z>3:return
        var box: AABB=value*row.bounds
        if box.position.x<-.612 or box.end.x>.612 or box.position.z<-.312 or box.end.z>.312 or box.position.y<-.04 or box.end.y>.555:
            host.notice="变换超出缸壁、水面或缸底，保留上一个有效位置。";return
        selected_node.transform=value;row.factor=scales.x;selected_node.set_meta("free_transform",true)
    else:
        var data: Dictionary=host.objects[host.selected].data
        var patch: Dictionary={}
        if gizmo.mode=="move":patch.at=[snappedf(value.origin.x,.05),snappedf(value.origin.z,.05)]
        elif gizmo.mode=="rotate":patch.yaw=value.basis.get_euler().y
        else:patch.scale=clampf(value.basis.get_scale().x,.4,1.3)
        host._execute_build("patch",{"id":data.id,"patch":patch},false)

func finish(cancelled: bool) -> void:
    if before.is_empty():return
    if cancelled:
        var index: int=host.selected
        host._restore(before)
        host.selected=index;_reset_tool()
        if not tank:host._sync_panel()
    elif host._state()!=before:
        if tank:
            host.history.append(before);host.future.clear()
            if host.history.size()>30:host.history.pop_front()
        else:host.edit_history.remember(before)
    before={}


func _reset_tool() -> void:
    if tank:
        host._set_tool("select")
    else:
        host.editor._set_tool("")
