extends SceneTree
## Restore a source-painted attachment mark on skin; never change fin or body arrays.
func _initialize():
    var plan=JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[0]));assert(FileAccess.get_sha256(plan.source_resource)==plan.source_resource_sha256)
    var original=load(plan.source_resource) as ArrayMesh;var mesh=original.duplicate() as ArrayMesh;var mat=original.surface_get_material(0).duplicate() as ShaderMaterial;assert(mat!=null)
    var code:String=mat.shader.code;assert(not code.contains("pectoral142_mask"));var shader=Shader.new()
    code=code.replace("shader_type spatial;","shader_type spatial;\nuniform sampler2D pectoral142_source : source_color,filter_nearest,repeat_disable;\nuniform sampler2D pectoral142_mask : filter_nearest,repeat_disable;\n")
    var factor="texture(pectoral142_mask,UV).r";var gated=false
    if plan.has("spatial_xy_bounds_native"):
        assert(code.contains("varying vec3 rest114_position;"),"Immutable rest coordinates required for anatomical RGB ownership");var box:Array=plan.spatial_xy_bounds_native;assert(box.size()==4 and box[0]<box[2]and box[1]<box[3]);var function="float pectoral143_owner(){return step(%.9f,rest114_position.x)*step(rest114_position.x,%.9f)*step(%.9f,rest114_position.y)*step(rest114_position.y,%.9f);}\n"%[box[0],box[2],box[1],box[3]];code=code.replace("void fragment()",function+"void fragment()");gated=true
    var assignment="ALBEDO=mix(ALBEDO,texture(pectoral142_source,UV).rgb,"+factor+");"
    if gated:assignment="if(pectoral143_owner()>.5){"+assignment+"}"
    var end=code.rfind("}");assert(end>code.find("void fragment()"));code=code.substr(0,end)+"\n// Body-owned source attachment mark, after existing fin cleaning and head charts.\n"+assignment+"\n"+code.substr(end);shader.code=code;mat.shader=shader
    for key in ["source","mask"]:
        assert(FileAccess.get_sha256(plan[key])==plan[key+"_sha256"]);var image=Image.load_from_file(plan[key]);assert(image!=null);mat.set_shader_parameter("pectoral142_"+key,ImageTexture.create_from_image(image))
    mesh.surface_set_material(0,mat);DirAccess.make_dir_recursive_absolute(plan.output.get_base_dir());assert(ResourceSaver.save(mesh,plan.output,ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var cold=ResourceLoader.load(plan.output,"ArrayMesh",ResourceLoader.CACHE_MODE_IGNORE) as ArrayMesh
    for si in original.get_surface_count():
        var before=original.surface_get_arrays(si);var after=cold.surface_get_arrays(si)
        for field in Mesh.ARRAY_MAX:assert(before[field]==after[field],"Geometry/UV/skin changed")
    var f=FileAccess.open(plan.output.get_base_dir().path_join("resource.validation.json"),FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"source_resource_sha256":plan.source_resource_sha256,"path":plan.output,"sha256":FileAccess.get_sha256(plan.output),"all_body_arrays_cold_reload_exact":true,"scope":"Surface0 RGB-only source attachment restoration on body. Geometry/UV/normals/skin/indices, other material surfaces and all fins preserved. No opacity change."}));f.close();quit()
