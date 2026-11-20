extends SubViewportContainer
const Shape = preload("Footprint.gd")
var viewport := SubViewport.new()
var model := MeshInstance3D.new()
var camera := Camera3D.new()
const ShellMesh = preload("ShellMesh.gd")

func _ready() -> void:
    stretch=true
    mouse_filter=Control.MOUSE_FILTER_IGNORE
    custom_minimum_size=Vector2(210,155)
    viewport.own_world_3d=true
    add_child(viewport)
    viewport.add_child(model)
    viewport.add_child(camera)
    camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    camera.environment=Environment.new()
    camera.environment.background_mode=Environment.BG_COLOR
    camera.environment.background_color=Color("#112b34")
    model.material_override=ShellMesh.material()

func display(tank: Dictionary) -> void:
    model.mesh=null
    viewport.render_target_update_mode=SubViewport.UPDATE_ONCE
    if tank.is_empty(): return
    var path := Shape.contour(tank)
    if not Shape.valid(path): return
    var rect := Shape.bounds(path)
    var height: float=tank.height
    model.mesh=ShellMesh.build(path,height)
    var target := Vector3(rect.get_center().x,height*.5,rect.get_center().y)
    var extent := rect.size.length()+height
    camera.position=target+Vector3(12,10,15).normalized()*maxf(22,extent)
    camera.far=maxf(100,extent*3)
    camera.look_at(target)
    camera.size=maxf(rect.size.length()*.83+height*1.1,2.0)
