extends Node3D
## Route-driven cover, flat walking floor and their actual collision surfaces.
const Route=preload("res://scripts/aquarium/passage/PassageRoute.gd")
var path := PackedVector3Array()
var floor_body: StaticBody3D
var shell_body: StaticBody3D
var triangles := 0

func _material(color: Color,glass:=false) -> StandardMaterial3D:
    var material := StandardMaterial3D.new();material.albedo_color=color;material.roughness=.85;material.metallic_specular=0
    material.cull_mode=BaseMaterial3D.CULL_DISABLED
    if glass:
        material.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
        material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
        material.depth_draw_mode=BaseMaterial3D.DEPTH_DRAW_DISABLED
    return material

func _triangle(tool: SurfaceTool,a: Vector3,b: Vector3,c: Vector3) -> void:
    var normal := (b-a).cross(c-a).normalized()
    for p in [a,b,c]:
        tool.set_normal(normal);tool.set_uv(Vector2(p.x,p.z)*.5);tool.add_vertex(p)

func _surface(tool: SurfaceTool,material: Material,name_value: String,collide:=true) -> StaticBody3D:
    var mesh: ArrayMesh=tool.commit();triangles+=mesh.get_faces().size()/3
    var visual := MeshInstance3D.new();visual.name=name_value;visual.mesh=mesh;visual.material_override=material;add_child(visual)
    visual.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    if not collide:return null
    var body := StaticBody3D.new();body.collision_layer=1;body.collision_mask=0;add_child(body)
    var shape := CollisionShape3D.new();var polygon := ConcavePolygonShape3D.new()
    polygon.set_faces(mesh.get_faces());polygon.backface_collision=true;shape.shape=polygon;body.add_child(shape)
    return body

func _profile(data: Dictionary) -> PackedVector2Array:
    var profile := PackedVector2Array();var r := Route.radius(data);var center: float=data.height-r
    if data.section=="round":
        for i in 24:
            var angle := TAU*float(i)/24
            profile.append(Vector2(cos(angle)*r,center+sin(angle)*r))
    else:
        profile.append(Vector2(-r,0));profile.append(Vector2(r,0))
        for i in 17:
            var angle := PI*float(i)/16
            profile.append(Vector2(cos(angle)*r,center+sin(angle)*r))
    return profile

func rebuild(data: Dictionary,with_collision:=true) -> void:
    for child in get_children():
        if child is StaticBody3D:child.collision_layer=0
        remove_child(child);child.queue_free()
    triangles=0;path=Route.samples(data)
    var profile := _profile(data);var rings: Array=[];var rights: Array[Vector3]=[]
    for i in path.size():
        var tangent: Vector3=path[mini(i+1,path.size()-1)]-path[maxi(0,i-1)]
        var right := Vector3(-tangent.z,0,tangent.x).normalized();rights.append(right)
        var ring := PackedVector3Array()
        for p in profile:ring.append(path[i]+right*p.x+Vector3.UP*p.y)
        rings.append(ring)
    var shell := SurfaceTool.new();shell.begin(Mesh.PRIMITIVE_TRIANGLES)
    var floor_tool := SurfaceTool.new();floor_tool.begin(Mesh.PRIMITIVE_TRIANGLES)
    for i in path.size()-1:
        for j in profile.size():
            var k := (j+1)%profile.size()
            _triangle(shell,rings[i][j],rings[i+1][j],rings[i+1][k])
            _triangle(shell,rings[i][j],rings[i+1][k],rings[i][k])
        var a: Vector3=path[i]-rights[i]*data.width*.5
        var b: Vector3=path[i]+rights[i]*data.width*.5
        var c: Vector3=path[i+1]+rights[i+1]*data.width*.5
        var d: Vector3=path[i+1]-rights[i+1]*data.width*.5
        _triangle(floor_tool,a,c,d);_triangle(floor_tool,a,b,c)
    var floor_paint := _material(Color("8ea2a5"))
    floor_paint.albedo_texture=load("res://assets/aquarium-hall-style-v3/hall_floor.png")
    floor_paint.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
    floor_body=_surface(floor_tool,floor_paint,"WalkingFloor",with_collision)
    shell_body=_surface(shell,_material(Color(.26,.55,.65,.055),true),"GlassCover",with_collision)
    # Sparse structural hoops make the cover legible while retaining open views.
    var frame := ImmediateMesh.new();frame.surface_begin(Mesh.PRIMITIVE_LINES)
    for i in path.size():
        if i%4!=0 and i!=path.size()-1:continue
        for j in profile.size():
            frame.surface_add_vertex(rings[i][j]);frame.surface_add_vertex(rings[i][(j+1)%profile.size()])
    frame.surface_end()
    var hoop := MeshInstance3D.new();hoop.mesh=frame;hoop.material_override=_material(Color("66848e"));add_child(hoop)
