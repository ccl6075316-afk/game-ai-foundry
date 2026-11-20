extends RefCounted
const Workshop = preload("Workshop.gd")
const Footprint = preload("Footprint.gd")
const Design = preload("ShellDesign.gd")
var templates: Dictionary={}
var active_design: Dictionary={}
var ghost := MeshInstance3D.new()
var active_name := ""
var session: RefCounted
var hall: Control
var handles := preload("HallShellHandles.gd").new()
var library_path := Workshop.LIBRARY_PATH

func _init(owner: Control) -> void:
    hall=owner
    session=preload("HallShellSession.gd").new(hall)
    handles.hall=hall
    handles.mouse_filter=Control.MOUSE_FILTER_IGNORE
    hall.canvas.add_child(handles)
    handles.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    ghost.material_override=preload("ShellMesh.gd").material()
    ghost.hide()
    hall.world.add_child(ghost)

func entries() -> Array:
    templates={"shell_rect":Footprint.standard("rect"),"shell_ellipse":Footprint.standard("ellipse")}
    var file := ConfigFile.new()
    if file.load(library_path)==OK and file.has_section("templates"):
        for id in file.get_section_keys("templates"):
            templates["shell_"+id]=file.get_value("templates",id)
    var items: Array=[]
    for id in templates:
        items.append({"id":id,"label":templates[id].name+"缸" if id in ["shell_rect","shell_ellipse"] else templates[id].name,"category":"展缸","preview":icon(templates[id])})
    return items

func icon(template: Dictionary) -> Texture2D:
    # Miniature axonometric drawing of the actual template contour.
    var contour := Footprint.contour(template)
    var top := PackedVector2Array()
    for point in contour:
        top.append(Vector2(point.x*.85-point.y*.62,point.x*.24+point.y*.36))
    var bounds := Footprint.bounds(top)
    var factor := minf(104.0/maxf(.01,bounds.size.x),32.0/maxf(.01,bounds.size.y))
    for i in top.size():
        top[i]=(top[i]-bounds.get_center())*factor+Vector2(64,23)
    var bottom := PackedVector2Array()
    for point in top:bottom.append(point+Vector2(0,25))
    var image := Image.create_empty(128,76,false,Image.FORMAT_RGBA8)
    for i in top.size():
        var j := (i+1)%top.size()
        var face := PackedVector2Array([top[i],top[j],bottom[j],bottom[i]])
        _fill_polygon(image,face,Color("#388785"))
    _fill_polygon(image,top,Color("#a0dbcf"))
    return ImageTexture.create_from_image(image)

func _fill_polygon(image: Image, points: PackedVector2Array, color: Color) -> void:
    for row in image.get_height():
        var y := row+.5
        var crossings: Array[float]=[]
        for i in points.size():
            var a := points[i]
            var b := points[(i+1)%points.size()]
            if (a.y<=y and b.y>y) or (b.y<=y and a.y>y):
                crossings.append(lerpf(a.x,b.x,(y-a.y)/(b.y-a.y)))
        crossings.sort()
        for i in range(0,crossings.size()-1,2):
            var start := ceili(crossings[i]-.5)
            var end := ceili(crossings[i+1]-.5)
            image.fill_rect(Rect2i(start,row,end-start,1),color)

func choose(id: String) -> void:
    active_design=Design.from_template(templates[id])
    ghost.mesh=preload("ShellMesh.gd").build(Design.contour(active_design),active_design.height)
    active_name=templates[id].name
    hall.editor._set_tool("shell")

func preview(at: Vector3) -> void:
    var data: Dictionary=hall.editor._candidate("shell",at)
    var allowed: bool=hall.editor._valid_placement(data,hall.objects) and hall.objects.size()<hall.MAX_OBJECTS
    if allowed:
        allowed=hall.objects.filter(func(r):return r.data.kind in ["shell","tank"]).size()<hall.MAX_TANKS
    ghost.transform=hall._transform(data)
    ghost.material_override.albedo_color=Color(1,1,1,.7) if allowed else Color(1,.2,.2,.8)
    ghost.show()
    hall.panel.set_tool_feedback("shell",allowed)

func open_workshop() -> void:
    if hall.tank_session.active_editor!=null: return
    hall.editor._set_tool("")
    hall.build_editor.gizmo.cancel()
    handles.cancel()
    var workshop := preload("res://scenes/tank_design_workshop.tscn").instantiate()
    workshop.library_path=library_path
    hall.tank_session.active_editor=workshop
    hall.viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED
    hall.visitor_crowd.set_paused(true)
    workshop.z_index=10
    hall.add_child(workshop)
    workshop.finished.connect(func():
        workshop.hide()
        workshop.queue_free()
        hall.tank_session.active_editor=null
        hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
        hall.visitor_crowd.set_paused(false)
        var palette: Control=hall.build_editor.palette
        palette.entries=entries()+palette.entries.filter(func(item):return not str(item.id).begins_with("shell_"))
        palette.search.clear()
        palette.tabs.current_tab=1
        palette.refresh()
        hall.notice="从展缸目录拖到大厅空地放置。")
