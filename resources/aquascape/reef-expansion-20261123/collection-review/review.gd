extends SceneTree

const Contents = preload("res://scripts/aquarium/tank_design/ShellContentsView.gd")
const Design = preload("res://scripts/aquarium/tank_design/ShellDesign.gd")
const Interior = preload("res://scripts/aquarium/tank_design/ShellInterior.gd")
const Finished = preload("res://scripts/aquarium/tank_design/FinishedShell.gd")

var layouts: Array
var design: Dictionary
var view: SubViewport
var stage: Node3D
var camera: Camera3D
var active := 0
var orbit := 0.0
var overhead := false
var empty := false
var status: Label
var results: Array[Dictionary] = []
var test_only := false
var assets: Dictionary


func _initialize() -> void:
    start.call_deferred()


func start() -> void:
    var args := OS.get_cmdline_user_args()
    if args.is_empty():
        push_error("Supply layouts.json before launch.")
        quit(2)
        return
    test_only = DisplayServer.get_name() == "headless"
    var fixture: Variant = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
    if not fixture is Dictionary:
        push_error("Could not read layout JSON.")
        quit(2)
        return
    design = fixture.design
    layouts = fixture.layouts
    assets = Interior.assets()
    view = SubViewport.new()
    view.own_world_3d = true
    view.size = Vector2i(1536, 960)
    view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    view.msaa_3d = Viewport.MSAA_4X
    root.add_child(view)
    if not test_only:
        set_window(args)
    var command := args[2] if args.size() > 2 else ""
    if not command.is_empty():
        if command == "--check" and args.size() > 3:
            await record(args[3], false)
        elif command == "--capture" and args.size() > 3 and not test_only:
            await record(args[3], true)
        else:
            push_error("Use --check DIRECTORY or --capture DIRECTORY.")
            quit(2)
    else:
        render()
        root.window_input.connect(on_input)


func set_window(args: PackedStringArray) -> void:
    var screen := DisplayServer.get_primary_screen()
    var bounds := DisplayServer.screen_get_usable_rect(screen)
    root.set_flag(Window.FLAG_NO_FOCUS, true)
    root.title = "潮汐馆 · 缸体定制原型 · 造景组合试放"
    root.current_screen = screen
    var factor := minf(.82 * bounds.size.x / 1280.0, .82 * bounds.size.y / 800.0)
    root.size = Vector2i(Vector2(1280, 800) * factor)
    root.position = bounds.position + (bounds.size - root.size) / 2
    var screen_preview := TextureRect.new()
    screen_preview.texture = view.get_texture()
    screen_preview.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
    screen_preview.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
    root.add_child(screen_preview)
    screen_preview.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    status = Label.new()
    status.position = Vector2(16, 12)
    status.add_theme_font_size_override("font_size", 16)
    status.add_theme_color_override("font_shadow_color", Color("#183344"))
    status.add_theme_constant_override("shadow_offset_y", 2)
    root.add_child(status)
    root.show()
    if args.size() > 1 and args[1].ends_with(".gdextension"):
        GDExtensionManager.load_extension(args[1])
    root.set_flag(Window.FLAG_NO_FOCUS, false)


func lighting(layout: Dictionary) -> void:
    var settings := Environment.new()
    settings.background_mode = Environment.BG_COLOR
    settings.background_color = Color(layout.backdrop_bottom)
    settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    settings.ambient_light_color = Color("#dce9e9") if active == 0 else Color("#e9efe0")
    settings.ambient_light_energy = .28
    settings.fog_enabled = true
    settings.fog_light_color = Color(layout.fog_color)
    settings.fog_light_energy = .56
    settings.fog_density = .017 if active == 0 else .010
    var env := WorldEnvironment.new()
    env.environment = settings
    stage.add_child(env)
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-40, -35, 0)
    sun.light_color = Color("#f9f1df")
    sun.light_energy = .63
    sun.shadow_enabled = true
    sun.directional_shadow_max_distance = 36.0
    stage.add_child(sun)
    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-31, 135, 0)
    fill.light_color = Color("#9ecadc") if active == 0 else Color("#c1d2a2")
    fill.light_energy = .18
    stage.add_child(fill)


func bed_mesh(data: Dictionary) -> MeshInstance3D:
    var path := Design.contour(design)
    var triangles := Geometry2D.triangulate_polygon(path)
    var bed := MeshInstance3D.new()
    var surface := ImmediateMesh.new()
    # Production substrate material, UV scale and bed elevation. The front
    # window is open for an unobstructed placement review.
    var substrate := Finished.paint(data.substrate).duplicate() as StandardMaterial3D
    substrate.albedo_color = Color("#ebe4d6") if active == 0 else Color("#bfc3bb")
    substrate.roughness = 1.0
    substrate.emission_energy_multiplier = .026
    if not test_only:
        var texels := substrate.albedo_texture.get_image()
        if texels != null and not texels.is_empty():
            if texels.is_compressed():
                texels.decompress()
            if texels.generate_mipmaps() == OK:
                substrate.albedo_texture = ImageTexture.create_from_image(texels)
                substrate.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
    Finished.cap(surface, path, triangles, data.depth_cm * .01, substrate)
    Finished.band(surface, path, -.25, data.depth_cm * .01, Finished.paint("rim"))
    bed.mesh = surface
    stage.add_child(bed)
    return bed


