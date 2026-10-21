extends "../../../scripts/volume-fish/capture_surface_mouth_audit.gd"
## Read-only107 evidence. Run against the actual game; no asset/material edits.
var frozen_textures: Dictionary = {}

func bytes_sha(data: PackedByteArray) -> String:
    var hashing := HashingContext.new()
    assert(hashing.start(HashingContext.HASH_SHA256) == OK)
    assert(hashing.update(data) == OK)
    return hashing.finish().hex_encode()

func save_json(path: String, value: Variant):
    var file := FileAccess.open(path, FileAccess.WRITE)
    assert(file != null)
    file.store_string(JSON.stringify(value, "  "))
    file.close()

func freeze_texture(texture: Texture2D, folder: String) -> Dictionary:
    var key := texture.get_instance_id()
    if frozen_textures.has(key): return frozen_textures[key]
    var image := texture.get_image()
    assert(image != null and not image.is_empty())
    var had_mips := image.has_mipmaps()
    if image.is_compressed(): assert(image.decompress() == OK)
    image.convert(Image.FORMAT_RGBA8)
    image.clear_mipmaps()
    var digest := bytes_sha(image.get_data())
    var path := folder + "/rgba-" + digest + ".png"
    assert(image.save_png(path) == OK)
    var result := {"resource_path": texture.resource_path, "file": path,
        "png_sha256": FileAccess.get_sha256(path), "base_rgba_sha256": digest,
        "size": [image.get_width(), image.get_height()], "had_mipmaps": had_mips,
        "snapshot": "Actual Texture2D.get_image base level; RGBA8, no unused mip bytes"}
    frozen_textures[key] = result
    return result

func describe_value(value: Variant, folder: String) -> Variant:
    if value is Texture2D: return freeze_texture(value, folder)
    if value == null or value is bool or value is int or value is float or value is String: return value
    if value is Array:
        var items: Array = []
        for item in value: items.append(describe_value(item, folder))
        return items
    return {"variant_type": type_string(typeof(value)), "value": var_to_str(value)}

func material_data(material: Material, folder: String) -> Dictionary:
    var result := {"class": material.get_class(), "name": material.resource_name,
        "resource_path": material.resource_path}
    if material is ShaderMaterial:
        result.shader_path = material.shader.resource_path
        result.shader_code_sha256 = material.shader.code.sha256_text()
        var shader_file: String = folder + "/shader-" + result.shader_code_sha256 + ".gdshader"
        var file := FileAccess.open(shader_file, FileAccess.WRITE)
        assert(file != null)
        file.store_string(material.shader.code); file.close()
        result.shader_file = shader_file
        result.uniforms = {}
        for uniform in material.shader.get_shader_uniform_list():
            result.uniforms[uniform.name] = describe_value(material.get_shader_parameter(uniform.name), folder)
    elif material is StandardMaterial3D:
        result.albedo_color = describe_value(material.albedo_color, folder)
        result.albedo_texture = describe_value(material.albedo_texture, folder)
        result.transparency = material.transparency
    return result

