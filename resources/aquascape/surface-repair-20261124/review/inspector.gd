extends SceneTree

const Interior = preload("res://scripts/aquarium/tank_design/ShellInterior.gd")
const LitCurrent = preload("res://scripts/aquarium/tank_design/RootedCurrent.gd")
const Contents = preload("res://scripts/aquarium/tank_design/ShellContentsView.gd")
const DESIGN := {"kind":"rect", "width":15.0, "depth":8.0, "height":5.1, "radii":[0,0,0,0]}
const START_ID := "dragon_stone"

var assets: Dictionary
var selected := START_ID
var search := LineEdit.new()
var eligible := CheckButton.new()
var only_repairs := CheckButton.new()
var list := ItemList.new()
var rotate_hint := Label.new()
var item_title := Label.new()
var cover := CheckButton.new()
var split := CheckButton.new()
var repaint := CheckButton.new()
var gray := CheckButton.new()
var compare_mode := OptionButton.new()
var neutral := StandardMaterial3D.new()
var repaired_ids: Dictionary = {}
var reference_models: Dictionary = {}
var review_cache: Dictionary = {}
var light := HSlider.new()
var algae_area: HSlider
var algae_strength: HSlider
var grow_shader := Shader.new()
var grow_texture: ImageTexture
var motion_metadata: Dictionary = {}
var preview_row := HBoxContainer.new()
var panes: Array[Dictionary] = []
var azimuth := 22.0
var elevation := 14.0
var zoom := 1.0
var fore := Vector2.ZERO

func _initialize() -> void:
    setup.call_deferred()

func area_theme() -> Theme:
    var palette := Theme.new()
    palette.default_font_size = 16
    palette.set_color("font_color", "Label", Color("#ecf2f2"))
    palette.set_color("font_color", "Button", Color("#e0eeee"))
    palette.set_color("font_color", "ItemList", Color("#cddadc"))
    palette.set_color("font_selected_color", "ItemList", Color("#ffffff"))
    palette.set_stylebox("panel", "ItemList", flat("#212b30", 8, 8))
    palette.set_stylebox("selected", "ItemList", flat("#2c5557", 5, 3))
    palette.set_stylebox("selected_focus", "ItemList", flat("#2c5557", 5, 3))
    return palette

func flat(color: String, padding: int, rounding: int) -> StyleBoxFlat:
    var box := StyleBoxFlat.new()
    box.bg_color = Color(color)
    box.set_corner_radius_all(rounding)
    box.content_margin_left = padding
    box.content_margin_right = padding
    box.content_margin_top = padding
    box.content_margin_bottom = padding
    return box

