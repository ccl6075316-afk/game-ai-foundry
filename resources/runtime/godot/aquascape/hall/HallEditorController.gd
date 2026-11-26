extends RefCounted
## Build tools and their transient state. All persistent edits go through HallBuildCommands.
var host: Control
var input := preload("res://scripts/aquarium/hall/HallEditorInput.gd").new()
const Footprint := preload("res://scripts/aquarium/HallFootprint.gd")
const Storeys := preload("res://scripts/aquarium/hall/HallStoreys.gd")
var dragging := false
var move_selection_id := ""
var drag_press := Vector2.ZERO
var drag_moved := false
const DRAG_SLOP := 6.0
var orbiting := false
var drag_offset := Vector3.ZERO
var pending_kind := ""
var selection_box: MeshInstance3D
var id_serial := 1
var build_preview: Node3D
var parcel_hints: Node3D
var tank_size_index := 1
var pending_yaw := 0.0
var wall_anchor: Variant=null
var wall_with_door := false
var wall_with_window := false
var wall_profile_choice := "plain"
var wall_half_height := false
var panning := false
const Architecture=preload("HallArchitecture.gd")
var region_finish := 0
var ceiling_height := 6.6
var column_round := false
var floor_anchor: Variant=null
var floor_preview_key: Array=[]

func _init(hall: Control) -> void:
    host = hall

func create_preview_nodes() -> void:
    selection_box = MeshInstance3D.new()
    host.world.add_child(selection_box)
    var wire: StandardMaterial3D = host._paint(Color("f2cc72"), true)
    wire.no_depth_test = true
    selection_box.material_override = wire
    selection_box.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    build_preview = Node3D.new()
    host.world.add_child(build_preview)
    parcel_hints = Node3D.new()
    host.world.add_child(parcel_hints)

func handle_input(event: InputEvent) -> bool:
    if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT and not event.pressed:
        dragging=false
    if event is InputEventKey and event.pressed:
        dragging=false
    var bridge: RefCounted = host.build_editor
    if bridge!=null and bridge.shells.session.mode!="" and event is InputEventKey and event.pressed:
        if event.keycode==KEY_ESCAPE:
            if bridge.shells.handles.active>=0:bridge.shells.handles.cancel()
            elif not bridge.shells.session.prop_editor.cancel_drag():bridge.shells.session.cancel()
            return true
        if event.keycode==KEY_S and (event.ctrl_pressed or event.meta_pressed):
            var focus := host.get_viewport().gui_get_focus_owner() as Control
            if focus is LineEdit and focus.get_parent() is SpinBox:
                (focus.get_parent() as SpinBox).apply()
            bridge.shells.session.save()
            return true
        if bridge.shells.session.prop_editor.selected_prop>=0 and not event.ctrl_pressed and not event.meta_pressed and not event.echo:
            if event.keycode in [KEY_W,KEY_E,KEY_R]:
                bridge.shell_inspector.interior_tools.set_prop_mode({KEY_W:"move",KEY_E:"rotate",KEY_R:"scale"}[event.keycode])
                return true
        return false
    if host.editing and not host.tank_session.inspecting and event is InputEventKey and event.pressed and not event.echo and not event.ctrl_pressed:
        if event.keycode in [KEY_PAGEUP, KEY_PAGEDOWN]:
            _change_level(1 if event.keycode == KEY_PAGEUP else -1)
            return true
        if event.keycode in [KEY_Q, KEY_E] and (pending_kind == "stair" or (pending_kind == "" and host.selected >= 0 and host.objects[host.selected].data.kind == "stair")):
            var direction := -1 if event.keycode == KEY_Q else 1
            if pending_kind == "stair":
                pending_yaw += direction * PI / 2
                _preview(_floor_hit(host.pointer))
            else:
                _rotate_selected(direction)
            return true
    if bridge!=null and bridge.shells.session.prop_editor.is_dragging() and event is InputEventMouse:
        var local := event.duplicate() as InputEventMouse
        local.position=host.canvas.get_global_transform_with_canvas().affine_inverse()*event.position
        if bridge.shells.session.interior_input(local):return true
    if bridge != null and bridge.shells.handles.active>=0:
        if event is InputEventKey and event.pressed:
            if event.keycode==KEY_ESCAPE:bridge.shells.handles.cancel()
            return true
        if event is InputEventMouseMotion or event is InputEventMouseButton:
            var local := event.duplicate() as InputEventMouse
            local.position=host.canvas.get_global_transform_with_canvas().affine_inverse()*event.position
            return bridge.shells.handles.handle(local)
    if bridge != null and bridge.gizmo.dragging and (event is InputEventMouseMotion or event is InputEventMouseButton):
        var local_event: InputEvent = event.duplicate()
        local_event.position = host.get_global_transform_with_canvas().affine_inverse() * event.position
        if bridge.input_event(local_event):
            return true
    if host.editing and bridge != null and bridge.key(event):
        return true
    if event is InputEventMouseButton and not event.pressed:
        if event.button_index == MOUSE_BUTTON_RIGHT:
            orbiting = false
        if event.button_index == MOUSE_BUTTON_MIDDLE:
            panning = false
    return false

