extends "capture_body_coverage.gd"
## Portable material copies have new object IDs. Prove exact arrays/native pixels
## against a baseline that passed077, then validate the RGB-only wrapper and GPU.
var preservation:Dictionary={}
var preservation_path:String
func _initialize():
    preservation_path=OS.get_environment("FOUNDRY_SOURCE_BODY143_PLAN");assert(not preservation_path.is_empty());preservation=JSON.parse_string(FileAccess.get_file_as_string(preservation_path));assert(preservation.ok)
    for path in preservation.frozen_inputs:assert(FileAccess.get_sha256(path)==preservation.frozen_inputs[path])
    super._initialize()
func image_bytes(texture:Texture2D)->PackedByteArray:
    assert(texture!=null);var im=texture.get_image().duplicate();assert(im!=null)
    if im.is_compressed():assert(im.decompress()==OK)
    im.clear_mipmaps();im.convert(Image.FORMAT_RGBA8);return im.get_data()
func same_material_inputs(actual:ShaderMaterial,expected:ShaderMaterial):
    for uniform in expected.shader.get_shader_uniform_list():
        var a=actual.get_shader_parameter(uniform.name);var b=expected.get_shader_parameter(uniform.name)
        if b is Texture2D:assert(a is Texture2D and a.get_size()==b.get_size() and image_bytes(a)==image_bytes(b),"Preserved body texture differs: "+String(uniform.name))
        else:assert(a==b,"Preserved body input differs: "+String(uniform.name))
func authorize_body_shader(model:Node3D,species:String,mesh:MeshInstance3D,surface:int,material:ShaderMaterial)->Dictionary:
    if not preservation.species.has(species):return super.authorize_body_shader(model,species,mesh,surface,material)
    var p:Dictionary=preservation.species[species];assert(String(mesh.name)=="Closed_body");var reference=load(p.baseline_resource) as ArrayMesh;assert(reference!=null and reference.get_surface_count()==mesh.mesh.get_surface_count())
    for si in reference.get_surface_count():
        var a=mesh.mesh.surface_get_arrays(si);var b=reference.surface_get_arrays(si)
        for field in Mesh.ARRAY_MAX:assert(a[field]==b[field],"Actual body arrays changed")
    var original=reference.surface_get_material(surface) as ShaderMaterial;assert(original!=null and mesh.get_active_material(surface)==material);var expected:String=original.shader.code
    if surface==0:
        expected=expected.replace("shader_type spatial;","shader_type spatial;\nuniform sampler2D pectoral142_source : source_color,filter_nearest,repeat_disable;\nuniform sampler2D pectoral142_mask : filter_nearest,repeat_disable;\n");var end=expected.rfind("}");expected=expected.substr(0,end)+"\n// Body-owned source attachment mark, after existing fin cleaning and head charts.\nALBEDO=mix(ALBEDO,texture(pectoral142_source,UV).rgb,texture(pectoral142_mask,UV).r);\n"+expected.substr(end)
        for key in ["source","mask"]:
            var im=Image.load_from_file(p[key]);assert(im!=null);assert(image_bytes(material.get_shader_parameter("pectoral142_"+key))==image_bytes(ImageTexture.create_from_image(im)),"New body source/mask mismatch")
        var baseline=JSON.parse_string(FileAccess.get_file_as_string(preservation.baseline_capture));var proved=false
        for row in baseline.dynamic_body_shaders:
            if row.species==species and row.generated_shader_sha256==original.shader.code.sha256_text():proved=true
        assert(proved,"Original body shader did not pass baseline077")
    assert(material.shader.code==expected,"Unexpected replacement body shader change");same_material_inputs(material,original)
    var clean=RegEx.new();assert(clean.compile("(?s)//[^\\n]*|/\\*.*?\\*/")==OK);var code=clean.sub(material.shader.code,"",true);var tokens=RegEx.new();assert(tokens.compile("\\b(?:ALPHA|ALPHA_SCISSOR_THRESHOLD|ALPHA_HASH_SCALE|discard)\\b")==OK);assert(tokens.search(code)==null,"Body opacity changed")
    return {"ok":true,"species":species,"generated_shader_sha256":material.shader.code.sha256_text(),"baseline_resource_sha256":FileAccess.get_sha256(p.baseline_resource),"source_body_plan_sha256":FileAccess.get_sha256(preservation_path),"scope":"Exact validated baseline arrays/old material inputs/nativeRGBA; only frozen source-RGB attachment wrapper added. Actual GPU077 coverage remains independently captured."}
func authorize_relief(model:Node3D,mesh:MeshInstance3D):
    var species=String(model.get_meta("fin_source141",{}).get("species",""))
    if not preservation.species.has(species):super.authorize_relief(model,mesh);return
    var p:Dictionary=mesh.get_meta("decorative_relief112");var body=model.find_child(p.underlying_body,true,false) as MeshInstance3D;assert(body!=null and body.skin==mesh.skin and body.skeleton==mesh.skeleton and mesh.get_parent()==body.get_parent());assert(p.model_sha256==FileAccess.get_sha256(model.scene_file_path)and p.profile_sha256==FileAccess.get_sha256("res://assets/models/fish/motion/eye-relief112.json"));var receipt:Dictionary=model.get_meta("eye_relief112_receipt");assert(receipt.helper_sha256==FileAccess.get_sha256("res://scripts/aquarium/EyeRelief112.gd"));var material=mesh.get_active_material(0) as StandardMaterial3D;assert(material!=null and material.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED);var source=(body.get_active_material(0) as ShaderMaterial).get_shader_parameter("source_texture") as Texture2D;assert(material.albedo_texture.get_size()==source.get_size()and image_bytes(material.albedo_texture)==image_bytes(source),"Relief source pixels differ from preserved body source")
func extra_capture_bindings()->Dictionary:
    var result:Dictionary=preservation.frozen_inputs.duplicate();result[preservation_path]=FileAccess.get_sha256(preservation_path);var script=get_script()
    while script!=null:result[script.resource_path]=FileAccess.get_sha256(script.resource_path);script=script.get_base_script()
    return result
