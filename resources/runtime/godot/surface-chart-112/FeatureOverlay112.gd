extends RefCounted
const MODEL_SHA="9d6d24c81dbe7318451c83cfc8378f4aa66cb8c16a81c2b56f22b0289af08319"
func apply(model:Node3D,species:String)->int:
    if species!="arapaima":return 0
    assert(FileAccess.get_sha256("res://assets/models/fish/arapaima.glb")==MODEL_SHA)
    var overlay=model.find_child("Frontal_head_overlay",true,false) as MeshInstance3D
    assert(overlay!=null and overlay.mesh.get_surface_count()==17)
    var records:Array=[]
    for surface in overlay.mesh.get_surface_count():
        var base=overlay.get_active_material(surface) as StandardMaterial3D
        assert(base!=null and base.albedo_texture!=null)
        var material=ShaderMaterial.new();material.shader=preload("res://scripts/aquarium/FeatureOverlay112.gdshader")
        material.set_shader_parameter("source_texture",base.albedo_texture);material.set_shader_parameter("tint",base.albedo_color)
        material.render_priority=base.render_priority
        overlay.set_surface_override_material(surface,material)
        records.append({"surface":surface,"source_size":base.albedo_texture.get_size(),"alpha":base.albedo_color.a})
    model.set_meta("feature_overlay112_receipt",{"model_sha256":MODEL_SHA,"surfaces":records,"body_changed":false,"gill_cover_untouched":true,"source_front_eyes_removed_from_decorative_overlay":true,"helper_sha256":FileAccess.get_sha256(get_script().resource_path)})
    return records.size()