func canvas_input(event: InputEvent) -> void:
    if host.build_editor == null or not host.build_editor.input_event(event):
        input.canvas_input(host, event)

func key_input(event: InputEvent) -> void:
    if host.build_editor!=null and host.build_editor.shells.session.mode!="":return
    input.key_input(host, event)

func _expand_at(at: Vector3) -> bool:
    if not host._execute_build("expand",{"cell":Footprint.at(at)}):return false
    host.notice="已铺一块 6×7 米地基，可继续点击空地。"
    return true

func _fit_hall() -> void:
    var rect: Rect2=Footprint.extent(host.parcels)
    # Keep the hall in the visible space to the left of the inspector.
    host.camera_target=Vector3(rect.get_center().x+1.8,Storeys.elevation(host.active_level)+1.0,rect.get_center().y-.6)
    host.view_size=maxf(maxf(rect.size.y*1.45,rect.size.x*.98),20.5)
    if host.highest_shell_top>host.camera_target.y+host.view_size*.5:
        host.camera_target.y=host.highest_shell_top*.4
        host.view_size=maxf(host.view_size,host.highest_shell_top*2)
    host._camera()

func frame_tall_shell() -> void:
    if host.selected<0:return
    var row: Dictionary=host.objects[host.selected]
    if row.data.kind!="shell":return
    var box: AABB=row.node.transform*host._bounds(row.data)
    if box.size.y<=host.view_size*.45:return
    host.view_size=maxf(host.view_size,box.size.length()*2)
    host.camera_target=box.get_center()-host.editor_camera.global_basis.y*(host.view_size*.1)
    host._camera()

func _refresh_parcel_hints() -> void:
    if not is_instance_valid(parcel_hints):return
    host._clear_geometry(parcel_hints)
    if pending_kind!="parcel" or not host.editing:return
    for cell in Footprint.candidates(host.parcels):
        var rect: Rect2=Footprint.rect(cell);var p := rect.get_center()
        var material: StandardMaterial3D = host._paint(Color(.24,.69,.64,.18),true)
        material.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
        host._box(parcel_hints,Vector3(p.x,.015,p.y),Vector3(5.84,.025,6.84),material)
        var sign := Label3D.new();sign.text="＋ 6×7 m";sign.position=Vector3(p.x,.12,p.y);sign.rotation.x=-PI/2;sign.font_size=55;sign.pixel_size=.012;parcel_hints.add_child(sign)

func _valid_placement(data: Dictionary,rows: Array,ignore_id: String="",cells: Array=[]) -> bool:
    var valid: bool = Architecture.valid_object(data) and host.layout_rules._valid_placement(data,rows,ignore_id,host.parcels if cells.is_empty() else cells)
    if valid:valid=host.layout_rules._valid_level_support(data,host.floor_cells)
    if valid:valid=host.layout_rules._exterior_clear({"parcels":host.parcels,"exterior_wall":host._state().get("exterior_wall",{}),"objects":[data]})
    return valid

func _change_finish(key: String) -> void:
    host._execute_build("style",{"key":key,"value":(host.document.style(key)+1)%3})

