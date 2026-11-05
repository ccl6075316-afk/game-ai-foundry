extends "FishListViewer.gd"
## Synthetic materials and skinned triangle only; no fish loads or captures.
var test_case:="positive"

func run() -> void:
    var out:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):out=arg.trim_prefix("--output=")
        if arg.begins_with("--case="):test_case=arg.trim_prefix("--case=")
    if out.is_empty():quit(2);return
    DirAccess.make_dir_recursive_absolute(out)
    config={"output":out,"mode":"material_fixture","model_role":"synthetic fixture, no fish"}
    catalog={"bindings":{}}
    var original:=StandardMaterial3D.new()
    original.albedo_color=Color(0,0,0,.37)
    original.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
    original.alpha_scissor_threshold=.43
    original.emission_enabled=true
    original.emission=Color(.2,.4,.7,1.)
    original.emission_energy_multiplier=2.3
    original.texture_filter=BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
    var image:=Image.create(2,2,false,Image.FORMAT_RGBA8);image.fill(Color(.12,.34,.56,.78))
    original.emission_texture=ImageTexture.create_from_image(image)
    var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX]=PackedVector3Array([Vector3.ZERO,Vector3.RIGHT,Vector3.UP])
    arrays[Mesh.ARRAY_NORMAL]=PackedVector3Array([Vector3.BACK,Vector3.BACK,Vector3.BACK])
    arrays[Mesh.ARRAY_TEX_UV]=PackedVector2Array([Vector2.ZERO,Vector2.RIGHT,Vector2.UP])
    arrays[Mesh.ARRAY_BONES]=PackedInt32Array([0,0,0,0,0,0,0,0,0,0,0,0])
    arrays[Mesh.ARRAY_WEIGHTS]=PackedFloat32Array([1,0,0,0,1,0,0,0,1,0,0,0])
    var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);mesh.surface_set_material(0,original)
    var instance:=MeshInstance3D.new();instance.name="SyntheticEmissionOnly";instance.mesh=mesh
    var skin:=Skin.new();skin.add_bind(0,Transform3D(Basis.IDENTITY,Vector3(.1,.2,.3)));instance.skin=skin
    var rig:=Skeleton3D.new();rig.add_bone("FixtureBone");rig.set_bone_rest(0,Transform3D(Basis.IDENTITY,Vector3(.2,.3,.4)))
    root.add_child(rig);rig.add_child(instance);instance.skeleton=NodePath("..")
    meshes.append(instance)
    var before_arrays:=var_to_bytes(mesh.surface_get_arrays(0));var before_bind:=skin.get_bind_pose(0);var before_bone:=rig.get_bone_rest(0);var before_transform:=instance.transform
    if test_case.begins_with("bad-"):
        var bad: Variant
        match test_case:
            "bad-null":bad=null
            "bad-empty":bad={}
            "bad-filter":bad={"texture_filter":"linear"}
            "bad-type":bad={"texture_filter":1}
            "bad-extra":bad={"texture_filter":"nearest","script":"not-allowed.gd"}
            "bad-shader":
                bad={"texture_filter":"nearest"};instance.set_surface_override_material(0,ShaderMaterial.new())
            "bad-missing":
                bad={"texture_filter":"nearest"};mesh.surface_set_material(0,null)
            _:bad=[]
        config.engine_materials=bad
        # Exercise the production caller's explicit failure, receipt and exit.
        if _apply_engine_materials():
            _check("bad_config_must_not_pass",false);_finish()
        return
    _check("default_has_no_binding_field",not config.has("engine_materials"))
    _check("default_noop_success",_apply_engine_materials())
    _check("default_identity_and_filter_unchanged",instance.get_active_material(0)==original and instance.get_surface_override_material(0)==null and original.texture_filter==BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS)
    config.engine_materials={"texture_filter":"nearest"}
    _check("nearest_opt_in_success",_apply_engine_materials())
    var bound: BaseMaterial3D=instance.get_active_material(0)
    _check("material_cloned_and_nearest",bound!=original and bound.texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST and original.texture_filter==BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS)
    _check("all_stored_material_values_preserved",_same_material_except_filter(original,bound))
    _check("emission_only_texture_rgba_preserved",bound.albedo_color==original.albedo_color and bound.albedo_texture==null and bound.emission_enabled and bound.emission==original.emission and bound.emission_texture==original.emission_texture and bound.emission_texture.get_image().get_data()==image.get_data())
    _toggle_gray()
    _check("gray_uses_mesh_override",gray and instance.material_override!=null and instance.get_active_material(0)!=bound)
    _toggle_gray()
    _check("texture_roundtrip_restores_nearest_clone",not gray and instance.material_override==null and instance.get_active_material(0)==bound and bound.texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST)
    _check("mesh_uv_skin_and_bone_unchanged",instance.mesh==mesh and instance.skin==skin and var_to_bytes(mesh.surface_get_arrays(0))==before_arrays and skin.get_bind_pose(0)==before_bind and rig.get_bone_rest(0)==before_bone and instance.transform==before_transform)
    # Clone the actual active surface override, not only the mesh's material.
    var surface_material: StandardMaterial3D=original.duplicate();surface_material.emission=Color(.7,.2,.1)
    instance.set_surface_override_material(0,surface_material)
    var result: Dictionary=ENGINE_MATERIAL_BINDINGS.apply(meshes,config)
    _check("actual_surface_override_copied",result.ok and instance.get_active_material(0)!=surface_material and _same_material_except_filter(surface_material,instance.get_active_material(0)))
    # Mesh-wide priority is copied to each surface before it is released.
    instance.material_override=surface_material
    result=ENGINE_MATERIAL_BINDINGS.apply(meshes,config)
    _check("mesh_override_effective_nearest_and_gray_safe",result.ok and instance.material_override==null and _same_material_except_filter(surface_material,instance.get_active_material(0)) and instance.get_active_material(0).texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST)
    # A late unsupported surface must fail before the earlier surface is changed.
    var second:=MeshInstance3D.new();second.mesh=ArrayMesh.new();second.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);second.mesh.surface_set_material(0,ShaderMaterial.new());root.add_child(second)
    var current=instance.get_active_material(0);var batch: Array=[instance,second]
    result=ENGINE_MATERIAL_BINDINGS.apply(batch,config)
    _check("unsupported_batch_preflight_is_atomic",not result.ok and instance.get_active_material(0)==current and second.get_surface_override_material(0)==null)
    _finish()

func _same_material_except_filter(a: BaseMaterial3D,b: BaseMaterial3D) -> bool:
    for property in a.get_property_list():
        var name: String=property.name
        if not (property.usage & PROPERTY_USAGE_STORAGE) or name in ["texture_filter","resource_path","resource_scene_unique_id"]:continue
        if a.get(name)!=b.get(name):return false
    return true
