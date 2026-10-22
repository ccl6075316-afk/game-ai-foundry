extends RefCounted
const CONFIG="res://assets/models/fish/motion/source-jaw112.json"
func apply(model:Node3D,species:String)->int:
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(CONFIG))
    if not cfg.profiles.has(species):return 0
    var p:Dictionary=cfg.profiles[species]
    assert(FileAccess.get_sha256("res://assets/models/fish/"+species+".glb")==p.model_sha256)
    var body=model.find_child(p.mesh,true,false) as MeshInstance3D
    assert(body!=null and body.mesh.get_surface_count()==2)
    var skin=body.get_active_material(0) as ShaderMaterial;assert(skin!=null)
    var texture=skin.get_shader_parameter("source_texture") as Texture2D;assert(texture!=null)
    var shader_code:String=skin.shader.code
    var old:Dictionary={}
    for key in ["mouth_source_projection","rim_local_source"]:
        old[key]=skin.get_shader_parameter(key);skin.set_shader_parameter(key,false)
    var lining=ShaderMaterial.new();lining.resource_name="Source-bound oral lining112";lining.shader=preload("res://scripts/aquarium/SourceJaw112.gdshader")
    lining.set_shader_parameter("source_texture",texture);lining.set_shader_parameter("source_size",Vector2(texture.get_size()))
    body.set_surface_override_material(1,lining)
    model.set_meta("source_jaw112_receipt",{"model_sha256":p.model_sha256,"mesh":p.mesh,"mouth_source_projection":false,"rim_local_source":false,"previous_uniforms":old,"skin_shader_unchanged":skin.shader.code==shader_code,"helper_sha256":FileAccess.get_sha256(get_script().resource_path),"profile_sha256":FileAccess.get_sha256(CONFIG),"lining_sha256":FileAccess.get_sha256("res://scripts/aquarium/SourceJaw112.gdshader")})
    return 1