func _floor_hit(screen: Vector2) -> Variant:
    var origin: Vector3 = host.editor_camera.project_ray_origin(screen);var ray: Vector3 = host.editor_camera.project_ray_normal(screen)
    if absf(ray.y)<.001:return null
    var t: float=(Storeys.elevation(host.active_level)-origin.y)/ray.y
    if t<0:return null
    return origin+ray*t

func _move_selected(at: Vector3,remember:=false) -> bool:
    if host.selected<0:return false
    var row: Dictionary=host.objects[host.selected].data
    var snap := 1.0 if row.kind=="stair" else .25
    var target := [snappedf(at.x,snap),snappedf(at.z,snap)]
    if row.at==target:return false
    return host._execute_build("patch",{"id":row.id,"patch":{"at":target}},remember)

func _rotate_selected(direction: float) -> bool:
    if host.selected<0:return false
    var data: Dictionary=host.objects[host.selected].data
    var interval := PI/2 if data.kind in ["wall","stair"] else deg_to_rad(15)
    if not host._execute_build("patch",{"id":data.id,"patch":{"yaw":data.yaw+interval*direction}}):
        host.notice="旋转后会碰到其他物件或墙。";return false
    return true

func _resize_selected(value: float) -> bool:
    if host.selected<0:return false
    var data: Dictionary=host.objects[host.selected].data
    if data.kind=="stair":return false
    var patch: Dictionary={}
    if data.kind=="wall":patch.length=snappedf(clampf(value,3 if data.get("door",false) else .5,18),.5)
    else:patch.scale=clampf(value,.4,1.3)
    if not host._execute_build("patch",{"id":data.id,"patch":patch}):host.notice="放大后空间不足。";host._sync_panel();return false
    return true

func set_tank_size(index: int) -> void:
    tank_size_index = index

func _candidate(kind: String,at: Vector3) -> Dictionary:
    var preset := [.5,.65,1.0]
    var snap := 1.0 if kind=="stair" else .25
    var data := {"id":"placement-preview","kind":kind,"name":{"tank":"新展缸","bench":"观赏长凳","plinth":"石灯展示台","stair":"楼梯","column":"建筑柱"}.get(kind,"隔墙"),"at":[snappedf(at.x,snap),snappedf(at.z,snap)],"yaw":pending_yaw,"scale":float(preset[tank_size_index]) if kind=="tank" else 1.0}
    if host.active_level>0:data.level=host.active_level
    if kind=="shell":
        data.design=host.build_editor.shells.active_design.duplicate(true)
        data.name=host.build_editor.shells.active_name
    if kind=="column":data.height=3.2;data.width=.6;data.round=column_round
    if kind=="tank":data.fish_count=0;data.content={}
    return data

func _add_at(kind: String,at: Vector3) -> bool:
    if host.objects.size()>=host.MAX_OBJECTS:host.notice="大厅最多 80 件物品。";return false
    if kind in ["shell","tank"] and host.objects.filter(func(r):return r.data.kind in ["shell","tank"]).size()>=host.MAX_TANKS:host.notice="本版最多 8 个展缸。";return false
    var id: String="hall-%d-%d" % [Time.get_unix_time_from_system(),id_serial];id_serial+=1
    var data := _candidate(kind,at);data.id=id
    if kind=="shell":return host.build_editor.shells.session.begin("shape",data)
    if not host._execute_build("add",{"object":data}):return false
    host.selected=host.objects.size()-1;_set_tool("");host._sync_panel()
    host.notice="楼梯已放置。按 Page Up 到上层，在黄色出口铺地板。" if kind=="stair" else "已添加。先单击选中，再按住物件拖动。"
    return true

func _wall_candidate(start: Vector3,finish: Vector3) -> Dictionary:
    start=Vector3(snappedf(start.x,.5),0,snappedf(start.z,.5))
    finish=Vector3(snappedf(finish.x,.5),0,snappedf(finish.z,.5))
    var along_x := absf(finish.x-start.x)>=absf(finish.z-start.z)
    if along_x:finish.z=start.z;finish.x=start.x+clampf(finish.x-start.x,-18,18)
    else:finish.x=start.x;finish.z=start.z+clampf(finish.z-start.z,-18,18)
    var data := {"id":"wall-preview","kind":"wall","name":"门洞隔墙" if wall_with_door else "馆内隔墙","at":[(start.x+finish.x)/2,(start.z+finish.z)/2],"yaw":0.0 if along_x else PI/2,"scale":1.0,"length":start.distance_to(finish),"door":wall_with_door}
    if wall_with_window:
        data.name="窗洞墙";data.opening="window";data.opening_width=1.8;data.opening_height=1.5;data.sill=1.0
    data.wall_profile=wall_profile_choice
    if wall_profile_choice=="rock":data.wall_finish=5;data.name="立体岩壁"
    if wall_half_height:data.height=1.2;data.name="半高墙"
    if host.active_level>0:data.level=host.active_level
    return data

