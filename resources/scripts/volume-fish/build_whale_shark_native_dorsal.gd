extends SceneTree
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func digest(value)->String:
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(value));return h.finish().hex_encode()
func _initialize():
    var args=OS.get_cmdline_user_args()
    var plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
    var path_base=args[0].get_base_dir().path_join(plan.get("path_base",".")).simplify_path()
    for key in ["source_body","source_image","output"]:
        if not String(plan[key]).is_absolute_path() and not String(plan[key]).begins_with("res://"):
            plan[key]=path_base.path_join(plan[key]).simplify_path()
    assert(FileAccess.get_sha256(plan.source_body)==plan.source_body_sha256)
    assert(FileAccess.get_sha256(plan.source_image)==plan.source_image_sha256)
    var original=load(plan.source_body) as ArrayMesh
    var candidate=original.duplicate() as ArrayMesh
    var source=original.surface_get_material(0) as ShaderMaterial
    var material=PORTABLE.freeze(source) as ShaderMaterial
    var code=source.shader.code
    var old="vec3 native_color153=texture(skin153_flat,texcoord153).rgb;"
    assert(code.count(old)==1)
    var replacement="""
    // Native top artwork, continuous longitudinal correspondence. No repeating tile.
    float sx=.12+clamp((uv.x-.1626)/(.9961-.1626),0.,1.)*(.97-.12);
    float radius=.034;
    radius=mix(radius,.057,clamp((sx-.12)/.08,0.,1.));
    radius=mix(radius,.069,clamp((sx-.20)/.05,0.,1.));
    radius=mix(radius,.119,clamp((sx-.25)/.15,0.,1.));
    radius=mix(radius,.160,clamp((sx-.40)/.15,0.,1.));
    radius=mix(radius,.202,clamp((sx-.55)/.15,0.,1.));
    radius=mix(radius,.215,clamp((sx-.70)/.10,0.,1.));
    radius=mix(radius,.191,clamp((sx-.80)/.10,0.,1.));
    radius=mix(radius,.146,clamp((sx-.90)/.07,0.,1.));
    // Preserve the native image pixel aspect ratio in physical surface distance.
    float source_distance=abs(arc)*(2028.*.85/.8335)/937.;
    float outer=radius*.92;
    // Unseen shoulder skin continues the complete same-X native half-field.
    // Reflect beyond the visible donor edge, excluding the centre stripe from repeats.
    float inner=min(.018,outer*.25);
    if(source_distance>outer){
        float span=outer-inner;
        float q=mod(source_distance-outer,2.*span);
        source_distance=outer-(q<=span?q:2.*span-q);
    }
    float sy=.497+sign(arc)*source_distance;
    // The first median fin is drawn on one side of the centreline in the source.
    // Only that bounded painted fin uses the opposite original body pixel.
    if(((sx>.386 && sx<.478 && sy>.443)||(sx>.242 && sx<.315 && sy>.479)) && sy<.497){sy=.994-sy;}
    vec3 native_color153=texture(skin153_flat,vec2(sx,sy)).rgb;
    """
    code=code.replace(old,replacement)
    var shader=Shader.new();shader.code=code;material.shader=shader
    var image=Image.load_from_file(plan.source_image);assert(image!=null)
    material.set_shader_parameter("skin153_flat",ImageTexture.create_from_image(image))
    candidate.surface_set_material(0,material)
    for si in original.get_surface_count():
        assert(digest(original.surface_get_arrays(si))==digest(candidate.surface_get_arrays(si)))
        assert(digest(original.get("_surfaces")[si].get("lods",[]))==digest(candidate.get("_surfaces")[si].get("lods",[])))
    DirAccess.make_dir_recursive_absolute(plan.output)
    assert(ResourceSaver.save(candidate,plan.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var f=FileAccess.open(plan.output+"/material.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"source_body_sha256":plan.source_body_sha256,"source_image_sha256":plan.source_image_sha256,"candidate_sha256":FileAccess.get_sha256(plan.output+"/body.res"),"arrays_and_lods_unchanged":true,"source_image_dimensions":[image.get_width(),image.get_height()],"scope":"Local source-mapping experiment; not visual approval or final whole-fish validation."},"  "));f.close()
    print("SOURCE_CANDIDATE_SAVED");quit()
