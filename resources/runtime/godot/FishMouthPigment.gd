extends RefCounted
## Actual upper/lower lip rim and recessed mouth; no painted horizontal seam.
var profiles: Dictionary={}
func apply(model: Node3D,species: String) -> int:
    if profiles.is_empty():profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-pigment.json")).profiles
    if not profiles.has(species):return 0
    var p: Dictionary=profiles[species]
    assert(preload("res://scripts/aquarium/FishRuntimeData.gd").sha256("res://assets/models/fish/"+species+".glb")==p.model_sha256,"Stale mouth pigment profile")
    var mesh=model.find_child(p.mesh,true,false) as MeshInstance3D
    assert(mesh!=null and mesh.mesh.get_surface_count()==2,"Unexpected mouth surface inventory")
    var skin=mesh.get_active_material(p.skin_surface) as ShaderMaterial
    var cavity=mesh.get_active_material(p.oral_surface) as StandardMaterial3D
    assert(skin!=null and cavity!=null and cavity.albedo_texture==null,"Mouth skin/interior ownership mismatch")
    var oral=ShaderMaterial.new();oral.shader=load("res://scripts/aquarium/FishMouthPigment.gdshader")
    oral.set_shader_parameter("source_texture",skin.get_shader_parameter("source_texture"))
    assert(mesh.mesh.surface_get_arrays(p.oral_surface)[Mesh.ARRAY_TEX_UV2].size()>0,"Missing actual rim coordinates")
    for key in ["rim_width_native","recess_width_native"]:oral.set_shader_parameter(key,p[key])
    mesh.set_surface_override_material(p.oral_surface,oral)
    return 2
