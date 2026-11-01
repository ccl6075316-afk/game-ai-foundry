extends SceneTree
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func digest(value)->String:
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(value));return h.finish().hex_encode()
func _initialize():
    var args=OS.get_cmdline_user_args()
    var plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
    assert(FileAccess.get_sha256(plan.source_body)==plan.source_body_sha256)
    assert(FileAccess.get_sha256(plan.arc_lut)==plan.arc_lut_sha256)
    var original=load(plan.source_body) as ArrayMesh
    var candidate=original.duplicate() as ArrayMesh
    var source=original.surface_get_material(0) as ShaderMaterial
    assert(abs(source.get_shader_parameter("skin153_head_keep").y-float(plan.active_max_x))<1e-7)
    assert(source.get_shader_parameter("skin153_arc_x")==Vector2(plan.arc_x[0],plan.arc_x[1]))
    var material=PORTABLE.freeze(source) as ShaderMaterial
    var lut=Image.create_from_data(plan.size[0],plan.size[1],false,Image.FORMAT_RF,FileAccess.get_file_as_bytes(plan.arc_lut))
    material.set_shader_parameter("skin153_arc",ImageTexture.create_from_image(lut))
    assert(material.shader.code==source.shader.code)
    var preserved=[]
    for u in source.shader.get_shader_uniform_list():
        if u.name=="skin153_arc":continue
        var before=source.get_shader_parameter(u.name);var after=material.get_shader_parameter(u.name)
        if before is Texture2D:
            assert(before.get_image().get_data()==after.get_image().get_data())
            assert(before.get_image().get_format()==after.get_image().get_format())
        else:assert(before==after)
        preserved.append(u.name)
    candidate.surface_set_material(0,material)
    for si in original.get_surface_count():
        assert(digest(original.surface_get_arrays(si))==digest(candidate.surface_get_arrays(si)))
        assert(digest(original.get("_surfaces")[si].get("lods",[]))==digest(candidate.get("_surfaces")[si].get("lods",[])))
    DirAccess.make_dir_recursive_absolute(plan.output)
    assert(ResourceSaver.save(candidate,plan.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var f=FileAccess.open(plan.output+"/material.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"source_sha256":plan.source_body_sha256,"candidate_sha256":FileAccess.get_sha256(plan.output+"/body.res"),"arc_sha256":plan.arc_lut_sha256,"shader_unchanged":true,"preserved_uniforms":preserved,"arrays_and_lods_unchanged":true,"scope":"Only skin153_arc float pixels changed. Native RGB, original shader, every other uniform, mesh/UV/weights/LOD preserved. Candidate requiring GPU/visual and final fish gates."},"  "));f.close()
    print("METRIC_BOUND");quit()
