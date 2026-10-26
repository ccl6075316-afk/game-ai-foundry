extends SceneTree
const PORTABLE=preload("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd")
func digest(value)->String:
    var h=HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(value));return h.finish().hex_encode()
func _initialize():
    var args=OS.get_cmdline_user_args()
    var plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]))
    var path_base=args[0].get_base_dir().path_join(plan.get("path_base",".")).simplify_path()
    for key in ["source","output"]:
        if not String(plan[key]).is_absolute_path() and not String(plan[key]).begins_with("res://"):
            plan[key]=path_base.path_join(plan[key]).simplify_path()
    assert(FileAccess.get_sha256(plan.source)==plan.source_sha256)
    var original=load(plan.source) as ArrayMesh
    var candidate=original.duplicate() as ArrayMesh
    var material=original.surface_get_material(0).duplicate() as ShaderMaterial
    var code:String=material.shader.code
    var old="vec2 texcoord153=vec2((p.x-skin153_origin_x)/skin153_extent.x,.5+arc/skin153_extent.y);"
    assert(code.count(old)==1)
    var arc_image:Image=material.get_shader_parameter("skin153_arc").get_image()
    var size:int=arc_image.get_width()
    var field=Image.create(size,arc_image.get_height(),false,Image.FORMAT_RGBF)
    var positions=plan.scale_knots
    var arc_range:Vector2=material.get_shader_parameter("skin153_arc_x")
    var lo:float=arc_range.x;var hi:float=arc_range.y
    var phase:float=plan.phase;var previous=0.
    var scales=[]
    for i in size:
        var x=lerpf(lo,hi,float(i)/(size-1))
        var j=0
        while j<positions.size()-2 and x>positions[j+1][0]:j+=1
        var t=smoothstep(float(positions[j][0]),float(positions[j+1][0]),x)
        var scale=lerpf(float(positions[j][1]),float(positions[j+1][1]),t)
        assert(scale>.1)
        if i>0:phase+=(hi-lo)/(size-1)/float(plan.extent_x)*.5*(1./scale+1./previous)
        for y in arc_image.get_height():field.set_pixel(i,y,Color(arc_image.get_pixel(i,y).r,phase,scale))
        previous=scale;scales.append(scale)
    # Pack controls beside the unchanged arc field: Compatibility allows only 16 samplers.
    code=code.replace("uniform sampler2D skin153_flat", "uniform float dorsal_extent_y;\nuniform sampler2D skin153_flat")
    code=code.replace("float arc=texture(skin153_arc,lookup).r;","vec3 scale_field=texture(skin153_arc,lookup).rgb;\n    float arc=scale_field.r;")
    code=code.replace(old,"vec2 texcoord153=vec2(fract(scale_field.g),.5+arc/(dorsal_extent_y*scale_field.b));")
    var shader=Shader.new();shader.code=code;assert(not shader.get_shader_uniform_list().is_empty())
    material.shader=shader
    material.set_shader_parameter("skin153_arc",ImageTexture.create_from_image(field))
    material.set_shader_parameter("dorsal_extent_y",float(plan.extent_x)*.5)
    candidate.surface_set_material(0,PORTABLE.freeze(material))
    for si in original.get_surface_count():
        assert(digest(original.surface_get_arrays(si))==digest(candidate.surface_get_arrays(si)))
    DirAccess.make_dir_recursive_absolute(plan.output)
    assert(ResourceSaver.save(candidate,plan.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var f=FileAccess.open(plan.output+"/material.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"source":plan.source,"source_sha256":plan.source_sha256,"candidate_sha256":FileAccess.get_sha256(plan.output+"/body.res"),"recipe_sha256":FileAccess.get_sha256(args[0]),"scope":"Local material candidate: native source RGB retained; complete 1152px ordered field repeats longitudinally, no small-patch quilting. All mesh arrays preserved. Taper controls are art choices, not measured anatomy. GPU/visual and final gates pending."},"  "));f.close()
    print("CANDIDATE_SAVED");quit()
