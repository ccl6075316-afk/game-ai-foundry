extends RefCounted
func template_path()->String:return get_script().resource_path.get_base_dir()+"/LipMaterial115.gdshaderinc"
func wrap(code:String)->String:
    assert(code.count("ALBEDO=chart112_color(color.rgb);")==1 and code.contains("rest114_position") and not code.contains("vec3 lip115_color("))
    # rest114 declarations must precede this fragment-only helper.
    code=code.replace("void vertex()",FileAccess.get_file_as_string(template_path())+"\nvoid vertex()")
    return code.replace("ALBEDO=chart112_color(color.rgb);","ALBEDO=lip115_color(color.rgb,chart112_color(color.rgb));")
func bind(material:ShaderMaterial,p:Dictionary)->void:
    var spec:Dictionary=p.mouth_protection115;var curve=PackedVector3Array()
    for row in spec.curve_native:curve.append(Vector3(row[0],row[1],row[2]))
    assert(curve.size()>1 and curve.size()<=32)
    material.set_shader_parameter("lip115_count",curve.size());curve.resize(32);material.set_shader_parameter("lip115_curve",curve)
    material.set_shader_parameter("lip115_pixel",1./float(p.source_size[0]));material.set_shader_parameter("lip115_margin_pixels",Vector2(spec.margin_pixels[0],spec.margin_pixels[1]))
    material.set_shader_parameter("lip115_lower_margin_pixels",Vector2(spec.lower_margin_pixels[0],spec.lower_margin_pixels[1]))
func validate(material:ShaderMaterial,p:Dictionary)->void:
    var spec:Dictionary=p.mouth_protection115
    assert(int(material.get_shader_parameter("lip115_count"))==spec.curve_native.size())
    var curve:PackedVector3Array=material.get_shader_parameter("lip115_curve")
    for i in spec.curve_native.size():
        var row:Array=spec.curve_native[i];assert(curve[i].is_equal_approx(Vector3(row[0],row[1],row[2])))
    assert(is_equal_approx(material.get_shader_parameter("lip115_pixel"),1./float(p.source_size[0])))
    assert(material.get_shader_parameter("lip115_margin_pixels").is_equal_approx(Vector2(spec.margin_pixels[0],spec.margin_pixels[1])))
    assert(material.get_shader_parameter("lip115_lower_margin_pixels").is_equal_approx(Vector2(spec.lower_margin_pixels[0],spec.lower_margin_pixels[1])))
