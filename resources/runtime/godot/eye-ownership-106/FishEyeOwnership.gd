extends RefCounted
## 106 isolated candidate repair: mode1 needs frozen RGB-only copies; never acceptance.
const DEFAULT_CONFIG = "res://assets/models/fish/motion/eye-ownership-106.json"
var last_error: String = ""
var last_receipt: Dictionary = {}

func _fail(message: String) -> int:
    last_error = message
    push_error("FishEyeOwnership106: " + message)
    return 0

# Flatten only the known source helper include, resolving relative paths against
# its containing shader. Unexpected includes fail instead of changing semantics.
func _expand_includes(code: String, base_path: String, depth: int = 0) -> String:
    if depth > 8:
        last_error = "Include recursion limit"
        return ""
    var expression := RegEx.new()
    expression.compile('(?m)^\\s*#include\\s+"([^"\\n]+)"\\s*$')
    var matches := expression.search_all(code)
    for index in range(matches.size() - 1, -1, -1):
        var found: RegExMatch = matches[index]
        var name := found.get_string(1)
        if name.get_file() != "FishHeadSource.gdshaderinc":
            last_error = "Unsupported include: " + name
            return ""
        var path := name if name.begins_with("res://") else base_path.get_base_dir().path_join(name).simplify_path()
        if not path.begins_with("res://") or not FileAccess.file_exists(path):
            last_error = "Missing include: " + path
            return ""
        var included := _expand_includes(FileAccess.get_file_as_string(path), path, depth + 1)
        if not last_error.is_empty(): return ""
        code = code.substr(0, found.get_start()) + included + code.substr(found.get_end())
    if code.contains("#include"):
        last_error = "Unrecognized include syntax"
        return ""
    return code

# Tokenize while skipping comments. Balanced parentheses preserve arbitrary UV
# expressions (including function calls) and let us reject explicit LOD/bias args.
func _tokens(code: String) -> Array[Dictionary]:
    var result: Array[Dictionary] = []
    var expression := RegEx.new()
    expression.compile('(?s)//[^\\n]*|/\\*.*?\\*/|[A-Za-z_][A-Za-z_0-9]*|[^\\s]')
    for item in expression.search_all(code):
        var token := item.get_string()
        if token.begins_with("//") or token.begins_with("/*"): continue
        result.append({"text":token, "start":item.get_start(), "end":item.get_end()})
    return result

func _wrap_samples(code: String) -> Dictionary:
    var tokens := _tokens(code)
    var edits: Array[Dictionary] = []
    var counts := {"source_texture":0, "opaque_skin":0}
    # Inspect EVERY use of either sampler, not just operations named texture*.
    # This rejects texelFetch, aliases, sampler parameters, macros and any future
    # sampling API unless explicitly supported here.
    for sampler_index in range(tokens.size()):
        var sampler: String = tokens[sampler_index].text
        if not counts.has(sampler): continue
        if _sampler_declaration_end(tokens, sampler_index) >= 0: continue
        var i := sampler_index - 2
        if i < 0 or sampler_index + 1 >= tokens.size() or tokens[i].text != "texture" or tokens[i + 1].text != "(" or tokens[sampler_index + 1].text != ",":
            last_error = "Unsupported source sampler use: " + sampler
            return {}
        var nesting := 1
        var end := -1
        for j in range(i + 4, tokens.size()):
            var token: String = tokens[j].text
            if token == "(": nesting += 1
            if token == ")": nesting -= 1
            if nesting == 1 and token == ",":
                last_error = "Texture bias/LOD argument is unsupported"
                return {}
            if nesting == 0:
                end = j
                break
        if end < 0:
            last_error = "Unbalanced source texture call"
            return {}
        # Replace just texture(sampler, with wrapper(. UV expression stays intact.
        edits.append({"start":tokens[i].start, "end":tokens[i + 3].end,
            "text":"ink_source_sample(" if sampler == "source_texture" else "ink_opaque_sample("})
        counts[sampler] += 1
    for i in range(edits.size() - 1, -1, -1):
        var edit: Dictionary = edits[i]
        code = code.substr(0, edit.start) + edit.text + code.substr(edit.end)
    if counts.source_texture == 0 or counts.opaque_skin == 0:
        last_error = "Both source and opaque fallback calls must be present"
        return {}
    return {"code":code, "sample_calls":counts}