func backdrop(layout: Dictionary) -> void:
    var mesh := QuadMesh.new()
    mesh.size = Vector2(100, 40)
    var instance := MeshInstance3D.new()
    instance.mesh = mesh
    instance.position = Vector3(0, 1.1, -11.2)
    instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    var shader := Shader.new()
    shader.code = """
shader_type spatial;
render_mode unshaded, cull_disabled, fog_disabled;
uniform vec3 low_color: source_color;
uniform vec3 high_color: source_color;
varying vec3 local_position;
void vertex() { local_position=VERTEX; }
void fragment() {
    float light = smoothstep(-4.0, 6.0, local_position.y);
    ALBEDO = mix(low_color, high_color, light);
}
"""
    var paint := ShaderMaterial.new()
    paint.shader = shader
    paint.set_shader_parameter("low_color", Color(layout.backdrop_bottom))
    paint.set_shader_parameter("high_color", Color(layout.backdrop_top))
    instance.material_override = paint
    stage.add_child(instance)


func to_prop(row: Dictionary, id: String) -> Dictionary:
    var footprint := Interior.bounds(design)
    var uv := (Vector2(row.at[0], row.at[1]) - footprint.position) / footprint.size
    var horizontal := float(row.size) * float(row.get("footprint_scale", 1.0))
    return {"id":id, "u":uv.x, "v":uv.y, "rotation":[0,deg_to_rad(row.yaw),0],
            "stretch":[horizontal,row.size,horizontal]}


func support_faces(node: Node3D) -> PackedVector3Array:
    var result := PackedVector3Array()
    for mesh: MeshInstance3D in node.find_children("*", "MeshInstance3D", true, false):
        for p: Vector3 in mesh.mesh.get_faces():
            result.append(mesh.global_transform * p)
    return result


func seat(row: Dictionary, faces: PackedVector3Array) -> Vector3:
    var result := Vector3.INF
    var score := INF
    for i in range(-2, 3):
        for j in range(-2, 3):
            var offset := Vector2(i, j) * .125
            var from := Vector3(row.at[0] + offset.x, design.height, row.at[1] + offset.y)
            var high := -INF
            var grade := 0.0
            for k in range(0, faces.size(), 3):
                var intersect: Variant = Geometry3D.ray_intersects_triangle(
                    from, Vector3.DOWN, faces[k], faces[k+1], faces[k+2])
                if intersect is Vector3 and intersect.y > high:
                    high = intersect.y
                    grade = absf((faces[k+1] - faces[k]).cross(faces[k+2] - faces[k]).normalized().y)
            if high > .25 and grade > .42:
                var error := absf(high - row.top) + offset.length() * .73 + (1.0 - grade) * .14
                if error < score:
                    score = error
                    result = Vector3(from.x, high, from.z)
    return result


