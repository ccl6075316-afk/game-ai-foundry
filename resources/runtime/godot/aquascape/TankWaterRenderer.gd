extends Node3D
## One depth-aware pass shared by up to eight transformed tanks (both legacy HallTank3D
## and player-built shell tanks). No source fish mesh or texture edits.
var paint: ShaderMaterial
var quad: MeshInstance3D
var clock := 0.0
var frozen := false
var enabled := true
var count := 0
const Passage=preload("res://scripts/aquarium/passage/PassageRoute.gd")
const ShellDesign=preload("res://scripts/aquarium/tank_design/ShellDesign.gd")
const ShellInterior=preload("res://scripts/aquarium/tank_design/ShellInterior.gd")
const WaterProfile=preload("res://scripts/aquarium/TankWaterProfile.gd")
var dry_route: Dictionary={}
var dry_path := PackedVector3Array()

func set_dry_route(route: Dictionary,path: PackedVector3Array) -> void:
    dry_route=route.duplicate(true);dry_path=path.duplicate()
    apply_dry_parameters(paint)

func apply_dry_parameters(material: ShaderMaterial) -> void:
    var starts := PackedVector4Array();var ends := PackedVector4Array()
    for i in 48:
        starts.append(Vector4(dry_path[i].x,dry_path[i].y,dry_path[i].z,0) if i<dry_path.size()-1 else Vector4.ZERO)
        ends.append(Vector4(dry_path[i+1].x,dry_path[i+1].y,dry_path[i+1].z,0) if i<dry_path.size()-1 else Vector4.ZERO)
    material.set_shader_parameter("dry_count",maxi(0,dry_path.size()-1))
    material.set_shader_parameter("dry_a",starts);material.set_shader_parameter("dry_b",ends)
    if not dry_route.is_empty():material.set_shader_parameter("dry_profile",Vector4(dry_route.width,dry_route.height,1 if dry_route.section=="arch" else 0,.35))

func _ready() -> void:
    quad=MeshInstance3D.new();quad.name="TankWaterComposite"
    var mesh := QuadMesh.new();mesh.size=Vector2(2,2);quad.mesh=mesh
    quad.extra_cull_margin=16384;quad.ignore_occlusion_culling=true
    quad.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    paint=ShaderMaterial.new();paint.shader=load("res://scripts/aquarium/TankWaterVolume.gdshader")
    paint.render_priority=126;quad.material_override=paint;add_child(quad)

func _shell_water_config(data: Dictionary) -> Dictionary:
    var cfg := WaterProfile.DEFAULT.duplicate(true)
    var interior: Dictionary = data.get("interior", {})
    var tint_key: String = str(interior.get("tint", "neutral"))
    if tint_key == "warm":
        cfg["tint"] = "3c8e9c"
        cfg["deep_scatter"] = Color("0c2e40")
        cfg["shaft_color"] = Color("dceee6")
        cfg["caustic_color"] = Color("eceee0")
    elif tint_key == "cool":
        cfg["tint"] = "2274a6"
        cfg["deep_scatter"] = Color("061a34")
        cfg["shaft_color"] = Color("9ad0ea")
        cfg["caustic_color"] = Color("b8e2f0")
    else:
        cfg["tint"] = "3588a0"
        cfg["deep_scatter"] = Color("0b2a42")
        cfg["shaft_color"] = Color("c4e4ea")
        cfg["caustic_color"] = Color("e2f2ee")
    var brightness := float(interior.get("brightness", 1.0))
    cfg["shaft_strength"] = clampf(0.28 + brightness * 0.14, 0.14, 0.54)
    cfg["caustics"] = clampf(0.32 + brightness * 0.16, 0.12, 0.56)
    return cfg

