extends RefCounted
## Prototype material transport. No production configuration or acceptance edits.
var texture_cache:Dictionary={}
func freeze(source:Material) -> Material:
    if not source is ShaderMaterial:
        var copy=source.duplicate()
        if copy is StandardMaterial3D and copy.albedo_texture:copy.albedo_texture=texture_copy(copy.albedo_texture)
        return copy
    var result=ShaderMaterial.new();result.shader=Shader.new();result.shader.code=source.shader.code;result.render_priority=source.render_priority
    for u in source.shader.get_shader_uniform_list():
        var value=source.get_shader_parameter(u.name)
        if value==null:continue
        result.set_shader_parameter(u.name,texture_copy(value) if value is Texture2D else value)
    return result
func texture_copy(source:Texture2D) -> Texture2D:
    var id=source.get_instance_id()
    if not texture_cache.has(id):
        var image=source.get_image().duplicate();assert(image!=null)
        if image.is_compressed():assert(image.decompress()==OK)
        if image.has_mipmaps():image.clear_mipmaps()
        texture_cache[id]=ImageTexture.create_from_image(image)
    return texture_cache[id]
func transport_table(source:Texture2D,part:Dictionary,stride:int,uv_table:bool=false) -> ImageTexture:
    var old=source.get_image();assert(old!=null and old.get_format()==Image.FORMAT_RGBAF)
    var image=Image.create(256,ceili(float(part.positions.size()*stride)/256),false,Image.FORMAT_RGBAF)
    for i in part.references.size():
        var refs=part.references[i]
        for record in stride:
            var value=Color(0,0,0,0)
            for j in 3:
                var at=int(refs[0][j])*stride+record
                assert(at>=0 and at<old.get_width()*old.get_height())
                value+=old.get_pixel(at%old.get_width(),at/old.get_width())*float(refs[1][j])
            if uv_table:value=Color(part.uv[i][0],part.uv[i][1],0,1)
            var at=i*stride+record;image.set_pixel(at%256,at/256,value)
    return ImageTexture.create_from_image(image)
func material(source:Material,part:Dictionary) -> Material:
    var result=freeze(source)
    if not result is ShaderMaterial:return result
    var shader=result.shader.code
    if shader.contains("VERTEX_ID"):
        assert(shader.contains("rest114_index") or shader.contains("material130_count"),"Unimplemented vertex-ID transport")
    var groups=[
        {"textures":["rest114_positions","rest114_normals","rest114_uvs"],"size":"rest114_size","count":"rest114_count","stride":1},
        {"textures":["eye_rest_lookup","eye_uv_lookup"],"size":"eye_lookup_size","count":"eye_vertex_count","stride":1},
        {"textures":["mouth136_records"],"size":"mouth136_size","count":"","stride":int(source.get_shader_parameter("mouth136_stride")) if source.get_shader_parameter("mouth136_stride")!=null else 1},
        {"textures":["material130_positions"],"size":"material130_size","count":"material130_count","stride":1}]
    for group in groups:
        var active=false
        for key in group.textures:
            var texture=source.get_shader_parameter(key)
            if not texture is Texture2D:continue
            active=true
            var transported=transport_table(texture,part,group.stride,key in ["rest114_uvs","eye_uv_lookup"])
            result.set_shader_parameter(key,transported)
        if active:
            var size=Vector2i(256,ceili(float(part.positions.size()*group.stride)/256))
            result.set_shader_parameter(group.size,Vector2(size) if group.size=="eye_lookup_size" else size)
            if group.count!="":result.set_shader_parameter(group.count,part.positions.size())
    return result
func arrays(part:Dictionary) -> Array:
    var a=[];a.resize(Mesh.ARRAY_MAX)
    var vertices=PackedVector3Array();var normals=PackedVector3Array();var uv=PackedVector2Array();var uv2=PackedVector2Array();var colors=PackedColorArray();var bones=PackedInt32Array();var weights=PackedFloat32Array()
    for row in part.positions:vertices.append(Vector3(row[0],row[1],row[2]))
    for row in part.normals:normals.append(Vector3(row[0],row[1],row[2]))
    for row in part.uv:uv.append(Vector2(row[0],row[1]))
    for row in part.uv2:uv2.append(Vector2(row[0],row[1]))
    for row in part.colors:colors.append(Color(row[0],row[1],row[2],row[3]))
    for row in part.bones:
        for value in row:bones.append(int(value))
    for row in part.weights:
        for value in row:weights.append(float(value))
    a[Mesh.ARRAY_VERTEX]=vertices;a[Mesh.ARRAY_NORMAL]=normals;a[Mesh.ARRAY_TEX_UV]=uv;a[Mesh.ARRAY_BONES]=bones;a[Mesh.ARRAY_WEIGHTS]=weights;a[Mesh.ARRAY_INDEX]=PackedInt32Array(part.indices)
    if not uv2.is_empty():a[Mesh.ARRAY_TEX_UV2]=uv2
    if not colors.is_empty():a[Mesh.ARRAY_COLOR]=colors
    return a
func apply(model:Node3D,data:Dictionary) -> int:
    var total=0
    for row in data.nodes:
        var target=model.get_node(row.path) as MeshInstance3D;assert(target!=null and target.skin!=null)
        var mesh=ArrayMesh.new()
        for part in row.surfaces:
            assert(not part.indices.is_empty(),"Budget deleted a required surface")
            mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays(part))
            mesh.surface_set_material(mesh.get_surface_count()-1,material(target.get_active_material(int(part.surface)),part))
            total+=part.indices.size()/3
        target.mesh=mesh
        for si in mesh.get_surface_count():target.set_surface_override_material(si,null)
    assert(total==int(data.actual_triangles));return total
