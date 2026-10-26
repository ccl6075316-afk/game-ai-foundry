extends SceneTree
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func digest(value)->String:
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(value));return h.finish().hex_encode()
func _initialize():
    var plan_path=OS.get_cmdline_user_args()[0]
    var plan=JSON.parse_string(FileAccess.get_file_as_string(plan_path))
    var path_base=plan_path.get_base_dir().path_join(plan.get("path_base",".")).simplify_path()
    for key in ["source_body","output"]:
        if not String(plan[key]).is_absolute_path() and not String(plan[key]).begins_with("res://"):
            plan[key]=path_base.path_join(plan[key]).simplify_path()
    assert(FileAccess.get_sha256(plan.source_body)==plan.source_body_sha256)
    var original=load(plan.source_body) as ArrayMesh;var candidate=original.duplicate() as ArrayMesh
    var source=original.surface_get_material(0) as ShaderMaterial
    var material=PORTABLE.freeze(source) as ShaderMaterial
    var code=source.shader.code
    var marker="base=mix(base,dorsal,top);"
    assert(code.count(marker)==1)
    var replacement="""
    // The approved crown remains byte-for-byte the original branch (height >= .70).
    float seam_side=1.-smoothstep(.35,.70,height);
    float seam_fore=1.-smoothstep(.310,.334,p.x);
    float seam_active=seam_side*seam_fore*valid;
    // Use the same native surface-distance donor through the lateral join,
    // instead of mixing stretched top-atlas pixels into that band.
    dorsal=mix(dorsal,native_color153,seam_active);
    float flank=smoothstep(-.32,-.08,height)*seam_active*(1.-protected);
    top=max(top,flank);
    // Current pectoral roots occupy x .11..25 and y approximately -.035.
    // Carry blue body skin to those roots, with a bounded transition to the belly.
    float root_x=smoothstep(.09,.125,p.x)*(1.-smoothstep(.235,.275,p.x));
    float root_h=smoothstep(-.70,-.40,height)*(1.-smoothstep(.10,.35,height));
    float root_side=smoothstep(.60,.85,abs(n.z));
    float root_join=root_x*root_h*root_side;
    top=max(top,root_join*(1.-protected));
    bottom*=1.-.92*root_join;
    base=mix(base,dorsal,top);
    // A protected gill must retain its native side pixels, not the older chart112
    // grain which has already modified the incoming base on oblique normals.
    float native_gill=gill*max(smoothstep(-.45,-.20,height),smoothstep(.705,.720,native_uv.x))*seam_side;
    float head_join=smoothstep(.300,.330,p.x)*(1.-smoothstep(.365,.375,p.x));
    head_join*=smoothstep(.45,.80,abs(n.z))*seam_side*(1.-eye*eye_side);
    base=mix(base,skin_sample(native_uv).rgb,max(native_gill,head_join));
    """
    code=code.replace(marker,replacement)
    assert(code.get_slice("void vertex()",1)==source.shader.code.get_slice("void vertex()",1))
    var shader=Shader.new();shader.code=code;material.shader=shader
    var preserved=[]
    for u in source.shader.get_shader_uniform_list():
        var a=source.get_shader_parameter(u.name);var b=material.get_shader_parameter(u.name)
        if a is Texture2D:assert(a.get_image().get_data()==b.get_image().get_data())
        else:assert(a==b)
        preserved.append(u.name)
    candidate.surface_set_material(0,material)
    for si in original.get_surface_count():
        assert(digest(original.surface_get_arrays(si))==digest(candidate.surface_get_arrays(si)))
        assert(digest(original.get("_surfaces")[si].get("lods",[]))==digest(candidate.get("_surfaces")[si].get("lods",[])))
    DirAccess.make_dir_recursive_absolute(plan.output)
    assert(ResourceSaver.save(candidate,plan.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var f=FileAccess.open(plan.output+"/material.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"candidate_sha256":FileAccess.get_sha256(plan.output+"/body.res"),"source_body_sha256":plan.source_body_sha256,"all_uniforms_preserved":preserved,"geometry_uv_weights_lods_unchanged":true,"vertex_fragment_entry_unchanged":true,"scope":"RGB seam candidate; visual/physical final gates separate."},"  "));f.close();print("SEAM_CANDIDATE_SAVED");quit()
