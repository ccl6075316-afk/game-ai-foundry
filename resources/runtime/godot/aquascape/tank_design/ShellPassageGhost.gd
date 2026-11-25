extends Node3D
var has_cover:=false

func paint(color: Color) -> StandardMaterial3D:
    var material:=StandardMaterial3D.new()
    material.albedo_color=color
    material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    material.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    material.cull_mode=BaseMaterial3D.CULL_DISABLED
    material.render_priority=8
    return material

func build(proposal: Dictionary,design: Dictionary,width: float) -> void:
    var allowed:bool=proposal.reason==""
    var color:=Color(.13,.9,.7,.32) if allowed else Color(1,.16,.12,.4)
    if proposal.action=="route" and preload("ShellPassage.gd").valid(proposal.route):
        var cover=preload("ShellPassageView.gd").new()
        add_child(cover)
        cover.build(proposal.route,design,false,false)
        var preview_material:=paint(color)
        for mesh:MeshInstance3D in cover.find_children("*","MeshInstance3D",true,false):
            mesh.material_override=preview_material
            mesh.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
            has_cover=true
    var marker:=MeshInstance3D.new()
    var ring:=CylinderMesh.new()
    ring.top_radius=.16
    ring.bottom_radius=.16
    ring.height=.025
    marker.mesh=ring
    marker.position=Vector3(proposal.point.x,.095,proposal.point.y)
    marker.material_override=paint(Color(color.r,color.g,color.b,.85))
    add_child(marker)
    if proposal.action!="entrance" or not allowed:return
    var path:=preload("ShellDesign.gd").contour(design)
    var best:=INF
    var tangent:=Vector2.RIGHT
    for i in path.size():
        var q:=Geometry2D.get_closest_point_to_segment(proposal.point,path[i],path[(i+1)%path.size()])
        var distance:float=q.distance_to(proposal.point)
        if distance<best:
            best=distance
            tangent=(path[(i+1)%path.size()]-path[i]).normalized()
    var arch:=ImmediateMesh.new()
    arch.surface_begin(Mesh.PRIMITIVE_LINE_STRIP)
    var radius:=width*.5
    arch.surface_add_vertex(Vector3(proposal.point.x-tangent.x*radius,.08,proposal.point.y-tangent.y*radius))
    for i in 33:
        var a:=PI-PI*i/32.0
        var p:Vector2=proposal.point+tangent*cos(a)*radius
        arch.surface_add_vertex(Vector3(p.x,1.4+sin(a)*radius,p.y))
    arch.surface_add_vertex(Vector3(proposal.point.x+tangent.x*radius,.08,proposal.point.y+tangent.y*radius))
    arch.surface_end()
    var portal:=MeshInstance3D.new()
    portal.mesh=arch
    portal.material_override=paint(Color(color.r,color.g,color.b,.9))
    add_child(portal)
