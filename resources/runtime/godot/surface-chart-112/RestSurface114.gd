extends RefCounted
## Tables use the actual imported surface vertex order, never GLB accessor order.
const WIDTH=256
const PREFIX="""
    // rest114_vertex_begin
    int rest114_index=clamp(VERTEX_ID,0,rest114_count-1);
    ivec2 rest114_at=ivec2(rest114_index%rest114_size.x,rest114_index/rest114_size.x);
    vec4 rest114_p=texelFetch(rest114_positions,rest114_at,0);
    vec4 rest114_n=texelFetch(rest114_normals,rest114_at,0);
    vec4 rest114_uv=texelFetch(rest114_uvs,rest114_at,0);
    rest114_position=rest114_p.xyz;rest114_normal=rest114_n.xyz;
    rest114_error=(VERTEX_ID>=rest114_count||rest114_p.w<.5||rest114_n.w<.5||rest114_uv.w<.5||any(greaterThan(abs(UV-rest114_uv.xy),vec2(.000001))))?1.:0.;
    // rest114_vertex_end
"""
const GUARD="\nif(rest114_error>.001){ALBEDO=vec3(1.,0.,1.);}\n"
func digest(value:Variant)->String:
    var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(value if value is PackedByteArray else var_to_bytes(value));return ctx.finish().hex_encode()
func template_path()->String:return get_script().resource_path.get_base_dir()+"/RestSurface114.gdshaderinc"
func wrap_chart(code:String)->String:
    assert(code.count("chart112_rest_position=VERTEX;chart112_rest_normal=NORMAL;")==1)
    code=code.replace("chart112_rest_position=VERTEX;chart112_rest_normal=NORMAL;","chart112_rest_position=rest114_position;chart112_rest_normal=rest114_normal;")
    assert(not code.contains("rest114_vertex_begin"))
    code=code.replace("void vertex()",FileAccess.get_file_as_string(template_path())+"\nvoid vertex()")
    var parser=load("res://scripts/aquarium/FishEyeOwnership.gd").new()
    var vertex:Dictionary=parser._stage_braces(code,"vertex");assert(vertex.size()>0)
    code=code.insert(vertex.open,PREFIX)
    var fragment:Dictionary=parser._stage_braces(code,"fragment");assert(fragment.size()>0)
    return code.insert(fragment.close,GUARD)
func tables(mesh:MeshInstance3D,surface:int)->Dictionary:
    var a:Array=mesh.mesh.surface_get_arrays(surface)
    var p:PackedVector3Array=a[Mesh.ARRAY_VERTEX];var n:PackedVector3Array=a[Mesh.ARRAY_NORMAL];var uv:PackedVector2Array=a[Mesh.ARRAY_TEX_UV]
    assert(not p.is_empty() and n.size()==p.size() and uv.size()==p.size())
    var height=ceili(float(p.size())/WIDTH);var result:Dictionary={"count":p.size(),"size":Vector2i(WIDTH,height)}
    for key in ["positions","normals","uvs"]:
        var image=Image.create(WIDTH,height,false,Image.FORMAT_RGBAF)
        for i in p.size():
            var v:Color
            if key=="positions":v=Color(p[i].x,p[i].y,p[i].z,1.)
            elif key=="normals":v=Color(n[i].x,n[i].y,n[i].z,1.)
            else:v=Color(uv[i].x,uv[i].y,0.,1.)
            image.set_pixel(i%WIDTH,i/WIDTH,v)
        result[key]=image
    return result
func snapshot(mesh:MeshInstance3D)->Dictionary:
    var a:Array=[];var lods:Array=[]
    for si in mesh.mesh.get_surface_count():
        a.append(mesh.mesh.surface_get_arrays(si))
        lods.append(mesh.mesh.get("_surfaces")[si].get("lods",[]))
    return {"all_surface_arrays_sha256":digest(a),"lods_sha256":digest(lods)}
func bind(model:Node3D,mesh:MeshInstance3D,surface:int,material:ShaderMaterial)->void:
    var t=tables(mesh,surface)
    material.set_shader_parameter("rest114_count",t.count);material.set_shader_parameter("rest114_size",t.size)
    var hashes:Dictionary={}
    for key in ["positions","normals","uvs"]:
        material.set_shader_parameter("rest114_"+key,ImageTexture.create_from_image(t[key]));hashes[key]=digest(t[key].get_data())
    var receipt=snapshot(mesh)
    receipt.merge({"mesh":str(mesh.name),"surface":surface,"model_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(model.scene_file_path),"helper_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(get_script().resource_path),"template_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(template_path()),"tables_sha256":hashes,"count":t.count,"size":[t.size.x,t.size.y]})
    var records:Dictionary=model.get_meta("rest_surface114_receipts",{});records[str(mesh.name)+":"+str(surface)]=receipt;model.set_meta("rest_surface114_receipts",records)
func validate(model:Node3D,mesh:MeshInstance3D,surface:int,material:ShaderMaterial)->Dictionary:
    var records:Dictionary=model.get_meta("rest_surface114_receipts",{});var key=str(mesh.name)+":"+str(surface);assert(records.has(key));var r:Dictionary=records[key]
    assert(r.model_sha256==preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(model.scene_file_path) and r.helper_sha256==preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(get_script().resource_path) and r.template_sha256==preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(template_path()))
    var actual=snapshot(mesh);assert(r.all_surface_arrays_sha256==actual.all_surface_arrays_sha256 and r.lods_sha256==actual.lods_sha256)
    var t=tables(mesh,surface);assert(int(material.get_shader_parameter("rest114_count"))==t.count and material.get_shader_parameter("rest114_size")==t.size and r.count==t.count and r.size==[t.size.x,t.size.y])
    for name in ["positions","normals","uvs"]:
        var texture=material.get_shader_parameter("rest114_"+name) as Texture2D;assert(texture!=null)
        var image=texture.get_image();assert(image!=null and image.get_format()==Image.FORMAT_RGBAF and not image.has_mipmaps() and image.get_size()==t.size)
        assert(image.get_data()==t[name].get_data() and digest(image.get_data())==r.tables_sha256[name],"114 actual LUT differs from current imported attributes")
    return r