func freeze_mesh(mesh: MeshInstance3D, folder: String, excluded_fin: bool, full_geometry: bool) -> Dictionary:
    var result := {"mesh": str(mesh.name), "node_path": str(mesh.get_path()),
        "visible": intrinsic[mesh.get_instance_id()], "excluded_fin": excluded_fin,
        "mesh_class": mesh.mesh.get_class(), "mesh_resource_path": mesh.mesh.resource_path,
        "skeleton": str(mesh.skeleton), "skin_path": mesh.skin.resource_path if mesh.skin != null else "",
        "transform": var_to_str(mesh.transform), "global_transform": var_to_str(mesh.global_transform),
        "surfaces": []}
    for surface in mesh.mesh.get_surface_count():
        var arrays: Array = mesh.mesh.surface_get_arrays(surface)
        var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
        var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL] if arrays[Mesh.ARRAY_NORMAL] != null else PackedVector3Array()
        var uv: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV] if arrays[Mesh.ARRAY_TEX_UV] != null else PackedVector2Array()
        var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
        var raw: Dictionary = RenderingServer.mesh_get_surface(mesh.mesh.get_rid(), surface)
        var lods: Dictionary = {}
        var index_width: int = raw.index_data.size() / raw.index_count if raw.get("index_count", 0) > 0 else 0
        for lod in raw.get("lods", []):
            var bytes: PackedByteArray = lod.index_data
            var decoded := PackedInt32Array()
            assert(index_width in [2,4])
            for offset in range(0, bytes.size(), index_width): decoded.append(bytes.decode_u16(offset) if index_width == 2 else bytes.decode_u32(offset))
            lods[lod.edge_length] = decoded
        var geometry := {"format": "Godot4 FileAccess.store_var; trusted local evidence only",
            "mesh": str(mesh.name), "surface": surface, "arrays": arrays, "lods": lods,
            "primitive": mesh.mesh.surface_get_primitive_type(surface), "transform": mesh.transform,
            "global_transform": mesh.global_transform, "skeleton": mesh.skeleton, "skin": []}
        if mesh.skin != null:
            for bind in mesh.skin.get_bind_count():
                geometry.skin.append({"bone": mesh.skin.get_bind_bone(bind), "name": mesh.skin.get_bind_name(bind), "pose": mesh.skin.get_bind_pose(bind)})
        var packed_path: String = ""
        if full_geometry:
            packed_path = folder + "/" + str(mesh.name).validate_filename() + "-surface-%d.bin" % surface
            var file := FileAccess.open(packed_path, FileAccess.WRITE)
            assert(file != null)
            file.store_var(geometry); file.close()
        var lod_inventory: Array = []
        for distance in lods:
            var lod_indices: PackedInt32Array = lods[distance]
            lod_inventory.append({"edge_length": distance, "indices": lod_indices.size(),
                "triangles": lod_indices.size() / 3, "index_sha256": bytes_sha(lod_indices.to_byte_array())})
        var packed_vertex := vertices.to_byte_array()
        packed_vertex.append_array(normals.to_byte_array()); packed_vertex.append_array(uv.to_byte_array()); packed_vertex.append_array(indices.to_byte_array())
        var active: Material = mesh.get_active_material(surface)
        assert(active != null)
        result.surfaces.append({"surface": surface, "vertices": vertices.size(), "indices": indices.size(),
            "packed_position_normal_uv0_indices_sha256": bytes_sha(packed_vertex), "lods": lod_inventory,
            "packed_file": packed_path, "packed_sha256": FileAccess.get_sha256(packed_path) if full_geometry else "",
            "material": material_data(active, folder)})
    return result

func unlit(material: Material) -> Material:
    # Base audit keys by resource_path; generated shaders may have an empty path.
    if material is ShaderMaterial:
        var key: String = material.shader.code.sha256_text()
        if not shaders.has(key):
            var shader := Shader.new()
            var code: String = material.shader.code
            code = code.replace("render_mode", "render_mode unshaded,") if code.contains("render_mode") else code.replace("shader_type spatial;", "shader_type spatial;\nrender_mode unshaded;")
            shader.code = code; shaders[key] = shader
        var copy: ShaderMaterial = material.duplicate()
        copy.shader = shaders[key]
        return copy
    return super.unlit(material)

