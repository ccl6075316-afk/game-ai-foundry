extends RefCounted
## Experimental explicit source-ink RGB replacement, never an automatic ink classifier.
## Call AFTER existing friendly/head-source helpers have assembled their materials.
const DEFAULT_CONFIG = "res://assets/models/fish/motion/source-ink.json"
const TEMPLATE = "FishSourceInk.gdshaderinc"
var last_error: String = ""
var last_receipt: Dictionary = {}

func _fail(message: String) -> int:
    last_error = message
    push_error("FishSourceInk: " + message)
    return 0

func _load_png(spec: Dictionary, size: Vector2i) -> Image:
    var path: String = spec.get("path", "")
    if not path.begins_with("res://") or not path.ends_with(".png"):
        last_error = "Expected a res:// raw PNG path"
        return null
    var expected: String = spec.get("sha256", "")
    if expected.length() != 64 or FileAccess.get_sha256(path) != expected:
        last_error = "Stale or missing PNG: " + path
        return null
    var image := Image.load_from_file(path)
    if image == null or image.get_size() != size:
        last_error = "Wrong PNG dimensions: " + path
        return null
    image.convert(Image.FORMAT_RGBA8)
    return image

func _exact_meshes(node: Node, mesh_name: String, result: Array[MeshInstance3D]) -> void:
    if node is MeshInstance3D and str(node.name) == mesh_name:
        result.append(node as MeshInstance3D)
    for child in node.get_children():
        _exact_meshes(child, mesh_name, result)

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

