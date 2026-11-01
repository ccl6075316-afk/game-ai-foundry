extends Node3D
## Rectangular pilot water volume. Fish retain their native size, mesh and Swim rig.
const Route=preload("res://scripts/aquarium/passage/PassageRoute.gd")
var cover: Node3D
var water_renderer: Node3D
var water_proxy: Node3D
var glass: ShaderMaterial
var ports: Node3D
var factory
var fish: Array=[]
var route: Dictionary={}
var path := PackedVector3Array()
var elapsed := 0.0
var frozen := false
var fish_clearance_failures := 0

func paint(color: Color,art:=false) -> StandardMaterial3D:
    var p := StandardMaterial3D.new();p.albedo_color=color;p.metallic_specular=0;p.roughness=.9
    if art:
        p.albedo_texture=load("res://assets/aquarium-hall-style-v3/hall_floor.png")
        p.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
        p.uv1_triplanar=true;p.uv1_world_triplanar=true;p.uv1_scale=Vector3.ONE*.5
    return p

func box(parent: Node3D,at: Vector3,size_value: Vector3,material: Material,collision:=false) -> MeshInstance3D:
    var mesh := MeshInstance3D.new();var cube := BoxMesh.new();cube.size=size_value
    mesh.mesh=cube;mesh.position=at;mesh.material_override=material;parent.add_child(mesh)
    if collision:solid(parent,at,size_value)
    return mesh

func solid(parent: Node3D,at: Vector3,size_value: Vector3) -> void:
    if size_value.x<.001 or size_value.y<.001 or size_value.z<.001:return
    var body := StaticBody3D.new();body.collision_layer=1;body.collision_mask=0;parent.add_child(body)
    var shape := CollisionShape3D.new();var cube := BoxShape3D.new();cube.size=size_value;shape.position=at;shape.shape=cube;body.add_child(shape)

func _ready() -> void:
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    var env := WorldEnvironment.new();env.environment=Environment.new();add_child(env)
    env.environment.background_mode=Environment.BG_COLOR;env.environment.background_color=Color("081522")
    env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    env.environment.ambient_light_color=Color("c6e0e8");env.environment.ambient_light_energy=.85
    var light := DirectionalLight3D.new();light.rotation_degrees=Vector3(-45,-25,0);light.light_energy=.7;add_child(light)
    for x in [-5,5]:
        var lamp := OmniLight3D.new();lamp.position=Vector3(x,5,0);lamp.omni_range=15;lamp.light_energy=1.1;lamp.light_color=Color("bcdce5");add_child(lamp)
    box(self,Vector3(0,-1.25,0),Vector3(18,.5,12),paint(Color("b4c7c9"),true),true)
    box(self,Vector3(0,3.5,-8),Vector3(32,9,.3),paint(Color("7896a2"),true))
    for x in [-9,9]:
        for z in [-6,6]:box(self,Vector3(x,3,z),Vector3(.08,8,.08),paint(Color("496371")))
    for z in [-6,6]:
        box(self,Vector3(0,7,z),Vector3(18,.08,.08),paint(Color("496371")))
        solid(self,Vector3(0,3,z),Vector3(18,8,.05))
    glass=ShaderMaterial.new();glass.shader=load("res://scripts/aquarium/passage/PassageOuterGlass.gdshader")
    for x in [-9,9]:box(self,Vector3(x,3,0),Vector3(.018,8,12),glass)
    for z in [-6,6]:box(self,Vector3(0,3,z),Vector3(18,8,.018),glass)
    water_proxy=Node3D.new();water_proxy.name="WaterVolume";add_child(water_proxy)
    water_proxy.position.y=-1;water_proxy.scale=Vector3(3,8.0/2.775,4)
    water_renderer=load("res://scripts/aquarium/TankWaterRenderer.gd").new();add_child(water_renderer)
    cover=load("res://scripts/aquarium/passage/PassageMesh.gd").new();add_child(cover)
    ports=Node3D.new();add_child(ports)
    factory=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();factory._load_profiles()
    var species := ["red_emperor","red_seabream","black_seabream","yellow_croaker"]
    for i in 24:
        var id: String=species[i%species.size()];var profile: Dictionary=factory.profiles[id]
        factory._add_fish(self,id,float(profile.real_length_cm)/100,profile,Vector3.ZERO,i*.37)
        var row: Dictionary=factory.fish[-1];row.phase=float(i)*TAU/24
        row.radius=float(profile.real_length_cm)/100*.55+.12
        row.carrier.position=_fish_target(i,0);fish.append(row)