func setup() -> void:
    neutral.albedo_color = Color("#929695")
    neutral.roughness = 1.0
    assets = Interior.assets().duplicate()
    var folder: String = get_script().resource_path.get_base_dir()
    grow_shader.code = FileAccess.get_file_as_string(folder.path_join("algae-preview.gdshader"))
    var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(folder.path_join("../release.json")))
    var args := OS.get_cmdline_user_args()
    var baseline := args.find("--baseline")
    for row: Dictionary in manifest.items:
        repaired_ids[row.id] = true
        if baseline >= 0 and baseline + 1 < args.size():
            var path := args[baseline + 1].path_join(row.id + ".glb")
            if FileAccess.file_exists(path):
                reference_models[row.id] = path
    var grow_image := Image.load_from_file(folder.path_join("algae-grow.png"))
    grow_texture = ImageTexture.create_from_image(grow_image)
    if not assets.has(selected):
        selected = assets.keys()[0]
    root.title = "潮汐馆 · 缸体定制原型 · 造景材质审查"
    root.min_size = Vector2i(820, 550)
    var actual := DisplayServer.screen_get_usable_rect(DisplayServer.get_primary_screen())
    root.current_screen = DisplayServer.get_primary_screen()
    root.size = Vector2i(Vector2(actual.size) * Vector2(.80, .78))
    root.position = actual.position + (actual.size - root.size) / 2
    root.set_flag(Window.FLAG_NO_FOCUS, true)

    var surface := PanelContainer.new()
    surface.theme = area_theme()
    surface.add_theme_stylebox_override("panel", flat("#192226", 16, 0))
    root.add_child(surface)
    surface.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    var page := HBoxContainer.new()
    page.add_theme_constant_override("separation", 18)
    surface.add_child(page)
    var index := VBoxContainer.new()
    index.custom_minimum_size.x = 230
    index.add_theme_constant_override("separation", 8)
    page.add_child(index)
    var index_heading := Label.new()
    index_heading.text = "布景  ·  %d" % Interior.assets().size()
    index_heading.add_theme_font_size_override("font_size", 20)
    index.add_child(index_heading)
    search.placeholder_text = "搜索布景名称"
    index.add_child(search)
    search.text_changed.connect(func(_text: String) -> void: filter_list())
    eligible.text = "只看可覆藻"
    index.add_child(eligible)
    eligible.toggled.connect(func(_enabled: bool) -> void: filter_list())
    only_repairs.text = "只看本轮修版  ·  %d" % repaired_ids.size()
    only_repairs.button_pressed = true
    only_repairs.toggled.connect(func(_enabled: bool) -> void: filter_list())
    index.add_child(only_repairs)
    list.size_flags_vertical = Control.SIZE_EXPAND_FILL
    index.add_child(list)
    list.item_selected.connect(choose)

    var main := VBoxContainer.new()
    main.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    main.add_theme_constant_override("separation", 8)
    page.add_child(main)
    item_title.add_theme_font_size_override("font_size", 24)
    main.add_child(item_title)
    var actions := HBoxContainer.new()
    actions.add_theme_constant_override("separation", 8)
    main.add_child(actions)
    cover.text = "覆藻"
    cover.toggled.connect(func(_enabled: bool) -> void: apply_appearance())
    actions.add_child(cover)
    repaint.text = "看旧版"
    repaint.toggled.connect(func(_active: bool) -> void: apply_appearance())
    actions.add_child(repaint)
    gray.text = "灰模"
    gray.toggled.connect(func(_active: bool) -> void: apply_appearance())
    actions.add_child(gray)
    split.text = "并排对照"
    split.toggled.connect(func(_enabled: bool) -> void: apply_appearance())
    actions.add_child(split)
    compare_mode.add_item("原版与修版")
    compare_mode.add_item("原材质与覆藻")
    compare_mode.item_selected.connect(func(_i: int) -> void: apply_appearance())
    actions.add_child(compare_mode)
    var spacer := Control.new()
    spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    actions.add_child(spacer)
    var light_label := Label.new()
    light_label.text = "亮度"
    actions.add_child(light_label)
    light.custom_minimum_size.x = 102
    light.min_value = .35
    light.max_value = 1.65
    light.step = .05
    light.value = 1.0
    light.value_changed.connect(update_lights)
    actions.add_child(light)

    var film_settings := HBoxContainer.new()
    film_settings.add_theme_constant_override("separation", 12)
    main.add_child(film_settings)
    algae_area = labeled_slider(film_settings,"覆盖面积",.5)
    algae_strength = labeled_slider(film_settings,"浓淡",.72)

    var presets := HBoxContainer.new()
    presets.add_theme_constant_override("separation", 5)
    main.add_child(presets)
    for preset: Array in [["正面",0.0,0.0],["背面",180.0,0.0],["左侧",270.0,0.0],["右侧",90.0,0.0],
            ["俯视",0.0,89.0],["仰视",0.0,-89.0]]:
        var button := Button.new()
        button.text = preset[0]
        button.pressed.connect(set_angle.bind(float(preset[1]),float(preset[2])))
        presets.add_child(button)
    var reset := Button.new()
    reset.text = "重置视角"
    reset.pressed.connect(reset_view)
    presets.add_child(reset)
    preview_row.size_flags_vertical = Control.SIZE_EXPAND_FILL
    preview_row.add_theme_constant_override("separation", 6)
    main.add_child(preview_row)
    panes.append(build_pane())
    panes.append(build_pane())
    rotate_hint.text = "拖动旋转   ·   滚轮缩放   ·   右键拖动平移   ·   A 切换覆藻"
    rotate_hint.modulate = Color("#a2b4b8")
    main.add_child(rotate_hint)

    filter_list()
    split.set_pressed_no_signal(true)
    choose_selection()
    if DisplayServer.get_name() != "headless":
        root.show()
        if not args.is_empty() and args[0].ends_with(".gdextension"):
            GDExtensionManager.load_extension(args[0])
        root.set_flag(Window.FLAG_NO_FOCUS,false)
    root.window_input.connect(keyboard)
    var check_arg := args.find("--check")
    if check_arg >= 0 and check_arg + 1 < args.size():
        await check(args[check_arg + 1])

