extends RefCounted
## Positive end offsets extend to the far face. Negative ones stop at the near face.
const EPS := .0001

static func segment(a: Vector2,b: Vector2,level: int=0,height: float=3.2) -> Dictionary:
    return {"a":a,"b":b,"axis":0 if absf(a.x-b.x)>absf(a.y-b.y) else 1,"level":level,"height":height}

static func wall(data: Dictionary) -> Dictionary:
    var center := Vector2(data.at[0],data.at[1])
    var half := Vector2(cos(data.yaw),-sin(data.yaw))*float(data.length)*.5
    return segment(center-half,center+half,data.get("level",0))

static func offsets(parts: Array) -> Array[Vector2]:
    var result: Array[Vector2]=[]
    for part in parts:
        result.append(Vector2(end_offset(part,part.a,parts),end_offset(part,part.b,parts)))
    return result

static func end_offset(part: Dictionary,p: Vector2,parts: Array) -> float:
    var axis: int=part.axis
    var straight := false
    var transverse := false
    var crosses := false
    var other_height := 0.0
    var cross_arms := 0
    for other in parts:
        if is_same(part,other) or part.level!=other.level:continue
        var a: Vector2=other.a
        var b: Vector2=other.b
        if other.axis==axis:
            if p.distance_squared_to(a)<EPS*EPS or p.distance_squared_to(b)<EPS*EPS:straight=true
            continue
        if absf(p[axis]-a[axis])>EPS:continue
        var perpendicular := 1-axis
        var low := minf(a[perpendicular],b[perpendicular])
        var high := maxf(a[perpendicular],b[perpendicular])
        if p[perpendicular]<low-EPS or p[perpendicular]>high+EPS:continue
        transverse=true
        cross_arms+=1
        crosses=crosses or (p[perpendicular]>low+EPS and p[perpendicular]<high-EPS)
        other_height=maxf(other_height,other.height)
    if not transverse:return 0
    crosses=crosses or cross_arms>=2
    if straight:return -1 if crosses and axis==1 else 0
    if crosses:return -1
    if not is_equal_approx(part.height,other_height):return 1 if part.height>other_height else -1
    return 1 if axis==0 else -1
