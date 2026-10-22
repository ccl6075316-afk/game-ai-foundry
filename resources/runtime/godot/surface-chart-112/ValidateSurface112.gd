extends RefCounted
func digest(value:Variant)->String:
    var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(value if value is PackedByteArray else var_to_bytes(value));return ctx.finish().hex_encode()
func coverage_safe(code:String):
    var rx=RegEx.new();rx.compile('(?s)//[^\\n]*|/\\*.*?\\*/|[A-Za-z_][A-Za-z_0-9]*')
    for hit in rx.search_all(code):
        var token=hit.get_string()
        if token.begins_with("//") or token.begins_with("/*"):continue
        assert(token!="ALPHA" and not token.begins_with("ALPHA_") and token!="discard","112 body code changes coverage: "+token)
func actual_texture(texture:Texture2D,path:String):
    assert(texture!=null and FileAccess.file_exists(path))
    var a=texture.get_image();assert(a!=null)
    if a.is_compressed():assert(a.decompress()==OK)
    if a.has_mipmaps():a.clear_mipmaps()
    a.convert(Image.FORMAT_RGBA8)
    var b=Image.new();assert(b.load_png_from_buffer(FileAccess.get_file_as_bytes(path))==OK);b.convert(Image.FORMAT_RGBA8)
    assert(a.get_size()==b.get_size() and a.get_data()==b.get_data(),"112 actual chart pixels differ from frozen PNG")
