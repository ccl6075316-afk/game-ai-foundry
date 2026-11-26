extends RefCounted
## One box specification drives visible volume and physical collisions.
const Architecture=preload("HallArchitecture.gd")

static func parts(data: Dictionary,ends: Vector2=Vector2.ZERO) -> Array:
    var out: Array=[]
    var h := Architecture.height(data)
    var t := float(data.get("thickness",.18))
    var depth := Architecture.wall_depth(data)
    var core := Architecture.wall_core_depth(data)
    var left := -float(data.length)*.5-ends.x*core*.5
    var right := float(data.length)*.5+ends.y*core*.5
    if right-left<.01:return out
    var profile: String=data.get("wall_profile","plain")
    _part(out,data,Rect2(left,0,right-left,h-.08),core,false)
    _part(out,data,Rect2(left,h-.08,right-left,.08),depth,true)
    if profile=="wainscot":
        var skirt := minf(1.0,h*.48)
        _part(out,data,Rect2(left,0,right-left,skirt),t+.08,true)
        _part(out,data,Rect2(left,skirt,right-left,.09),depth,true)
        _part(out,data,Rect2(left,0,right-left,.12),depth,true)
    elif profile in ["pilaster","recessed"]:
        var rail := .16 if profile=="recessed" else .12
        _part(out,data,Rect2(left,0,right-left,rail),depth,true)
        _part(out,data,Rect2(left,h-rail,right-left,rail),depth,true)
        var width := minf(.18 if profile=="recessed" else .26,(right-left)*.5)
        var count := maxi(1,ceili((right-left)/1.8))
        for i in range(count+1):
            var x := lerpf(left+width*.5,right-width*.5,float(i)/count)
            if Architecture.opening(data)!="none":
                var hole := Architecture.aperture(data)
                if x+width*.5>hole.position.x and x-width*.5<hole.end.x:continue
            _part(out,data,Rect2(x-width*.5,rail,width,h-rail*2),depth,true)
        if Architecture.opening(data)!="none":
            var hole := Architecture.aperture(data)
            var rim := .12
            _part(out,data,Rect2(hole.position.x-rim,hole.position.y,rim,hole.size.y+rim),depth,true)
            _part(out,data,Rect2(hole.end.x,hole.position.y,rim,hole.size.y+rim),depth,true)
            _part(out,data,Rect2(hole.position.x,hole.end.y,hole.size.x,rim),depth,true)
            if hole.position.y>0:_part(out,data,Rect2(hole.position.x-rim,hole.position.y-rim,hole.size.x+rim*2,rim),depth,true)
    return out

static func _part(out: Array,data: Dictionary,rect: Rect2,depth: float,trim: bool) -> void:
    var pieces: Array[Rect2]=[rect]
    if Architecture.opening(data)!="none":
        var cut := rect.intersection(Architecture.aperture(data))
        if cut.has_area():
            pieces=[Rect2(rect.position,Vector2(cut.position.x-rect.position.x,rect.size.y)),
                Rect2(Vector2(cut.end.x,rect.position.y),Vector2(rect.end.x-cut.end.x,rect.size.y)),
                Rect2(Vector2(cut.position.x,rect.position.y),Vector2(cut.size.x,cut.position.y-rect.position.y)),
                Rect2(Vector2(cut.position.x,cut.end.y),Vector2(cut.size.x,rect.end.y-cut.end.y))]
    for p in pieces:
        if p.size.x<=.0001 or p.size.y<=.0001:continue
        out.append({"at":Vector3(p.get_center().x,p.get_center().y,0),"size":Vector3(p.size.x,p.size.y,depth),"trim":trim})

static func exposed_faces(boxes: Array) -> Array:
    # Boolean boundary of axis-aligned volumes; later trim owns coincident faces.
    var faces: Array=[]
    for i in boxes.size():
        var box := AABB(boxes[i].at-boxes[i].size*.5,boxes[i].size)
        for axis in 3:
            var u := (axis+1)%3;var v := (axis+2)%3
            for sign in [-1,1]:
                var plane: float=box.position[axis] if sign<0 else box.end[axis]
                var pieces: Array[Rect2]=[Rect2(box.position[u],box.position[v],box.size[u],box.size[v])]
                for j in boxes.size():
                    if i==j:continue
                    var other := AABB(boxes[j].at-boxes[j].size*.5,boxes[j].size)
                    var outside: float=plane+sign*.00001
                    var hidden: bool=outside>other.position[axis] and outside<other.end[axis]
                    var coincident: bool=j>i and absf(plane-(other.position[axis] if sign<0 else other.end[axis]))<.000001
                    if not hidden and not coincident:continue
                    var cut := Rect2(other.position[u],other.position[v],other.size[u],other.size[v])
                    var next: Array[Rect2]=[]
                    for piece in pieces:next.append_array(_subtract(piece,cut))
                    pieces=next
                    if pieces.is_empty():break
                for rect in pieces:faces.append({"axis":axis,"sign":sign,"plane":plane,"rect":rect,"trim":boxes[i].trim})
    return faces

static func _subtract(rect: Rect2,cut: Rect2) -> Array[Rect2]:
    var hit := rect.intersection(cut)
    if not hit.has_area():return [rect]
    var result: Array[Rect2]=[]
    for piece in [Rect2(rect.position,Vector2(hit.position.x-rect.position.x,rect.size.y)),
        Rect2(Vector2(hit.end.x,rect.position.y),Vector2(rect.end.x-hit.end.x,rect.size.y)),
        Rect2(Vector2(hit.position.x,rect.position.y),Vector2(hit.size.x,hit.position.y-rect.position.y)),
        Rect2(Vector2(hit.position.x,hit.end.y),Vector2(hit.size.x,rect.end.y-hit.end.y))]:
        if piece.size.x>.000001 and piece.size.y>.000001:result.append(piece)
    return result

static func emit_face(builder: SurfaceTool,face: Dictionary) -> void:
    var axis: int=face.axis;var u := (axis+1)%3;var v := (axis+2)%3
    var rect: Rect2=face.rect;var points: Array[Vector3]=[]
    for uv in [rect.position,Vector2(rect.end.x,rect.position.y),rect.end,Vector2(rect.position.x,rect.end.y)]:
        var p := Vector3.ZERO;p[axis]=face.plane;p[u]=uv.x;p[v]=uv.y;points.append(p)
    var normal := Vector3.ZERO;normal[axis]=face.sign
    for index in ([0,2,1,0,3,2] if face.sign>0 else [0,1,2,0,2,3]):
        builder.set_normal(normal);builder.set_uv(Vector2.ZERO);builder.add_vertex(points[index])
