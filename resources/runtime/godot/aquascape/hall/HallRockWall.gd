extends RefCounted
## Editable faceted rock envelope. Render, static collision and navigation share these vertices.
const Architecture=preload("HallArchitecture.gd")
const MAX_TRIANGLES=16000
static var cache: Dictionary={}

static func build(data: Dictionary,ends: Vector2=Vector2.ZERO) -> Dictionary:
    var key := str([data.get("length",4),Architecture.height(data),data.get("thickness",.18),
        Architecture.opening(data),Architecture.aperture(data),data.get("rock_depth",.65),
        data.get("rock_relief",.75),data.get("rock_size",1.1),data.get("rock_seed",7),ends])
    if cache.has(key):return cache[key]
    var h := Architecture.height(data)
    var core := Architecture.wall_core_depth(data)
    var left := -float(data.length)*.5-ends.x*core*.5
    var right := float(data.length)*.5+ends.y*core*.5
    var hole := Architecture.aperture(data)
    var opened := Architecture.opening(data)!="none"
    var size := float(data.get("rock_size",1.1))
    var xs := _axis(left,right,size,28,[hole.position.x,hole.end.x] if opened else [])
    var ys := _axis(0,h,size*.72,24,[hole.position.y,hole.end.y] if opened else [])
    var cells: Dictionary={}
    var fronts: Dictionary={};var backs: Dictionary={}
    var seed := int(data.get("rock_seed",7))
    var relief := float(data.get("rock_relief",.75))
    var depth := float(data.get("rock_depth",.65))
    for j in ys.size():
        for i in xs.size():
            var x: float=xs[i];var y: float=ys[j]
            # Shared corner positions make the entire envelope watertight, including apertures.
            if i>0 and i<xs.size()-1 and (not opened or (absf(x-hole.position.x)>.001 and absf(x-hole.end.x)>.001)):
                x+=(_noise(i,j,seed)-.5)*minf(xs[i]-xs[i-1],xs[i+1]-xs[i])*.78*relief
            if j>0 and j<ys.size()-1 and (not opened or (absf(y-hole.position.y)>.001 and absf(y-hole.end.y)>.001)):
                y+=(_noise(j,i,seed+19)-.5)*minf(ys[j]-ys[j-1],ys[j+1]-ys[j])*.72*relief
            if j==ys.size()-1:y-=.10*relief*_noise(i,0,seed)
            var id := Vector2i(i,j)
            for sign in [-1,1]:
                var base := .12+.60*_noise(i,j,seed+sign*29)
                var foot := .16*maxf(0,1-y/.65)
                var z: float=sign*(core*.5+depth*lerpf(.43,base+foot,relief))
                if sign>0:fronts[id]=Vector3(x,y,z)
                else:backs[id]=Vector3(x,y,z)
    for j in ys.size()-1:
        for i in xs.size()-1:
            if opened and hole.has_point(Vector2((xs[i]+xs[i+1])*.5,(ys[j]+ys[j+1])*.5)):continue
            cells[Vector2i(i,j)]=true
    var triangles := PackedVector3Array()
    var volumes: Array[AABB]=[]
    for id: Vector2i in cells:
        var corners: Array[Vector2i]=[id,id+Vector2i.RIGHT,id+Vector2i.ONE,id+Vector2i.DOWN]
        var volume := AABB(fronts[id],Vector3.ZERO)
        for sign in [-1,1]:
            var points: Array[Vector3]=[]
            var inner: Array[Vector3]=[]
            var center := Vector3.ZERO
            for corner in corners:
                var p: Vector3=fronts[corner] if sign>0 else backs[corner]
                points.append(p);center+=p*.25;volume=volume.expand(p)
            var bulge := depth*lerpf(.43,.30+.62*_noise(id.x,id.y,seed+sign*11),relief)
            for k in 4:
                var p := points[k].lerp(center,.35+.25*_noise(id.x+k,id.y,seed))
                p.z=sign*(core*.5+bulge*(.68+.32*_noise(id.x+k,id.y+k,seed+41)))
                inner.append(p);volume=volume.expand(p)
            var normal := Vector3(0,0,sign)
            _quad(triangles,inner,normal)
            for k in 4:_quad(triangles,[points[k],points[(k+1)%4],inner[(k+1)%4],inner[k]],normal)
        volumes.append(volume)
        # End, top, floor and hole reveals are real surfaces, not alpha cutouts.
        for k in 4:
            var neighbor: Vector2i=id+[Vector2i.UP,Vector2i.RIGHT,Vector2i.DOWN,Vector2i.LEFT][k]
            if cells.has(neighbor):continue
            var a := corners[k];var b := corners[(k+1)%4]
            _quad(triangles,[fronts[a],backs[a],backs[b],fronts[b]],
                [Vector3.DOWN,Vector3.RIGHT,Vector3.UP,Vector3.LEFT][k])
    assert(triangles.size()/3<=MAX_TRIANGLES,"Complete rock wall exceeds its architectural mesh budget")
    var builder := SurfaceTool.new();builder.begin(Mesh.PRIMITIVE_TRIANGLES)
    for i in range(0,triangles.size(),3):
        var normal := -(triangles[i+1]-triangles[i]).cross(triangles[i+2]-triangles[i]).normalized()
        for j in 3:builder.set_normal(normal);builder.set_uv(Vector2.ZERO);builder.add_vertex(triangles[i+j])
    builder.index()
    var mesh := builder.commit()
    var shape := ConcavePolygonShape3D.new();shape.set_faces(mesh.get_faces())
    var result := {"mesh":mesh,"shape":shape,"volumes":volumes,"triangles":triangles.size()/3}
    if cache.size()>=32:cache.erase(cache.keys()[0])
    cache[key]=result
    return result

static func _axis(start: float,finish: float,step: float,limit: int,cuts: Array) -> Array[float]:
    var result: Array[float]=[start,finish]
    var count := clampi(ceili((finish-start)/step),1,limit)
    for i in range(1,count):
        var fraction := (float(i)+(_noise(i,count,37)-.5)*.60)/count
        var value := lerpf(start,finish,fraction)
        var near_cut := false
        for cut in cuts:
            if absf(value-cut)<step*.25:near_cut=true
        if not near_cut:result.append(value)
    for cut in cuts:
        if cut>start+.001 and cut<finish-.001:result.append(cut)
    result.sort();return result

static func _noise(x: int,y: int,seed: int) -> float:
    return fposmod(sin(float(x*127+y*311+seed*73))*43758.5453,1.0)

static func _quad(out: PackedVector3Array,p: Array,normal: Vector3) -> void:
    for tri in [[0,1,2],[0,2,3]]:
        var a: Vector3=p[tri[0]];var b: Vector3=p[tri[1]];var c: Vector3=p[tri[2]]
        if (b-a).cross(c-a).dot(normal)>0:
            out.append(a);out.append(c);out.append(b)
        else:out.append(a);out.append(b);out.append(c)
