extends Node3D
const Passage=preload("ShellPassage.gd")
var collision_enabled:=true

func triangle(tool: SurfaceTool,a: Vector3,b: Vector3,c: Vector3) -> void:
    var normal:=(b-a).cross(c-a).normalized()
    for p in [a,b,c]:
        tool.set_normal(normal)
        tool.set_uv(Vector2(p.x,p.z))
        tool.add_vertex(p)

func surface(tool: SurfaceTool,paint: Material,label: String) -> void:
    var mesh:=tool.commit()
    var instance:=MeshInstance3D.new()
    instance.name=label
    instance.mesh=mesh
    instance.material_override=paint
    instance.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    add_child(instance)
    if not collision_enabled:return
    instance.create_trimesh_collision()
    var collision:CollisionShape3D=instance.get_child(0).get_child(0)
    collision.shape.backface_collision=true

func build(route: Dictionary,design: Dictionary={},editing:=false,with_collision:=true) -> void:
    collision_enabled=with_collision
    if route.is_empty():return
    var roof_profile:=Passage.profile(route)
    var outline:=Passage.inside_footprint(route,design)
    if outline.is_empty():return
    var floor_tool:=SurfaceTool.new()
    floor_tool.begin(Mesh.PRIMITIVE_TRIANGLES)
    var indices:=Geometry2D.triangulate_polygon(outline)
    for i in range(0,indices.size(),3):
        var a:=outline[indices[i]]
        var b:=outline[indices[i+1]]
        var c:=outline[indices[i+2]]
        triangle(floor_tool,Vector3(a.x,.065,a.y),Vector3(c.x,.065,c.y),Vector3(b.x,.065,b.y))
    var floor_paint:=StandardMaterial3D.new()
    floor_paint.albedo_color=Color("84989c")
    floor_paint.albedo_texture=load("res://assets/aquarium-hall-style-v3/hall_floor.png")
    floor_paint.uv1_scale=Vector3(.5,.5,.5)
    floor_paint.cull_mode=BaseMaterial3D.CULL_DISABLED
    surface(floor_tool,floor_paint,"WalkingFloor")
    var cover:=SurfaceTool.new()
    cover.begin(Mesh.PRIMITIVE_TRIANGLES)
    var bounds:=Rect2(outline[0],Vector2.ZERO)
    for p in outline:bounds=bounds.expand(p)
    var step:=.24
    for z in ceili(bounds.size.y/step):
        for x in ceili(bounds.size.x/step):
            var p:=bounds.position+Vector2(x,z)*step
            var tile:=PackedVector2Array([p,p+Vector2(step,0),p+Vector2(step,step),p+Vector2(0,step)])
            for polygon in Geometry2D.intersect_polygons(outline,tile):
                var triangles:=Geometry2D.triangulate_polygon(polygon)
                for i in range(0,triangles.size(),3):
                    var vertices:Array[Vector3]=[]
                    for j in 3:
                        var q:=polygon[triangles[i+j]]
                        vertices.append(Vector3(q.x,Passage.profile_roof(q,roof_profile),q.y))
                    triangle(cover,vertices[0],vertices[2],vertices[1])
    var path:=Passage.points(route)
    var entrance_direction:=(path[1]-path[0]).normalized()
    var exit_direction:=(path[-1]-path[-2]).normalized()
    var contour:=preload("ShellDesign.gd").contour(design)
    var has_exit:=path[-1].distance_to(Passage.nearest_wall(path[-1],contour))<.05
    # The entrance end opens onto the exterior approach, with no glass cap across it.
    for i in outline.size():
        var a:=outline[i]
        var b:=outline[(i+1)%outline.size()]
        if ((a+b)*.5-path[0]).dot(entrance_direction)<.05:continue
        if has_exit and ((a+b)*.5-path[-1]).dot(exit_direction)>-.05:continue
        var c:=Vector3(b.x,Passage.profile_roof(b,roof_profile),b.y)
        var d:=Vector3(a.x,Passage.profile_roof(a,roof_profile),a.y)
        triangle(cover,Vector3(a.x,.065,a.y),Vector3(b.x,.065,b.y),c)
        triangle(cover,Vector3(a.x,.065,a.y),c,d)
    var glass:=StandardMaterial3D.new()
    glass.albedo_color=Color(.35,.72,.78,.17)
    glass.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    glass.cull_mode=BaseMaterial3D.CULL_DISABLED
    glass.roughness=.12
    glass.render_priority=2
    surface(cover,glass,"GlassCover")
    var frame:=ImmediateMesh.new()
    frame.surface_begin(Mesh.PRIMITIVE_LINES)
    for i in outline.size():
        var midpoint:=(outline[i]+outline[(i+1)%outline.size()])*.5
        if (midpoint-path[0]).dot(entrance_direction)<.05:continue
        if has_exit and (midpoint-path[-1]).dot(exit_direction)>-.05:continue
        for y in [.08,Passage.WALL_HEIGHT]:
            frame.surface_add_vertex(Vector3(outline[i].x,y,outline[i].y))
            frame.surface_add_vertex(Vector3(outline[(i+1)%outline.size()].x,y,outline[(i+1)%outline.size()].y))
    for i in path.size():
        var direction:=(path[mini(i+1,path.size()-1)]-path[maxi(0,i-1)]).normalized()
        var right:=Vector2(-direction.y,direction.x)
        var r:=Passage.node_radius(route,i)
        for j in 32:
            var a:=PI*j/32.0
            var b:=PI*(j+1)/32.0
            var p:=path[i]+right*cos(a)*r
            var q:=path[i]+right*cos(b)*r
            if Passage.profile_roof(p,roof_profile)>Passage.WALL_HEIGHT+sin(a)*r+.05:continue
            frame.surface_add_vertex(Vector3(p.x,Passage.WALL_HEIGHT+sin(a)*r+.01,p.y))
            frame.surface_add_vertex(Vector3(q.x,Passage.WALL_HEIGHT+sin(b)*r+.01,q.y))
    for room in route.get("rooms",[]):
        for axis in [Vector2.RIGHT,Vector2.UP]:
            for j in 48:
                var a:=PI*j/48.0
                var b:=PI*(j+1)/48.0
                var p:Vector2=path[int(room.node)]+axis*cos(a)*float(room.radius)
                var q:Vector2=path[int(room.node)]+axis*cos(b)*float(room.radius)
                frame.surface_add_vertex(Vector3(p.x,Passage.WALL_HEIGHT+sin(a)*float(room.radius)+.01,p.y))
                frame.surface_add_vertex(Vector3(q.x,Passage.WALL_HEIGHT+sin(b)*float(room.radius)+.01,q.y))
    frame.surface_end()
    var metal:=StandardMaterial3D.new()
    metal.albedo_color=Color("80999e")
    metal.roughness=.45
    metal.emission_enabled=true
    metal.emission=Color("24383c")
    metal.emission_energy_multiplier=.25
    var beams:=SurfaceTool.new()
    beams.begin(Mesh.PRIMITIVE_TRIANGLES)
    var vertices:PackedVector3Array=frame.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
    for i in range(0,vertices.size(),2):beam(beams,vertices[i],vertices[i+1])
    var rim:=MeshInstance3D.new()
    rim.name="StructuralFrame"
    rim.mesh=beams.commit()
    rim.material_override=metal
    add_child(rim)
    if editing:
        var markers:=ImmediateMesh.new()
        markers.surface_begin(Mesh.PRIMITIVE_LINES)
        for p in path:
            for i in 24:
                var a:=TAU*i/24.0
                var b:=TAU*(i+1)/24.0
                var r:=.12
                markers.surface_add_vertex(Vector3(p.x+cos(a)*r,.085,p.y+sin(a)*r))
                markers.surface_add_vertex(Vector3(p.x+cos(b)*r,.085,p.y+sin(b)*r))
        markers.surface_end()
        var handles:=MeshInstance3D.new()
        handles.name="EditMarkers"
        handles.mesh=markers
        handles.material_override=metal
        add_child(handles)

    if not collision_enabled:return
    # Keep the water side inaccessible while preserving the door openings.
    var wall_faces:=PackedVector3Array()
    for i in contour.size():
        var a:=contour[i]
        var b:=contour[(i+1)%contour.size()]
        var steps:=maxi(1,ceili(a.distance_to(b)/.08))
        for j in steps:
            var p:=a.lerp(b,float(j)/steps)
            var q:=a.lerp(b,float(j+1)/steps)
            var middle:=(p+q)*.5
            if Geometry2D.is_point_in_polygon(middle,outline):continue
            var pa:=Vector3(p.x,0,p.y)
            var pb:=Vector3(q.x,0,q.y)
            var pc:=Vector3(q.x,design.height,q.y)
            var pd:=Vector3(p.x,design.height,p.y)
            wall_faces.append_array(PackedVector3Array([pa,pb,pc,pa,pc,pd]))
    var boundary:=StaticBody3D.new()
    var shape:=CollisionShape3D.new()
    var polygon:=ConcavePolygonShape3D.new()
    polygon.backface_collision=true
    polygon.set_faces(wall_faces)
    shape.shape=polygon
    boundary.add_child(shape)
    add_child(boundary)

func beam(tool: SurfaceTool,a: Vector3,b: Vector3) -> void:
    var direction:=(b-a).normalized()
    if a.distance_to(b)<.0001:return
    var side:=direction.cross(Vector3.UP)
    if side.length_squared()<.001:side=direction.cross(Vector3.RIGHT)
    side=side.normalized()*.025
    var other:=direction.cross(side)
    for i in 6:
        var angle:=TAU*i/6.0
        var next:=TAU*(i+1)/6.0
        var offset:=side*cos(angle)+other*sin(angle)
        var next_offset:=side*cos(next)+other*sin(next)
        triangle(tool,a+offset,b+offset,b+next_offset)
        triangle(tool,a+offset,b+next_offset,a+next_offset)
