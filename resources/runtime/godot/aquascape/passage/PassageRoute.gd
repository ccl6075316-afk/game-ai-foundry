extends RefCounted
## Metres, continuous elevations and a flat walking chord. No scene references.
const MAX_SEGMENTS=48
const MAX_POINTS=12

static func initial() -> Dictionary:
    return {"schema_version":1,"section":"round","width":2.6,"height":2.8,"points":[[-13.0,0.0,0.0],[-6.0,.45,-1.2],[0.0,1.5,0.0],[6.0,2.5,1.2],[13.0,3.0,0.0]]}

static func point(values: Array) -> Vector3:
    return Vector3(float(values[0]),float(values[1]),float(values[2]))

static func array(value: Vector3) -> Array:
    return [value.x,value.y,value.z]

static func radius(data: Dictionary) -> float:
    return (data.height*data.height+data.width*data.width*.25)/(2.0*data.height) if data.section=="round" else data.width*.5

static func samples(data: Dictionary) -> PackedVector3Array:
    var knots: Array=data.points
    var curve := Curve3D.new();curve.bake_interval=.08
    for i in knots.size():
        var p := point(knots[i])
        var before := point(knots[maxi(0,i-1)])
        var after := point(knots[mini(knots.size()-1,i+1)])
        var tangent := (after-before).normalized()
        var handle: float=minf(p.distance_to(before) if i>0 else p.distance_to(after),p.distance_to(after) if i<knots.size()-1 else p.distance_to(before))*.35
        curve.add_point(p,-tangent*handle if i>0 else Vector3.ZERO,tangent*handle if i<knots.size()-1 else Vector3.ZERO)
    var length := curve.get_baked_length()
    var count := mini(MAX_SEGMENTS,maxi(4,ceili(length/.8)))
    var result := PackedVector3Array()
    for i in count+1:result.append(curve.sample_baked(length*float(i)/count,true))
    return result

static func validate(data: Variant) -> String:
    if not data is Dictionary or data.get("schema_version")!=1:return "路线版本无效。"
    for key in data:
        if key not in ["schema_version","section","width","height","points"]:return "路线包含未知字段。"
    if data.get("section") not in ["round","arch"]:return "请选择圆筒或直墙拱顶。"
    for key in ["width","height"]:
        var v: Variant=data.get(key)
        if not (v is float or v is int) or not is_finite(float(v)):return "宽高必须是有限数值。"
    if data.width<2 or data.width>3.6 or data.height<2.4 or data.height>3.6:return "试建宽度 2～3.6 米，净高 2.4～3.6 米。"
    if not data.get("points") is Array or data.points.size()<2 or data.points.size()>MAX_POINTS:return "需要 2～12 个控制点。"
    for values in data.points:
        if not values is Array or values.size()!=3:return "控制点需要 X、标高、Z。"
        for v in values:
            if not (v is float or v is int) or not is_finite(float(v)):return "控制点数值无效。"
        if absf(values[0])>14 or values[1]<0 or values[1]>4 or absf(values[2])>4:return "控制点须在试建场地内：X ±14、Z ±4、标高 0～4 米。"
    var first := point(data.points[0]);var last := point(data.points[-1])
    if not ((first.x<=-11 and last.x>=11) or (first.x>=11 and last.x<=-11)):return "起点、终点分别放在缸两侧的平台区（X ≤－11 / X ≥11）。"
    for i in data.points.size()-1:
        if point(data.points[i]).distance_to(point(data.points[i+1]))<1.2:return "相邻控制点至少间隔 1.2 米。"
    var path := samples(data);var length := 0.0
    var outer := radius(data)
    for i in path.size()-1:
        var d: Vector3=path[i+1]-path[i];var horizontal := Vector2(d.x,d.z).length()
        if horizontal<.01 or absf(d.y)/horizontal>.34:return "坡道太陡，请拉长上升路线或降低中间控制点。"
        length+=d.length()
        if absf(path[i].x)<9.2:
            if absf(path[i].z)+outer>5.85:return "弯道太靠近缸侧壁，请向中间收一点。"
            if path[i].y+data.height>6.8:return "通道顶部接近水面，请降低标高或净高。"
            if data.section=="round" and path[i].y+data.height-2*outer<-.95:return "圆筒下部接近缸底，请提高路线或减小宽度。"
        if i>0:
            var before: Vector3=path[i]-path[i-1]
            var angle := absf(Vector2(before.x,before.z).angle_to(Vector2(d.x,d.z)))
            if angle>.001 and horizontal/(2*sin(angle*.5))<outer*1.4:return "转弯太急，请放宽弯道或减小通道宽度。"
    if length>40:return "本轮试建路线总长不超过 40 米。"
    for i in path.size():
        for j in range(i+1,path.size()):
            if j-i<ceili((outer*2+1)/.8):continue
            if Vector2(path[i].x-path[j].x,path[i].z-path[j].z).length()<outer*2+.1 and absf(path[i].y-path[j].y)<data.height+.2:return "通道折返相互挤压，请拉开两段路线。"
    return ""