func _commit_wall(start: Vector3,finish: Vector3) -> bool:
    var data := _wall_candidate(start,finish)
    if data.length<(3 if data.door else .5):host.notice="门洞隔墙至少 3 米。" if data.door else "请拉出至少半米长的直墙。";return false
    if host.objects.size()>=host.MAX_OBJECTS:host.notice="大厅最多 80 件物品。";return false
    data.id="wall-%d-%d" % [Time.get_unix_time_from_system(),id_serial];id_serial+=1
    if not host._execute_build("add",{"object":data}):return false
    host.selected=host.objects.size()-1
    if pending_kind=="wall":
        var base := Vector3(snappedf(start.x,.5),Storeys.elevation(host.active_level),snappedf(start.z,.5))
        wall_anchor=Vector3(2*float(data.at[0])-base.x,base.y,2*float(data.at[1])-base.z)
    host._sync_panel()
    host.notice="下一段从墙尾继续。点击新终点，Esc 结束。"
    return true

func _set_tool(kind: String) -> void:
    if kind in ["floor","floor_erase"] and host.active_level==0:
        host.notice="一层使用地基。放置楼梯后，按 Page Up 在上层铺地板。";return
    if kind=="parcel" and host.active_level>0:_change_level(-host.active_level)
    if host.build_editor!=null and host.build_editor.shells!=null:
        host.build_editor.shells.ghost.hide()
    pending_kind=kind;pending_yaw=0;wall_anchor=null;dragging=false
    move_selection_id=""
    floor_anchor=null;floor_preview_key=[]
    if is_instance_valid(build_preview):host._clear_geometry(build_preview)
    _refresh_parcel_hints()
    host.notice={"shell":"把展缸拖到空地，放下后拖外框边线或顶点调大小。","parcel":"点击任意空地铺一块 6×7 米地基，可隔开铺设。","wall":"先点墙起点，再点终点；自动取直线，Esc 取消。","tank":"移动鼠标预览新展缸；Q/E 转向，点击放下，Esc 取消。","bench":"点击空地放长凳。","plinth":"点击空地放展示台。","stair":"点击放楼梯，Q/E 转向，箭头指向上层出口。","floor":"点击铺一格，拖动铺一片。黄色标记是楼梯出口。","floor_erase":"点击或拖动拆除楼板，留下挑空。","":"单击选中物件，再按住它拖动。"}.get(kind,"")
    host._sync_panel()
    if kind in Architecture.REGION_TOOLS:host.notice="拖动选择区域；左侧设置材料或天花高度，Esc 结束。"
    if kind=="column":host.notice="点击放置柱子，选中后调整高度和宽度。"
    if kind=="parcel":
        var extent: Rect2=Footprint.extent(host.parcels)
        host.view_size=maxf(maxf(extent.size.y*1.45,extent.size.x*.98)+13,30);host._camera()

