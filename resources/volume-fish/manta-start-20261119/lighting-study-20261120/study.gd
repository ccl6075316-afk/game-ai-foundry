extends Node3D

const WATER := preload("res://water_light.gdshader")
const FPS := 30
const SEGMENT_FRAMES := 180
var asset: Node3D
var player: AnimationPlayer
var camera := Camera3D.new()
var key := DirectionalLight3D.new()
var skin := ShaderMaterial.new()
var sand := ShaderMaterial.new()
var caption := Label.new()
var clock_s := 0.0
var mode := 1
var close_up := false
var rendering := false

func _ready() -> void:
    var root_dir := ProjectSettings.globalize_path("res://")
    var path := root_dir.path_join("../surface-motion-03/manta.glb").simplify_path()
    var doc := GLTFDocument.new()
    var state := GLTFState.new()
    if doc.append_from_file(path,state) != OK:
        push_error(path)
        get_tree().quit(1)
        return
    asset = doc.generate_scene(state) as Node3D
    add_child(asset)
    var mesh: MeshInstance3D = asset.find_children("*","MeshInstance3D",true,false)[0]
    var source := mesh.get_active_material(0) as StandardMaterial3D
    skin.shader = WATER
    skin.set_shader_parameter("skin",source.albedo_texture)
    mesh.material_override = skin
    player = asset.find_child("AnimationPlayer",true,false)
    player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
    player.play("Cruise")
    player.pause()

    var floor_image := Image.load_from_file(root_dir.path_join("../../../../projects/fishing-2d/game/assets/aquascape-sand-v1/fine-sand.png").simplify_path())
    if floor_image == null or floor_image.is_empty():
        push_error("Game sand texture missing")
        get_tree().quit(1)
        return
    floor_image.generate_mipmaps()
    sand.shader = WATER
    sand.set_shader_parameter("grain",ImageTexture.create_from_image(floor_image))
    sand.set_shader_parameter("seabed",true)
    var plane := PlaneMesh.new()
    plane.size = Vector2(140,140)
    plane.material = sand
    var floor_mesh := MeshInstance3D.new()
    floor_mesh.mesh = plane
    floor_mesh.position.y = -.92
    add_child(floor_mesh)
    add_child(camera)
    camera.current = true
    camera.fov = 31.
    var env := Environment.new()
    env.background_mode = Environment.BG_COLOR
    env.background_color = Color("#175569")
    env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.ambient_light_color = Color("#aacbd4")
    env.ambient_light_energy = .66
    env.fog_enabled = true
    env.fog_light_color = Color("#367586")
    env.fog_density = .033
    env.fog_sun_scatter = 0.0
    camera.environment = env
    add_child(key)
    key.position = Vector3(-2.8,5.,1.0)
    key.look_at(Vector3.ZERO)
    key.light_color = Color("#f3f5e6")
    key.light_energy = .95
    key.shadow_enabled = true
    key.shadow_bias = .018
    key.shadow_normal_bias = .35
    key.directional_shadow_max_distance = 18.
    key.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
    add_child(caption)
    caption.position = Vector2(54,36)
    var font := SystemFont.new()
    font.font_names = PackedStringArray(["Microsoft YaHei UI","Microsoft YaHei"])
    caption.add_theme_font_override("font",font)
    caption.add_theme_font_size_override("font_size",32)
    caption.add_theme_color_override("font_color",Color("#f1f6f4"))
    caption.add_theme_color_override("font_shadow_color",Color("#1a3441b0"))
    caption.add_theme_constant_override("shadow_offset_y",2)
    rendering = "--capture" in OS.get_cmdline_user_args() or "--stills" in OS.get_cmdline_user_args()
    pose(0)
    if rendering:
        capture.call_deferred()

func pose(t: float) -> void:
    player.seek(fposmod(t,player.get_animation("Cruise").length),true)
    # Drift relative to the floor; both cameras follow the same swimming animal.
    asset.position = Vector3(0,.015*cos(t*2.1),fposmod(t*.19+25.,50.)-25.)
    var phase := fposmod(t,6.0)
    var point := asset.position + (Vector3(.13,.015,.22) if close_up else Vector3(0,.02,-.34))
    var direction := Vector3(2.75,1.28,3.35) if close_up else Vector3(2.30,2.35,4.20)
    direction = direction.rotated(Vector3.UP,.076*sin(phase*TAU/6.))
    camera.position = point + direction.normalized() * (1.12 if close_up else 3.35)
    camera.look_at(point,Vector3.UP)
    for mat in [skin,sand]:
        mat.set_shader_parameter("surface_light",float(mode))
        mat.set_shader_parameter("water_time",t)
    caption.text = "A　柔和顶光" if mode == 0 else "B　波纹顶光"

func _process(delta: float) -> void:
    if not rendering and player != null:
        clock_s += delta
        pose(clock_s)

func _unhandled_key_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode == KEY_1: mode = 0
        if event.keycode == KEY_2: mode = 1
        if event.keycode == KEY_SPACE: close_up = not close_up

func capture() -> void:
    var folder := OS.get_temp_dir().path_join("foundry-manta-lights-20261120")
    DirAccess.make_dir_recursive_absolute(folder)
    var stills := "--stills" in OS.get_cmdline_user_args()
    for look in 2:
        mode = look
        for frame in SEGMENT_FRAMES:
            if stills and frame not in [22,66,142]:
                continue
            close_up = frame >= 120
            pose(frame/float(FPS))
            await get_tree().process_frame
            await RenderingServer.frame_post_draw
            var img := get_viewport().get_texture().get_image()
            if img.get_size() != Vector2i(1920,1080) or img.save_jpg(folder.path_join("%04d.jpg" % (look*SEGMENT_FRAMES+frame)),.94) != OK:
                push_error("Capture failed")
                get_tree().quit(2)
                return
    get_tree().quit()
