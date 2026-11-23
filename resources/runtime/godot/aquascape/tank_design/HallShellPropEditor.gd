extends RefCounted
## One selected model and its in-flight transform. The interior session owns the draft.
const Design=preload("ShellDesign.gd")
const Interior=preload("ShellInterior.gd")
const PropTransform=preload("../editor/PropTransform.gd")

var hall:Control
var session:RefCounted:
    get:return hall.build_editor.shells.session
var selected_prop := -1
var drag_origin: Variant=null
var drag_offset := Vector2.ZERO
var gizmo:=preload("../editor/EditorGizmo.gd").new()
var start_pose:=Transform3D.IDENTITY
var preview_changed:=false

func _init(owner_hall: Control) -> void:
    hall=owner_hall
    hall.canvas.add_child(gizmo)
    gizmo.move_pick_start=.55
    gizmo.started.connect(begin_transform)
    gizmo.changed.connect(preview_world_transform)
    gizmo.finished.connect(finish_transform)
    gizmo.hide()

func pick_prop(screen: Vector2) -> int:
    var eye:Vector3=hall.editor_camera.project_ray_origin(screen)
    var direction:Vector3=hall.editor_camera.project_ray_normal(screen)
    var nearest:=-1
    var best:=INF
    for i in session.contents.props.size():
        var entry:Dictionary=session.contents.props[i]
        var pose:Transform3D=entry.root.global_transform
        var inverse:=pose.affine_inverse()
        var bounds:AABB=entry.bounds
        var hit:Variant=bounds.grow(.035).intersects_ray(inverse*eye,inverse.basis*direction)
        if hit==null:continue
        var distance:=eye.distance_squared_to(pose*hit)
        if distance<best:
            nearest=i
            best=distance
    return nearest

func handle(event: InputEvent) -> bool:
    if not event is InputEventMouse:return false
    if gizmo.dragging and event is InputEventMouseMotion and not event.button_mask&MOUSE_BUTTON_MASK_LEFT:
        cancel_drag()
        return true
    if drag_origin==null and gizmo.handle(event):return true
    var screen:Vector2=event.position*Vector2(hall.viewport.size)/hall.canvas.size
    if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
        if event.pressed:
            var picked:=pick_prop(screen)
            if picked>=0 and picked==selected_prop and gizmo.mode=="move":
                var hit:Variant=session.bed_hit(screen)
                if hit==null:return true
                begin_transform()
                drag_origin=event.position
                drag_offset=Vector2(start_pose.origin.x,start_pose.origin.z)-hit
            elif picked!=selected_prop:
                select(picked)
        elif drag_origin!=null:
            finish_transform(false)
        return true
    if event is InputEventMouseMotion and drag_origin!=null:
        if not event.button_mask&MOUSE_BUTTON_MASK_LEFT:
            cancel_drag()
        elif preview_changed or event.position.distance_to(drag_origin)>=hall.editor.DRAG_SLOP:
            var hit:Variant=session.bed_hit(screen)
            if hit!=null:
                var p:Vector2=hit+drag_offset
                var box:=Interior.bounds(session.draft.design)
                var height:float=session.draft.design.height
                var bed:Dictionary=session.draft.interior
                var entry: Dictionary = session.contents.props[selected_prop]
                var uv := (p-box.position)/box.size
                var lift: float = entry.item.get("lift_m", 0.0)
                var y := Interior.prop_anchor_y(entry.item.id, uv, bed, height, start_pose.basis, entry.bounds) + lift
                var pose:=Transform3D(start_pose.basis,Vector3(p.x,y,p.y))
                preview_transform(pose)
        return true
    return false

func set_mode(value: String) -> void:
    if gizmo.mode!=value:cancel_drag()
    gizmo.mode=value
    sync_gizmo()

func begin_transform() -> void:
    start_pose=session.contents.props[selected_prop].root.transform
    preview_changed=false

func preview_world_transform(value: Transform3D) -> void:
    preview_transform(session.contents.global_transform.affine_inverse()*value)