func apply(model: Node3D, species: String, mode: int = 0, config_path: String = DEFAULT_CONFIG) -> int:
    last_error = ""
    last_receipt = {}
    if mode < 0 or mode > 4: return _fail("Invalid ink mode")
    var parsed = JSON.parse_string(FileAccess.get_file_as_string(config_path))
    if not parsed is Dictionary or parsed.get("schema_version", 0) != 1 or not parsed.get("profiles") is Dictionary:
        return _fail("Invalid source-ink configuration")
    if not parsed.profiles.has(species): return 0
    var p: Dictionary = parsed.profiles[species]
    if p.get("mesh", "") != "Closed_body" or p.get("surface", -1) != 0:
        return _fail("Only explicit Closed_body exterior surface 0 is supported")
    var model_path: String = p.get("model_path", "")
    if not model_path.begins_with("res://") or not model_path.ends_with("/" + species + ".glb"):
        return _fail("Invalid species model path")
    if str(p.get("model_sha256", "")).length() != 64 or FileAccess.get_sha256(model_path) != p.model_sha256:
        return _fail("Stale model: " + species)
    # The caller must pass the actual instantiated scene, not a similarly named mesh.
    if model.scene_file_path != model_path:
        return _fail("Instantiated model path does not match frozen GLB")
    var matches: Array[MeshInstance3D] = []
    _exact_meshes(model, p.mesh, matches)
    if matches.size() != 1: return _fail("Expected exactly one named exterior mesh")
    var mesh := matches[0]
    if mesh.mesh == null or mesh.mesh.get_surface_count() == 0 or mesh.material_override != null:
        return _fail("Missing body surface or whole-mesh material override")
    var original := mesh.get_active_material(0) as ShaderMaterial
    if original == null or original.shader == null or bool(original.get_shader_parameter("fin")):
        return _fail("Expected assembled exterior ShaderMaterial, fin=false")
    if original.shader.code.contains("ink_source_sample"):
        return _fail("Source ink helper is already installed")
    var dims = p.get("source_size", [])
    if not dims is Array or dims.size() != 2: return _fail("Invalid source dimensions")
    var size := Vector2i(int(dims[0]), int(dims[1]))
    if size.x < 1 or size.y < 1 or size.x > 65536 or size.y > 65536:
        return _fail("Source dimensions outside donor encoding range")
    for key in ["source", "mask", "donors"]:
        if not p.get(key) is Dictionary: return _fail("Missing PNG descriptor: " + key)
    var source := _load_png(p.source, size)
    if source == null: return _fail(last_error)
    var mask := _load_png(p.mask, size)
    if mask == null: return _fail(last_error)
    var donors := _load_png(p.donors, size)
    if donors == null: return _fail(last_error)
    var texture := original.get_shader_parameter("source_texture") as Texture2D
    var fallback := original.get_shader_parameter("opaque_skin") as Texture2D
    if texture == null or fallback == null or texture.get_size() != Vector2(size) or fallback.get_size() != Vector2(size):
        return _fail("Source/fallback texture dimensions differ from frozen source")
    var base := texture.get_image()
    if base == null: return _fail("Source texture pixels unavailable")
    if base.is_compressed() and base.decompress() != OK: return _fail("Cannot decode source texture")
    base.convert(Image.FORMAT_RGBA8)
    # The accepted shader uses filter_nearest WITHOUT mipmap sampling. get_data()
    # also includes imported mip levels, whereas a PNG snapshot stores level 0.
    # Compare every base-level RGBA byte, not unrelated unused mip storage.
    var base_had_mipmaps := base.has_mipmaps()
    if base_had_mipmaps: base.clear_mipmaps()
    # Never Color.srgb_to_linear() or an opaque-only selection for validation.
    if base.get_data() != source.get_data(): return _fail("Material source differs from frozen decoded source PNG")
    var mask_bytes := mask.get_data()
    var donor_bytes := donors.get_data()
    var source_bytes := source.get_data()
    var count := 0
    for pixel in range(size.x * size.y):
        var offset := pixel * 4
        if mask_bytes[offset] != 0 and mask_bytes[offset] != 255:
            return _fail("Mask red channel must be binary 0/255")
        if mask_bytes[offset] == 0: continue
        var x := int(donor_bytes[offset]) * 256 + int(donor_bytes[offset + 1])
        var y := int(donor_bytes[offset + 2]) * 256 + int(donor_bytes[offset + 3])
        if x >= size.x or y >= size.y: return _fail("Donor coordinate outside source")
        var donor_offset := (y * size.x + x) * 4
        if source_bytes[donor_offset + 3] < 243 or mask_bytes[donor_offset] != 0:
            return _fail("Donor must be opaque source skin outside the exclusion mask")
        count += 1
    if count == 0: return _fail("Empty exclusion mask")
    var shader_origin: String = original.shader.resource_path
    if shader_origin.is_empty(): shader_origin = p.get("shader_origin", "")
    var code := _expand_includes(original.shader.code, shader_origin)
    if not last_error.is_empty(): return _fail(last_error)
    if not _sampler_is_native_nearest(code, "source_texture") or not _sampler_is_native_nearest(code, "opaque_skin"):
        return _fail("Original source/fallback must use source_color, nearest, repeat_disable")
    var wrapped := _wrap_samples(code)
    if not last_error.is_empty(): return _fail(last_error)
    code = wrapped.code
    var template_path: String = get_script().resource_path.get_base_dir().path_join(TEMPLATE)
    if not FileAccess.file_exists(template_path): return _fail("Missing shader template")
    var first_function := RegEx.new()
    first_function.compile('(?m)^(?:void|float|int|bool|vec[234]|ivec[234]|mat[234])\\s+\\w+\\s*\\(')
    var found := first_function.search(code)
    if found == null: return _fail("Cannot find original shader function boundary")
    var injected := FileAccess.get_file_as_string(template_path)
    code = code.substr(0, found.get_start()) + injected + "\n" + code.substr(found.get_start())
    # Shallow duplication preserves every existing parameter/resource. Only the
    # duplicated material receives the new shader/data maps; no GLB/UV edits.
    var material := original.duplicate() as ShaderMaterial
    var shader := Shader.new()
    shader.code = code
    material.shader = shader
    material.set_shader_parameter("ink_mask", ImageTexture.create_from_image(mask))
    material.set_shader_parameter("ink_donors", ImageTexture.create_from_image(donors))
    material.set_shader_parameter("ink_source_size", Vector2(size))
    material.set_shader_parameter("ink_mode", mode)
    mesh.set_surface_override_material(0, material)
    last_receipt = {"species":species, "mode":mode, "mesh":"Closed_body", "surface":0,
        "masked_source_texels":count, "sample_calls":wrapped.sample_calls,
        "source_base_level_all_rgba_equal":true, "source_unused_mipmaps_removed_for_comparison":base_had_mipmaps,
        "model_sha256":p.model_sha256, "source_sha256":p.source.sha256,
        "mask_sha256":p.mask.sha256, "donors_sha256":p.donors.sha256}
    return 1
