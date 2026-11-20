extends RefCounted

static func standard(kind: String) -> Dictionary:
    return {"kind":kind, "name":"长方形" if kind == "rect" else "圆形",
        "extent":Vector2(4, 2.5) if kind == "rect" else Vector2(3, 3),
        "height":1.6, "radii":[0.0, 0.0, 0.0, 0.0], "position":Vector2.ZERO}

# The signed offset places the midpoint of a quadratic arc under the pointer.
static func edge(a: Vector2, b: Vector2, bend: float, t: float) -> Vector2:
    return a.lerp(b, t) + (b-a).orthogonal().normalized() * bend * 4.0 * t * (1.0-t)

static func contour(tank: Dictionary) -> PackedVector2Array:
    var points := PackedVector2Array()
    if tank.kind == "custom":
        var nodes: PackedVector2Array = tank.nodes
        for i in nodes.size():
            var steps := 16 if absf(tank.bends[i]) > .001 else 1
            for j in steps:
                points.append(edge(nodes[i], nodes[(i+1)%nodes.size()], tank.bends[i], float(j)/steps))
        return points
    var half: Vector2 = tank.extent * .5
    if tank.kind == "ellipse":
        for i in 72:
            points.append(Vector2.from_angle(TAU*i/72) * half)
        return points
    var signs := [Vector2(-1,-1), Vector2(1,-1), Vector2(1,1), Vector2(-1,1)]
    for i in 4:
        var radius := clampf(tank.radii[i], 0, minf(half.x, half.y))
        if radius <= .001:
            points.append(signs[i] * half)
        else:
            var center: Vector2 = signs[i] * (half - Vector2.ONE * radius)
            for j in 13:
                var point := center + Vector2.from_angle(PI + (i+j/12.0)*PI*.5)*radius
                if points.is_empty() or not points[-1].is_equal_approx(point):
                    points.append(point)
    if points.size()>1 and points[0].is_equal_approx(points[-1]):
        points.resize(points.size()-1)
    return points

static func valid(points: PackedVector2Array) -> bool:
    if points.size()<3:
        return false
    for i in points.size():
        var next := (i+1)%points.size()
        if points[i].distance_squared_to(points[next]) < .000001:
            return false
        for j in range(i+2, points.size()):
            var end := (j+1)%points.size()
            if end != i and Geometry2D.segment_intersects_segment(points[i], points[next], points[j], points[end]) != null:
                return false
    return Geometry2D.triangulate_polygon(points).size() == (points.size()-2)*3

static func bounds(points: PackedVector2Array) -> Rect2:
    var rect := Rect2(points[0], Vector2.ZERO)
    for p in points:
        rect = rect.expand(p)
    return rect