func labeled_slider(row: HBoxContainer, title: String, initial: float) -> HSlider:
    var label := Label.new()
    label.text = title
    row.add_child(label)
    var slider := HSlider.new()
    slider.min_value = 0.0
    slider.max_value = 1.0
    slider.step = .01
    slider.value = initial
    slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    slider.custom_minimum_size.x = 62
    row.add_child(slider)
    var value := Label.new()
    value.custom_minimum_size.x = 40
    value.text = "%d%%" % roundi(initial * 100)
    row.add_child(value)
    slider.value_changed.connect(func(fraction: float) -> void:
        value.text = "%d%%" % roundi(fraction * 100)
        apply_algae_sliders())
    return slider

func build_pane() -> Dictionary:
    var pane := PanelContainer.new()
    pane.add_theme_stylebox_override("panel", flat("#121c21", 1, 0))
    pane.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    preview_row.add_child(pane)
    var column := VBoxContainer.new()
    column.add_theme_constant_override("separation", 0)
    pane.add_child(column)
    var caption := Label.new()
    caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    caption.custom_minimum_size.y = 25
    column.add_child(caption)
    var child := SubViewportContainer.new()
    child.size_flags_vertical = Control.SIZE_EXPAND_FILL
    child.stretch = true
    child.mouse_default_cursor_shape = Control.CURSOR_DRAG
    child.gui_input.connect(view_input)
    column.add_child(child)
    var viewport := SubViewport.new()
    viewport.own_world_3d = true
    viewport.render_target_update_mode = SubViewport.UPDATE_WHEN_VISIBLE
    viewport.msaa_3d = Viewport.MSAA_2X
    child.add_child(viewport)
    child.resized.connect(update_camera)
    var world := WorldEnvironment.new()
    world.environment = Environment.new()
    world.environment.background_mode = Environment.BG_COLOR
    world.environment.background_color = Color("#40535a")
    world.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    world.environment.ambient_light_color = Color("#e3edf2")
    world.environment.ambient_light_energy = .50
    viewport.add_child(world)
    var key := DirectionalLight3D.new()
    key.rotation_degrees = Vector3(-47,-27,0)
    key.light_energy = .68
    viewport.add_child(key)
    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-23,142,0)
    fill.light_energy = .30
    viewport.add_child(fill)
    var holder := MeshInstance3D.new()
    viewport.add_child(holder)
    var contents := Contents.new()
    holder.add_child(contents)
    var camera := Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    viewport.add_child(camera)
    camera.make_current()
    return {"node":pane, "viewport":viewport, "camera":camera, "caption":caption,
        "contents":contents, "world":world, "key":key, "fill":fill}

func filter_list() -> void:
    list.clear()
    var query := search.text.strip_edges().to_lower()
    for id: String in assets:
        var row: Dictionary = assets[id]
        if only_repairs.button_pressed and not repaired_ids.has(id):
            continue
        if eligible.button_pressed and not Interior.supports_algae(id):
            continue
        if not query.is_empty() and not row.name_zh.contains(query) and not id.contains(query):
            continue
        var i := list.add_item(row.name_zh)
        list.set_item_metadata(i,id)
        if id == selected:
            list.select(i)
            list.ensure_current_is_visible()
    if list.get_selected_items().is_empty() and list.item_count > 0:
        list.select(0)
        choose(0)

func choose(i: int) -> void:
    selected = list.get_item_metadata(i)
    zoom = 1.0
    fore = Vector2.ZERO
    choose_selection()

func choose_selection() -> void:
    item_title.text = assets[selected].name_zh
    if not Interior.supports_algae(selected):
        cover.set_pressed_no_signal(false)
        if not reference_models.has(selected):
            split.set_pressed_no_signal(false)
    repaint.set_pressed_no_signal(false)
    gray.set_pressed_no_signal(false)
    apply_appearance()

