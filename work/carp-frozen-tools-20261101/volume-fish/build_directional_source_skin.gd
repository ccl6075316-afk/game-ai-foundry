extends SceneTree
## Continuous, source-projected dorsal/ventral colour on the actual rest surface.
## No quilt tiling, vertex edits, alpha edits or replacement of original lip pixels.
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func digest(value)->String:
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(value));return h.finish().hex_encode()
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var path=args[0]
    var p=JSON.parse_string(FileAccess.get_file_as_string(path));assert(p.kind=="directional_native_source_skin")
    assert(FileAccess.get_sha256(p.source_body.path)==p.source_body.sha256)
    var original=load(p.source_body.path) as ArrayMesh;var candidate=original.duplicate() as ArrayMesh
    var mat=original.surface_get_material(0) as ShaderMaterial;var code:String=mat.shader.code
    var marker="ALBEDO=front112_color(chart112_color(color.rgb));"
    assert(code.count(marker)==1 and code.contains("rest114_position") and code.contains("chart112_section"))
    assert(code.rfind("ALBEDO=mix")>code.find(marker),"Original135 lip continuity must follow new colour")
    var decl="""
uniform sampler2D skin152_top : source_color,filter_nearest,repeat_disable;
uniform sampler2D skin152_bottom : source_color,filter_nearest,repeat_disable;
uniform sampler2D skin152_attachment : filter_nearest,repeat_disable;
uniform vec2 skin152_dorsal_blend;
uniform vec2 skin152_ventral_blend;
uniform vec4 skin152_lateral_gill_x;
uniform vec2 skin152_body_u_support;
varying vec3 skin152_p;
varying vec3 skin152_n;
vec3 skin152_color(vec3 base,vec2 native_uv){
    vec3 p=skin152_p;vec3 n=normalize(skin152_n);
    vec4 section=chart112_section(p.x);
    float height=(p.y-section.y)/max(section.z,1e-7);
    float across=clamp(p.z/max(section.w,1e-7),-1.,1.);
    vec2 uv=vec2(clamp(p.x*chart112_u_affine.x+chart112_u_affine.y,0.,.999999),.5+.5*across);
    float top=smoothstep(skin152_dorsal_blend.x,skin152_dorsal_blend.y,n.y);
    float bottom=smoothstep(skin152_ventral_blend.x,skin152_ventral_blend.y,-height);
    // Preserve the complete source eye only on its true lateral surfaces.
    float eye=1.-smoothstep(1.10,1.45,length((p.xy-chart112_eye_rect_native.xy)/max(chart112_eye_rect_native.zw,vec2(1e-7))));
    float eye_side=smoothstep(.45,.75,abs(n.z));
    // True lateral gills remain on the sides; they must not wrap across the crown.
    float gill=smoothstep(skin152_lateral_gill_x.x,skin152_lateral_gill_x.y,p.x)*(1.-smoothstep(skin152_lateral_gill_x.z,skin152_lateral_gill_x.w,p.x))*smoothstep(.72,.9,abs(n.z));
    float attachment=texture(skin152_attachment,native_uv).r*eye_side;
    float protected=max(max(eye*eye_side,gill),attachment);
    float valid=smoothstep(skin152_body_u_support.x,skin152_body_u_support.y,uv.x);
    top*=valid*(1.-protected);bottom*=valid*(1.-protected);
    base=mix(base,texture(skin152_top,uv).rgb,top);
    return mix(base,texture(skin152_bottom,uv).rgb,bottom);
}
"""
    var vertex_marker="chart112_rest_position=rest114_position;chart112_rest_normal=rest114_normal;"
    assert(code.count(vertex_marker)==1)
    code=code.replace(vertex_marker,vertex_marker+"skin152_p=rest114_position;skin152_n=rest114_normal;")
    code=code.replace(marker,"ALBEDO=skin152_color(front112_color(chart112_color(color.rgb)),UV);")
    code=code.replace("void vertex()",decl+"\nvoid vertex()")
    var shader=Shader.new();shader.code=code;mat=mat.duplicate() as ShaderMaterial;mat.shader=shader
    for kind in ["top","bottom"]:
        assert(FileAccess.get_sha256(p[kind].path)==p[kind].sha256)
        var image=Image.load_from_file(p[kind].path);assert(image!=null and image.get_width()==p.atlas_width)
        mat.set_shader_parameter("skin152_"+kind,ImageTexture.create_from_image(image))
    assert(FileAccess.get_sha256(p.attachment_mask.path)==p.attachment_mask.sha256)
    var attachment_image=Image.load_from_file(p.attachment_mask.path);assert(attachment_image!=null)
    mat.set_shader_parameter("skin152_attachment",ImageTexture.create_from_image(attachment_image))
    mat.set_shader_parameter("skin152_dorsal_blend",Vector2(p.dorsal_blend[0],p.dorsal_blend[1]))
    mat.set_shader_parameter("skin152_ventral_blend",Vector2(p.ventral_blend[0],p.ventral_blend[1]))
    mat.set_shader_parameter("skin152_lateral_gill_x",Vector4(p.lateral_gill_x[0],p.lateral_gill_x[1],p.lateral_gill_x[2],p.lateral_gill_x[3]))
    mat.set_shader_parameter("skin152_body_u_support",Vector2(p.body_u_support[0],p.body_u_support[1]))
    candidate.surface_set_material(0,PORTABLE.freeze(mat));var arrays=[]
    for si in original.get_surface_count():
        assert(digest(original.surface_get_arrays(si))==digest(candidate.surface_get_arrays(si)))
        var old_surfaces=original.get("_surfaces");var new_surfaces=candidate.get("_surfaces")
        assert(old_surfaces is Array and new_surfaces is Array)
        assert(digest(old_surfaces[si].get("lods",[]))==digest(new_surfaces[si].get("lods",[])))
        arrays.append(digest(candidate.surface_get_arrays(si)))
    DirAccess.make_dir_recursive_absolute(p.output);assert(ResourceSaver.save(candidate,p.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var f=FileAccess.open(p.output+"/material.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"species":p.species,"plan_sha256":FileAccess.get_sha256(path),"builder_sha256":FileAccess.get_sha256(get_script().resource_path),"body_sha256":FileAccess.get_sha256(p.output+"/body.res"),"arrays":arrays,"geometry_uv_skin_lods_unchanged":true,"old_shader_sha256":original.surface_get_material(0).shader.code.sha256_text(),"new_shader_sha256":code.sha256_text(),"scope":"Bounded RGB-only candidate. Native source-coordinate maps, actual GPU/source eyes/gills/lips and final applicable gates remain separate; no appearance acceptance."}));f.close();quit()
