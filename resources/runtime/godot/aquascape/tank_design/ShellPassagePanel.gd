extends VBoxContainer
const Passage=preload("ShellPassage.gd")
const Design=preload("ShellDesign.gd")
var session: RefCounted
var panel: Control
var entrance: Variant=null
var selected:=-1
# -1 controls the next placement; selecting a node targets its incoming segment.
var width_segment:=-1
var moving:=false
var width:=HSlider.new()
var radius:=HSlider.new()
var width_label:Label
var radius_label:Label
var ghost:Node3D
var hover_state:Dictionary={}
var hover_point:Variant=null
var hover_msec:=0

func setup(owner_session: RefCounted,owner_panel: Control) -> void:
    session=owner_session
    panel=owner_panel
    panel.slider(self,"通道宽度（米）",width,1.8,3.6,.1)
    width_label=get_child(get_child_count()-2)
    width.value_changed.connect(func(_value):
        update_width_label()
        resize_route()
    )
    width.value=2.2
    panel.slider(self,"圆顶观景区半径（米）",radius,1.5,3.5,.1)
    radius_label=get_child(get_child_count()-2)
    radius.value_changed.connect(func(value):radius_label.text="圆顶半径 %.1f 米"%value)
    radius.value=2.0
    for spec in [["继续绘制末端","extend"],["移动选中节点","move"],["添加／更新圆顶观景区","room"],["移除选中观景区","remove_room"],["撤回末端节点","undo"],["移除整条通道","clear"]]:
        var button:=Button.new()
        button.text=spec[0]
        button.pressed.connect(action.bind(spec[1]))
        add_child(button)
    radius.drag_ended.connect(func(_changed):
        var route:=current()
        if route.get("rooms",[]).any(func(room):return int(room.node)==selected):action("room")
    )

func current() -> Dictionary:
    return session.draft.get("interior",{}).get("passage",{}).duplicate(true)

func problem(route: Dictionary) -> String:
    var bed:Dictionary=session.draft.get("interior",{}).duplicate(true)
    bed.passage=route
    var reason:=Passage.problem(session.draft.design,bed)
    if reason!="":return reason
    var footprint:=Passage.footprint(route)
    if not footprint.is_empty():
        for entry in session.contents.props:
            var bounds:AABB=entry.root.transform*entry.bounds
            var rectangle:=PackedVector2Array([Vector2(bounds.position.x,bounds.position.z),Vector2(bounds.end.x,bounds.position.z),Vector2(bounds.end.x,bounds.end.z),Vector2(bounds.position.x,bounds.end.z)])
            if not Geometry2D.intersect_polygons(footprint,rectangle).is_empty():return "通道占用范围内有造景，请先移开。"
    return ""

func commit(route: Dictionary) -> bool:
    clear_hover()
    var reason:=problem(route)
    if reason!="":panel.status.text=reason;return false
    var bed:Dictionary=session.draft.get("interior",{}).duplicate(true)
    bed.passage=route
    if not session.change({"interior":bed}):panel.status.text="修改与现有缸内布置冲突。";return false
    panel.status.text="移动鼠标预览下一段，点击确认。点击已有节点可选中调整。"
    return true

# Both hovering and clicking use this pure proposal, including wall snapping.
func proposal_at(p: Vector2) -> Dictionary:
    var contour:=Design.contour(session.draft.design)
    var wall:=Passage.nearest_wall(p,contour)
    if p.distance_to(wall)<.5:p=wall
    var result:Dictionary={"action":"none","point":p,"route":{},"reason":""}
    if session.draft.get("interior",{}).get("substrate")!="bare":
        result.reason="先在底床页选择「裸缸底（无沙）」。"
        return result
    var route:=current()
    if route.is_empty():
        if entrance==null:
            result.action="entrance"
            if p.distance_to(wall)>.05:result.reason="请先点缸壁设入口。"
            return result
        route={"width":width.value,"widths":[width.value],"points":[[entrance.x,entrance.y],[p.x,p.y]],"rooms":[]}
        result.node=1
    else:
        var path:=Passage.points(route)
        if moving and selected>0:
            route.points[selected]=[p.x,p.y]
            result.node=selected
        else:
            for i in path.size():
                if p.distance_to(path[i])<.45:
                    result.action="select"
                    result.node=i
                    result.point=path[i]
                    return result
            if path.size()>=Passage.MAX_POINTS:
                result.reason="最多 12 个节点。"
                return result
            route.widths=Passage.widths(route)
            route.widths.append(width.value)
            route.points.append([p.x,p.y])
            result.node=route.points.size()-1
    result.action="route"
    result.route=route
    result.reason=problem(route)
    return result