func mesh_of_preview(path: String) -> Mesh:
    if not review_cache.has(path):
        var importer := GLTFDocument.new()
        var data := GLTFState.new()
        var status := importer.append_from_file(path,data)
        assert(status == OK, path)
        var mesh_tree := importer.generate_scene(data)
        var mesh: MeshInstance3D = mesh_tree.find_children("*","MeshInstance3D",true,false)[0]
        review_cache[path] = mesh.mesh
        mesh_tree.free()
    return review_cache[path]

func sync(pane: Dictionary, is_coated: bool, use_reference := false) -> void:
    var item := {"id":selected,"u":.5,"v":.5}
    if is_coated:
        item["algae"] = true
    pane.contents.sync({"design":DESIGN},{"substrate":"fine_sand","depth_cm":12.0,"brightness":0.0,"props":[item]})
    pane.caption.text = "覆藻" if is_coated else ("旧版" if use_reference else "当前版")
    if gray.button_pressed:
        pane.caption.text += "灰模"
    var instance: Node3D = pane.contents.props[0].root
    for mesh: MeshInstance3D in instance.find_children("*","MeshInstance3D",true,false):
        mesh.material_override = neutral if gray.button_pressed else null
    if reference_models.has(selected):
        var view_mesh: MeshInstance3D = instance.find_children("*","MeshInstance3D",true,false)[0]
        if pane.get("current_instance") != instance:
            pane.base_mesh = view_mesh.mesh
        view_mesh.mesh = mesh_of_preview(reference_models[selected]) if use_reference else pane.base_mesh
    if pane.get("current_instance") == instance and pane.get("current_reference") == use_reference:
        return
    pane.current_instance = instance
    pane.current_reference = use_reference
    pane.algae_materials = []
    if is_coated:
        for mesh: MeshInstance3D in instance.find_children("*","MeshInstance3D",true,false):
            for surface in mesh.mesh.get_surface_count():
                var standard := mesh.get_active_material(surface) as ShaderMaterial
                if standard == null or not (standard.shader == Interior.Algae.FILM_SHADER or standard.shader == grow_shader):
                    continue
                var variant := ShaderMaterial.new()
                variant.shader = grow_shader
                var source: BaseMaterial3D = mesh.mesh.surface_get_material(surface)
                variant.set_shader_parameter("stone_art",source.albedo_texture)
                variant.set_shader_parameter("algae_art",grow_texture)
                variant.set_shader_parameter("tiles_per_model_unit",standard.get_shader_parameter("tiles_per_model_unit"))
                mesh.set_surface_override_material(surface,variant)
                pane.algae_materials.append(variant)
    bind_existing_current(pane,instance)

func bind_existing_current(pane: Dictionary, instance: Node3D) -> void:
    var row: Dictionary = assets[selected]
    pane.motion = "静态"
    if row.has("rooted_current"):
        pane.motion = "水流摆动"
        return
    if not row.get("animated",false):
        return
    if row.get("deformation") == "shader":
        var source: String = row.shader_metadata
        if not motion_metadata.has(source):
            var doc: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(source))
            motion_metadata[source] = {}
            for data: Dictionary in doc.outputs:
                motion_metadata[source][data.id] = data
        var config: Dictionary = motion_metadata[source][selected].duplicate()
        config.amplitude = .10
        for mesh: MeshInstance3D in instance.find_children("*","MeshInstance3D",true,false):
            LitCurrent.apply(mesh,config)
        pane.motion = "水流摆动"
        return
    for player: AnimationPlayer in instance.find_children("*","AnimationPlayer",true,false):
        for name in player.get_animation_list():
            if String(name).ends_with("WaterSway"):
                player.get_animation(name).loop_mode = Animation.LOOP_LINEAR
                player.play(name)
                pane.motion = "水流摆动"
                break

func apply_algae_sliders() -> void:
    for pane in panes:
        for paint: ShaderMaterial in pane.get("algae_materials",[]):
            paint.set_shader_parameter("coverage_area",algae_area.value)
            paint.set_shader_parameter("color_strength",algae_strength.value)