func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size = Vector2i(1200,800)
    hall = load("res://scripts/aquarium/VolumeFishExhibit.gd").new(); root.add_child(hall)
    hall.set_process(false); hall.paused = true; hall.header.hide(); hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
    hall.screen.position = Vector2.ZERO; hall.screen.size = Vector2(1200,800)
    hall.viewport.size = Vector2i(1200,800); hall.viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    ownership = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*", "MeshInstance3D", true, false): intrinsic[mesh.get_instance_id()] = mesh.visible
    for label in hall.world.find_children("*", "Label3D", true, false): label.hide()
    if requested.is_empty(): requested = hall.SPECIES.duplicate()
    var files: Dictionary = {}
    var copied_profiles: Dictionary = {}
    for relative in ["scripts/aquarium/VolumeFishExhibit.gd", "scripts/aquarium/FishSurfaceOwnership.gd", "scripts/aquarium/FishHeadSource.gd", "scripts/aquarium/FishHeadSource.gdshaderinc", "scripts/aquarium/FishBodyOpaque.gdshader", "scripts/aquarium/FishMouthPigment.gdshader", "scripts/aquarium/FoundryFishMotion.gd", "assets/models/fish/motion/head-source.json", "assets/models/fish/motion/mouth-pigment.json", "assets/models/fish/motion/body-opacity.json", "assets/models/fish/motion/surface-ownership.json", "assets/models/fish/motion/motion.json", "assets/models/fish/motion/presentation.json"]:
        if not FileAccess.file_exists("res://" + relative): continue
        files[relative] = FileAccess.get_sha256("res://" + relative)
        if relative.ends_with(".json"):
            copied_profiles[relative] = JSON.parse_string(FileAccess.get_file_as_string("res://" + relative))
    save_json(out + "/original-profiles.json", copied_profiles)
    for species in requested:
        assert(species in hall.SPECIES)
        hall._select_display(species)
        var entry: Dictionary = hall._selected()
        for tank in hall.tanks: tank.root.visible = tank.species == species
        for mesh in hall.world.find_children("*", "MeshInstance3D", true, false): mesh.visible = entry.model.is_ancestor_of(mesh) and intrinsic[mesh.get_instance_id()]
        entry.controller.set_motion_controls({"body_amplitude":0., "body_frequency":1., "fin_amplitude":0., "fin_frequency":1.}, true)
        assert(entry.controller.set_action("Swim", true)); entry.controller.step(0.); entry.controller.seek(0.)
        if entry.has("jaw_controller"): entry.jaw_controller.apply(1.)
        await process_frame
        var folder: String = out + "/" + species
        DirAccess.make_dir_recursive_absolute(folder)
        var meshes: Array = []; var stored: Array = []
        for mesh in entry.model.find_children("*", "MeshInstance3D", true, false):
            meshes.append(freeze_mesh(mesh, folder, ownership[species].fins.has(str(mesh.name)), species == "zander"))
            for surface in mesh.mesh.get_surface_count(): stored.append([mesh, surface, mesh.get_surface_override_material(surface), mesh.get_active_material(surface)])
        var r: Dictionary = region(entry); var captures: Array = []
        for view in [["head-side",0.,0.], ["head-opposite",PI,0.], ["head-top",0.,1.56], ["head-front",PI/2.,0.], ["head-oblique",.65,.20]]:
            camera(entry, r, true, view[1], view[2])
            for mode in ["texture", "albedo"]:
                set_mode(entry, stored, mode)
                var path: String = folder + "/" + view[0] + "-" + mode + ".png"
                await shot(path)
                captures.append({"view":view[0], "mode":mode, "file":path, "sha256":FileAccess.get_sha256(path), "camera_transform":var_to_str(hall.camera.global_transform)})
        set_mode(entry, stored, "texture")
        var record := {"species":species, "name":hall.LABELS[species], "game":ProjectSettings.globalize_path("res://"),
            "model_path":entry.model.scene_file_path, "model_sha256":FileAccess.get_sha256(entry.model.scene_file_path),
            "controller_snapshot":entry.controller.snapshot(), "separate_jaw":entry.has("jaw_controller"),
            "body_region_native":var_to_str(r.body), "head_region_native":var_to_str(r.head), "meshes":meshes, "captures":captures}
        save_json(folder + "/audit.validation.json", record); records.append(record)
        print("EYE_AUDIT_107 ", species)
    var script_index := OS.get_cmdline_args().find("--script")
    var script_path: String = OS.get_cmdline_args()[script_index+1] if script_index >= 0 else ""
    save_json(out + "/capture.validation.json", {"ok":records.size()==requested.size(), "status":"done", "next_action":"human_review",
        "records":records, "files":files, "script_sha256":FileAccess.get_sha256(script_path),
        "profile_snapshot_sha256":FileAccess.get_sha256(out+"/original-profiles.json"),
        "scope":"Read-only actual assembled materials, baseRGBA snapshots, original packed mesh arrays/all existing LODs and five head camera views. Zero-amplitude Swim0 only; not anatomy/fin/body/LOD/whole-fish acceptance. No mesh, source or shader repair."})
    hall.queue_free(); await process_frame
    if RenderingServer.has_method("force_sync"): RenderingServer.force_sync()
    await process_frame
    quit()
