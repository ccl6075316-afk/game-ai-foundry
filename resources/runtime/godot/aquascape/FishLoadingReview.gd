extends Node
var directory := ""
var target := "hall"
var rounds := 2
var results: Array=[]
var verify_cache := false
var signatures: Dictionary={}
var resource_signatures: Dictionary={}
var checks: Dictionary={}

func _digest(value: Variant) -> String:
    var context := HashingContext.new();context.start(HashingContext.HASH_SHA256);context.update(var_to_bytes(value));return context.finish().hex_encode()

func _texture(texture: Texture2D) -> String:
    if texture==null:return "null"
    var id := texture.get_instance_id()
    if not resource_signatures.has(id):
        var image := texture.get_image()
        resource_signatures[id]=_digest([image.get_format(),image.get_size(),image.has_mipmaps(),image.get_data()])
    return resource_signatures[id]

func _appearance(model: Node3D) -> String:
    var meshes: Dictionary={}
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        var geometry_id: int=mesh.mesh.get_instance_id()
        if not resource_signatures.has(geometry_id):
            var arrays: Array=[]
            for i in mesh.mesh.get_surface_count():arrays.append(mesh.mesh.surface_get_arrays(i))
            resource_signatures[geometry_id]=_digest(arrays)
        var materials: Array=[]
        for i in mesh.mesh.get_surface_count():
            var mat: Material=mesh.get_active_material(i)
            if mat is ShaderMaterial:
                var params: Dictionary={}
                for uniform in mat.shader.get_shader_uniform_list():
                    var value: Variant=mat.get_shader_parameter(uniform.name)
                    params[uniform.name]=_texture(value) if value is Texture2D else value
                for key in ["mouth_source_projection","rim_local_source"]:params[key]=mat.get_shader_parameter(key)
                materials.append([mat.shader.code.sha256_text(),_digest(params)])
            elif mat is StandardMaterial3D:
                materials.append([_texture(mat.albedo_texture),mat.albedo_color,mat.texture_filter,mat.cull_mode,mat.roughness,mat.metallic,mat.metallic_specular,mat.transparency,mat.vertex_color_use_as_albedo])
            else:materials.append("null")
        meshes[str(model.get_path_to(mesh))]=[resource_signatures[geometry_id],mesh.transform,mesh.visible,materials,str(mesh.skeleton)]
    return _digest([meshes,model.scale,model.position])

func _ready() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--capture-dir="):directory=arg.trim_prefix("--capture-dir=")
        if arg.begins_with("--profile-target="):target=arg.trim_prefix("--profile-target=")
        if arg.begins_with("--rounds="):rounds=int(arg.trim_prefix("--rounds="))
        if arg=="--verify-cache":verify_cache=true
    assert(not directory.is_empty() and target in ["hall","shared"])
    DirAccess.make_dir_recursive_absolute(directory)
    call_deferred("_run")