func apply_appearance() -> void:
    var supported := Interior.supports_algae(selected)
    var has_reference := reference_models.has(selected)
    var comparing := split.button_pressed and (supported or has_reference)
    var side_by_side_algae := comparing and supported and not gray.button_pressed and (not has_reference or compare_mode.selected == 1)
    compare_mode.visible = comparing and supported and has_reference and not gray.button_pressed
    split.disabled = not (supported or has_reference) or (gray.button_pressed and not has_reference)
    cover.disabled = not supported or comparing or gray.button_pressed
    cover.tooltip_text = "" if supported else "这个布景没有覆藻材质"
    repaint.visible = has_reference
    repaint.disabled = comparing
    algae_area.editable = supported and not gray.button_pressed and (not comparing or side_by_side_algae)
    algae_strength.editable = algae_area.editable
    panes[1].node.visible = comparing and (not gray.button_pressed or has_reference)
    sync(panes[0], cover.button_pressed and not comparing and not gray.button_pressed,
        has_reference and (not side_by_side_algae if comparing else repaint.button_pressed))
    if panes[1].node.visible:
        sync(panes[1], side_by_side_algae)
    if assets[selected].get("category") == "plant":
        item_title.text = "%s  ·  %s" % [assets[selected].name_zh, panes[0].motion]
    apply_algae_sliders()
    update_camera.call_deferred()

func update_lights(intensity: float) -> void:
    for pane in panes:
        pane.world.environment.ambient_light_energy = .50 * intensity
        pane.key.light_energy = .68 * intensity
        pane.fill.light_energy = .30 * intensity

func set_angle(a: float, e: float) -> void:
    azimuth = a
    elevation = e
    update_camera()

func reset_view() -> void:
    zoom = 1.0
    fore = Vector2.ZERO
    set_angle(22.0,14.0)

func view_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.pressed:
        if event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
            zoom = clampf(zoom * (1.12 if event.button_index == MOUSE_BUTTON_WHEEL_UP else .89),.35,5.0)
            update_camera()
    elif event is InputEventMouseMotion:
        if event.button_mask & MOUSE_BUTTON_MASK_LEFT:
            azimuth = fposmod(azimuth - event.relative.x * .40,360.0)
            elevation = clampf(elevation + event.relative.y * .32,-89.0,89.0)
            update_camera()
        elif event.button_mask & (MOUSE_BUTTON_MASK_RIGHT | MOUSE_BUTTON_MASK_MIDDLE):
            fore += Vector2(-event.relative.x,event.relative.y) * .002 / zoom
            update_camera()

func keyboard(event: InputEvent) -> void:
    if not event is InputEventKey or not event.pressed or event.echo or root.gui_get_focus_owner() == search:
        return
    if event.keycode == KEY_A and not cover.disabled:
        cover.button_pressed = not cover.button_pressed
    elif event.keycode == KEY_ESCAPE:
        quit()

func update_camera() -> void:
    var a := deg_to_rad(azimuth)
    var e := deg_to_rad(elevation)
    var ray := Vector3(sin(a)*cos(e),sin(e),cos(a)*cos(e))
    var common_size := 0.0
    for pane in panes:
        if not pane.node.visible:
            continue
        var box: AABB
        if pane.contents.props.is_empty():
            continue
        var prop: Dictionary = pane.contents.props[0]
        box = prop.root.transform * prop.bounds
        var camera: Camera3D = pane.camera
        var p := box.get_center()
        camera.look_at_from_position(p + ray * (5 + box.size.length() * 2),p)
        var h := camera.basis.x.abs().dot(box.size)
        var v := camera.basis.y.abs().dot(box.size)
        var area: Vector2i = pane.viewport.size
        common_size = maxf(common_size,maxf(.04,maxf(v,h*maxf(1,area.y)/maxf(1,area.x)) * 1.24 / zoom))
        camera.h_offset = fore.x * box.size.length()
        camera.v_offset = fore.y * box.size.length()
    for pane in panes:
        if pane.node.visible:
            pane.camera.size = maxf(.04,common_size)

func first_mesh(pane: Dictionary) -> MeshInstance3D:
    return pane.contents.props[0].root.find_children("*","MeshInstance3D",true,false)[0]