func use_at(p: Vector2) -> void:
    var proposal:=proposal_at(p)
    clear_hover()
    if proposal.reason!="":panel.status.text=proposal.reason;return
    match proposal.action:
        "entrance":
            entrance=proposal.point
            panel.status.text="入口已选。移动鼠标预览第一段，点击确认。"
        "select":
            selected=proposal.node
            width_segment=maxi(0,selected-1)
            sync_controls(current())
            panel.status.text="已选节点 %d：宽度只修改第 %d 段。也可移动或添加圆顶。"%[selected+1,width_segment+1]
        "route":
            if commit(proposal.route):
                entrance=null
                moving=false
                selected=proposal.node
                width_segment=-1
                update_width_label()

func preview_at(p: Vector2,force:=false) -> void:
    hover_point=p
    if not force and Time.get_ticks_msec()-hover_msec<45:return
    hover_msec=Time.get_ticks_msec()
    var proposal:=proposal_at(p)
    if proposal==hover_state:return
    clear_hover(false)
    hover_state=proposal.duplicate(true)
    ghost=preload("ShellPassageGhost.gd").new()
    session.preview.add_child(ghost)
    ghost.build(proposal,session.draft.design,width.value)
    if proposal.action=="route" and ghost.has_cover and is_instance_valid(session.contents.passage):
        session.contents.passage.hide()
    if proposal.reason!="":panel.status.text=proposal.reason
    elif proposal.action=="entrance":panel.status.text="入口预览，点击定位，再向缸内画通道。"
    elif proposal.action=="select":panel.status.text="点击选中节点 %d。"%(int(proposal.node)+1)
    else:panel.status.text="半透明部分为点击后的通道。点击确认，红色表示无法施工。"

func clear_hover(reset_point:=true) -> void:
    if is_instance_valid(ghost):
        ghost.get_parent().remove_child(ghost)
        ghost.queue_free()
    ghost=null
    hover_state={}
    if reset_point:hover_point=null
    if is_instance_valid(session.contents) and is_instance_valid(session.contents.passage):session.contents.passage.show()

func update_width_label() -> void:
    width_label.text=("下一段宽度 %.1f 米"%width.value) if width_segment<0 else ("第 %d 段宽度 %.1f 米"%[width_segment+1,width.value])

func resize_route() -> void:
    clear_hover()
    var route:=current()
    # Changing the placement size must never resize already placed segments.
    if route.is_empty() or width_segment<0:return
    route.widths=Passage.widths(route)
    if width_segment>=route.widths.size():return
    var previous:float=route.widths[width_segment]
    route.widths[width_segment]=width.value
    if not commit(route):
        width.set_value_no_signal(previous)
        update_width_label()

func action(id: String) -> void:
    clear_hover()
    var route:=current()
    if id=="extend":
        width_segment=-1
        selected=-1
        moving=false
        update_width_label()
        panel.status.text="调节下一段宽度，移动鼠标预览，再点击连接末端。"
        return
    if id=="clear":
        if commit({}):entrance=null;selected=-1;moving=false;width_segment=-1;update_width_label()
        return
    if route.is_empty():panel.status.text="先点缸壁和缸底画一段通道。";return
    if id=="undo":
        route.widths=Passage.widths(route)
        route.widths.pop_back()
        route.points.pop_back()
        route.rooms=route.get("rooms",[]).filter(func(room):return room.node<route.points.size())
        if commit({} if route.points.size()<2 else route):selected=-1;width_segment=-1;update_width_label()
        return
    if selected<=0 or selected>=route.points.size():panel.status.text="先点选缸内通道节点。";return
    if id=="move":moving=true;panel.status.text="点新的裸缸底位置移动节点。";return
    route.rooms=route.get("rooms",[]).filter(func(room):return int(room.node)!=selected)
    if id=="room":route.rooms.append({"node":selected,"radius":radius.value})
    if not commit(route):sync_controls(current())

func sync_controls(route: Dictionary) -> void:
    if not route.is_empty():
        var index:int=width_segment if width_segment>=0 else route.points.size()-2
        width.set_value_no_signal(Passage.segment_width(route,index))
    update_width_label()
    for room in route.get("rooms",[]):
        if int(room.node)==selected:radius.set_value_no_signal(room.radius)
    radius_label.text="圆顶半径 %.1f 米"%radius.value