func _run() -> void:
    for round_index in rounds:
        var started := Time.get_ticks_usec()
        var scene_path := "res://scenes/aquarium_hall_3d.tscn" if target=="hall" else "res://scenes/shared_3d_hall.tscn"
        var scene=load(scene_path).instantiate()
        if target=="hall":scene.configure_save(directory+"/not-user-layout.json",false)
        add_child(scene)
        var built := Time.get_ticks_usec()
        await RenderingServer.frame_post_draw
        var rendered := Time.get_ticks_usec()
        var metrics: Array=[]
        if target=="shared":metrics=scene.loading_metrics.duplicate(true)
        else:
            for row in scene.objects:
                if row.tank!=null and row.tank.factory!=null:metrics.append_array(row.tank.factory.loading_metrics)
        results.append({"round":round_index,"scene":target,"cpu_build_ms":(built-started)/1000.0,"first_draw_wait_ms":(rendered-built)/1000.0,"total_to_first_draw_ms":(rendered-started)/1000.0,"fish":metrics})
        print("SCENE_LOAD "+JSON.stringify(results[-1]))
        if verify_cache:
            var entries: Array=[]
            if target=="shared":entries=scene.fish
            else:
                for row in scene.objects:
                    if row.tank!=null:entries.append_array(row.tank.fish)
            for entry in entries:
                var signature := _appearance(entry.model)
                if not signatures.has(entry.species):signatures[entry.species]=signature
                else:checks["same_geometry_shaders_uniforms_pixels_"+entry.species]=signatures[entry.species]==signature
            if entries.size()>1:
                checks["independent_skeleton_nodes"]=entries[0].skeleton!=entries[1].skeleton
                var second_controls: Dictionary=entries[1].controller.motion_controls()
                entries[0].controller.set_motion_controls({"body_amplitude":.37},true)
                checks["independent_motion_controls"]=entries[1].controller.motion_controls()==second_controls
            var reference: Node3D=entries[0].model
            var copy: Node3D=preload("res://scripts/aquarium/FishAppearanceCache.gd").get_model(entries[0].species)
            if copy!=null:
                copy.hide();scene.world.add_child(copy)
                var a: Skeleton3D=reference.find_children("*","Skeleton3D",true,false)[0]
                var b: Skeleton3D=copy.find_children("*","Skeleton3D",true,false)[0]
                var old := a.get_bone_pose_rotation(0);var other := b.get_bone_pose_rotation(0)
                a.set_bone_pose_rotation(0,Quaternion(Vector3.UP,.1))
                checks["same_species_skeleton_pose_isolated"]=b.get_bone_pose_rotation(0)==other;a.set_bone_pose_rotation(0,old)
                for mesh in reference.find_children("*","MeshInstance3D",true,false):
                    var first_material=mesh.get_active_material(0)
                    if not first_material is ShaderMaterial:continue
                    var counterpart=copy.get_node(reference.get_path_to(mesh)) as MeshInstance3D
                    var second_material=counterpart.get_active_material(0) as ShaderMaterial
                    var old_value: Variant=first_material.get_shader_parameter("tint")
                    var other_value: Variant=second_material.get_shader_parameter("tint")
                    first_material.set_shader_parameter("tint",Color(.2,.3,.4))
                    checks["same_species_material_parameters_isolated"]=first_material!=second_material and second_material.get_shader_parameter("tint")==other_value
                    first_material.set_shader_parameter("tint",old_value);break
                # Allow GLES material dependency updates before retiring this
                # validation-only instance; production instances live in-world.
                await RenderingServer.frame_post_draw
                copy.queue_free()
                await get_tree().process_frame
            results[-1]["appearance_signatures"]=signatures.duplicate()
        if round_index==0:
            var img: Image=scene.viewport.get_texture().get_image()
            img.save_png(directory+"/"+target+"-first-frame.png")
        remove_child(scene);scene.free()
        for i in 4:await get_tree().process_frame
    var failures: Array=[]
    if verify_cache:
        var fixture := directory+"/cache-fixture.json"
        var stream := FileAccess.open(fixture,FileAccess.WRITE);stream.store_string('{"value":1}');stream.close()
        var data=preload("res://scripts/aquarium/FishRuntimeData.gd")
        data.begin_entry();var first_data: Dictionary=data.read_json(fixture)
        var cache=preload("res://scripts/aquarium/FishAppearanceCache.gd")
        cache._templates["__invalidation_probe"]={"model":Node3D.new(),"dependencies":{fixture:data.sha256(fixture)}}
        stream=FileAccess.open(fixture,FileAccess.WRITE);stream.store_string('{"value":2}');stream.close()
        data.begin_entry();var second_data: Dictionary=data.read_json(fixture)
        checks["changed_same_size_source_json_invalidates"]=first_data.value==1 and second_data.value==2
        checks["changed_dependency_discards_prepared_template"]=cache.get_model("__invalidation_probe")==null and not cache._templates.has("__invalidation_probe")
    for key in checks:
        if not checks[key]:failures.append(key)
    var report := {"schema_version":1,"command":"aquarium.loading-profile","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","checks":checks,"results":results,"gpu":RenderingServer.get_video_adapter_name(),"cache_metrics":preload("res://scripts/aquarium/FishAppearanceCache.gd").metrics,"data_metrics":preload("res://scripts/aquarium/FishRuntimeData.gd").metrics,"limitations":["Process-cold runtime with existing importer/driver caches; not an OS cold-disk or cleared GPU-cache test."],"failures":failures}
    var file := FileAccess.open(directory+"/"+target+".validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    get_tree().quit(0 if failures.is_empty() else 1)
