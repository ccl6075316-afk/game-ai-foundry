extends RefCounted

const PAINT = preload("RootedCurrent.gdshader")
static var materials: Dictionary = {}

static func apply(mesh: MeshInstance3D, options: Dictionary) -> void:
    var low := Vector3(options.anchor_min[0], options.anchor_min[1], options.anchor_min[2])
    var size := Vector3(options.anchor_size[0], options.anchor_size[1], options.anchor_size[2])
    var amplitude: float = options.amplitude
    # A rotating tip can extend past its rest AABB.
    mesh.extra_cull_margin += mesh.get_aabb().size.length() * amplitude
    for i in mesh.mesh.get_surface_count():
        var source := mesh.get_active_material(i) as StandardMaterial3D
        if source == null or source.albedo_texture == null:
            continue
        var cutoff := source.alpha_scissor_threshold if source.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR else 0.0
        var key := [source.albedo_texture, low, size, amplitude, cutoff]
        if not materials.has(key):
            var paint := ShaderMaterial.new()
            paint.shader = PAINT
            paint.set_shader_parameter("artwork", source.albedo_texture)
            paint.set_shader_parameter("anchor_min", low)
            paint.set_shader_parameter("anchor_size", size)
            paint.set_shader_parameter("amplitude", amplitude)
            paint.set_shader_parameter("alpha_cutoff", cutoff)
            materials[key] = paint
        mesh.set_surface_override_material(i, materials[key])
