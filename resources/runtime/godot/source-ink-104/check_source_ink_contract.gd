extends SceneTree
## Headless grammar regression checks, not GPU/visual acceptance.
var failures: Array[String] = []

func _check(condition: bool, label: String) -> void:
    if not condition: failures.append(label)

func _init() -> void:
    var directory: String = get_script().resource_path.get_base_dir()
    var helper = load(directory.path_join("FishSourceInk.gd")).new()
    var declarations := "uniform sampler2D source_texture : source_color,filter_nearest,repeat_disable;\nuniform sampler2D opaque_skin : source_color,filter_nearest,repeat_disable;\n"
    var calls := "vec4 x=texture(source_texture, vec2(1.0,max(a,b))); vec4 y=texture(opaque_skin, f(uv));"
    for filename in ["FishBodyOpaque.gdshader", "FishFriendlyBody.gdshader"]:
        helper.last_error = ""
        var source := FileAccess.get_file_as_string(directory.get_base_dir().path_join(filename))
        var expanded: String = helper._expand_includes(source, "res://scripts/aquarium/" + filename)
        _check(helper.last_error.is_empty(), filename + " include expansion")
        _check(helper._sampler_is_native_nearest(expanded, "source_texture"), filename + " real source declaration")
        _check(helper._sampler_is_native_nearest(expanded, "opaque_skin"), filename + " real fallback declaration")
        var result: Dictionary = helper._wrap_samples(expanded)
        _check(helper.last_error.is_empty() and not result.is_empty(), filename + " wrapping")
        if result.is_empty(): continue
        _check(result.code.count(".a") == expanded.count(".a"), filename + " alpha expressions retained")
        _check(result.code.count("ALBEDO=") == expanded.count("ALBEDO="), filename + " final RGB logic retained")
    helper.last_error = ""
    var valid: Dictionary = helper._wrap_samples(declarations + "// texture(source_texture,wrong)\n" + calls)
    _check(helper.last_error.is_empty() and not valid.is_empty(), "comments ignored and nested UV valid")
    if not valid.is_empty():
        _check(valid.code.contains("ink_source_sample( vec2(1.0,max(a,b)))"), "nested UV expression retained")
        _check(valid.code.contains("// texture(source_texture,wrong)"), "comment not rewritten")
    for extra in [
        "texelFetch(source_texture,ivec2(0,0),0);",
        "texelFetch(opaque_skin,ivec2(0,0),0);",
        "textureLod(source_texture,uv,0.);",
        "texture(source_texture,uv,1.);",
        "custom_sampler(source_texture,uv);",
        "custom_sampler(uv,opaque_skin);",
        "sampler2D alias=source_texture;"
    ]:
        helper.last_error = ""
        var rejected: Dictionary = helper._wrap_samples(declarations + calls + extra)
        _check(rejected.is_empty() and not helper.last_error.is_empty(), "reject unsupported sampler use: " + extra)
    var nearest := "uniform sampler2D source_texture : source_color,filter_nearest,repeat_disable;"
    var linear := "uniform sampler2D source_texture : source_color,filter_linear,repeat_disable;"
    for fake in ["// " + nearest + "\n" + linear, "/* " + nearest + " */\n" + linear]:
        _check(not helper._sampler_is_native_nearest(fake, "source_texture"), "commented nearest cannot mask linear declaration")
    _check(not helper._sampler_is_native_nearest(nearest + nearest, "source_texture"), "duplicate real sampler declarations rejected")
    _check(helper._sampler_is_native_nearest("/* " + linear + " */" + nearest, "source_texture"), "commented linear does not reject real nearest")
    _check(not helper._sampler_is_native_nearest(nearest.replace("filter_nearest", "filter_nearest_mipmap"), "source_texture"), "mipmap sampler rejected")
    var snapshot := Image.create(4, 4, false, Image.FORMAT_RGBA8)
    snapshot.fill(Color(0.2, 0.4, 0.6, 1.0))
    snapshot.set_pixel(0, 0, Color(0.1, 0.2, 0.3, 0.0))
    var imported := snapshot.duplicate() as Image
    imported.generate_mipmaps()
    _check(imported.has_mipmaps() and imported.get_data().size() > snapshot.get_data().size(), "mip storage differs despite equal base level")
    imported.clear_mipmaps()
    _check(imported.get_data() == snapshot.get_data(), "clearing unused mips preserves every base RGBA byte")
    imported.set_pixel(0, 0, Color(0.8, 0.2, 0.3, 0.0))
    _check(imported.get_data() != snapshot.get_data(), "alpha-zero RGB remains part of strict equality")
    if failures.is_empty():
        print("source-ink-104 contract checks passed; GPU behavior remains unvalidated")
        quit(0)
    else:
        for failure in failures: push_error(failure)
        quit(1)
