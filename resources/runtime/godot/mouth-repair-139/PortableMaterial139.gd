extends RefCounted
## Freeze base-level texture pixels instead of import-cache-specific handles.
static func texture_copy(texture:Texture2D)->ImageTexture:
    var image=texture.get_image();assert(image!=null)
    image=image.duplicate()
    if image.is_compressed():assert(image.decompress()==OK)
    if image.has_mipmaps():image.clear_mipmaps()
    return ImageTexture.create_from_image(image)
static func freeze(material:Material)->Material:
    if material is ShaderMaterial:
        var shader=Shader.new();shader.code=material.shader.code
        var frozen=ShaderMaterial.new();frozen.shader=shader;frozen.resource_name=material.resource_name
        frozen.render_priority=material.render_priority
        for row in material.shader.get_shader_uniform_list():
            var value=material.get_shader_parameter(row.name)
            if value==null:continue
            frozen.set_shader_parameter(row.name,texture_copy(value) if value is Texture2D else value)
        return frozen
    var frozen=material.duplicate()
    if frozen is StandardMaterial3D and frozen.albedo_texture!=null:frozen.albedo_texture=texture_copy(frozen.albedo_texture)
    return frozen
