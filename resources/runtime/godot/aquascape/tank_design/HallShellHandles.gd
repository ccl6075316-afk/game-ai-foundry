extends Control
## A horizontal resize frame in the tank's own axes, projected into the hall.
const Design = preload("ShellDesign.gd")
const CORNERS := [Vector2(-1,-1), Vector2(1,-1), Vector2(1,1), Vector2(-1,1)]
const EDGES := [Vector2(0,-1), Vector2(1,0), Vector2(0,1), Vector2(-1,0)]
const FIRST_EDGE := 4
const HEIGHT := 8
const GOLD := Color("#ffd682")
const BLUE := Color("#9cdaff")
const INK := Color("#19363f")
var hall: Control
var row: Dictionary={}
var corners := PackedVector2Array()
var height_handle := Vector2.ZERO
var height_base := Vector2.ZERO
var hovered := -1
var active := -1
var start_mouse := Vector2.ZERO
var start_data: Dictionary={}
var initial_pose := Transform3D.IDENTITY

func project(world: Vector3) -> Vector2:
    return hall.editor_camera.unproject_position(world)*hall.canvas.size/Vector2(hall.viewport.size)

func sync(selected_row: Dictionary) -> void:
    row=selected_row
    corners.clear()
    if not row.is_empty():
        var bounds := Design.bounds(row.data.design)
        var center := bounds.get_center()
        var pose: Transform3D=row.node.transform
        for sign_pair: Vector2 in CORNERS:
            var point := Vector3(center.x+sign_pair.x*bounds.size.x*.5,bounds.end.y,center.z+sign_pair.y*bounds.size.z*.5)
            corners.append(project(pose*point))
        # Keep height outside the outline so even a small tank has four usable corners.
        height_base=(corners[0]+corners[2])*.5
        var top := minf(minf(corners[0].y,corners[1].y),minf(corners[2].y,corners[3].y))
        height_handle=Vector2(height_base.x,top-21.0)
    var over_canvas: bool= hall.get_viewport().gui_get_hovered_control()==hall.canvas
    hovered=pick(get_local_mouse_position()) if over_canvas else -1
    queue_redraw()

func pick(screen: Vector2) -> int:
    if corners.is_empty(): return -1
    if height_handle.distance_to(screen)<=10: return HEIGHT
    var nearest := -1
    var distance := INF
    for i in 4:
        var shorter := minf(corners[i].distance_to(corners[(i+1)%4]),corners[i].distance_to(corners[(i+3)%4]))
        var d := screen.distance_to(corners[i])
        if d<=clampf(shorter*.25,3,11) and d<distance:
            nearest=i
            distance=d
    if nearest>=0: return nearest
    distance=8.0
    for i in 4:
        var point := Geometry2D.get_closest_point_to_segment(screen,corners[i],corners[(i+1)%4])
        var d := screen.distance_to(point)
        if d<distance:
            distance=d
            nearest=FIRST_EDGE+i
    return nearest

func _draw() -> void:
    if corners.is_empty(): return
    var target := active if active>=0 else hovered
    draw_line(height_base,height_handle,Color(BLUE,.65),1.5,true)
    for i in 4:
        var next := (i+1)%4
        var lit := target==FIRST_EDGE+i or target==i or target==next
        draw_line(corners[i],corners[next],INK,4.5,true)
        draw_line(corners[i],corners[next],Color.WHITE if lit else GOLD,3.0 if lit else 1.7,true)
    for i in 4:
        var extent := Vector2.ONE*(6.0 if target==i else 4.5)
        draw_rect(Rect2(corners[i]-extent-Vector2.ONE,2*(extent+Vector2.ONE)),INK)
        draw_rect(Rect2(corners[i]-extent,2*extent),Color.WHITE if target==i else GOLD)
    draw_circle(height_handle,8,INK)
    draw_circle(height_handle,5.5,Color.WHITE if target==HEIGHT else BLUE)

func on_plane(screen: Vector2) -> Vector3:
    var pixel: Vector2=screen*Vector2(hall.viewport.size)/hall.canvas.size
    var ray: Vector3=hall.editor_camera.project_ray_normal(pixel)
    var origin: Vector3=hall.editor_camera.project_ray_origin(pixel)
    var height := (initial_pose*Vector3(0,start_data.design.height,0)).y
    return initial_pose.affine_inverse()*(origin+ray*((height-origin.y)/ray.y))

func handle(event: InputEvent) -> bool:
    if active<0:
        if not event is InputEventMouseButton or not event.pressed or event.button_index!=MOUSE_BUTTON_LEFT: return false
        if row.is_empty() or hall.build_editor.shells.session.mode!="shape":return false
        active=pick(event.position)
        if active<0: return false
        start_mouse=event.position
        start_data=row.data.duplicate(true)
        initial_pose=row.node.transform
        return true
    if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT and not event.pressed:
        if active==HEIGHT:hall.build_editor.shells.session.frame_height()
        reset()
        return true
    if event is InputEventMouseMotion:
        var design: Dictionary=start_data.design.duplicate(true)
        var patch := {"design":design}
        if active==HEIGHT:
            var axis := project(initial_pose*Vector3.UP)-project(initial_pose.origin)
            if axis.length()<1:
                axis=Vector2.UP*hall.canvas.size.y/hall.editor_camera.size*initial_pose.basis.y.length()
            design.height=maxf(Design.MIN_HEIGHT,design.height+(event.position-start_mouse).dot(axis)/maxf(axis.length_squared(),1e-12))
        else:
            var delta := on_plane(event.position)-on_plane(start_mouse)
            var direction: Vector2=CORNERS[active] if active<FIRST_EDGE else EDGES[active-FIRST_EDGE]
            resize_footprint(patch,direction,Vector2(delta.x,delta.z))
        hall.build_editor.shells.session.change(patch)
        return true
    return false

func resize_footprint(patch: Dictionary,direction: Vector2,delta: Vector2) -> void:
    var design: Dictionary=patch.design
    var bounds := Design.bounds(design)
    var old := Vector2(bounds.size.x,bounds.size.z)
    var extent := old+direction*delta
    if design.kind=="custom":
        # Project the gesture onto the allowed uniform resize from the fixed side or corner.
        var span := old*direction
        var factor := maxf(.05,1.0+delta.dot(span)/span.length_squared())
        extent=old*factor
        var local_center := Vector2(bounds.get_center().x,bounds.get_center().z)
        for pair in design.points:
            var p := local_center+(Vector2(pair[0],pair[1])-local_center)*factor
            pair[0]=p.x
            pair[1]=p.y
    else:
        extent=extent.clamp(Vector2.ONE*.5,Vector2.ONE*16)
        design.width=extent.x
        design.depth=extent.y
        for i in 4: design.radii[i]=minf(design.radii[i],minf(extent.x,extent.y)*.5)
    var shift := direction*(extent-old)*.5
    var center := initial_pose*Vector3(shift.x,0,shift.y)
    patch.at=[center.x,center.z]

func cancel() -> void:
    if active<0: return
    hall.build_editor.shells.session.change({"design":start_data.design,"at":start_data.at})
    reset()

func reset() -> void:
    active=-1
    start_data={}
