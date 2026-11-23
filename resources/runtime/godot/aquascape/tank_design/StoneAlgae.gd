extends RefCounted

const FILM_SHADER = preload("StoneAlgae.gdshader")
const FILM_ART = preload("StoneAlgae.png")
const SUPPORTED := [
    "rock", "river_boulder", "basalt_column", "pale_limestone", "dragon_stone",
    "lava_rock", "slate_stack", "stone_bridge", "ruin_arch", "broken_column",
    "stone_lantern", "slate_cave", "ruined_tower", "red_sandstone", "quartz_rock",
]
static var variants: Dictionary = {}

static func supports(id: String) -> bool:
    return id in SUPPORTED

static func apply(mesh: MeshInstance3D) -> void:
    var size := mesh.get_aabb().size
    var tiles := 1.45 / maxf(0.001, size[size.max_axis_index()])
    for surface in mesh.mesh.get_surface_count():
        var original := mesh.get_active_material(surface) as StandardMaterial3D
        if original == null or original.albedo_texture == null:
            continue
        var key := [original.albedo_texture, tiles]
        if not variants.has(key):
            var film := ShaderMaterial.new()
            film.shader = FILM_SHADER
            film.set_shader_parameter("stone_art", original.albedo_texture)
            film.set_shader_parameter("algae_art", FILM_ART)
            film.set_shader_parameter("tiles_per_model_unit", tiles)
            variants[key] = film
        mesh.set_surface_override_material(surface, variants[key])
