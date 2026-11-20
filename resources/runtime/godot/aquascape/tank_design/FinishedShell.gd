extends RefCounted
## Display mesh for a committed tank, with independently drawn bed, glass and water.
const Design = preload("ShellDesign.gd")
const BEDS = {
    "fine_sand": ["细沙", preload("res://assets/aquascape-sand-v1/fine-sand.png")],
    "river_gravel": ["河砾", preload("res://assets/aquascape-substrates-v2/river_gravel.png")],
    "aquasoil_dark": ["深色底泥", preload("res://assets/aquascape-substrates-v2/aquasoil_dark.png")],
    "quartz_white": ["白石英", preload("res://assets/aquascape-substrates-v2/quartz_white.png")]
}
const Interior=preload("ShellInterior.gd")
const DEFAULT_BED = {"substrate":"fine_sand","depth_cm":5}
static var finishes := {}

static func valid_interior(value: Variant) -> bool:
    return value is Dictionary and value.get("substrate") is String and BEDS.has(value.substrate) and Design.number(value.get("depth_cm")) and value.depth_cm>=1 and value.depth_cm<=20 and Interior.valid(value)

static func paint(id: String) -> Material:
    if finishes.has(id):return finishes[id]
    if id in ["glass","water"]:
        var transparent := ShaderMaterial.new()
        transparent.shader=preload("ShellGlass.gdshader")
        transparent.set_shader_parameter("water",id=="water")
        transparent.render_priority=1 if id=="glass" else 0
        finishes[id]=transparent
    else:
        var solid := StandardMaterial3D.new()
        solid.cull_mode=BaseMaterial3D.CULL_DISABLED
        if BEDS.has(id):
            solid.albedo_texture=BEDS[id][1]
            solid.emission_enabled=true
            solid.emission_texture=BEDS[id][1]
            solid.emission_energy_multiplier=.15
        else:
            solid.albedo_color=Color("#485961")
            solid.metallic=.42;solid.roughness=.36
        finishes[id]=solid
    return finishes[id]

static func face_vertex(mesh: ImmediateMesh,p: Vector2,y: float,n: Vector3) -> void:
    mesh.surface_set_normal(n)
    mesh.surface_set_uv(p*1.25)
    mesh.surface_add_vertex(Vector3(p.x,y,p.y))

static func cap(mesh: ImmediateMesh, path: PackedVector2Array, triangles: PackedInt32Array, y: float, material: Material) -> void:
    mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES,material)
    for i in triangles:face_vertex(mesh,path[i],y,Vector3.UP)
    mesh.surface_end()

static func band(mesh: ImmediateMesh,path: PackedVector2Array,low: float,high: float,material: Material) -> void:
    mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES,material)
    for i in path.size():
        var a := path[i]
        var b := path[(i+1)%path.size()]
        var normal := Vector3(b.y-a.y,0,a.x-b.x).normalized()
        for j in [0,1,2,0,2,3]:
            face_vertex(mesh,a if j in [0,3] else b,low if j<2 else high,normal)
    mesh.surface_end()

static func build(data: Dictionary) -> ImmediateMesh:
    var path := Design.contour(data.design)
    var triangles := Geometry2D.triangulate_polygon(path)
    var height: float=data.design.height
    var interior: Dictionary=data.get("interior",DEFAULT_BED)
    var bed_y := float(interior.depth_cm)*.01
    var mesh := ImmediateMesh.new()
    if interior.get("heights",[]).is_empty():
        cap(mesh,path,triangles,bed_y,paint(interior.substrate))
    else:
        preload("ShellBedMesh.gd").draw(mesh,path,Interior.bounds(data.design),interior,height,paint(interior.substrate))
    var base_rim:=minf(.025,bed_y)
    if not interior.get("heights",[]).is_empty():
        preload("ShellBedMesh.gd").edges(mesh,path,Interior.bounds(data.design),interior,height,paint(interior.substrate))
    else:
        base_rim=bed_y
    band(mesh,path,0,base_rim,paint("rim"))
    band(mesh,path,base_rim,height,paint("glass"))
    cap(mesh,path,triangles,height-minf(.09,height*.05),paint("water"))
    band(mesh,path,height-.018,height,paint("rim"))
    return mesh