func _sampler_declaration_end(tokens: Array[Dictionary], index: int) -> int:
    if index < 2 or index + 1 >= tokens.size(): return -1
    if tokens[index - 2].text != "uniform" or tokens[index - 1].text != "sampler2D" or tokens[index + 1].text != ":": return -1
    # Hint names separated only by commas; arrays/default expressions/macros are
    # outside this module's accepted sampler declaration grammar.
    var expect_hint := true
    for i in range(index + 2, tokens.size()):
        var token: String = tokens[i].text
        if token == ";": return i if not expect_hint else -1
        if expect_hint:
            if not token.is_valid_identifier(): return -1
        elif token != ",":
            return -1
        expect_hint = not expect_hint
    return -1

func _sampler_is_native_nearest(code: String, name: String) -> bool:
    var tokens := _tokens(code)
    var declarations := 0
    var native_nearest := false
    for i in range(tokens.size()):
        if tokens[i].text != name: continue
        var end := _sampler_declaration_end(tokens, i)
        if end < 0: continue
        declarations += 1
        var hints: Array[String] = []
        for j in range(i + 2, end):
            var token: String = tokens[j].text
            if token == ",": continue
            hints.append(token)
            if token.begins_with("filter_") and token != "filter_nearest": return false
            if token.begins_with("repeat_") and token != "repeat_disable": return false
        native_nearest = hints.has("source_color") and hints.has("filter_nearest") and hints.has("repeat_disable")
    return declarations == 1 and native_nearest


func _load_png(spec: Dictionary, size: Vector2i) -> Image:
    var path: String = spec.get("path", "")
    if not path.begins_with("res://") or not path.ends_with(".png") or str(spec.get("sha256", "")).length() != 64 or preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(path) != spec.sha256:
        last_error = "Missing/stale PNG: " + path
        return null
    var image := Image.new()
    var decoded := image.load_png_from_buffer(FileAccess.get_file_as_bytes(path))
    if decoded != OK or image.get_size() != size:
        last_error = "PNG dimensions differ from frozen source"
        return null
    image.convert(Image.FORMAT_RGBA8)
    return image

func _hash_bytes(bytes: PackedByteArray) -> String:
    var context := HashingContext.new()
    context.start(HashingContext.HASH_SHA256)
    context.update(bytes)
    return context.finish().hex_encode()

func _vertex_order_hash(arrays: Array) -> String:
    var context := HashingContext.new()
    context.start(HashingContext.HASH_SHA256)
    for index in [Mesh.ARRAY_VERTEX, Mesh.ARRAY_NORMAL, Mesh.ARRAY_TEX_UV, Mesh.ARRAY_INDEX]:
        context.update(arrays[index].to_byte_array())
    return context.finish().hex_encode()

func _mesh_snapshot(mesh: MeshInstance3D) -> Dictionary:
    var arrays := HashingContext.new()
    var lods := HashingContext.new()
    arrays.start(HashingContext.HASH_SHA256)
    lods.start(HashingContext.HASH_SHA256)
    var levels: Array = []
    for surface in mesh.mesh.get_surface_count():
        arrays.update(var_to_bytes(mesh.mesh.surface_get_arrays(surface)))
        var data := RenderingServer.mesh_get_surface(mesh.mesh.get_rid(), surface)
        lods.update(var_to_bytes(data.get("lods", [])))
        levels.append(data.get("lods", []).size())
    return {"mesh_resource_id":mesh.mesh.get_instance_id(), "mesh_rid_id":mesh.mesh.get_rid().get_id(),
        "all_surface_arrays_sha256":arrays.finish().hex_encode(), "all_lods_sha256":lods.finish().hex_encode(),
        "surface_count":mesh.mesh.get_surface_count(), "lod_counts":levels,
        "skeleton_path":str(mesh.skeleton), "skin_resource_id":mesh.skin.get_instance_id() if mesh.skin != null else 0}