func preview_transform(pose: Transform3D) -> void:
    var entry:Dictionary=session.contents.props[selected_prop]
    var path:=Design.contour(session.draft.design)
    var anchor:=Vector2(pose.origin.x,pose.origin.z)
    var panel:Control=hall.build_editor.shell_inspector.interior_tools
    var scale:=pose.basis.get_scale()
    if scale[scale.min_axis_index()]<Interior.MIN_PROP_SCALE or Interior.clearance(anchor,path)<.01 or not Interior.prop_fits(pose,entry.bounds,path,session.draft.design.height):
        panel.status.text="布景需要留在缸壁、缸底和缸顶以内。"
        return
    entry.root.transform=pose
    preview_changed=not pose.is_equal_approx(start_pose)
    hall.editor.selection_box.transform=entry.root.global_transform

func finish_transform(cancelled: bool) -> void:
    drag_origin=null
    if not preview_changed:return
    preview_changed=false
    var entry:Dictionary=session.contents.props[selected_prop]
    var before:Dictionary=entry.item
    if cancelled:
        entry.root.transform=start_pose
    else:
        var pose:Transform3D=entry.root.transform
        var box:=Interior.bounds(session.draft.design)
        var uv:=(Vector2(pose.origin.x,pose.origin.z)-box.position)/box.size
        var bed:Dictionary=session.draft.interior.duplicate()
        var item:=before.duplicate()
        item.u=uv.x
        item.v=uv.y
        item.lift_m=pose.origin.y-Interior.prop_anchor_y(item.id, uv, bed, session.draft.design.height, pose.basis, entry.bounds)
        item.rotation=PropTransform.array(pose.basis.orthonormalized().get_euler())
        item.stretch=PropTransform.array(pose.basis.get_scale())
        var props:Array=bed.props.duplicate()
        props[selected_prop]=item
        bed.props=props
        # Keep the edited model alive when reconciling the new draft.
        entry.item=item
        if not session.change({"interior":bed}):
            entry.item=before
            entry.root.transform=start_pose
    show_selection()
    hall.build_editor.shell_inspector.interior_tools.set_prop_mode(gizmo.mode)

func is_dragging() -> bool:
    return drag_origin!=null or gizmo.dragging

func cancel_drag() -> bool:
    if not is_dragging():return false
    if gizmo.dragging:
        gizmo.dragging=false
        finish_transform(true)
    else:
        finish_transform(true)
    return true

func clear_selection() -> void:
    cancel_drag()
    if selected_prop>=0:select(-1)

func select(index: int) -> void:
    selected_prop=index
    show_selection()
    var item: Dictionary = session.contents.props[index].item if index>=0 else {}
    hall.build_editor.shell_inspector.interior_tools.select_prop(item)
    sync_gizmo()

func set_selected_algae(enabled: bool) -> bool:
    if selected_prop<0 or is_dragging():return false
    var bed: Dictionary = session.draft.interior.duplicate()
    var props: Array = bed.props.duplicate()
    var item: Dictionary = props[selected_prop].duplicate()
    if not Interior.supports_algae(item.id):return false
    if enabled:
        item.algae=true
    else:
        item.erase("algae")
    props[selected_prop]=item
    bed.props=props
    if not session.change({"interior":bed}):return false
    select(selected_prop)
    return true

func sync_gizmo() -> void:
    if selected_prop<0:
        gizmo.enabled=false
        gizmo.hide()
        return
    var node:Node3D=session.contents.props[selected_prop].root
    var factor:Vector2=hall.canvas.size/Vector2(hall.viewport.size)
    gizmo.sync(hall.editor_camera,node.global_transform,node.global_position,true,factor)
    gizmo.show()

func show_selection() -> void:
    if selected_prop<0:
        hall.editor.selection_box.hide()
        return
    var entry:Dictionary=session.contents.props[selected_prop]
    hall.editor.show_selection(entry.bounds.grow(.025),entry.root.global_transform)