func _preview(at: Variant) -> void:
    if pending_kind=="shell":
        if at!=null and host.editing:host.build_editor.shells.preview(at)
        else:host.build_editor.shells.ghost.hide()
        return
    if at!=null and host.editing and pending_kind in ["floor","floor_erase"]+Architecture.REGION_TOOLS:
        _preview_floor(at);return
    floor_preview_key=[]
    host._clear_geometry(build_preview)
    if at==null or pending_kind=="" or not host.editing:return
    var box: AABB
    var allowed := false
    if pending_kind=="parcel":
        var cell: Array=Footprint.at(at);var rect: Rect2=Footprint.rect(cell)
        box=AABB(Vector3(rect.position.x,.03,rect.position.y),Vector3(6,.06,7));allowed=Footprint.can_add(host.parcels,cell)
    elif pending_kind=="wall":
        if wall_anchor==null:
            box=AABB(Vector3(snappedf(at.x,.5)-.12,at.y,snappedf(at.z,.5)-.12),Vector3(.24,.12,.24));allowed=Footprint.contains(host.parcels,box)
        else:
            var data := _wall_candidate(wall_anchor,at)
            box=host._transform(data)*host._bounds(data);allowed=data.length>=(3 if data.door else .5) and Architecture.valid_object(data) and _valid_placement(data,host.objects)
    else:
        var data := _candidate(pending_kind,at)
        box=host._transform(data)*host._bounds(data);allowed=_valid_placement(data,host.objects) and host.objects.size()<host.MAX_OBJECTS
        if pending_kind in ["shell","tank"] and host.objects.filter(func(r):return r.data.kind in ["shell","tank"]).size()>=host.MAX_TANKS:allowed=false
    var paint: StandardMaterial3D = host._paint(Color(.3,.9,.65,.24) if allowed else Color(1,.28,.26,.30),true)
    paint.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA;paint.cull_mode=BaseMaterial3D.CULL_DISABLED
    if pending_kind=="wall" and wall_anchor!=null:
        var data := _wall_candidate(wall_anchor,at)
        var holder := Node3D.new();build_preview.add_child(holder);holder.transform=host._transform(data)
        if data.get("wall_profile", "plain")=="rock" and data.length>.01:
            var mesh := MeshInstance3D.new();mesh.mesh=preload("HallRockWall.gd").build(data).mesh;mesh.material_override=paint;holder.add_child(mesh)
        else:
            for part in preload("HallWallForm.gd").parts(data):host._box(holder,part.at,part.size,paint)
    else:host._box(build_preview,box.get_center(),box.size,paint)
    if pending_kind=="stair":
        var marker := Label3D.new()
        marker.text="上层出口 ↑";marker.billboard=BaseMaterial3D.BILLBOARD_ENABLED
        marker.position=host._transform(_candidate("stair",at))*Storeys.stair_landing(true).get_center()
        marker.pixel_size=.012;marker.font_size=32;build_preview.add_child(marker)
    host.panel.set_tool_feedback(pending_kind, allowed)

func _floor_payload(at: Vector3) -> Dictionary:
    var start: Vector3=at if floor_anchor==null else floor_anchor
    return {"start":[floori(start.x),host.active_level,floori(start.z)],"end":[floori(at.x),host.active_level,floori(at.z)],
        "erase":pending_kind=="floor_erase","tool":pending_kind,"value":ceiling_height if pending_kind=="ceiling" else region_finish}

func _preview_floor(at: Vector3) -> void:
    var payload := _floor_payload(at)
    var key := [host.document.revision,payload]
    if floor_preview_key==key:return
    floor_preview_key=key
    host._clear_geometry(build_preview)
    var result: Dictionary=Architecture.region_proposal(host._state(),payload) if pending_kind in Architecture.REGION_TOOLS else host.build_commands.floor_proposal(host._state(),payload)
    if result.ok and pending_kind in Architecture.REGION_TOOLS:result.ok=Architecture.valid_regions(result.layout,host.layout_rules)
    var a := Storeys.key(payload.start)
    var b := Storeys.key(payload.end)
    var lo := a.min(b)
    var hi := a.max(b)
    var size := Vector3(hi.x-lo.x+1,.035,hi.z-lo.z+1)
    var paint: StandardMaterial3D = host._paint(Color(.30,.91,.65,.4) if result.ok else Color(1,.32,.27,.47),true)
    paint.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    host._box(build_preview,Vector3(lo.x+size.x*.5,Storeys.elevation(host.active_level)+.05,lo.z+size.z*.5),size,paint)

func _commit_floor(at: Vector3) -> void:
    var payload := _floor_payload(at)
    floor_anchor=null
    if host._execute_build("region" if pending_kind in Architecture.REGION_TOOLS else "floor",payload):
        host.notice="区域设置已保存，可撤销。" if pending_kind in Architecture.REGION_TOOLS else ("已拆除选区楼板。" if payload.erase else "已铺设选区地板。")
    if pending_kind in ["floor","floor_erase"]+Architecture.REGION_TOOLS:_preview_floor(at)

