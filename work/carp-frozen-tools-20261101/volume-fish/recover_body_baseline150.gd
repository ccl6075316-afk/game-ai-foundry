extends SceneTree
## Recover a pre-RGB portable baseline, proving shader identity and exact arrays.
func _initialize():
    var args=OS.get_cmdline_user_args();var p=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var source=load(p.current_resource) as ArrayMesh;assert(source!=null)
    var baseline=source.duplicate(true) as ArrayMesh;var receipt=JSON.parse_string(FileAccess.get_file_as_string(p.baseline_capture));var records=[]
    for si in source.get_surface_count():
        var before=source.surface_get_material(si) as ShaderMaterial;assert(before!=null);var material=before.duplicate() as ShaderMaterial;var code:String=before.shader.code
        if si==0:
            var uniforms="\nuniform sampler2D pectoral142_source : source_color,filter_nearest,repeat_disable;\nuniform sampler2D pectoral142_mask : filter_nearest,repeat_disable;\n"
            var addition="\n// Body-owned source attachment mark, after existing fin cleaning and head charts.\nALBEDO=mix(ALBEDO,texture(pectoral142_source,UV).rgb,texture(pectoral142_mask,UV).r);\n"
            assert(code.count(uniforms)==1 and code.count(addition)==1,"Unknown source-body wrapper")
            code=code.replace(uniforms,"").replace(addition,"")
            var proved=false
            for row in receipt.dynamic_body_shaders:
                if row.species=="carp"and row.generated_shader_sha256==code.sha256_text():proved=true
            assert(proved,"Recovered baseline does not match passed077 shader")
        var shader=Shader.new();shader.code=code;material.shader=shader
        for uniform in shader.get_shader_uniform_list():
            var value=before.get_shader_parameter(uniform.name)
            if value is Texture2D:
                var im=value.get_image().duplicate()
                if im.is_compressed():assert(im.decompress()==OK)
                material.set_shader_parameter(uniform.name,ImageTexture.create_from_image(im))
            else:material.set_shader_parameter(uniform.name,value)
        baseline.surface_set_material(si,material);records.append({"surface":si,"recovered_shader_sha256":code.sha256_text()})
    assert(ResourceSaver.save(baseline,p.output,ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var cold=ResourceLoader.load(p.output,"ArrayMesh",ResourceLoader.CACHE_MODE_IGNORE) as ArrayMesh;assert(cold!=null)
    for si in source.get_surface_count():
        var a=source.surface_get_arrays(si);var b=cold.surface_get_arrays(si)
        for field in Mesh.ARRAY_MAX:assert(a[field]==b[field],"Recovered body arrays differ")
        var expected=baseline.surface_get_material(si) as ShaderMaterial;var actual=cold.surface_get_material(si) as ShaderMaterial;assert(actual.shader.code==expected.shader.code)
        for uniform in expected.shader.get_shader_uniform_list():
            var x=expected.get_shader_parameter(uniform.name);var y=actual.get_shader_parameter(uniform.name)
            if x is Texture2D:assert(y is Texture2D and x.get_image().get_format()==y.get_image().get_format() and x.get_image().get_data()==y.get_image().get_data(),"Portable native data changed")
            else:assert(x==y)
    var f=FileAccess.open(p.output.get_base_dir().path_join("recovery.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"scope":p.scope,"current_resource_sha256":FileAccess.get_sha256(p.current_resource),"derived_baseline_sha256":FileAccess.get_sha256(p.output),"original_binary_hash_not_claimed":true,"all_arrays_unchanged":true,"all_raw_texture_formats_and_bytes_unchanged":true,"cold_loaded":true,"records":records}));f.close();print("BODY_BASELINE150_RECOVERED");quit()