func fail_check(error: String) -> void:
    push_error(error)
    quit(1)

func check(path: String) -> void:
    only_repairs.button_pressed = false
    selected = "reef_through_arch"
    choose_selection()
    split.button_pressed = false
    var mesh := first_mesh(panes[0]).mesh
    cover.button_pressed = true
    if first_mesh(panes[0]).mesh != mesh or not first_mesh(panes[0]).get_active_material(0) is ShaderMaterial:
        fail_check("Toggle did not apply native algae to the selected model.")
        return
    cover.button_pressed = false
    if not first_mesh(panes[0]).get_active_material(0) is StandardMaterial3D:
        fail_check("Toggle did not restore the original material.")
        return
    split.button_pressed = true
    reset_view()
    if first_mesh(panes[0]).mesh != first_mesh(panes[1]).mesh:
        fail_check("Side-by-side model differs.")
        return
    for _tick in 4:
        await process_frame
    RenderingServer.force_draw(false)
    if root.get_texture().get_image().save_png(path) != OK:
        fail_check("Could not save comparison capture.")
        return
    eligible.button_pressed = true
    var shown := list.item_count
    var comparison_transform: Transform3D = panes[1].camera.transform
    var variant: ShaderMaterial = first_mesh(panes[1]).get_active_material(0)
    algae_area.value = .84
    algae_strength.value = .38
    if variant.get_shader_parameter("coverage_area") != .84 or variant.get_shader_parameter("color_strength") != .38 or panes[1].camera.transform != comparison_transform:
        fail_check("A slider did not update the material independently of the camera.")
        return
    await capture_file(path.get_base_dir().path_join("algae-area-high-strength-low.png"))
    algae_area.value = .24
    algae_strength.value = .90
    await capture_file(path.get_base_dir().path_join("algae-area-low-strength-high.png"))
    for i in list.item_count:
        if not Interior.supports_algae(list.get_item_metadata(i)):
            fail_check("Filter returned a prop without algae.")
            return
    var legacy := 0
    for id: String in assets:
        if assets[id].get("animated",false):
            selected = id
            choose_selection()
            if panes[0].motion != "水流摆动":
                fail_check("Existing water current could not be attached: " + id)
                return
            legacy += 1
            await process_frame
    eligible.button_pressed = false
    for id: String in ["treasure_chest","shipwreck","dragon_stone","slate_cave","rock"]:
        if not reference_models.has(id):
            continue
        selected = id
        choose_selection()
        split.button_pressed = true
        if first_mesh(panes[0]).mesh == first_mesh(panes[1]).mesh:
            fail_check("Historical comparison did not load: " + id)
            return
        await capture_file(path.get_base_dir().path_join(id+"-comparison.png"))
        if not is_equal_approx(panes[0].camera.size,panes[1].camera.size):
            fail_check("Material comparison drifted in scale: " + id)
            return
        set_angle(90.,7.)
        await capture_file(path.get_base_dir().path_join(id+"-ends.png"))
        reset_view()
        gray.button_pressed = true
        await capture_file(path.get_base_dir().path_join(id+"-gray-pair.png"))
        gray.button_pressed = false
    selected = "dragon_stone"
    choose_selection()
    split.button_pressed = true
    compare_mode.select(1)
    apply_appearance()
    var dark := first_mesh(panes[1]).get_active_material(0) as ShaderMaterial
    var base := first_mesh(panes[0]).get_active_material(0) as StandardMaterial3D
    if dark == null or base == null or dark.get_shader_parameter("stone_art") != base.albedo_texture:
        fail_check("Algae comparison replaced the revised base artwork.")
        return
    only_repairs.button_pressed = true
    if list.item_count != repaired_ids.size():
        fail_check("Repair filter does not match the released manifest.")
        return
    print("Review ready: %d assets, %d with algae, %d restored legacy plant motions. Toggle, split, filter and sliders verified." % [Interior.assets().size(),shown,legacy])
    quit()

func capture_file(path: String) -> void:
    for _i in 4:
        await process_frame
    RenderingServer.force_draw(false)
    var status := root.get_texture().get_image().save_png(path)
    assert(status == OK,path)
