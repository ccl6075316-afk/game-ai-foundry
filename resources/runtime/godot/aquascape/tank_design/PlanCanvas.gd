extends Control
const Shape = preload("Footprint.gd")
signal changed
var snap := true
var closed := false
var draft := {"kind":"custom","nodes":PackedVector2Array(),"bends":[],"height":1.6}
var drag := ""
var index := -1
var pixels: float:
    get: return minf(size.x/18.0, size.y/13.0)

func screen(p: Vector2) -> Vector2:
    return size*.5 + p*pixels

func world(p: Vector2) -> Vector2:
    return (p-size*.5)/pixels

func snap_point(p: Vector2) -> Vector2:
    return p.snapped(Vector2(.5,.5)) if snap else p

func update_view() -> void:
    queue_redraw()
    changed.emit()

func _draw() -> void:
    draw_rect(Rect2(Vector2.ZERO,size), Color("#102b34"))
    var spacing := pixels*.5
    if spacing < 1: return
    var origin := size*.5
    for ix in range(-ceili(origin.x/spacing),ceili(origin.x/spacing)+1):
        var x := origin.x+ix*spacing
        for iy in range(-ceili(origin.y/spacing),ceili(origin.y/spacing)+1):
            draw_circle(Vector2(x,origin.y+iy*spacing),1.4,Color("#45626a"))
    draw_shape(draft,Vector2.ZERO,true,closed)
    for i in draft.nodes.size():
        var a: Vector2 = draft.nodes[i]
        draw_circle(screen(a),6,Color("#ffe09a"))
        if closed or i+1<draft.nodes.size():
            var b: Vector2 = draft.nodes[(i+1)%draft.nodes.size()]
            draw_circle(screen(Shape.edge(a,b,draft.bends[i],.5)),4,Color.WHITE)

func draw_shape(tank: Dictionary, at: Vector2, active: bool, loop: bool) -> void:
    var path := Shape.contour(tank)
    if path.size()<2: return
    if not loop and tank.kind=="custom":
        var tail := 16 if absf(tank.bends[-1])>.001 else 1
        path.resize(path.size()-tail)
        path.append(tank.nodes[-1])
    for i in path.size(): path[i]=screen(at+path[i])
    if loop:
        if tank.kind!="custom" or Shape.valid(path):
            draw_colored_polygon(path,Color("#287477") if active else Color("#225258"))
        path.append(path[0])
    draw_polyline(path,Color("#99eee0") if active else Color("#60a9ac"),2.5,true)

func _gui_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
        if event.pressed:
            start_design(event.position)
        else: drag=""
        update_view()
        accept_event()
    elif event is InputEventMouseMotion and drag!="":
        var p := world(event.position.clamp(Vector2.ZERO,size))
        if drag=="node": draft.nodes[index]=snap_point(p)
        elif drag=="bend":
            var a: Vector2=draft.nodes[index]
            var b: Vector2=draft.nodes[(index+1)%draft.nodes.size()]
            draft.bends[index]=(p-(a+b)*.5).dot((b-a).orthogonal().normalized())
        update_view()
        accept_event()

func start_design(pos: Vector2) -> void:
    var nodes: PackedVector2Array=draft.nodes
    var p := world(pos)
    for i in nodes.size():
        if screen(nodes[i]).distance_to(pos)<10:
            if i==0 and nodes.size()>=3 and not closed:
                closed=true
            else:
                drag="node"
                index=i
            return
    var edge_count := nodes.size() if closed else maxi(0,nodes.size()-1)
    for i in edge_count:
        var a := nodes[i]
        var b := nodes[(i+1)%nodes.size()]
        var previous := a
        for j in range(1,17):
            var current := Shape.edge(a,b,draft.bends[i],j/16.0)
            if Geometry2D.get_closest_point_to_segment(p,previous,current).distance_to(p)*pixels<8:
                drag="bend"
                index=i
                return
            previous=current
    if not closed:
        draft.nodes.append(snap_point(p))
        draft.bends.append(0.0)
