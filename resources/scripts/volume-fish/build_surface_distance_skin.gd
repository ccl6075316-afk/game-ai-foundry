extends SceneTree
## Local RGB dorsal replacement over152, using actual rest-surface arc distances.
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func digest(value)->String:
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(value));return h.finish().hex_encode()
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var p=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
    assert(p.kind=="rest_surface_distance_skin")
    for key in ["source_body","flat_source","arc_lut"]:assert(FileAccess.get_sha256(p[key].path)==p[key].sha256)
    var original=load(p.source_body.path)as ArrayMesh;var candidate=original.duplicate()as ArrayMesh
    var mat=original.surface_get_material(0)as ShaderMaterial;var code:String=mat.shader.code
    var marker="base=mix(base,texture(skin152_top,uv).rgb,top);"
    assert(code.count(marker)==1 and code.contains("skin152_p=rest114_position;skin152_n=rest114_normal;"))
    var decl="""
uniform sampler2D skin153_flat : source_color,filter_nearest,repeat_disable;
uniform sampler2D skin153_arc : filter_linear,repeat_disable;
uniform vec2 skin153_arc_x;
uniform vec2 skin153_head_keep;
uniform vec2 skin153_extent;
uniform float skin153_origin_x;
"""
    code=code.replace("varying vec3 skin152_p;",decl+"\nvarying vec3 skin152_p;")
    code=code.replace(marker,"""
    float replace_back=1.-smoothstep(skin153_head_keep.x,skin153_head_keep.y,p.x);
    float theta=atan(across,height);
    vec2 lookup=vec2(clamp((p.x-skin153_arc_x.x)/(skin153_arc_x.y-skin153_arc_x.x),0.,1.),.5+theta/6.28318530718);
    float arc=texture(skin153_arc,lookup).r;
    vec2 texcoord153=vec2((p.x-skin153_origin_x)/skin153_extent.x,.5+arc/skin153_extent.y);
    vec3 native_color153=texture(skin153_flat,texcoord153).rgb;
    vec3 dorsal=mix(texture(skin152_top,uv).rgb,native_color153,replace_back);
    // Cover the upper shoulders too: projected side dots otherwise become vertical streaks.
    top=max(top,smoothstep(.00,.25,height)*replace_back*valid*(1.-protected));
    base=mix(base,dorsal,top);
""")
    var shader=Shader.new();shader.code=code;assert(not shader.get_shader_uniform_list().is_empty(),"Candidate shader failed to parse")
    mat=mat.duplicate()as ShaderMaterial;mat.shader=shader
    var source=Image.load_from_file(p.flat_source.path);assert(source!=null)
    mat.set_shader_parameter("skin153_flat",ImageTexture.create_from_image(source))
    var bytes=FileAccess.get_file_as_bytes(p.arc_lut.path)
    var lut=Image.create_from_data(p.arc_size[0],p.arc_size[1],false,Image.FORMAT_RF,bytes)
    mat.set_shader_parameter("skin153_arc",ImageTexture.create_from_image(lut))
    mat.set_shader_parameter("skin153_arc_x",Vector2(p.arc_x[0],p.arc_x[1]))
    mat.set_shader_parameter("skin153_head_keep",Vector2(p.head_keep[0],p.head_keep[1]))
    mat.set_shader_parameter("skin153_extent",Vector2(p.native_extent[0],p.native_extent[1]))
    mat.set_shader_parameter("skin153_origin_x",p.native_origin_x)
    candidate.surface_set_material(0,PORTABLE.freeze(mat))
    for si in original.get_surface_count():
        assert(digest(original.surface_get_arrays(si))==digest(candidate.surface_get_arrays(si)))
        assert(digest(original.get("_surfaces")[si].get("lods",[]))==digest(candidate.get("_surfaces")[si].get("lods",[])))
    DirAccess.make_dir_recursive_absolute(p.output)
    assert(ResourceSaver.save(candidate,p.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var f=FileAccess.open(p.output+"/material.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"body_sha256":FileAccess.get_sha256(p.output+"/body.res"),"recipe_sha256":FileAccess.get_sha256(args[0]),"builder_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"RGB-only local dorsal candidate. Actual arrays and LOD unchanged;152 head beyond upper keep boundary, original belly and final lip layer retained. GPU/local visual review and final affected gates separate."}));f.close();quit()