static func local_point(p: Vector3,a: Vector3,b: Vector3) -> Vector3:
    var axis := Vector2(b.x-a.x,b.z-a.z).normalized()
    var horizontal := Vector2(b.x-a.x,b.z-a.z).length()
    var q := Vector2(p.x-a.x,p.z-a.z)
    var along := q.dot(axis)
    return Vector3(q.dot(Vector2(-axis.y,axis.x)),p.y-a.y-along*(b.y-a.y)/horizontal,along)

static func contains(data: Dictionary,path: PackedVector3Array,p: Vector3,margin: float=0.0) -> bool:
    var r := radius(data);var center: float=data.height-r
    for i in path.size()-1:
        var q := local_point(p,path[i],path[i+1]);var length := Vector2(path[i+1].x-path[i].x,path[i+1].z-path[i].z).length()
        if q.z<-.35-margin or q.z>length+.35+margin:continue
        var y := q.y-center
        if data.section=="arch":
            if q.y< -margin:continue
            y=maxf(0,y)
        if Vector2(q.x,y).length()<=r+margin:return true
    return false

static func floor_at(path: PackedVector3Array,distance: float) -> Vector3:
    for i in path.size()-1:
        var length := path[i].distance_to(path[i+1])
        if distance<=length:return path[i].lerp(path[i+1],clampf(distance/length,0,1))
        distance-=length
    return path[-1]

static func _clip(span: Vector2,p: float,d: float,lo: float,hi: float) -> Vector2:
    if absf(d)<.000001:return Vector2(1,-1) if p<lo or p>hi else span
    var a := (lo-p)/d;var b := (hi-p)/d
    return Vector2(maxf(span.x,minf(a,b)),minf(span.y,maxf(a,b)))

static func _circle(p: Vector2,d: Vector2,r: float,span: Vector2) -> Vector2:
    var a := d.length_squared();var c := p.length_squared()-r*r
    if a<.0000001:return span if c<=0 else Vector2(1,-1)
    var b := p.dot(d);var disc := b*b-a*c
    if disc<0:return Vector2(1,-1)
    return Vector2(maxf(span.x,(-b-sqrt(disc))/a),minf(span.y,(-b+sqrt(disc))/a))

static func ray_span(data: Dictionary,a: Vector3,b: Vector3,origin: Vector3,direction: Vector3,wet: Vector2) -> Vector2:
    var p := local_point(origin,a,b);var d := local_point(origin+direction,a,b)-p
    var span := _clip(wet,p.z,d.z,-.35,Vector2(b.x-a.x,b.z-a.z).length()+.35)
    if span.y<=span.x:return Vector2(1,-1)
    var r := radius(data);var center: float=data.height-r
    var circle := _circle(Vector2(p.x,p.y-center),Vector2(d.x,d.y),r,span)
    if data.section=="round":return circle
    circle=_clip(circle,p.y,d.y,center,data.height)
    var box := _clip(_clip(span,p.x,d.x,-r,r),p.y,d.y,0,center)
    if circle.y>circle.x and box.y>box.x:return Vector2(minf(circle.x,box.x),maxf(circle.y,box.y))
    return circle if circle.y>circle.x else box

static func wet_length(data: Dictionary,path: PackedVector3Array,origin: Vector3,direction: Vector3,wet: Vector2) -> float:
    var spans: Array[Vector2]=[]
    for i in path.size()-1:
        var s := ray_span(data,path[i],path[i+1],origin,direction,wet)
        if s.y>s.x:spans.append(s)
    spans.sort_custom(func(a,b):return a.x<b.x)
    var dry := 0.0;var end := wet.x
    for s in spans:dry+=maxf(0,s.y-maxf(end,s.x));end=maxf(end,s.y)
    return maxf(0,wet.y-wet.x-dry)
