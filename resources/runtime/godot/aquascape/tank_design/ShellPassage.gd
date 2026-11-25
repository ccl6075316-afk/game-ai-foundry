extends RefCounted
## Local metres. A single floor-level route with optional circular viewing rooms.
const Design=preload("ShellDesign.gd")
const MAX_POINTS=12
const WALL_HEIGHT=1.4

static func valid(route: Variant) -> bool:
    if not route is Dictionary:return false
    if route.is_empty():return true
    if not route.get("points") is Array or route.points.size()<2 or route.points.size()>MAX_POINTS:return false
    if not Design.number(route.get("width")) or route.width<1.8 or route.width>3.6:return false
    if route.has("widths"):
        if not route.widths is Array or route.widths.size()!=route.points.size()-1:return false
        for width in route.widths:
            if not Design.number(width) or width<1.8 or width>3.6:return false
    if not route.get("rooms",[]) is Array:return false
    for p in route.points:
        if not p is Array or p.size()!=2:return false
        for v in p:
            if not Design.number(v):return false
    for room in route.get("rooms",[]):
        if not room is Dictionary or not Design.number(room.get("node")) or int(room.node)!=room.node:return false
        if room.node<1 or room.node>=route.points.size():return false
        if not Design.number(room.get("radius")) or room.radius<1.5 or room.radius>3.5:return false
    return true

static func points(route: Dictionary) -> PackedVector2Array:
    var result:=PackedVector2Array()
    for p in route.get("points",[]):result.append(Vector2(p[0],p[1]))
    return result

static func circle(p: Vector2,radius: float) -> PackedVector2Array:
    var polygon:=PackedVector2Array()
    for i in 48:polygon.append(p+Vector2.from_angle(TAU*i/48.0)*radius)
    return polygon

# Legacy saves have a single width. Materialize per-segment values only on edit.
static func widths(route: Dictionary) -> Array:
    if route.has("widths"):return route.widths.duplicate()
    var result:Array=[]
    for i in maxi(0,route.get("points",[]).size()-1):result.append(route.get("width",2.2))
    return result

static func segment_width(route: Dictionary,index: int) -> float:
    return float(route.widths[index]) if route.has("widths") else float(route.get("width",2.2))

static func node_radius(route: Dictionary,index: int) -> float:
    return segment_width(route,maxi(0,index-1))*.5

static func transition_length(route: Dictionary,index: int) -> float:
    if index==0:return 0.0
    return maxf(1.2,absf(segment_width(route,index)-segment_width(route,index-1))*1.5)

static func radius_at(route: Dictionary,index: int,t: float) -> float:
    var end_radius:=segment_width(route,index)*.5
    if index==0:return end_radius
    var a:Vector2=Vector2(route.points[index][0],route.points[index][1])
    var b:Vector2=Vector2(route.points[index+1][0],route.points[index+1][1])
    var blend:=clampf(t*a.distance_to(b)/maxf(.00001,minf(a.distance_to(b),transition_length(route,index))),0.0,1.0)
    blend=blend*blend*(3.0-2.0*blend)
    return lerpf(node_radius(route,index),end_radius,blend)

static func footprint(route: Dictionary) -> PackedVector2Array:
    var path:=points(route)
    if path.size()<2:return PackedVector2Array()
    var pieces:Array[PackedVector2Array]=[]
    for i in path.size()-1:
        var delta:=path[i+1]-path[i]
        if delta.length()<.0001:return PackedVector2Array()
        var right:=Vector2(-delta.y,delta.x).normalized()
        var steps:=maxi(1,ceili(delta.length()/.15))
        var strip:=PackedVector2Array()
        for j in steps+1:
            var t:=float(j)/steps
            strip.append(path[i].lerp(path[i+1],t)+right*radius_at(route,i,t))
        for j in range(steps,-1,-1):
            var t:=float(j)/steps
            strip.append(path[i].lerp(path[i+1],t)-right*radius_at(route,i,t))
        # Endpoint disks give rounded bends/caps, using the same junction radius.
        if i==0:pieces.append(circle(path[i],node_radius(route,i)))
        pieces.append(strip)
        pieces.append(circle(path[i+1],node_radius(route,i+1)))
    var result:PackedVector2Array=pieces[0]
    for i in range(1,pieces.size()):
        var joined:=Geometry2D.merge_polygons(result,pieces[i])
        if joined.size()!=1:return PackedVector2Array()
        result=joined[0]
    for room in route.get("rooms",[]):
        var joined:=Geometry2D.merge_polygons(result,circle(path[int(room.node)],room.radius))
        if joined.size()!=1:return PackedVector2Array()
        result=joined[0]
    return result

static func inside_footprint(route: Dictionary,design: Dictionary) -> PackedVector2Array:
    var outline:=footprint(route)
    if outline.is_empty():return outline
    var clipped:=Geometry2D.intersect_polygons(outline,Design.contour(design))
    return clipped[0] if clipped.size()==1 else PackedVector2Array()