func _stage_braces(code: String, name: String) -> Dictionary:
    var tokens := _tokens(code)
    var found: Dictionary = {}
    for i in range(tokens.size() - 4):
        if tokens[i].text != "void" or tokens[i + 1].text != name or tokens[i + 2].text != "(" or tokens[i + 3].text != ")" or tokens[i + 4].text != "{": continue
        if not found.is_empty():
            last_error = "Duplicate shader stage: " + name
            return {}
        var depth := 1
        for j in range(i + 5, tokens.size()):
            if tokens[j].text == "{": depth += 1
            if tokens[j].text == "}": depth -= 1
            if depth == 0:
                found = {"open":tokens[i + 4].end, "close":tokens[j].start}
                break
    if found.is_empty(): last_error = "Missing shader stage: " + name
    return found

func apply(model: Node3D, species: String, mode: int = 0, config_path: String = DEFAULT_CONFIG, probe: int = 0) -> int:
    last_error = ""
    last_receipt = {}
    if mode not in [0,1,2]: return _fail("Invalid mode; only0/1/2 are supported")
    if probe not in [0,1,2,3] or (mode != 2 and probe != 0): return _fail("RGB probes are allowed only in mode2")
    if not is_instance_valid(model): return _fail("Missing instantiated model")
    var config = JSON.parse_string(FileAccess.get_file_as_string(config_path))
    if not config is Dictionary or config.get("schema_version", 0) != 1 or not config.get("profiles") is Dictionary:
        return _fail("Invalid frozen eye configuration")
    if not config.profiles.has(species): return 0
    var p: Dictionary = config.profiles[species]
    var allowed = p.get("allowed_modes")
    if not allowed is Array or allowed.size() != 3 or float(allowed[0]) != 0.0 or float(allowed[1]) != 1.0 or float(allowed[2]) != 2.0 or p.get("mesh", "") != "Closed_body" or p.get("surface", -1) != 0:
        return _fail("Unsupported eye profile modes/surface")
    if not p.get("model_path", "").begins_with("res://") or model.scene_file_path != p.model_path or preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(p.model_path) != p.get("model_sha256", ""):
        return _fail("Frozen model hash or actual scene path mismatch")
    var matches: Array[MeshInstance3D] = []
    for node in model.find_children("*", "MeshInstance3D", true, false):
        if str(node.name) == "Closed_body": matches.append(node)
    if matches.size() != 1: return _fail("Expected exactly one Closed_body")
    var mesh := matches[0]
    if mesh.mesh == null or mesh.material_override != null: return _fail("Missing mesh or whole-mesh material override")
    var before := _mesh_snapshot(mesh)
    var arrays := mesh.mesh.surface_get_arrays(0)
    var positions: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
    var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
    if positions.size() != p.get("surface0_vertices", -1) or uvs.size() != positions.size() or _vertex_order_hash(arrays) != p.get("vertex_order_sha256", ""):
        return _fail("Actual imported vertex sequence differs from frozen profile")
    var original := mesh.get_active_material(0) as ShaderMaterial
    if original == null or original.shader == null or original.get_shader_parameter("fin") == true or original.get_shader_parameter("head_blend") == true:
        return _fail("Expected assembled exterior ShaderMaterial without auxiliary head blend")
    if original.shader.code.contains("feature_rest_normal") or original.shader.code.contains("eye_reference_rest"):
        return _fail("Old103 or already installed106 shader must not be layered")
    var dimensions = p.get("source_size", [])
    if not dimensions is Array or dimensions.size() != 2 or int(dimensions[0]) < 1 or int(dimensions[1]) < 1:
        return _fail("Invalid source dimensions")
    var size := Vector2i(int(dimensions[0]), int(dimensions[1]))
    if not p.get("source") is Dictionary or not p.get("source_eye_mask") is Dictionary: return _fail("Missing frozen source/mask")
    var source := _load_png(p.source, size)
    if source == null: return _fail(last_error)
    var mask := _load_png(p.source_eye_mask, size)
    if mask == null: return _fail(last_error)
    var texture := original.get_shader_parameter("source_texture") as Texture2D
    var fallback := original.get_shader_parameter("opaque_skin") as Texture2D
    if texture == null or fallback == null or texture.get_size() != Vector2(size) or fallback.get_size() != Vector2(size):
        return _fail("Actual source/fallback size mismatch")
    var image := texture.get_image()
    if image == null: return _fail("Actual source pixels unavailable")
    if image.is_compressed() and image.decompress() != OK: return _fail("Cannot decode actual source")
    image.convert(Image.FORMAT_RGBA8)
    var had_mips := image.has_mipmaps()
    if had_mips: image.clear_mipmaps()
    if image.get_data() != source.get_data(): return _fail("Actual source base-level RGBA differs from frozen runtime PNG")
    var mask_count := 0
    var mask_bytes := mask.get_data()
    for offset in range(0, mask_bytes.size(), 4):
        if mask_bytes[offset] not in [0, 255]: return _fail("Source eye mask red channel must be binary")
        if mask_bytes[offset] == 255: mask_count += 1
    if mask_count < 1 or mask_count != p.source_eye_mask.get("pixels", -1): return _fail("Empty/stale source eye mask footprint")
    var projection: Dictionary = p.get("projection", {})
    if projection.get("kind", "") != "rest_xy" or not model.has_meta("eye_lod_106_receipt"):
        return _fail("Expected approved restXY projection and explicit LOD exception receipt")
    if projection.get("downshift_native_pixels") != 22 or abs(float(projection.get("pixel_native", 0.))-.9/1986.) > 1e-15:
        return _fail("Projection differs from frozen CPU22px calibration")
    var eye_mask := _load_png(p.eye_layer_mask, size)
    var fallback_mask := _load_png(p.fallback_eye_mask, size)
    var opaque := _load_png(p.opaque_skin, size)
    if eye_mask == null or fallback_mask == null or opaque == null: return _fail(last_error)
    var fallback_image := fallback.get_image()
    if fallback_image == null: return _fail("Fallback pixels unavailable")
    if fallback_image.is_compressed() and fallback_image.decompress() != OK: return _fail("Cannot decode fallback")
    fallback_image.convert(Image.FORMAT_RGBA8)
    if fallback_image.has_mipmaps(): fallback_image.clear_mipmaps()
    if fallback_image.get_data() != opaque.get_data(): return _fail("Actual fallback RGBA differs from frozen donor")
    for spec in [p.eye_layer_mask,p.fallback_eye_mask]:
        var data_image: Image = eye_mask if spec == p.eye_layer_mask else fallback_mask
        var bytes := data_image.get_data()
        var selected := 0
        for offset in range(0,bytes.size(),4):
            if bytes[offset] not in [0,255]: return _fail("Nonbinary independent/fallback mask")
            if bytes[offset] == 255: selected += 1
        if selected != int(spec.pixels): return _fail("Mask footprint differs from freeze")
    var clean_source := _load_png(p.get("clean_source",{}),size)
    var clean_opaque := _load_png(p.get("clean_opaque",{}),size)
    if clean_source == null or clean_opaque == null: return _fail(last_error)
    for channel in [0,1]:
        var original_bytes: PackedByteArray = source.get_data() if channel == 0 else opaque.get_data()
        var clean_bytes: PackedByteArray = clean_source.get_data() if channel == 0 else clean_opaque.get_data()
        var region_bytes: PackedByteArray = mask.get_data() if channel == 0 else fallback_mask.get_data()
        for offset in range(0,clean_bytes.size(),4):
            if original_bytes[offset+3] != clean_bytes[offset+3]: return _fail("RGB copy changed original alpha")
            if region_bytes[offset] == 0:
                for component in 4:
                    if original_bytes[offset+component] != clean_bytes[offset+component]: return _fail("RGB copy changed outside-mask RGBA")
    var shader_origin: String = original.shader.resource_path
    if shader_origin.is_empty(): shader_origin = p.get("shader_origin", "")
    var code := _expand_includes(original.shader.code, shader_origin)
    if not last_error.is_empty(): return _fail(last_error)
    if not _sampler_is_native_nearest(code, "source_texture") or not _sampler_is_native_nearest(code, "opaque_skin"):
        return _fail("Expected unique real native nearest non-mipmap source/fallback declarations")
    var wrapped := _wrap_samples(code)
    if not last_error.is_empty(): return _fail(last_error)
    code = wrapped.code.replace("ink_source_sample(", "eye_source_sample(").replace("ink_opaque_sample(", "eye_opaque_sample(")
    if code.count("ALBEDO=color.rgb;") != 1: return _fail("Unexpected final original color assignment")
    code = code.replace("ALBEDO=color.rgb;", "color.rgb=eye_independent_diagnostic(color.rgb,eye_reference_rest,tint.rgb*COLOR.rgb);\n    ALBEDO=color.rgb;")
    var vertex := _stage_braces(code, "vertex")
    var fragment := _stage_braces(code, "fragment")
    if not last_error.is_empty(): return _fail(last_error)
    var changes := [{"offset":vertex.open, "text":"\n    vec4 eye_lookup_result=eye_lookup_vertex(VERTEX_ID, UV);\n    eye_reference_rest=eye_lookup_result.xyz;eye_lookup_error=eye_lookup_result.w;\n"},
        {"offset":fragment.close, "text":"\n    if (eye_mode == 2 && eye_lookup_error > 0.000001) { ALBEDO=vec3(1.0,0.0,1.0); EMISSION=vec3(1.0,0.0,1.0); }\n"}]
    changes.sort_custom(func(a, b): return a.offset > b.offset)
    for change in changes: code = code.substr(0, change.offset) + change.text + code.substr(change.offset)
    var first_function := RegEx.new()
    first_function.compile('(?m)^(?:void|float|int|bool|vec[234]|ivec[234]|mat[234])\\s+\\w+\\s*\\(')
    var found := first_function.search(code)
    if found == null: return _fail("Cannot find source shader function boundary")
    var template_path: String = get_script().resource_path.get_base_dir().path_join("FishEyeOwnership.gdshaderinc")
    if not FileAccess.file_exists(template_path): return _fail("Missing106 shader template")
    code = code.substr(0, found.get_start()) + FileAccess.get_file_as_string(template_path) + "\n" + code.substr(found.get_start())
    var width := mini(positions.size(), 256)
    var height := ceili(float(positions.size()) / float(width))
    var rest := Image.create(width, height, false, Image.FORMAT_RGBAF)
    var uv_reference := Image.create(width, height, false, Image.FORMAT_RGBAF)
    for index in positions.size():
        var xy := Vector2i(index % width, index / width)
        var point := positions[index]
        var uv := uvs[index]
        rest.set_pixelv(xy, Color(point.x, point.y, point.z, 1.0))
        uv_reference.set_pixelv(xy, Color(uv.x, uv.y, 0.0, 1.0))
    var material := original.duplicate() as ShaderMaterial
    var shader := Shader.new()
    shader.code = code
    if shader.get_shader_uniform_list().is_empty(): return _fail("106 shader compilation produced no uniforms")
    material.shader = shader
    material.set_shader_parameter("eye_rest_lookup", ImageTexture.create_from_image(rest))
    material.set_shader_parameter("eye_uv_lookup", ImageTexture.create_from_image(uv_reference))
    material.set_shader_parameter("eye_source_mask", ImageTexture.create_from_image(mask))
    material.set_shader_parameter("eye_lookup_size", Vector2(width, height))
    material.set_shader_parameter("eye_vertex_count", positions.size())
    material.set_shader_parameter("eye_source_size", Vector2(size))
    material.set_shader_parameter("eye_mode", mode)
    material.set_shader_parameter("eye_probe",probe)
    material.set_shader_parameter("eye_clean_source",ImageTexture.create_from_image(clean_source))
    material.set_shader_parameter("eye_clean_opaque",ImageTexture.create_from_image(clean_opaque))
    material.set_shader_parameter("eye_fallback_mask", ImageTexture.create_from_image(fallback_mask))
    material.set_shader_parameter("eye_layer_mask", ImageTexture.create_from_image(eye_mask))
    material.set_shader_parameter("eye_anchor_xy", Vector2(projection.anchor_rest_xy[0],projection.anchor_rest_xy[1]))
    material.set_shader_parameter("eye_pupil_uv", Vector2(projection.source_pupil_px[0]/size.x,projection.source_pupil_px[1]/size.y))
    material.set_shader_parameter("eye_pixel_native", projection.pixel_native)
    material.set_shader_parameter("eye_downshift_pixels", projection.downshift_native_pixels)
    material.set_shader_parameter("eye_z_gap", Vector2(projection.central_gap_abs_z,projection.full_owner_abs_z))
    mesh.set_surface_override_material(0, material)
    var after := _mesh_snapshot(mesh)
    if before != after:
        mesh.set_surface_override_material(0, original)
        return _fail("Mesh/LOD/skeleton preservation check failed")
    last_receipt = {"species":species, "mode":mode,"probe":probe, "allowed_modes":[0,1,2], "color_repair_implemented":true,"accepted":false, "clean_source_sha256":p.clean_source.sha256,"clean_opaque_sha256":p.clean_opaque.sha256,"copies_outside_mask_rgba_equal":true,"copies_all_alpha_equal":true,
        "model_sha256":p.model_sha256, "source_sha256":p.source.sha256, "source_eye_mask_sha256":p.source_eye_mask.sha256,
        "source_embedded_sha256":p.source_embedded_sha256, "projection":projection, "eye_layer_mask_sha256":p.eye_layer_mask.sha256, "fallback_eye_mask_sha256":p.fallback_eye_mask.sha256, "fallback_texture_sha256":p.opaque_skin.sha256, "lod_exception_receipt":model.get_meta("eye_lod_106_receipt"), "profile_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(config_path),
        "input_profile_sha256":p.get("input_profile_sha256", ""), "helper_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(get_script().resource_path),
        "template_sha256":preload("res://scripts/aquarium/FishRuntimeData.gd").sha256(template_path), "generated_shader_sha256":shader.code.sha256_text(), "source_base_level_all_rgba_equal":true,
        "source_unused_mipmaps_removed_for_comparison":had_mips, "source_eye_mask_pixels":mask_count,
        "vertex_order_sha256":p.vertex_order_sha256, "mesh_before":before, "mesh_after":after, "mesh_unchanged":true,
        "lookup_format":"RGBAF", "lookup_size":[width,height], "lookup_mipmaps":false, "lookup_srgb":false,
        "rest_lookup_sha256":_hash_bytes(rest.get_data()), "uv_lookup_sha256":_hash_bytes(uv_reference.get_data()),
        "wrapped_source_calls":wrapped.sample_calls, "gpu_vertex_id_mapping":"pending", "visual_acceptance":"pending"}
    model.set_meta("eye_ownership_106_receipt", last_receipt)
    return 1
