extends RefCounted
## Explicit per-species source feature exclusion, applied only to exterior skin.
## A candidate study: a successful local mask does not accept a whole fish.
var profiles:Dictionary={}
func apply(model:Node3D,species:String)->int:
    if profiles.is_empty():profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/local-source-features.json")).profiles
    if not profiles.has(species):return 0
    var p:Dictionary=profiles[species]
    assert(FileAccess.get_sha256("res://assets/models/fish/"+species+".glb")==p.model_sha256,"Stale local feature model")
    var mesh=model.find_child(p.mesh,true,false) as MeshInstance3D
    assert(mesh!=null and p.surface==0)
    var material=mesh.get_active_material(p.surface).duplicate() as ShaderMaterial
    assert(material!=null and material.shader.code.contains("friendly_eye_uv"))
    var texture:Texture2D=material.get_shader_parameter("source_texture")
    assert(texture!=null)
    assert(texture.get_size()==Vector2(p.source_size[0],p.source_size[1]))
    var code:String=material.shader.code
    assert(code.count("void vertex(){rest_position=VERTEX;}")==1)
    code=code.replace("varying vec3 rest_position;","varying vec3 rest_position;\nvarying vec3 feature_rest_normal;\n"+FileAccess.get_file_as_string("res://scripts/aquarium/FishLocalSourceFeature.gdshaderinc"))
    code=code.replace("void vertex(){rest_position=VERTEX;}","void vertex(){rest_position=VERTEX;feature_rest_normal=NORMAL;}")
    var end:int=code.rfind("}")
    code=code.substr(0,end)+"\n    ALBEDO=local_source_feature_color(UV,rest_position,feature_rest_normal,ALBEDO);\n    if(feature_mode==2){ALBEDO=vec3(0.);EMISSION=vec3(local_source_feature_mask(UV,rest_position,feature_rest_normal)>0.?1.:0.);}\n"+code.substr(end)
    var shader=Shader.new();shader.code=code;material.shader=shader
    var e:Array=p.source_eye;material.set_shader_parameter("feature_eye",Vector4(e[0],e[1],e[2],e[3]))
    var f:Array=p.rest_normal_z_fade;material.set_shader_parameter("feature_normal_fade",Vector2(f[0],f[1]))
    var r:Array=p.source_rect_donor;material.set_shader_parameter("feature_donor_rect",Vector4(r[0],r[1],r[2],r[3]))
    if p.get("kind", "eye_bridge")=="source_ink":
        material.set_shader_parameter("feature_type",1)
        for key in ["ink_mask","ink_donors"]:
            assert(FileAccess.get_sha256(p[key])==p[key+"_sha256"],"Stale ink data")
            var image=Image.load_from_file(p[key])
            assert(image!=null and image.get_size()==Vector2i(p.source_size[0],p.source_size[1]))
            material.set_shader_parameter("feature_"+key,ImageTexture.create_from_image(image))
    material.set_shader_parameter("feature_mode",int(OS.get_environment("FISH_FEATURE_MODE")) if OS.has_environment("FISH_FEATURE_MODE") else 1)
    mesh.set_surface_override_material(p.surface,material)
    return 1
