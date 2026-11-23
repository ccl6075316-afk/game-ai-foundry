extends SceneTree

const Interior = preload("res://scripts/aquarium/tank_design/ShellInterior.gd")
const Contents = preload("res://scripts/aquarium/tank_design/ShellContentsView.gd")
var holder: MeshInstance3D
var contents: Contents
var camera: Camera3D
var title: Label

func _initialize() -> void:
    review.call_deferred()

func review() -> void:
    var args := OS.get_cmdline_user_args()
    var primary := DisplayServer.get_primary_screen()
    var frame := DisplayServer.screen_get_usable_rect(primary)
    root.current_screen = primary
    root.size = (Vector2(frame.size) * .68).floor()
    root.position = frame.position + (frame.size - root.size) / 2
    root.title = "潮汐馆 · 缸体定制原型 · 石面覆藻对照"
    root.set_flag(Window.FLAG_NO_FOCUS, true)
    root.show()
    GDExtensionManager.load_extension(args[0])
    var environment := WorldEnvironment.new()
    var settings := Environment.new()
    settings.background_mode = Environment.BG_COLOR
    settings.background_color = Color("#3d5361")
    settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    settings.ambient_light_color = Color("#d1e6f1")
    settings.ambient_light_energy = .55
    environment.environment = settings
    root.add_child(environment)
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-54, -27, 0)
    sun.light_energy = .67
    root.add_child(sun)
    var fill := DirectionalLight3D.new()
    fill.rotation_degrees = Vector3(-15, 145, 0)
    fill.light_energy = .23
    root.add_child(fill)
    camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    root.add_child(camera)
    holder = MeshInstance3D.new()
    root.add_child(holder)
    contents = Contents.new()
    holder.add_child(contents)
    title = Label.new()
    title.position = Vector2(24, 16)
    title.add_theme_font_size_override("font_size", 22)
    root.add_child(title)
    var design := {"kind":"rect", "width":15.0, "depth":8.0, "height":5.1, "radii":[0,0,0,0]}
    var output := args[1]
    DirAccess.make_dir_recursive_absolute(output)
    for id: String in Interior.assets().keys().filter(Interior.supports_algae):
        for enabled: bool in [false, true]:
            var props := [{"id": id, "u": .5, "v": .5}]
            if enabled:
                props[0].algae = true
            contents.sync({"design":design}, {"substrate":"fine_sand", "depth_cm":12.0, "props":props})
            var entry: Dictionary = contents.props[0]
            var bounds: AABB = entry.root.transform * entry.bounds
            var target := bounds.get_center()
            camera.look_at_from_position(target + Vector3(.33,.29,1) * 6, target)
            camera.size = 1.24 * maxf(bounds.size.y, bounds.size.x * .73)
            title.text = "%s  ·  %s" % [Interior.assets()[id].name_zh, "开启覆藻" if enabled else "原材质"]
            for tick in 2:
                await process_frame
            RenderingServer.force_draw(false)
            if root.get_texture().get_image().save_png(output.path_join(id + ("-film.png" if enabled else "-base.png"))) != OK:
                push_error("Could not capture " + id)
                quit(1)
                return
    quit()
