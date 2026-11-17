extends Node3D
## Low-poly prey only for the replay. The grip ring is the rendered contact.
const CONTACT := 1.55
const TAKE_END := 2.08
var mesh_instance: MeshInstance3D
var material: StandardMaterial3D
var squid: ArrayMesh
var fish_eye: Array[MeshInstance3D]=[]

func _ready() -> void:
    material=StandardMaterial3D.new()
    material.vertex_color_use_as_albedo=true
    material.roughness=.68
    material.cull_mode=BaseMaterial3D.CULL_DISABLED
    mesh_instance=MeshInstance3D.new()
    mesh_instance.material_override=material
    add_child(mesh_instance)
    squid=build_squid()
    for side in [-1,1]:
        var eye:=MeshInstance3D.new()
        var pupil:=SphereMesh.new()
        pupil.radius=.0062
        pupil.height=.0124
        pupil.radial_segments=8
        pupil.rings=4
        eye.mesh=pupil
        var dark:=StandardMaterial3D.new()
        dark.albedo_color=Color("#14282c")
        dark.roughness=.39
        eye.material_override=dark
        eye.position=Vector3(-.202,.019,.029*side)
        add_child(eye)
        fish_eye.append(eye)

func triangle(tool: SurfaceTool, a: Vector3,b: Vector3,c: Vector3,tint: Color) -> void:
    for p in [a,b,c]:
        tool.set_color(tint)
        tool.add_vertex(p)

func ring(tool: SurfaceTool, pos: Array[Vector3], colors: Array[Color], rings: int, slices: int) -> void:
    for i in range(rings-1):
        for j in slices:
            var a:=i*slices+j
            var b:=i*slices+(j+1)%slices
            for index in [a,b,a+slices,b,b+slices,a+slices]:
                tool.set_color(colors[index])
                tool.add_vertex(pos[index])

func build_squid() -> ArrayMesh:
    var tool:=SurfaceTool.new()
    tool.begin(Mesh.PRIMITIVE_TRIANGLES)
    var positions: Array[Vector3]=[]
    var colors: Array[Color]=[]
    for i in 12:
        var u:=float(i)/11.
        var x:=lerpf(-.022,.017,u)
        var radius:=maxf(.0003,.0077*sin(PI*pow(u,.64)))
        for j in 10:
            var angle:=TAU*float(j)/10.
            positions.append(Vector3(x,cos(angle)*radius,sin(angle)*radius*.82))
            colors.append(Color("#b18176").lerp(Color("#ddb7a2"),.5-.5*cos(angle)))
    ring(tool,positions,colors,12,10)
    for side in [-1,1]:
        triangle(tool,Vector3(-.021,0,0),Vector3(-.012,0,.0089*side),Vector3(-.001,0,.003*side),Color("#cb988c"))
    for arm in 7:
        var angle:=TAU*float(arm)/7.
        var n:=Vector3(0,cos(angle),sin(angle))
        triangle(tool,Vector3(.015,0,0)+n*.002,Vector3(.020,0,0)+n*.0044,Vector3(.037,0,0)+n*.0058,Color("#c28a7d"))
    tool.generate_normals()
    return tool.commit()

func fish(t: float, pad: float, attachment: float, bend_delta: float) -> ArrayMesh:
    var tool:=SurfaceTool.new()
    tool.begin(Mesh.PRIMITIVE_TRIANGLES)
    var positions: Array[Vector3]=[]
    var colors: Array[Color]=[]
    var lag:=bend_delta*.036+.008*sin(t*13.5)*(1.-attachment)
    for i in 21:
        var x:=lerpf(-.252,.252,float(i)/20.)
        var free:=smoothstep(.006,.206,absf(x))
        var fullness:=smoothstep(-.26,-.183,x)*(1.-.82*smoothstep(-.071,.247,x))
        var natural:=maxf(.001,.053*fullness)
        var height:=lerpf(lerpf(natural,pad,attachment),natural,free)
        var section_z:=lag*free*free*signf(x)
        for j in 12:
            var angle:=TAU*float(j)/12.
            var y:=cos(angle)
            positions.append(Vector3(x,y*height,sin(angle)*natural*.70+section_z))
            colors.append(Color("#b1b5a5").lerp(Color("#426a70"),smoothstep(-.50,.89,y)))
    ring(tool,positions,colors,21,12)
    var tail:=Vector3(.250,0,lag)
    for side in [-1,1]:
        triangle(tool,tail,Vector3(.338,.053*side,lag*1.35),Vector3(.300,0,lag*1.22),Color("#5b7980"))
    triangle(tool,Vector3(-.063,.053,0),Vector3(.016,.086,0),Vector3(.062,.048,0),Color("#688188"))
    for eye in fish_eye:
        eye.position.z=signf(eye.position.z)*.029-lag*.97
    tool.generate_normals()
    return tool.commit()

func pose(gait, t: float, large: bool) -> Dictionary:
    var open_frame: Dictionary=gait.oral_frame()
    var center: Vector3=open_frame.center
    var connect: float=gait.blend(t,1.34,CONTACT)
    var neutral_basis:=Basis(Vector3.UP,.12) if not large else Basis(Vector3.UP,1.4)
    var orient: Basis=open_frame.crosswise if large else open_frame.forward
    var native: Vector3=gait.prey_free(t,large)
    position=native.lerp(center,connect)
    basis=neutral_basis.slerp(orient,connect)
    var pad: float=open_frame.gap*.5
    var past:=0.
    if large:
        mesh_instance.mesh=fish(t,pad,connect,gait.bend(t-.13)-gait.bend(t))
    else:
        mesh_instance.mesh=squid
        past=gait.blend(t,CONTACT,TAKE_END)
        var interior: Vector3=gait.point(Vector3(.804,-.130,0.),gait.head)
        position=position.lerp(interior,past)
    for eye in fish_eye:
        eye.visible=large
    var output: Dictionary={
        "mouth_gap_m":open_frame.gap,"prey_center_to_mouth_m":position.distance_to(center),
        "prey_world":position,"inside_progress":past,"prey_rendered":mesh_instance.visible,
    }
    if large and t>=CONTACT:
        var p:=basis.y*pad
        output["upper_grip_m"]=(position+p).distance_to(open_frame.upper)
        output["lower_grip_m"]=(position-p).distance_to(open_frame.lower)
        # The ring at x=0 and j=0/6 is the center of the rendered body.
        output["visual_pad_m"]=pad
    return output
