extends RefCounted
const CONFIG="res://assets/models/fish/motion/front-skin112.json"
func apply(model:Node3D,species:String)->int:
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(CONFIG))
    if not cfg.profiles.has(species):return 0
    var p:Dictionary=cfg.profiles[species];assert(FileAccess.get_sha256(model.scene_file_path)==p.model_sha256)
    var primary=model.find_child(p.primary_mesh,true,false) as MeshInstance3D;var source=(primary.get_active_material(0) as ShaderMaterial).get_shader_parameter("source_texture") as Texture2D
    assert(source!=null and FileAccess.get_sha256(p.source.path)==p.source.sha256)
    var native_image=Image.new();assert(native_image.load_png_from_buffer(FileAccess.get_file_as_bytes(p.source.path))==OK)
    source=ImageTexture.create_from_image(native_image) # Exact original PNG texels; no importer alpha-border RGB rewrite.
    var template_path="res://scripts/aquarium/FrontSkin112.gdshaderinc";var template=FileAccess.get_file_as_string(template_path);var records:Dictionary={}
    for target in p.targets:
        var mesh=model.find_child(target.mesh,true,false) as MeshInstance3D;assert(mesh!=null)
        for si in target.surfaces:
            var original=mesh.get_active_material(int(si)) as ShaderMaterial;assert(original!=null)
            var base:String=original.shader.code;var assignment="ALBEDO=chart112_color(color.rgb);" if base.contains("chart112_color") else "ALBEDO=color.rgb;"
            assert(base.count(assignment)==1 and base.count("void vertex()")==1)
            var code=base.replace("void vertex()",template+"\nvoid vertex()")
            if target.get("immutable_rest114",false):
                var marker="// rest114_vertex_end";assert(code.count(marker)==1,"Immutable front colour requires an already bound114 surface")
                code=code.replace(marker,marker+"\nfront112_rest=rest114_position;front112_normal=rest114_normal;")
            else:code=code.insert(code.find("{",code.find("void vertex()"))+1,"front112_rest=VERTEX;front112_normal=NORMAL;")
            code=code.replace(assignment,"ALBEDO=front112_color("+("chart112_color(color.rgb)" if base.contains("chart112_color") else "color.rgb")+");")
            var material=original.duplicate() as ShaderMaterial;var shader=Shader.new();shader.code=code;material.shader=shader
            material.set_shader_parameter("front112_source",source);material.set_shader_parameter("front112_source_size",Vector2(source.get_size()))
            material.set_shader_parameter("front112_x",Vector2(target.x[0],target.x[1]));material.set_shader_parameter("front112_y_split",p.y_split)
            material.set_shader_parameter("front112_half_width",target.half_width);material.set_shader_parameter("front112_pixel_per_native",p.pixel_per_native)
            for kind in ["upper","lower"]:
                var r:Array=p[kind];material.set_shader_parameter("front112_"+kind,Vector4(r[0],r[1],r[2],r[3]))
            mesh.set_surface_override_material(int(si),material)
            records[str(mesh.name)+":"+str(int(si))]={"model_sha256":p.model_sha256,"helper_sha256":FileAccess.get_sha256(get_script().resource_path),"template_sha256":FileAccess.get_sha256(template_path),"profile_sha256":FileAccess.get_sha256(CONFIG),"base_shader_code":base,"base_shader_path":original.shader.resource_path,"base_shader_sha256":base.sha256_text(),"generated_shader_sha256":code.sha256_text(),"assignment":assignment}
    model.set_meta("front_skin112_receipts",records);return records.size()
