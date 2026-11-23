extends SceneTree

var camera: Camera3D
var model: Node3D
var yaw := 0.63
var pitch := 0.65
var zoom := 8.1
var center := Vector3(0, 0.32, 0)
var inventory: Array = []
var capture_mode := false
var panel: CanvasLayer
var base_dir := ""

func _initialize() -> void:
    call_deferred("setup")

func setup() -> void:
    base_dir = ProjectSettings.globalize_path("res://").get_base_dir().get_base_dir().path_join("r2")
    capture_mode = "--capture" in OS.get_cmdline_user_args()
    root.title = "章鱼灰模 02 · 形态预览"
    root.size = Vector2i(1100, 800)
    var screen_id := DisplayServer.get_primary_screen()
    var usable := DisplayServer.screen_get_usable_rect(screen_id)
    if usable.size.x > 0 and usable.size.y > 0:
        root.size = Vector2i(mini(1100, usable.size.x - 80), mini(800, usable.size.y - 80))
        root.position = usable.position + (usable.size - root.size) / 2
    var world := Node3D.new()
    root.add_child(world)
    var doc := GLTFDocument.new()
    var state := GLTFState.new()
    var result := doc.append_from_file(base_dir.path_join("octopus-gray.glb"), state)
    if result != OK:
        push_error("Cannot read grey GLB: " + str(result))
        quit(2)
        return
    model = doc.generate_scene(state)
    world.add_child(model)
    collect(model)
    var env := WorldEnvironment.new()
    env.environment = Environment.new()
    env.environment.background_mode = Environment.BG_COLOR
    env.environment.background_color = Color(0.12, 0.15, 0.18)
    env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.environment.ambient_light_color = Color(0.87, 0.92, 1)
    env.environment.ambient_light_energy = 0.65
    world.add_child(env)
    for angles in [Vector3(-45,-25,0), Vector3(35,150,0)]:
        var light := DirectionalLight3D.new()
        light.rotation_degrees = angles
        light.light_energy = 0.8
        world.add_child(light)
    camera = Camera3D.new()
    camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    camera.near = 0.01
    world.add_child(camera)
    camera.current = true
    update_camera()
    panel = CanvasLayer.new()
    root.add_child(panel)
    var title := Label.new()
    title.text = "章鱼 · 灰模 02"
    title.position = Vector2(24,18)
    title.add_theme_font_size_override("font_size",24)
    panel.add_child(title)
    var subtitle := Label.new()
    subtitle.text = "形态预览：八腕、腕间蹼、双列吸盘、漏斗   /   静态候选"
    subtitle.position = Vector2(24,55)
    panel.add_child(subtitle)
    var row := HBoxContainer.new()
    row.position = Vector2(24,90)
    panel.add_child(row)
    for entry in [["斜视",0.63,0.65],["俯视",0.0,1.55],["侧视",1.57,0.08],["腹面",0.0,-1.55]]:
        var button := Button.new()
        button.text = str(entry[0])
        button.custom_minimum_size = Vector2(74,34)
        var y := float(entry[1])
        var p := float(entry[2])
        button.pressed.connect(func(): yaw=y;pitch=p;update_camera())
        row.add_child(button)
    var help := Label.new()
    help.text = "左键拖动旋转 · 滚轮缩放 · R 复位\n本轮看形体；吸盘为简化占位，尚未制作游动。"
    help.position = Vector2(24, root.size.y-66)
    panel.add_child(help)
    root.window_input.connect(input_event)
    root.close_requested.connect(func():quit())
    await process_frame
    await process_frame
    if capture_mode:
        for entry in [["godot-oblique",0.63,0.65],["godot-top",0.0,1.55],["godot-side",1.57,0.08],["godot-underside",0.0,-1.55]]:
            yaw=float(entry[1]);pitch=float(entry[2]);update_camera()
            await process_frame
            RenderingServer.force_draw(false)
            var image := root.get_texture().get_image()
            image.save_png(base_dir.path_join(str(entry[0])+".png"))
        var tris := 0
        for part in inventory: tris += int(part.triangles)
        var build: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(base_dir.path_join("gray-build.validation.json")))
        var report := {"kind":"octopus_gray_godot_cold_load","ok":inventory.size()==9 and tris==int(build.triangles),"triangles":tris,"meshes":inventory,"capture_mode":"hidden GPU, GLB cold read","animations":0,"user_accepted":false}
        var file := FileAccess.open(base_dir.path_join("gray-godot.validation.json"),FileAccess.WRITE)
        file.store_string(JSON.stringify(report,"  "))
        quit(0 if report.ok else 3)

func collect(node: Node) -> void:
    if node is MeshInstance3D:
        var tris := 0
        for s in range(node.mesh.get_surface_count()):
            var a: Array = node.mesh.surface_get_arrays(s)
            tris += a[Mesh.ARRAY_INDEX].size()/3 if a[Mesh.ARRAY_INDEX]!=null else a[Mesh.ARRAY_VERTEX].size()/3
        inventory.append({"name":node.name,"triangles":tris})
    for child in node.get_children():collect(child)

func update_camera() -> void:
    camera.size = zoom
    camera.position = center + 8*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))
    camera.look_at(center)

func input_event(event: InputEvent) -> void:
    if event is InputEventMouseMotion and event.button_mask & MOUSE_BUTTON_MASK_LEFT:
        yaw -= event.relative.x*.007
        pitch = clampf(pitch+event.relative.y*.007,-1.55,1.55)
        update_camera()
    if event is InputEventMouseButton and event.pressed:
        if event.button_index==MOUSE_BUTTON_WHEEL_UP:zoom=maxf(1.2,zoom*.90)
        if event.button_index==MOUSE_BUTTON_WHEEL_DOWN:zoom=minf(12,zoom/0.90)
        update_camera()
    if event is InputEventKey and event.pressed and event.keycode==KEY_R:
        yaw=.63;pitch=.65;zoom=8.1;update_camera()
