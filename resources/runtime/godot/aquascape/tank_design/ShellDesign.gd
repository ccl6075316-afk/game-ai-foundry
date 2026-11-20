extends RefCounted
const MIN_HEIGHT := .3
const Shape = preload("Footprint.gd")

# Layout documents contain JSON values. Freeze a custom template's outline per instance.
static func from_template(template: Dictionary) -> Dictionary:
    var design := {"kind":template.kind, "height":template.height}
    if template.kind=="custom":
        var points: Array=[]
        for point in Shape.contour(template): points.append([point.x,point.y])
        design.points=points
    else:
        design.width=template.extent.x
        design.depth=template.extent.y
        design.radii=template.radii.duplicate()
    return design

static func contour(design: Dictionary) -> PackedVector2Array:
    if design.kind=="custom":
        var path := PackedVector2Array()
        for pair in design.points: path.append(Vector2(pair[0],pair[1]))
        return path
    return Shape.contour({"kind":design.kind,"extent":Vector2(design.width,design.depth),"radii":design.radii})

static func number(value: Variant) -> bool:
    return (value is float or value is int) and is_finite(value)

static func valid_height(value: Variant) -> bool:
    # The camera and collision bounds use single-precision 3D vectors.
    return number(value) and value>=MIN_HEIGHT and is_finite(Vector3(0,value,0).length_squared()*16.0)

static func valid(design: Variant) -> bool:
    if not design is Dictionary or not valid_height(design.get("height")): return false
    if design.get("kind")=="custom":
        if not design.get("points") is Array or design.points.size()<3: return false
        for pair in design.points:
            if not pair is Array or pair.size()!=2 or not number(pair[0]) or not number(pair[1]): return false
        return Shape.valid(contour(design))
    if design.get("kind") not in ["rect","ellipse"]: return false
    for key in ["width","depth"]:
        if not number(design.get(key)) or design[key]<.5 or design[key]>16: return false
    if not design.get("radii") is Array or design.radii.size()!=4: return false
    for r in design.radii:
        if not number(r) or r<0 or r>minf(design.width,design.depth)*.5+.00001: return false
    return true

static func bounds(design: Dictionary) -> AABB:
    var rect: Rect2
    if design.kind=="custom":
        rect=Shape.bounds(contour(design))
    else:
        var extent := Vector2(design.width,design.depth)
        rect=Rect2(-extent*.5,extent)
    return AABB(Vector3(rect.position.x,0,rect.position.y),Vector3(rect.size.x,design.height,rect.size.y))