func _change_level(direction: int) -> bool:
    if not host.editing or host.tank_session.inspecting or host.tank_session.active_editor!=null:return false
    var next := clampi(host.active_level+direction,0,host.highest_level)
    if next==host.active_level:return false
    if host.build_editor!=null:host.build_editor.gizmo.cancel()
    host.floor_views[host.active_level]=host.camera_target
    var target: Vector3 = host.camera_target+Vector3.UP*Storeys.elevation(next-host.active_level)
    if not host.floor_views.has(next) and next>host.active_level:
        # The first visit to a storey starts at the entrance the player just built.
        for i in range(host.objects.size()-1,-1,-1):
            var row: Dictionary=host.objects[i]
            if row.data.kind=="stair" and Storeys.level(row.data)+1==next:
                var landing := Storeys.stair_landing(true).get_center()
                target=row.node.transform*Vector3(landing.x,.5+Storeys.HEIGHT,landing.z)
                break
    host.camera_target=host.floor_views.get(next,target)
    host.active_level=next;host.selected=-1;_set_tool("")
    _refresh_floor_view(true,true);host._camera();host._sync_panel()
    host.notice="当前查看 %d 层。" % (host.active_level+1)
    return true

func _set_lower_life(value: bool) -> void:
    host.show_lower_life=value
    _refresh_floor_view(false)

func _refresh_floor_view(update_guides: bool,update_reference: bool=false) -> void:
    host.scene_projection.show_floors(host.active_level,host.editing)
    if is_instance_valid(host.scene_projection.architecture_view):host.scene_projection.architecture_view.set_view(host.active_level,host.editing)
    if update_reference:host.scene_projection.show_floor_below(host.active_level,host.editing,host.objects)
    host.visible_objects=[]
    for row in host.objects:
        var level := Storeys.level(row.data)
        var current: bool=not host.editing or level==host.active_level
        var incoming: bool=host.editing and row.data.kind=="stair" and level+1==host.active_level
        var lower_fish: bool=host.editing and host.show_lower_life and row.tank!=null and level+1==host.active_level
        row.node.visible=current or incoming or lower_fish
        if row.tank!=null:
            row.tank.visible=current
            row.tank.fish_visuals.visible=current or lower_fish
        row.body.collision_layer=2 if current else 0
        if current or incoming:host.visible_objects.append(row)
    if is_instance_valid(host.visitor_crowd):
        host.visitor_crowd.visible=true
        host.visitor_crowd.visible_level=host.active_level if host.editing else -1
        host.visitor_crowd.lower_visible_level=host.active_level-1 if host.editing and host.show_lower_life else -1
    if update_guides:host.scene_projection.show_floor_guides(host.active_level,host.editing,host.parcels,host.objects,host.floor_cells)

func _delete_selected() -> void:
    if host.selected<0:return
    var id: String=host.objects[host.selected].data.id
    if host._execute_build("remove",{"id":id}):host.selected=-1;host._sync_panel();host.notice="已删除，可撤销。"

func _selection() -> void:
    selection_box.visible=host.editing and host.selected>=0 and host.objects[host.selected].data.kind!="shell"
    if not selection_box.visible:return
    var row: Dictionary=host.objects[host.selected]
    show_selection(host._bounds(row.data).grow(.025),row.node.transform)

func show_selection(box: AABB, pose: Transform3D) -> void:
    selection_box.show()
    var mesh := ImmediateMesh.new();mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for pair in [[0,1],[1,3],[3,2],[2,0],[4,5],[5,7],[7,6],[6,4],[0,4],[1,5],[2,6],[3,7]]:
        for corner in pair:mesh.surface_add_vertex(box.get_endpoint(corner))
    mesh.surface_end();selection_box.mesh=mesh;selection_box.transform=pose

func _fish_count_changed(value: float) -> void:
    if host.selected<0 or host.objects[host.selected].data.kind!="tank":return
    if host._execute_build("patch",{"id":host.objects[host.selected].data.id,"patch":{"fish_count":int(value)}}):host.notice="已调整这个展缸的展示海鱼数量。"