func sync(rows: Array,delta: float=0.0) -> void:
    if not frozen:clock+=minf(delta,.05)
    var xs := PackedVector4Array();var ys := PackedVector4Array();var zs := PackedVector4Array()
    var colors := PackedVector4Array();var optics := PackedVector4Array();var extras := PackedVector4Array()
    var deeps := PackedVector4Array();var shafts := PackedVector4Array()
    var extinctions := PackedVector4Array();var caustic_tints := PackedVector4Array();var tilts := PackedVector4Array()
    count=0
    for row in rows:
        if count==8:break
        var inv := Transform3D.IDENTITY
        var config: Dictionary = {}
        var scale_x := 1.0
        var shape_kind := 0.0
        if row.get("tank") != null:
            if not row.data.water.enabled:continue
            var tank_node: Node3D = row.tank
            if not is_instance_valid(tank_node):continue
            inv = tank_node.global_transform.affine_inverse()
            config = row.data.water
            scale_x = tank_node.global_basis.x.length()
            shape_kind = float(config.get("shape_kind", 0.0))
        elif row.get("data", {}).get("kind") == "shell":
            var shell_root: Node3D = row.get("node")
            if not is_instance_valid(shell_root) or not shell_root.is_visible_in_tree():continue
            var design: Dictionary = row.data.get("design", {})
            var kind_name: String = str(design.get("kind", ""))
            if kind_name not in ["rect", "ellipse"]:continue
            if not row.data.get("interior", {}).get("passage", {}).is_empty():continue
            var box := ShellDesign.bounds(design)
            var waterline := ShellInterior.waterline(float(design.height))
            if box.size.x < 0.1 or box.size.z < 0.1 or waterline < 0.1:continue
            var center := box.get_center()
            var local_xform := Transform3D(
                Basis.from_scale(Vector3(box.size.x / 6.0, waterline / 2.775, box.size.z / 3.0)),
                Vector3(center.x, 0.0, center.z)
            )
            var world_xform := shell_root.global_transform * local_xform
            inv = world_xform.affine_inverse()
            scale_x = world_xform.basis.x.length()
            shape_kind = 1.0 if kind_name == "ellipse" else 0.0
            config = _shell_water_config(row.data)
        else:
            continue

        xs.append(Vector4(inv.basis.x.x,inv.basis.y.x,inv.basis.z.x,inv.origin.x))
        ys.append(Vector4(inv.basis.x.y,inv.basis.y.y,inv.basis.z.y,inv.origin.y))
        zs.append(Vector4(inv.basis.x.z,inv.basis.y.z,inv.basis.z.z,inv.origin.z))
        var tint := Color(config.tint) if config.tint is String else (config.tint as Color)
        colors.append(Vector4(tint.r,tint.g,tint.b,float(config.strength)))
        optics.append(Vector4(float(config.visibility_m),float(config.reflection),float(config.ripple),float(config.caustics)))
        var wave_amp := float(config.get("wave_amp", 0.0))
        var shaft_str := float(config.get("shaft_strength", 0.0))
        extras.append(Vector4(scale_x, shape_kind, wave_amp, shaft_str))

        if config.has("deep_scatter"):
            var dc: Color = Color(config.deep_scatter) if config.deep_scatter is String else (config.deep_scatter as Color)
            deeps.append(Vector4(dc.r, dc.g, dc.b, float(config.get("vertical_decay", 0.22))))
        else:
            deeps.append(Vector4.ZERO)

        if config.has("shaft_color"):
            var sc: Color = Color(config.shaft_color) if config.shaft_color is String else (config.shaft_color as Color)
            shafts.append(Vector4(sc.r, sc.g, sc.b, float(config.get("caustic_scale", 0.72))))
        else:
            shafts.append(Vector4.ZERO)

        if config.has("extinction"):
            var ext: Vector3 = config.extinction
            extinctions.append(Vector4(ext.x, ext.y, ext.z, float(config.get("meniscus_strength", 0.0))))
        else:
            extinctions.append(Vector4(0.0, 0.0, 0.0, float(config.get("meniscus_strength", 0.0))))

        if config.has("caustic_color"):
            var cc: Color = Color(config.caustic_color) if config.caustic_color is String else (config.caustic_color as Color)
            caustic_tints.append(Vector4(cc.r, cc.g, cc.b, float(config.get("shaft_decay", 0.26))))
        else:
            caustic_tints.append(Vector4.ZERO)

        if config.has("light_tilt"):
            var lt: Vector3 = config.light_tilt
            tilts.append(Vector4(lt.x, lt.y, lt.z, 1.0))
        else:
            tilts.append(Vector4.ZERO)
        count+=1

    while xs.size()<8:
        xs.append(Vector4.ZERO);ys.append(Vector4.ZERO);zs.append(Vector4.ZERO)
        colors.append(Vector4.ZERO);optics.append(Vector4.ONE);extras.append(Vector4.ONE)
        deeps.append(Vector4.ZERO);shafts.append(Vector4.ZERO)
        extinctions.append(Vector4.ZERO);caustic_tints.append(Vector4.ZERO);tilts.append(Vector4.ZERO)
    paint.set_shader_parameter("water_count",count if enabled else 0)
    paint.set_shader_parameter("water_x",xs);paint.set_shader_parameter("water_y",ys);paint.set_shader_parameter("water_z",zs)
    paint.set_shader_parameter("water_color",colors);paint.set_shader_parameter("water_optics",optics);paint.set_shader_parameter("water_extra",extras)
    paint.set_shader_parameter("water_deep",deeps);paint.set_shader_parameter("water_shaft",shafts)
    paint.set_shader_parameter("water_extinction",extinctions);paint.set_shader_parameter("water_caustic_tint",caustic_tints)
    paint.set_shader_parameter("water_light_tilt",tilts)
    paint.set_shader_parameter("clock",clock)
    quad.visible=enabled and count>0

func ray_length(tank: Node3D,origin: Vector3,direction: Vector3,hit_distance: float) -> float:
    # CPU counterpart used to verify the GPU on known world-space samples.
    var inv := tank.global_transform.affine_inverse()
    var p: Vector3=inv*origin;var d: Vector3=inv.basis*direction
    var lo := Vector3(-3,0,-1.5);var hi := Vector3(3,2.775,1.5)
    var enter := 0.0;var leave := hit_distance
    for axis in 3:
        if absf(d[axis])<.000001:
            if p[axis]<lo[axis] or p[axis]>hi[axis]:return 0.0
        else:
            var a: float=(lo[axis]-p[axis])/d[axis];var b: float=(hi[axis]-p[axis])/d[axis]
            enter=maxf(enter,minf(a,b));leave=minf(leave,maxf(a,b))
    if dry_route.is_empty():return maxf(0,leave-enter)
    return Passage.wet_length(dry_route,dry_path,origin,direction,Vector2(enter,leave))
