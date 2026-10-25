extends Node3D
## One depth-aware pass shared by up to eight transformed tanks. No fish edits.
var paint: ShaderMaterial
var quad: MeshInstance3D
var clock := 0.0
var frozen := false
var enabled := true
var count := 0

func _ready() -> void:
    quad=MeshInstance3D.new();quad.name="TankWaterComposite"
    var mesh := QuadMesh.new();mesh.size=Vector2(2,2);quad.mesh=mesh
    quad.extra_cull_margin=16384;quad.ignore_occlusion_culling=true
    quad.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    paint=ShaderMaterial.new();paint.shader=load("res://scripts/aquarium/TankWaterVolume.gdshader")
    paint.render_priority=127;quad.material_override=paint;add_child(quad)

func sync(rows: Array,delta: float=0.0) -> void:
    if not frozen:clock+=minf(delta,.05)
    var xs := PackedVector4Array();var ys := PackedVector4Array();var zs := PackedVector4Array()
    var colors := PackedVector4Array();var optics := PackedVector4Array();var extras := PackedVector4Array()
    count=0
    for row in rows:
        if row.tank==null or not row.data.water.enabled:continue
        if count==8:break
        var inv: Transform3D=row.tank.global_transform.affine_inverse()
        xs.append(Vector4(inv.basis.x.x,inv.basis.y.x,inv.basis.z.x,inv.origin.x))
        ys.append(Vector4(inv.basis.x.y,inv.basis.y.y,inv.basis.z.y,inv.origin.y))
        zs.append(Vector4(inv.basis.x.z,inv.basis.y.z,inv.basis.z.z,inv.origin.z))
        var config: Dictionary=row.data.water;var tint := Color(config.tint)
        colors.append(Vector4(tint.r,tint.g,tint.b,float(config.strength)))
        optics.append(Vector4(float(config.visibility_m),float(config.reflection),float(config.ripple),float(config.caustics)))
        extras.append(Vector4(row.tank.global_basis.x.length(),0,0,0));count+=1
    while xs.size()<8:
        xs.append(Vector4.ZERO);ys.append(Vector4.ZERO);zs.append(Vector4.ZERO)
        colors.append(Vector4.ZERO);optics.append(Vector4.ONE);extras.append(Vector4.ONE)
    paint.set_shader_parameter("water_count",count if enabled else 0)
    paint.set_shader_parameter("water_x",xs);paint.set_shader_parameter("water_y",ys);paint.set_shader_parameter("water_z",zs)
    paint.set_shader_parameter("water_color",colors);paint.set_shader_parameter("water_optics",optics);paint.set_shader_parameter("water_extra",extras)
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
    return maxf(0,leave-enter)
