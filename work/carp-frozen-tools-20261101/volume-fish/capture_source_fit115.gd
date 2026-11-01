extends "./capture_surface_mouth_audit.gd"
func region(entry:Dictionary)->Dictionary:
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(OS.get_cmdline_user_args()[1]))
    var r:Dictionary=cfg.regions[entry.species]
    var body=AABB(Vector3(r.body[0],r.body[1],r.body[2]),Vector3(r.body[3],r.body[4],r.body[5]))
    var head=AABB(Vector3(r.head[0],r.head[1],r.head[2]),Vector3(r.head[3],r.head[4],r.head[5]))
    var ext:Vector3=head.size*entry.model.global_transform.basis.get_scale()
    return {"body":body,"head":head,"extent_m":maxf(ext.x,maxf(ext.y,ext.z))}
func _initialize():
    var args=OS.get_cmdline_user_args();out=args[0];requested=["black_seabream","zander"];call_deferred("run")
func unlit(material:Material)->Material:
    var copy:Material=material.duplicate()
    if copy is ShaderMaterial:
        var key:String=material.shader.code.sha256_text()
        if not shaders.has(key):
            var shader=Shader.new();var code:String=material.shader.code.replace("render_mode","render_mode unshaded,")
            code=code.replace("#include \"RestSurface114.gdshaderinc\"",FileAccess.get_file_as_string("res://scripts/aquarium/RestSurface114.gdshaderinc"))
            shader.code=code;shaders[key]=shader
        copy.shader=shaders[key]
    elif copy is StandardMaterial3D:copy.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    return copy
