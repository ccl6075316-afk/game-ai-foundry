extends SceneTree
## Data-only broad-head colour adapter for a portable112/139 body. Geometry,
## source pixels and the original eye/gill/lip domains stay independently bound.
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func digest(v)->String:
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(v));return h.finish().hex_encode()
func _initialize():call_deferred("run")
func run():
    var plan_path=OS.get_cmdline_user_args()[0];var p=JSON.parse_string(FileAccess.get_file_as_string(plan_path))
    assert(p.projection=="rest_triplanar" and p.normal_power==6 and p.surface==0)
    assert(FileAccess.get_sha256(p.source_body.path)==p.source_body.sha256)
    assert(FileAccess.get_sha256(p.source_image.path)==p.source_image.sha256)
    assert(p.support_x.size()==2 and p.support_x[0]<p.support_x[1] and p.support_x[0]>p.protected_native_x_max)
    var source=load(p.source_body.path) as ArrayMesh;var next=source.duplicate() as ArrayMesh
    var mat=source.surface_get_material(0) as ShaderMaterial;assert(mat!=null)
    var pixels=Image.load_from_file(p.source_image.path);pixels.convert(Image.FORMAT_RGBA8)
    var actual=(mat.get_shader_parameter("front112_source") as Texture2D).get_image().duplicate()
    if actual.is_compressed():assert(actual.decompress()==OK)
    actual.clear_mipmaps();actual.convert(Image.FORMAT_RGBA8)
    assert(actual.get_size()==pixels.get_size() and actual.get_data()==pixels.get_data(),"Native donor RGBA mismatch")
    var size:Vector2=pixels.get_size()
    for kind in ["upper","lower"]:
        var r:Array=p.donor_rects_px[kind];assert(r.size()==4 and r[0]>=0 and r[1]>=0 and r[2]<=size.x and r[3]<=size.y and r[0]<r[2] and r[1]<r[3])
        var expected=Vector4(r[0]/size.x,r[1]/size.y,r[2]/size.x,r[3]/size.y)
        assert(expected.is_equal_approx(mat.get_shader_parameter("front112_"+kind)),"Frozen donor rectangle differs from portable source")
    var before:String=mat.shader.code;var factor="smoothstep(.05,.75,normalize(front112_normal).x)";assert(before.count(factor)==1)
    assert(before.contains("front112_rest=rest114_position;front112_normal=rest114_normal;"),"Head colour must use immutable rest fields")
    if p.require_lip_continuity:assert(before.contains("mouth146_skin") and before.rfind("ALBEDO=mix")>before.find("ALBEDO=front112_color"))
    var code=before.replace(factor,"1.0")
    var planar="vec2 pixel=mod(floor(vec2(front112_rest.z,front112_rest.y)*front112_pixel_per_native),size);\n    vec2 uv=r.xy+(pixel+vec2(.5))/front112_source_size;\n    return mix(base,texture(front112_source,uv).rgb,amount);"
    assert(code.count(planar)==1)
    var triplanar="vec3 weights=pow(abs(normalize(front112_normal)),vec3(6.0));\n    weights/=max(weights.x+weights.y+weights.z,1e-8);\n    vec2 side_pixel=mod(floor(front112_rest.xy*front112_pixel_per_native),size);\n    vec2 top_pixel=mod(floor(front112_rest.xz*front112_pixel_per_native),size);\n    vec2 front_pixel=mod(floor(front112_rest.zy*front112_pixel_per_native),size);\n    vec3 grain=texture(front112_source,r.xy+(front_pixel+vec2(.5))/front112_source_size).rgb*weights.x;\n    grain+=texture(front112_source,r.xy+(top_pixel+vec2(.5))/front112_source_size).rgb*weights.y;\n    grain+=texture(front112_source,r.xy+(side_pixel+vec2(.5))/front112_source_size).rgb*weights.z;\n    return mix(base,grain,amount);"
    code=code.replace(planar,triplanar);var shader=Shader.new();shader.code=code
    mat=mat.duplicate() as ShaderMaterial;mat.shader=shader
    mat.set_shader_parameter("front112_x",Vector2(p.support_x[0],p.support_x[1]));mat.set_shader_parameter("front112_half_width",p.half_width)
    next.surface_set_material(0,PORTABLE.freeze(mat));var arrays=[]
    for si in source.get_surface_count():
        assert(digest(source.surface_get_arrays(si))==digest(next.surface_get_arrays(si)));arrays.append(digest(next.surface_get_arrays(si)))
    DirAccess.make_dir_recursive_absolute(p.output)
    assert(ResourceSaver.save(next,p.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var f=FileAccess.open(p.output+"/material.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"species":p.species,"plan_sha256":FileAccess.get_sha256(plan_path),"builder_sha256":FileAccess.get_sha256(get_script().resource_path),"body_sha256":FileAccess.get_sha256(p.output+"/body.res"),"arrays":arrays,"source_native_rgba_sha256":digest(actual.get_data()),"old_shader_sha256":before.sha256_text(),"new_shader_sha256":code.sha256_text(),"geometry_uv_skin_lods_unchanged":true,"scope":"RGB-only native safe-donor triplanar candidate. Blended surface-plane colours are derived texels, not a claim of unmodified RGB at every output pixel. Actual GPU, protected features, material binding and required physical gates remain separate."}));f.close();quit()
