extends Node3D
## Shared hall lighting; the retained source artwork and save document are untouched.
const PROFILE := "res://assets/aquarium-hall-blue-v5/lighting.json"
var profile: Dictionary
var environment: WorldEnvironment
var fill: DirectionalLight3D
var enabled := true
var building := true
var exhibits: Array=[]
var guides: Array=[]

func _ready() -> void:
    profile=JSON.parse_string(FileAccess.get_file_as_string(PROFILE))
    environment=WorldEnvironment.new();environment.environment=Environment.new();add_child(environment)
    environment.environment.background_mode=Environment.BG_COLOR
    environment.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    fill=DirectionalLight3D.new();fill.rotation_degrees=Vector3(-63,-25,0);add_child(fill)
    set_state(true,true)

func set_state(use_exhibit_lighting: bool,construction: bool) -> void:
    enabled=use_exhibit_lighting;building=construction
    var env := environment.environment
    env.background_color=Color(profile.background) if enabled else Color("101f2b")
    env.ambient_light_color=Color(profile.ambient_color) if enabled else Color("e0eee7")
    env.ambient_light_energy=float(profile.build_ambient if building else profile.walk_ambient) if enabled else .64
    fill.light_color=Color(profile.fill_color) if enabled else Color("f2eed6")
    fill.light_energy=float(profile.build_fill if building else profile.walk_fill) if enabled else .40
    fill.shadow_enabled=not enabled
    exhibits=exhibits.filter(func(ref):return ref.get_ref()!=null)
    guides=guides.filter(func(ref):return ref.get_ref()!=null)
    for ref in exhibits:
        var rig: Node3D=ref.get_ref();rig.visible=enabled
        _apply_tank_profile(rig)
    for ref in guides:
        var guide: MeshInstance3D=ref.get_ref();guide.visible=enabled
        guide.material_override.albedo_color=Color(profile.guide_color)

func apply_profile(config: Dictionary) -> void:
    # Review can replay V4 with identical geometry, fish pose and camera.
    profile=config.duplicate(true)
    set_state(enabled,building)

func _apply_tank_profile(rig: Node3D) -> void:
    for i in profile.tank_positions_x_m.size():
        var lamp: SpotLight3D=rig.get_node("TankTop%d" % i)
        lamp.light_color=Color(profile.tank_color);lamp.light_energy=float(profile.tank_energy)
        rig.get_node("TankStrip%d" % i).material_override.albedo_color=Color(profile.get("fixture_color","a3bdc2"))
    var spill: OmniLight3D=rig.get_node("BlueSpill")
    spill.light_color=Color(profile.get("spill_color","226ac8"))
    spill.light_energy=float(profile.get("spill_energy",0.0))
    spill.omni_range=float(profile.get("spill_range_m",4.0))
    var tank=rig.get_parent()
    var blue: bool=enabled and profile.has("backdrop_upper")
    tank.backdrop_paint.shader=load("res://scripts/aquarium/HallBlueBackdrop.gdshader" if blue else "res://scripts/aquarium/MarineBackdrop.gdshader")
    if blue:
        tank.backdrop_paint.set_shader_parameter("upper_color",Color(profile.backdrop_upper))
        tank.backdrop_paint.set_shader_parameter("lower_color",Color(profile.backdrop_lower))

func _fixture(parent: Node3D,at: Vector3,size: Vector3,color: Color,self_lit: bool) -> MeshInstance3D:
    var mesh := MeshInstance3D.new();var box := BoxMesh.new();box.size=size
    var material := StandardMaterial3D.new();material.albedo_color=color;material.roughness=1
    if self_lit:material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    mesh.mesh=box;mesh.material_override=material;mesh.position=at
    mesh.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    parent.add_child(mesh);return mesh

func attach_tank(tank: Node3D) -> Node3D:
    var rig := Node3D.new();rig.name="ExhibitLighting";tank.add_child(rig)
    for i in profile.tank_positions_x_m.size():
        var x: float=profile.tank_positions_x_m[i]
        var z: float=profile.tank_front_z_m
        _fixture(rig,Vector3(x,2.79,z),Vector3(2.35,.045,.13),Color("243943"),false)
        var strip := _fixture(rig,Vector3(x,2.762,z),Vector3(2.2,.012,.055),Color("a3bdc2"),true)
        strip.name="TankStrip%d" % i
        var light := SpotLight3D.new();light.name="TankTop%d" % i;rig.add_child(light)
        light.position=Vector3(x,2.72,z);light.rotation.x=deg_to_rad(float(profile.tank_tilt_degrees))
        light.light_color=Color(profile.tank_color);light.light_energy=float(profile.tank_energy)
        light.spot_range=float(profile.tank_range_m);light.spot_angle=float(profile.tank_angle_degrees)
        light.spot_attenuation=float(profile.tank_attenuation);light.spot_angle_attenuation=float(profile.tank_edge_attenuation)
        light.shadow_enabled=i<int(profile.tank_shadow_count)
        light.shadow_bias=.04;light.shadow_normal_bias=.5
    var spill := OmniLight3D.new();spill.name="BlueSpill";rig.add_child(spill)
    spill.position=Vector3(0,.45,1.72);spill.omni_attenuation=1.6
    spill.shadow_enabled=false
    _apply_tank_profile(rig)
    rig.visible=enabled;exhibits.append(weakref(rig));return rig

func add_guide(parent: Node3D,at: Vector3,size: Vector3) -> void:
    var marker := _fixture(parent,at,size,Color(profile.guide_color),true)
    marker.name="LowGuideLight";marker.visible=enabled;guides.append(weakref(marker))