# Build once per mesh instead of decoding the route for every roof vertex.
static func profile(route: Dictionary) -> Dictionary:
    var path:=points(route)
    var radii:=PackedFloat64Array()
    var ends:=PackedFloat64Array()
    var spans:=PackedFloat64Array()
    var deltas:=PackedVector2Array()
    var inverse_lengths:=PackedFloat64Array()
    for i in path.size():
        radii.append(node_radius(route,i))
        if i>=path.size()-1:continue
        var delta:=path[i+1]-path[i]
        deltas.append(delta)
        ends.append(segment_width(route,i)*.5)
        spans.append(minf(1.0,transition_length(route,i)/maxf(delta.length(),.00001)))
        inverse_lengths.append(1.0/maxf(delta.length_squared(),.00001))
    return {"path":path,"radii":radii,"ends":ends,"spans":spans,"deltas":deltas,"inverse_lengths":inverse_lengths,"rooms":route.get("rooms",[])}

static func profile_roof(p: Vector2,data: Dictionary) -> float:
    var path:PackedVector2Array=data.path
    var radii:PackedFloat64Array=data.radii
    var ends:PackedFloat64Array=data.ends
    var spans:PackedFloat64Array=data.spans
    var deltas:PackedVector2Array=data.deltas
    var inverse_lengths:PackedFloat64Array=data.inverse_lengths
    var height_squared:=0.0
    for i in deltas.size():
        var t:=clampf((p-path[i]).dot(deltas[i])*inverse_lengths[i],0.0,1.0)
        var blend:=clampf(t/maxf(spans[i],.00001),0.0,1.0)
        blend=blend*blend*(3.0-2.0*blend)
        var r:=lerpf(radii[i],ends[i],blend)
        height_squared=maxf(height_squared,r*r-p.distance_squared_to(path[i]+deltas[i]*t))
    for i in path.size():
        height_squared=maxf(height_squared,radii[i]*radii[i]-p.distance_squared_to(path[i]))
    for room in data.rooms:
        var r:float=room.radius
        height_squared=maxf(height_squared,r*r-p.distance_squared_to(path[int(room.node)]))
    return WALL_HEIGHT+sqrt(height_squared)

static func roof(p: Vector2,route: Dictionary) -> float:
    return profile_roof(p,profile(route))

static func nearest_wall(p: Vector2,contour: PackedVector2Array) -> Vector2:
    var best:=contour[0]
    for i in contour.size():
        var q:=Geometry2D.get_closest_point_to_segment(p,contour[i],contour[(i+1)%contour.size()])
        if p.distance_squared_to(q)<p.distance_squared_to(best):best=q
    return best

static func problem(design: Dictionary,bed: Dictionary) -> String:
    var route:Dictionary=bed.get("passage",{})
    if route.is_empty():return ""
    if not valid(route):return "观景通道数据无效。"
    if bed.substrate!="bare" or bed.depth_cm!=0 or not bed.get("heights",[]).is_empty():return "请先把底床改成裸缸底，清空沙层后施工。"
    if not bed.get("fish",[]).is_empty():return "试建阶段请先收回鱼。现有游动尚未接入通道避障。"
    var contour:=Design.contour(design)
    var path:=points(route)
    if path[0].distance_to(nearest_wall(path[0],contour))>.05:return "入口必须吸附缸壁。"
    var water:float=design.height-minf(.09,design.height*.05)
    var polygon:=footprint(route)
    if polygon.is_empty():return "通道产生交叉或封闭空洞，请调整节点。"
    for i in path.size()-1:
        if path[i].distance_to(path[i+1])<.5:return "相邻节点至少相隔半米。"
        var count:=maxi(2,ceili(path[i].distance_to(path[i+1])/.15))
        for j in count+1:
            var p:=path[i].lerp(path[i+1],float(j)/count)
            var r:=radius_at(route,i,float(j)/count)
            if not Geometry2D.is_point_in_polygon(p,contour) and p.distance_to(nearest_wall(p,contour))>.06:return "通道走出了展缸。"
            # Only the connected entrance and an optional terminal exit may cross the wall.
            var portal:=p.distance_to(path[0])<node_radius(route,0)+.15 or (path[-1].distance_to(nearest_wall(path[-1],contour))<.05 and p.distance_to(path[-1])<node_radius(route,path.size()-1)+.15)
            if not portal and p.distance_to(nearest_wall(p,contour))<r+.08:return "通道太靠近侧壁，请向内移动。"
            if roof(p,route)>water-.1:return "缸内高度不足，需降低通道宽度或观景区半径。"
    for room in route.get("rooms",[]):
        if path[int(room.node)].distance_to(nearest_wall(path[int(room.node)],contour))<float(room.radius)+.08:return "观景区碰到缸壁，请缩小或移向缸内。"
        if WALL_HEIGHT+float(room.radius)>water-.1:return "观景区圆顶超出水面。"
    var bounds:=Design.bounds(design)
    for prop in bed.get("props",[]):
        var center:=Vector2(bounds.position.x,bounds.position.z)+Vector2(bounds.size.x,bounds.size.z)*Vector2(prop.u,prop.v)
        var extent:=1.0
        if prop.has("stretch"):
            extent=Vector3(prop.stretch[0],prop.stretch[1],prop.stretch[2]).length()
        if Geometry2D.is_point_in_polygon(center,polygon) or center.distance_to(nearest_wall(center,polygon))<extent:
            return "通道预留范围内有造景，请先移开。"
    return ""