func validate_chart(model:Node3D,species:String,mesh:MeshInstance3D,surface:int,material:ShaderMaterial,outer:Dictionary={})->Dictionary:
    var r:Dictionary=model.get_meta("surface_chart_112_receipt",{});assert(not r.is_empty())
    var config="res://assets/models/fish/motion/surface-charts112.json";var helper="res://scripts/aquarium/BodyChart112.gd";var template="res://scripts/aquarium/BodyChart112.gdshaderinc"
    assert(r.model_sha256==FileAccess.get_sha256(model.scene_file_path) and r.helper_sha256==FileAccess.get_sha256(helper) and r.template_sha256==FileAccess.get_sha256(template) and r.profile_sha256==FileAccess.get_sha256(config))
    assert(str(mesh.name)==r.mesh and surface==int(r.surface))
    if outer.is_empty():assert(mesh.get_active_material(surface)==material)
    else:assert(mesh.get_active_material(surface).shader.code.sha256_text()==outer.generated_shader_sha256 and outer.base_shader_code==material.shader.code)
    assert(material.shader.code.sha256_text()==r.generated_shader_sha256 and r.base_shader_code.sha256_text()==r.base_shader_sha256)
    var base:String=r.base_shader_code;var value="chin.rgb" if species=="yellow_croaker" else "color.rgb";var assignment="ALBEDO="+value+";"
    assert(base.count(assignment)==1 and base.count("void vertex()")==1)
    var expected=base.replace("void vertex()",FileAccess.get_file_as_string(template)+"\nvoid vertex()")
    expected=expected.insert(expected.find("{",expected.find("void vertex()"))+1,"chart112_rest_position=VERTEX;chart112_rest_normal=NORMAL;")
    expected=expected.replace(assignment,"ALBEDO=chart112_color("+value+");")
    assert(expected==material.shader.code,"112 wrapper differs from exact authorized construction")
    coverage_safe(expected)
    if species in ["black_seabream","zander"]:
        var number="106" if species=="black_seabream" else "107";var eye:Dictionary=model.get_meta("eye_ownership_"+number+"_receipt",{})
        var eye_helper="res://scripts/aquarium/"+("review_candidates/black_seabream/" if number=="106" else "")+"FishEyeOwnership.gd"
        var eye_config="res://assets/models/fish/motion/eye-ownership-"+number+".json"
        assert(not eye.is_empty() and eye.generated_shader_sha256==r.base_shader_sha256 and eye.model_sha256==r.model_sha256)
        assert(eye.helper_sha256==FileAccess.get_sha256(eye_helper) and eye.profile_sha256==FileAccess.get_sha256(eye_config))
        var p:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(eye_config)).profiles[species]
        var h=load(eye_helper).new();assert(h._vertex_order_hash(mesh.mesh.surface_get_arrays(0))==p.vertex_order_sha256)
        assert(h._mesh_snapshot(mesh).all_surface_arrays_sha256==p.all_surface_arrays_sha256)
        assert(material.get_shader_parameter("eye_mode")==1 and material.get_shader_parameter("eye_vertex_count")==p.surface0_vertices)
        assert(eye.template_sha256==FileAccess.get_sha256(eye_helper.get_base_dir()+"/FishEyeOwnership.gdshaderinc"))
    elif species=="red_seabream":
        var ink=load("res://scripts/aquarium/review_candidates/red_seabream/FishSourceInk.gd").new()
        var origin="res://scripts/aquarium/review_candidates/red_seabream/FishBodyOpaque.gdshader"
        var code:String=ink._expand_includes(FileAccess.get_file_as_string(origin),origin);var wrapped:Dictionary=ink._wrap_samples(code);code=wrapped.code
        var rx=RegEx.new();rx.compile('(?m)^(?:void|float|int|bool|vec[234]|ivec[234]|mat[234])\\s+\\w+\\s*\\(');var found=rx.search(code);assert(found!=null)
        code=code.substr(0,found.get_start())+FileAccess.get_file_as_string("res://scripts/aquarium/review_candidates/red_seabream/FishSourceInk.gdshaderinc")+"\n"+code.substr(found.get_start())
        assert(code==base,"112 red source ink base differs from real helper construction")
    else:
        var origin="res://scripts/aquarium/review_candidates/yellow_croaker/FishBodyOpaque.gdshader" if species=="yellow_croaker" else "res://scripts/aquarium/FishBodyOpaque.gdshader"
        assert(base==FileAccess.get_file_as_string(origin),"Unknown112 static shader base")
    var p:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(config)).profiles[species]
    assert(p.model_sha256==r.model_sha256)
    for kind in ["dorsal","ventral"]:
        assert(FileAccess.get_sha256(p[kind].path)==p[kind].sha256);actual_texture(material.get_shader_parameter("chart112_"+kind),p[kind].path)
    assert(int(material.get_shader_parameter("chart112_section_count"))==p.sections.size())
    var actual:PackedVector4Array=material.get_shader_parameter("chart112_sections")
    for i in p.sections.size():assert(actual[i].is_equal_approx(Vector4(p.sections[i][0],p.sections[i][1],p.sections[i][2],p.sections[i][3])))
    if model.has_meta("head_lods112_receipt"):
        var lod:Dictionary=model.get_meta("head_lods112_receipt")
        assert(lod.model_sha256==r.model_sha256 and lod.runtime_mesh_resource_id==mesh.mesh.get_instance_id())
        assert(lod.all_decoded_surface_arrays_before==lod.all_decoded_surface_arrays_after)
        assert(digest(mesh.mesh.get("_surfaces"))==lod.actual_after_raw_surfaces_sha256)
        for raw in mesh.mesh.get("_surfaces"):assert(raw.get("lods",[]).is_empty())
    return {"ok":true,"species":species,"scope":"Exact112 opaque chart wrapper and frozen original base; visual/anatomical acceptance separate","generated_shader_sha256":r.generated_shader_sha256,"config_sha256":r.profile_sha256}
func validate_lining(model:Node3D,species:String,mesh:MeshInstance3D,surface:int,material:ShaderMaterial):
    var p:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/source-jaw112.json")).profiles[species]
    var r:Dictionary=model.get_meta("source_jaw112_receipt",{})
    assert(str(mesh.name)==p.mesh and surface==1 and r.model_sha256==p.model_sha256 and p.model_sha256==FileAccess.get_sha256(model.scene_file_path))
    assert(r.helper_sha256==FileAccess.get_sha256("res://scripts/aquarium/SourceJaw112.gd") and r.lining_sha256==FileAccess.get_sha256(material.shader.resource_path))
    assert(material.shader.code==FileAccess.get_file_as_string("res://scripts/aquarium/SourceJaw112.gdshader"));coverage_safe(material.shader.code)
    var skin=mesh.get_active_material(0) as ShaderMaterial
    assert(material.get_shader_parameter("source_texture")==skin.get_shader_parameter("source_texture"))
    assert(skin.get_shader_parameter("mouth_source_projection")==false and skin.get_shader_parameter("rim_local_source")==false)
