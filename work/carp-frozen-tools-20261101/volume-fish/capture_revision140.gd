extends "capture_mouth_delivery139.gd"
## Portable Shader resources have empty paths; cache unlit variants by code.
func unlit(material:Material)->Material:
    var copy:Material=material.duplicate()
    if copy is ShaderMaterial:
        var key=material.shader.code.sha256_text()
        if not shaders.has(key):
            var shader=Shader.new();var code:String=material.shader.code
            code=code.replace("render_mode","render_mode unshaded,") if code.contains("render_mode") else code.replace("shader_type spatial;","shader_type spatial;\nrender_mode unshaded;")
            shader.code=code;shaders[key]=shader
        copy.shader=shaders[key]
    elif copy is StandardMaterial3D:copy.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    return copy