func render() -> Dictionary:
    if is_instance_valid(stage):
        stage.free()
    stage = Node3D.new()
    view.add_child(stage)
    var layout: Dictionary = layouts[active]
    var bed := {"depth_cm":layout.depth_cm, "substrate":layout.substrate, "brightness":0.25, "props":[]}
    lighting(layout)
    backdrop(layout)
    var holder := bed_mesh(bed)
    var contents := Contents.new()
    holder.add_child(contents)
    var base_rows: Array[Dictionary] = []
    var pending: Array[Dictionary] = []
    var absent: Array[String] = []
    var mounted: Dictionary = {}
    var fallback_count := 0
    var dropped := 0
    if not empty:
        for row: Dictionary in layout.items:
            var resolved := ""
            for id: String in row.ids:
                if assets.has(id):
                    resolved = id
                    break
            if resolved.is_empty():
                absent.append(row.ids[0])
                continue
            if resolved != row.ids[0]:
                fallback_count += 1
            var item := to_prop(row, resolved)
            if row.has("support"):
                pending.append({"row":row, "item":item})
            else:
                bed.props.append(item)
                base_rows.append(row)
        contents.sync({"design":design}, bed)
        var hosts := {}
        for i in contents.props.size():
            if base_rows[i].has("key"):
                hosts[base_rows[i].key] = contents.props[i].root
        var support_cache := {}
        for candidate in pending:
            var row: Dictionary = candidate.row
            if not hosts.has(row.support):
                dropped += 1
                continue
            if not support_cache.has(row.support):
                support_cache[row.support] = support_faces(hosts[row.support])
            var hit := seat(row, support_cache[row.support])
            if hit == Vector3.INF:
                dropped += 1
                continue
            var mounted_item: Dictionary = candidate.item
            var footprint := Interior.bounds(design)
            var uv := (Vector2(hit.x, hit.z) - footprint.position) / footprint.size
            mounted_item.u = uv.x
            mounted_item.v = uv.y
            mounted_item.lift_m = hit.y - bed.depth_cm * .01 - .022
            mounted[str(bed.props.size())] = {"support":row.support, "surface_y_m":hit.y}
            bed.props.append(mounted_item)
    contents.sync({"design":design}, bed)
    camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    stage.add_child(camera)
    camera.make_current()
    place_camera()
    if is_instance_valid(status):
        status.text = "%s   15 × 8 × 5.1 米    ·    1 / 2 换景    A / D 转向    V 顶视    B 空缸" % layout.title
    var audit_items: Array[Dictionary] = []
    var fits := 0
    var lane_clear := true
    var trail := Design.contour(design)
    for index in contents.props.size():
        var entry: Dictionary = contents.props[index]
        var pose: Transform3D = entry.root.transform
        var contained := Interior.prop_fits(pose, entry.bounds, trail, design.height)
        var effective: AABB = pose * entry.bounds
        fits += int(contained)
        lane_clear = lane_clear and effective.end.z <= float(layout.lane_z)
        var detail := {"id":entry.item.id, "catalog_model":assets[entry.item.id].model,
                       "origin_m":[pose.origin.x,pose.origin.y,pose.origin.z],
                       "bounds_end_z_m":effective.end.z, "fits":contained}
        if mounted.has(str(index)):
            detail["mount"] = mounted[str(index)]
        audit_items.append(detail)
    return {"layout":layout.id, "registry_count":assets.size(), "instantiated":contents.props.size(),
            "contained":fits, "front_lane_z_m":layout.lane_z,
            "front_lane_m":design.depth*.5-layout.lane_z, "lane_clear":lane_clear,
            "absent_ids":absent, "fallback_count":fallback_count,
            "attachment_count":mounted.size(), "dropped_mounts":dropped,
            "bed_valid":Finished.valid_interior(bed), "items":audit_items}


func place_camera() -> void:
    var layout: Dictionary = layouts[active]
    var p: Array = layout.eye
    var aim := Vector3(0, 1.08, -.18)
    var relative := Vector3(p[0], p[1], p[2]).rotated(Vector3.UP, orbit)
    camera.size = layout.camera_size
    if overhead:
        relative = Vector3(.001, 19.0, .001).rotated(Vector3.UP, orbit)
        aim = Vector3(0, .2, 0)
        camera.size = 10.8
    camera.look_at_from_position(aim + relative, aim, Vector3.FORWARD if overhead else Vector3.UP)


func on_input(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo:
        return
    match event.keycode:
        KEY_1, KEY_2, KEY_LEFT, KEY_RIGHT:
            active = 0 if event.keycode in [KEY_LEFT,KEY_1] else 1
            orbit = 0
            overhead = false
            render()
        KEY_A, KEY_D:
            orbit += 0.15 if event.keycode == KEY_A else -0.15
            place_camera()
        KEY_V:
            overhead = not overhead
            place_camera()
        KEY_B:
            empty = not empty
            render()
        KEY_ESCAPE:
            quit()


func record(out: String, image: bool) -> void:
    DirAccess.make_dir_recursive_absolute(out)
    var ok := true
    for i in layouts.size():
        active = i
        var result := render()
        if image:
            for tick in 3:
                await process_frame
            RenderingServer.force_draw(false)
            var screenshot := out.path_join(layouts[i].id + ".webp")
            if view.get_texture().get_image().save_webp(screenshot, true, .93) != OK:
                push_error("Failed to save " + screenshot)
                quit(3)
                return
            result["image"] = screenshot
        print("%s registry=%d game props=%d fits=%d mounts=%d dropped=%d lane=%s" %
            [result.layout,result.registry_count,result.instantiated,result.contained,
             result.attachment_count,result.dropped_mounts,result.lane_clear])
        ok = (ok and result.bed_valid and result.instantiated > 0
              and result.contained == result.instantiated and result.lane_clear
              and result.absent_ids.is_empty() and result.dropped_mounts == 0)
        results.append(result)
    var report := FileAccess.open(out.path_join("placement.json"), FileAccess.WRITE)
    if report == null:
        quit(3)
        return
    report.store_string(JSON.stringify({"ok":ok, "design":design, "poses_from":"ShellContentsView",
        "player_saves_accessed":0, "layouts":results}, "  ") + "\n")
    report.close()
    quit(0 if ok else 1)
