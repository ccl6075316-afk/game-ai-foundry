extends SceneTree
func _initialize():
    var args=OS.get_cmdline_user_args();var plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var old=load(plan.source_resource) as ArrayMesh;var current=load(plan.output) as ArrayMesh;var uniforms=0
    assert(old.get_surface_count()==current.get_surface_count())
    for si in old.get_surface_count():
        var a=old.surface_get_arrays(si);var b=current.surface_get_arrays(si)
        for field in Mesh.ARRAY_MAX:assert(a[field]==b[field],"Geometry stream changed")
        assert(RenderingServer.mesh_get_surface(old.get_rid(),si).get("lods",[])==RenderingServer.mesh_get_surface(current.get_rid(),si).get("lods",[]),"Actual body LOD indices/distances changed")
        var original=old.surface_get_material(si);var modified=current.surface_get_material(si)
        assert(original.get_class()==modified.get_class(),"Material type changed")
        if original is StandardMaterial3D:
            assert(si>0,"Expected skin shader on surface0")
            for property in original.get_property_list():
                var name=String(property.name)
                if not(int(property.usage)&PROPERTY_USAGE_STORAGE)or name.begins_with("resource_")or name=="script":continue
                var x=original.get(name);var y=modified.get(name)
                if x is Texture2D:assert(y is Texture2D and x.get_size()==y.get_size()and x.get_image().get_data()==y.get_image().get_data(),"Standard material texture changed")
                else:assert(x==y,"Standard material property changed: "+name)
                uniforms+=1
            continue
        var before=original as ShaderMaterial;var after=modified as ShaderMaterial;assert(before!=null and after!=null)
        if si>0:assert(before.shader.code==after.shader.code)
        for row in before.shader.get_shader_uniform_list():
            var x=before.get_shader_parameter(row.name);var y=after.get_shader_parameter(row.name)
            if x is Texture2D:
                assert(y is Texture2D);var xi=x.get_image();var yi=y.get_image();assert(xi.get_size()==yi.get_size() and xi.get_format()==yi.get_format() and xi.get_data()==yi.get_data(),"Old texture changed "+row.name)
            else:assert(x==y,"Old uniform changed "+row.name)
            uniforms+=1
    var mat=current.surface_get_material(0) as ShaderMaterial
    for key in ["source","mask"]:
        var actual=(mat.get_shader_parameter("pectoral142_"+key) as Texture2D).get_image();var expected=Image.load_from_file(plan[key]);assert(actual.get_size()==expected.get_size() and actual.get_data()==expected.get_data())
    assert(mat.shader.code.contains("ALBEDO=mix(ALBEDO,texture(pectoral142_source,UV).rgb,texture(pectoral142_mask,UV).r);"))
    var f=FileAccess.open(args[1],FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"all_body_arrays_exact":true,"all_body_lods_exact":true,"original_uniforms_and_textures_exact":uniforms,"new_native_source_and_mask_exact":true,"resource_sha256":FileAccess.get_sha256(plan.output),"input_plan_sha256":FileAccess.get_sha256(args[0]),"scope":"Only additional RGB mask restoration on original opaque body material. All prior surface arrays/LOD indices/distances/uniforms/native images retained."}));f.close();quit()
