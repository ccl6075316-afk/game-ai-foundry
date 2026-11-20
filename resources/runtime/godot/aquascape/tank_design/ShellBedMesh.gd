extends RefCounted
const Interior=preload("ShellInterior.gd")
static var cached_path := PackedVector2Array()
static var cached_triangles := PackedVector2Array()

# Tessellate only a sculpted bed. Clip boundary cells to the actual outline,
# including concave and curved edges. Cache the topology across brush strokes.
static func draw(mesh: ImmediateMesh,path: PackedVector2Array,box: Rect2,bed: Dictionary,height: float,material: Material) -> void:
    if path!=cached_path:
        var vertices:=PackedVector2Array()
        var step:=box.size/Interior.GRID
        for z in Interior.GRID:
            for x in Interior.GRID:
                var p:=box.position+Vector2(x,z)*step
                var tile:=PackedVector2Array([p,p+Vector2(step.x,0),p+step,p+Vector2(0,step.y)])
                for poly in Geometry2D.intersect_polygons(path,tile):
                    for j in Geometry2D.triangulate_polygon(poly):vertices.append(poly[j])
        cached_path=path
        cached_triangles=vertices
    mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES,material)
    var du:=Vector2(1.0/Interior.GRID,0)
    var dv:=Vector2(0,du.x)
    for p in cached_triangles:
        var uv:=(p-box.position)/box.size
        var dx:=(Interior.floor_y(uv+du,bed,height)-Interior.floor_y(uv-du,bed,height))/(2*du.x*box.size.x)
        var dz:=(Interior.floor_y(uv+dv,bed,height)-Interior.floor_y(uv-dv,bed,height))/(2*dv.y*box.size.y)
        mesh.surface_set_normal(Vector3(-dx,1,-dz).normalized())
        mesh.surface_set_uv(p*1.25)
        mesh.surface_add_vertex(Vector3(p.x,Interior.floor_y(uv,bed,height),p.y))
    mesh.surface_end()

static func edges(mesh: ImmediateMesh,path: PackedVector2Array,box: Rect2,bed: Dictionary,height: float,material: Material) -> void:
    mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES,material)
    for i in path.size():
        var a:=path[i]
        var b:=path[(i+1)%path.size()]
        var span:=((b-a)/box.size).abs()*Interior.GRID
        var steps:=maxi(1,ceili(maxf(span.x,span.y)))
        var normal:=Vector3(b.y-a.y,0,a.x-b.x).normalized()
        for j in steps:
            var p:=a.lerp(b,float(j)/steps)
            var q:=a.lerp(b,float(j+1)/steps)
            for corner in [0,1,2,0,2,3]:
                var v:=p if corner in [0,3] else q
                var y:=Interior.floor_y((v-box.position)/box.size,bed,height) if corner>=2 else 0.0
                mesh.surface_set_normal(normal)
                mesh.surface_set_uv(Vector2(v.dot((b-a).normalized()),y)*1.25)
                mesh.surface_add_vertex(Vector3(v.x,y,v.y))
    mesh.surface_end()
