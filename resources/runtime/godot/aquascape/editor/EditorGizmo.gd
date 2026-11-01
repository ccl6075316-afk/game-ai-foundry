extends Control
## World-axis handles projected into the editor canvas. No document ownership.
signal started
signal changed(value: Transform3D)
signal finished(cancelled: bool)
var mode := "move"
var camera: Camera3D
var target := Transform3D.IDENTITY
var pivot := Vector3.ZERO
var enabled := false
var planar := false
var dragging := false
var axis := -1
var start_mouse := Vector2.ZERO
var start_transform := Transform3D.IDENTITY
var start_vector := Vector3.ZERO
var length_world := 1.0
var screen_factor := Vector2.ONE
const COLORS=[Color("f47979"),Color("7be29b"),Color("74b6ff")]

func _ready() -> void:mouse_filter=Control.MOUSE_FILTER_IGNORE
func project(p: Vector3) -> Vector2:return camera.unproject_position(p)*screen_factor
func axes() -> Array:
    if not planar:return [0,1,2]
    return [0,2] if mode=="move" else ([1] if mode=="rotate" else [3])
func unit(i: int) -> Vector3:
    var v := Vector3.ZERO;v[i]=1;return v
func direction(i: int) -> Vector3:
    return target.basis[i].normalized() if mode=="scale" else unit(i)
func ring_point(i: int,angle: float) -> Vector3:
    return pivot+(unit((i+1)%3)*cos(angle)+unit((i+2)%3)*sin(angle))*length_world*.8
func ring_vector(at: Vector2,i: int) -> Vector3:
    var p := at/screen_factor;var ray := camera.project_ray_normal(p);var origin := camera.project_ray_origin(p)
    var normal := unit(i);var denominator := ray.dot(normal)
    if absf(denominator)<.0001:return Vector3.ZERO
    return (origin+ray*((pivot-origin).dot(normal)/denominator)-pivot).normalized()
func sync(cam: Camera3D,value: Transform3D,center: Vector3,visible_value: bool,factor: Vector2) -> void:
    camera=cam;enabled=visible_value;screen_factor=factor
    if not dragging:target=value;pivot=center
    if enabled and not dragging:
        var p := camera.unproject_position(pivot)
        length_world=camera.project_position(p+Vector2(92,0),camera.global_position.distance_to(pivot)).distance_to(camera.project_position(p,camera.global_position.distance_to(pivot)))
    queue_redraw()
func _draw() -> void:
    if not enabled or not is_instance_valid(camera) or camera.is_position_behind(pivot):return
    var center := project(pivot)
    for i in axes():
        var color: Color=Color("ffe6a0") if i==3 else COLORS[i]
        if mode=="rotate":
            var points := PackedVector2Array()
            for n in 65:points.append(project(ring_point(i,TAU*n/64)))
            draw_polyline(points,color,3 if dragging and axis==i else 2,true)
        elif i!=3:
            var end := project(pivot+direction(i)*length_world)
            draw_line(center,end,color,3,true)
            if mode=="scale":draw_rect(Rect2(end-Vector2.ONE*5,Vector2.ONE*10),color)
            else:
                var d := (end-center).normalized();draw_colored_polygon(PackedVector2Array([end,end-d*13+d.orthogonal()*5,end-d*13-d.orthogonal()*5]),color)
            draw_string(ThemeDB.fallback_font,end+Vector2(7,-5),["X","Y","Z"][i],HORIZONTAL_ALIGNMENT_LEFT,-1,17,color)
    draw_rect(Rect2(center-Vector2.ONE*5,Vector2.ONE*10),Color("ffe6a0"),mode=="scale")
func pick(at: Vector2) -> int:
    if mode=="scale" and at.distance_to(project(pivot))<12:return 3
    var found := -1;var best := 12.0
    for i in axes():
        if i==3:continue
        if mode=="rotate":
            for n in 64:
                var a := project(ring_point(i,TAU*n/64));var b := project(ring_point(i,TAU*(n+1)/64))
                var distance := at.distance_to(Geometry2D.get_closest_point_to_segment(at,a,b))
                if distance<best:best=distance;found=i
        else:
            var a := project(pivot);var b := project(pivot+direction(i)*length_world)
            if a.distance_to(b)<18:continue
            var distance := at.distance_to(Geometry2D.get_closest_point_to_segment(at,a.lerp(b,.2),b))
            if distance<best:best=distance;found=i
    return found
func handle(event: InputEvent) -> bool:
    if not enabled:return false
    if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
        if not event.pressed:
            if dragging:dragging=false;finished.emit(false);return true
            return false
        axis=pick(event.position)
        if axis<0:return false
        start_mouse=event.position;start_transform=target
        start_vector=ring_vector(start_mouse,axis) if mode=="rotate" else Vector3.ZERO
        if mode=="rotate" and start_vector.length()<.5:return true
        dragging=true;started.emit();return true
    if event is InputEventMouseMotion and dragging:
        var value := start_transform
        if mode=="rotate":
            var current := ring_vector(event.position,axis)
            if current.length()<.5:return true
            var angle := snappedf(start_vector.signed_angle_to(current,unit(axis)),deg_to_rad(5))
            var rotation_value := Basis(unit(axis),angle)
            value.basis=rotation_value*start_transform.basis
            value.origin=pivot+rotation_value*(start_transform.origin-pivot)
        else:
            var screen_axis := Vector2(1,-1).normalized() if axis==3 else (project(pivot+direction(axis)*length_world)-project(pivot)).normalized()
            var amount: float=(event.position-start_mouse).dot(screen_axis)
            if mode=="move":value.origin+=unit(axis)*snappedf(amount/92*length_world,length_world/92)
            else:
                var factor := clampf(1+amount/100,.1,4)
                var scales := Vector3.ONE*factor if axis==3 else Vector3.ONE
                if axis!=3:scales[axis]=factor
                value.basis=start_transform.basis.scaled_local(scales)
        changed.emit(value);return true
    return dragging
func cancel() -> void:
    if dragging:dragging=false;changed.emit(start_transform);finished.emit(true)