func apply_route(data: Dictionary) -> void:
    route=data.duplicate(true);path=Route.samples(route);cover.rebuild(route)
    water_renderer.set_dry_route(route,path);water_renderer.apply_dry_parameters(glass)
    for child in ports.get_children():
        if child is StaticBody3D:child.collision_layer=0
        ports.remove_child(child);child.queue_free()
    var floor_material := paint(Color("8b9b9d"),true)
    for end in [path[0],path[-1]]:
        box(ports,Vector3(end.x+(-1.5 if end.x<0 else 1.5),end.y-.12,end.z),Vector3(3,.24,6),floor_material,true)
    for face in [-9.0,9.0]:
        var portal := Vector3(face,0,0)
        for i in path.size()-1:
            if (path[i].x-face)*(path[i+1].x-face)<=0 and absf(path[i+1].x-path[i].x)>.001:
                portal=path[i].lerp(path[i+1],(face-path[i].x)/(path[i+1].x-path[i].x));break
        var half := Route.radius(route)+.3
        var low: float=maxf(-1,portal.y+route.height-2*Route.radius(route)-.2) if route.section=="round" else portal.y-.2
        var top: float=portal.y+route.height+.2
        solid(ports,Vector3(face,(7+top)/2,0),Vector3(.05,7-top,12))
        solid(ports,Vector3(face,(-1+low)/2,0),Vector3(.05,low+1,12))
        var left: float=portal.z-half;var right: float=portal.z+half
        solid(ports,Vector3(face,(top+low)/2,(-6+left)/2),Vector3(.05,top-low,left+6))
        solid(ports,Vector3(face,(top+low)/2,(6+right)/2),Vector3(.05,top-low,6-right))
    for i in fish.size():
        if Route.contains(route,path,fish[i].carrier.position,fish[i].radius):fish[i].carrier.position=_safe_position(_fish_target(i,elapsed),fish[i].radius)

func _fish_target(i: int,time: float) -> Vector3:
    var a: float=float(i)*TAU/24+time*(.055+float(i%3)*.008)
    return Vector3(sin(a)*7.4,1.3+float(i%4)*1.2+sin(a*1.7)*.35,cos(a)*4.6)

func _safe_position(at: Vector3,margin: float) -> Vector3:
    for offset in [Vector3.ZERO,Vector3(0,1.5,0),Vector3(0,3,0),Vector3(0,0,2),Vector3(0,0,-2)]:
        var p: Vector3=at+offset;p.x=clampf(p.x,-8.1,8.1);p.z=clampf(p.z,-5.1,5.1);p.y=clampf(p.y,.1,6.3)
        if not Route.contains(route,path,p,margin):return p
    for y in [6.2,.2,5.0]:
        for x in [-7.5,0,7.5]:
            for z in [-5.0,5.0]:
                var p := Vector3(x,y,z)
                if not Route.contains(route,path,p,margin):return p
    push_error("No safe fish location outside passage")
    return Vector3(0,6.3,4.8)

func _process(delta: float) -> void:
    var step := 0.0 if frozen else minf(delta,.05);elapsed+=step
    if route.is_empty():return
    for i in fish.size():
        var row: Dictionary=fish[i]
        # Reuse skeletal animation; the pilot owns world-space placement.
        # The exhibit controller also writes a small-tank orbit on every step.
        var placement: Transform3D=row.carrier.transform
        row.controller.step(step);row.carrier.transform=placement
        var previous: Vector3=row.carrier.position
        var desired := _safe_position(_fish_target(i,elapsed),row.radius)
        var candidate := previous.move_toward(desired,step*.7)
        if not Route.contains(route,path,candidate,row.radius):row.carrier.position=candidate
        var motion: Vector3=row.carrier.position-previous
        if motion.length()>.0001:row.carrier.rotation.y=atan2(-motion.z,motion.x)+(PI if row.profile.head_sign<0 else 0)
        if Route.contains(route,path,row.carrier.position,row.radius):fish_clearance_failures+=1
    var config: Dictionary=preload("res://scripts/aquarium/TankWaterProfile.gd").preset(1)
    config.visibility_m=18.0;config.strength=.58;config.caustics=.25
    water_renderer.sync([{"tank":water_proxy,"data":{"water":config}}],step)

func _exit_tree() -> void:
    if is_instance_valid(factory):factory.free()
