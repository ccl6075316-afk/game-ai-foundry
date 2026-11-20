extends RefCounted

static func material() -> StandardMaterial3D:
    var paint := StandardMaterial3D.new()
    paint.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    paint.vertex_color_use_as_albedo=true
    paint.cull_mode=BaseMaterial3D.CULL_DISABLED
    paint.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    return paint

static func vertex(mesh: ImmediateMesh, point: Vector2, y: float, color: Color) -> void:
    mesh.surface_set_color(color)
    mesh.surface_add_vertex(Vector3(point.x,y,point.y))

static func build(path: PackedVector2Array, height: float) -> ImmediateMesh:
    var mesh := ImmediateMesh.new()
    mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
    var triangles := Geometry2D.triangulate_polygon(path)
    for i in triangles:
        vertex(mesh,path[i],0,Color("#c7b587"))
    for i in triangles:
        vertex(mesh,path[i],height*.91,Color(.22,.76,.73,.69))
    for i in path.size():
        var a := path[i]
        var b := path[(i+1)%path.size()]
        var tone := .52+.18*(b-a).normalized().x
        var glass := Color(.23,tone,.66,.64)
        for pair in [[a,0],[b,0],[b,height],[a,0],[b,height],[a,height]]:
            vertex(mesh,pair[0],pair[1],glass)
    mesh.surface_end()
    mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for i in path.size():
        vertex(mesh,path[i],height,Color("#e5fff5"))
        vertex(mesh,path[(i+1)%path.size()],height,Color("#e5fff5"))
    mesh.surface_end()
    return mesh