func validate_relief(model:Node3D,mesh:MeshInstance3D):
    var p:Dictionary=mesh.get_meta("decorative_relief112",{});var body=model.find_child(p.underlying_body,true,false) as MeshInstance3D
    assert(body!=null and body.skin==mesh.skin and body.skeleton==mesh.skeleton and mesh.get_parent()==body.get_parent())
    assert(p.model_sha256==FileAccess.get_sha256(model.scene_file_path) and p.profile_sha256==FileAccess.get_sha256("res://assets/models/fish/motion/eye-relief112.json"))
    var receipt:Dictionary=model.get_meta("eye_relief112_receipt",{});assert(receipt.helper_sha256==FileAccess.get_sha256("res://scripts/aquarium/EyeRelief112.gd"))
    var material=mesh.get_active_material(0) as StandardMaterial3D;assert(material!=null and material.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED)
    assert(material.albedo_texture==(body.get_active_material(0) as ShaderMaterial).get_shader_parameter("source_texture"))
func validate_front(model:Node3D,species:String,mesh:MeshInstance3D,surface:int,material:ShaderMaterial)->Dictionary:
    var key=str(mesh.name)+":"+str(surface);var records:Dictionary=model.get_meta("front_skin112_receipts",{});assert(records.has(key));var r:Dictionary=records[key]
    var config="res://assets/models/fish/motion/front-skin112.json";var helper="res://scripts/aquarium/FrontSkin112.gd";var template="res://scripts/aquarium/FrontSkin112.gdshaderinc"
    assert(r.model_sha256==FileAccess.get_sha256(model.scene_file_path) and r.helper_sha256==FileAccess.get_sha256(helper) and r.template_sha256==FileAccess.get_sha256(template) and r.profile_sha256==FileAccess.get_sha256(config))
    assert(mesh.get_active_material(surface)==material and material.shader.code.sha256_text()==r.generated_shader_sha256 and r.base_shader_code.sha256_text()==r.base_shader_sha256)
    var base:String=r.base_shader_code;var expected=base.replace("void vertex()",FileAccess.get_file_as_string(template)+"\nvoid vertex()")
    expected=expected.insert(expected.find("{",expected.find("void vertex()"))+1,"front112_rest=VERTEX;front112_normal=NORMAL;")
    expected=expected.replace(r.assignment,"ALBEDO=front112_color("+("chart112_color(color.rgb)" if base.contains("chart112_color") else "color.rgb")+");")
    assert(material.shader.code==expected);coverage_safe(expected)
    if base.contains("chart112_color"):
        var before=material.duplicate() as ShaderMaterial;var shader=Shader.new();shader.code=base;before.shader=shader
        assert(validate_chart(model,species,mesh,surface,before,r).ok)
    else:
        assert(r.base_shader_path=="res://scripts/aquarium/FishBodyOpaque.gdshader" and base==FileAccess.get_file_as_string(r.base_shader_path))
    var p:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(config)).profiles[species];assert(p.model_sha256==r.model_sha256 and FileAccess.get_sha256(p.source.path)==p.source.sha256)
    actual_texture(material.get_shader_parameter("front112_source"),p.source.path)
    for kind in ["upper","lower"]:
        var rr:Array=p[kind];assert(material.get_shader_parameter("front112_"+kind).is_equal_approx(Vector4(rr[0],rr[1],rr[2],rr[3])))
    var target:Dictionary={}
    for t in p.targets:
        if t.mesh==str(mesh.name):
            for si in t.surfaces:
                if int(si)==surface:target=t
    assert(not target.is_empty() and material.get_shader_parameter("front112_x").is_equal_approx(Vector2(target.x[0],target.x[1])))
    assert(is_equal_approx(material.get_shader_parameter("front112_half_width"),float(target.half_width)))
    return {"ok":true,"species":species,"scope":"Explicit112 source lip/chin color transport; geometry unchanged","generated_shader_sha256":r.generated_shader_sha256}
