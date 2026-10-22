extends RefCounted
const CONFIG="res://assets/models/fish/motion/surface-charts112.json"
const INCLUDE="BodyChart112.gdshaderinc"
var last_error: String=""
func apply(model: Node3D,species: String)->int:
    var config=JSON.parse_string(FileAccess.get_file_as_string(CONFIG))
    assert(config is Dictionary and config.get("profiles") is Dictionary,"Missing112 chart config")
    if not config.profiles.has(species):return 0
    var p: Dictionary=config.profiles[species]
    assert(FileAccess.get_sha256("res://assets/models/fish/"+species+".glb")==p.model_sha256,"Stale112 model")
    var body=model.find_child(p.mesh,true,false) as MeshInstance3D
    assert(body!=null)
    var material=body.get_active_material(int(p.surface)) as ShaderMaterial
    assert(material!=null and material.shader!=null)
    var original: String=material.shader.code
    var final_color: String="chin.rgb" if species=="yellow_croaker" else "color.rgb"
    var assignment: String="ALBEDO="+final_color+";"
    assert(original.count(assignment)==1 and original.count("void vertex()")==1,"Unsupported112 source shader: "+species+" "+material.shader.resource_path)
    assert(not original.contains("chart112_color"),"Chart already installed")
    var template_path=get_script().resource_path.get_base_dir().path_join(INCLUDE)
    var code=original.replace("void vertex()",FileAccess.get_file_as_string(template_path)+"\nvoid vertex()")
    var opening=code.find("{",code.find("void vertex()"))
    code=code.insert(opening+1,"chart112_rest_position=VERTEX;chart112_rest_normal=NORMAL;")
    code=code.replace(assignment,"ALBEDO=chart112_color("+final_color+");")
    var rest=preload("res://scripts/aquarium/RestSurface114.gd").new()
    code=rest.wrap_chart(code)
    var lip115:Dictionary={}
    if p.has("mouth_protection115"):
        var lip=preload("res://scripts/aquarium/LipMaterial115.gd").new()
        code=lip.wrap(code)
        lip115={"helper_sha256":FileAccess.get_sha256(lip.get_script().resource_path),"template_sha256":FileAccess.get_sha256(lip.template_path())}
    var shader=Shader.new();shader.code=code
    assert(not shader.get_shader_uniform_list().is_empty(),"112 chart shader failed")
    if model.has_meta("source_jaw112_receipt"):
        for key in ["mouth_source_projection","rim_local_source"]:assert(material.get_shader_parameter(key)==false,"Upstream SourceJaw projection changed")
    material=material.duplicate() as ShaderMaterial
    material.shader=shader
    # ShaderMaterial.duplicate omits parameters absent from the wrapped eye
    # shader's uniform list. Preserve SourceJaw's explicit disabled legacy
    # projections too; their exact false values remain part of the body gate.
    if model.has_meta("source_jaw112_receipt"):
        var jaw:Dictionary=model.get_meta("source_jaw112_receipt")
        assert(jaw.mesh==str(body.name) and jaw.mouth_source_projection==false and jaw.rim_local_source==false)
        for key in ["mouth_source_projection","rim_local_source"]:material.set_shader_parameter(key,false)
    body.set_surface_override_material(int(p.surface),material)
    rest.bind(model,body,int(p.surface),material)
    if p.has("mouth_protection115"):preload("res://scripts/aquarium/LipMaterial115.gd").new().bind(material,p)
    for kind in ["dorsal","ventral"]:
        assert(FileAccess.get_sha256(p[kind].path)==p[kind].sha256,"Stale112 chart")
        material.set_shader_parameter("chart112_"+kind,load(p[kind].path))
    var sections=PackedVector4Array()
    for row in p.sections:sections.append(Vector4(row[0],row[1],row[2],row[3]))
    material.set_shader_parameter("chart112_section_count",sections.size());sections.resize(128)
    material.set_shader_parameter("chart112_sections",sections)
    material.set_shader_parameter("chart112_u_affine",Vector2(p.u_affine[0],p.u_affine[1]))
    material.set_shader_parameter("chart112_normal_blend",Vector2(p.normal_blend[0],p.normal_blend[1]))
    material.set_shader_parameter("chart112_longitudinal",Vector4(p.longitudinal_u[0],p.longitudinal_u[1],p.longitudinal_u[2],p.longitudinal_u[3]))
    material.set_shader_parameter("chart112_pixel_per_native",p.pixel_per_native)
    material.set_shader_parameter("chart112_height",p.chart_height)
    var eyes=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/eye-relief112.json"))
    if eyes.profiles.has(species):
        var minimum=Vector2(INF,INF);var maximum=Vector2(-INF,-INF)
        for cap in eyes.profiles[species].caps:
            for point in cap.base_surface_points:
                minimum=minimum.min(Vector2(point[0],point[1]));maximum=maximum.max(Vector2(point[0],point[1]))
        var center=(minimum+maximum)*.5;var radius=(maximum-minimum)*.55
        material.set_shader_parameter("chart112_eye_rect_native",Vector4(center.x,center.y,radius.x,radius.y))
    model.set_meta("surface_chart_112_receipt",{"species":species,"model_sha256":p.model_sha256,"helper_sha256":FileAccess.get_sha256(get_script().resource_path),"template_sha256":FileAccess.get_sha256(template_path),"profile_sha256":FileAccess.get_sha256(CONFIG),"base_shader_code":original,"base_shader_sha256":original.sha256_text(),"generated_shader_sha256":code.sha256_text(),"geometry_changed":false,"surface":p.surface,"mesh":p.mesh})
    model.set_meta("lip_material115_receipt",lip115)
    return 1
