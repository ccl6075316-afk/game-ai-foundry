extends SceneTree

var camera: Camera3D
var model: Node3D
var yaw := 0.63
var pitch := 0.65
var zoom := 8.1
var player: AnimationPlayer
var clip := "ArmExplore"
var elapsed := 0.0
var playback_paused := false
var speed := 1.0
var camera_offset := Vector3.ZERO
var title_label: Label
var frame_report: Array = []
var stage_grid: MeshInstance3D
var center := Vector3(0, 0.32, 0)
var inventory: Array = []
var capture_mode := false
var panel: CanvasLayer
var base_dir := ""

func _initialize() -> void:
    call_deferred("setup")

func setup() -> void:
    base_dir = ProjectSettings.globalize_path("res://").get_base_dir().get_base_dir()
    capture_mode = "--capture" in OS.get_cmdline_user_args()
    root.title = "章鱼动作试版 · 舒展 / 小幅收腕滑行"
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
    var result := doc.append_from_file(base_dir.path_join("octopus-motion.glb"), state)
    if result != OK:
        push_error("Cannot read grey GLB: " + str(result))
        quit(2)
        return
    model = doc.generate_scene(state)
    world.add_child(model)
    collect(model)
    player = find_player(model)
    if player == null:
        push_error("No AnimationPlayer");quit(4);return
    print("CLIPS ", player.get_animation_list())
    set_clip("ArmExplore")
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
    title.text = "章鱼 · 动作试版 01"
    title.position = Vector2(24,18)
    title.add_theme_font_size_override("font_size",24)
    panel.add_child(title)
    title_label = title
    var subtitle := Label.new()
    subtitle.text = "骨骼动作试制 · 腕身蹼长度比例已复核 · 节奏与速度为演示调校"
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
    var motion_row := HBoxContainer.new()
    motion_row.position = Vector2(390,90)
    panel.add_child(motion_row)
    for item in [["舒展卷腕","ArmExplore"],["小幅收腕滑行","JetGlide"]]:
        var button := Button.new()
        button.text = item[0]
        var name: String = item[1]
        button.pressed.connect(func():set_clip(name))
        motion_row.add_child(button)
    var pause_button := Button.new()
    pause_button.text = "暂停 / 继续"
    pause_button.pressed.connect(func():playback_paused=not playback_paused)
    motion_row.add_child(pause_button)
    var slow_button := Button.new()
    slow_button.text = "半速 / 正常"
    slow_button.pressed.connect(func():speed=0.5 if speed==1.0 else 1.0)
    motion_row.add_child(slow_button)
    # A stationary sparse grid makes root displacement visible in the tracking view.
    var grid_mesh := ImmediateMesh.new()
    grid_mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for k in range(-20,41,2):
        grid_mesh.surface_add_vertex(Vector3(k,-4,-14));grid_mesh.surface_add_vertex(Vector3(k,-4,14))
    for k in range(-14,15,2):
        grid_mesh.surface_add_vertex(Vector3(-20,-4,k));grid_mesh.surface_add_vertex(Vector3(40,-4,k))
    grid_mesh.surface_end()
    var grid := MeshInstance3D.new();grid.mesh=grid_mesh
    var material := StandardMaterial3D.new();material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;material.albedo_color=Color(.22,.27,.30)
    grid.material_override=material;world.add_child(grid);stage_grid=grid
    var help := Label.new()
    help.text = "左键拖动旋转 · 滚轮缩放 · R 复位\n舒展卷腕 / 小幅收腕滑行 · 可暂停、半速；非实测游速。"
    help.position = Vector2(24, root.size.y-66)
    panel.add_child(help)
    root.window_input.connect(input_event)
    root.close_requested.connect(func():quit())
    await process_frame
    await process_frame
    if capture_mode:
        var frame_dir := base_dir.path_join("frames")
        DirAccess.make_dir_recursive_absolute(frame_dir)
        var frame_indices = [0,90,180,252,324,396,468,540,611] if "--probe" in OS.get_cmdline_user_args() else range(612)
        for frame in frame_indices:
            var time: float = frame/30.0
            if frame==0:set_clip("ArmExplore")
            if frame==180:set_clip("JetGlide")
            elapsed=time if frame<180 else time-6.0
            apply_pose()
            if frame>=324 and frame<468:
                yaw=1.35;pitch=.22
            elif frame>=468:
                yaw=.15;pitch=-1.35
            else:
                yaw=.63;pitch=.65
            update_camera()
            await process_frame
            RenderingServer.force_draw(false)
            root.get_texture().get_image().save_png(frame_dir.path_join("%04d.png"%frame))
            if frame in [0,45,90,135,180,216,252,288,324,360,396,432,468,504,540,576,611]:
                root.get_texture().get_image().save_png(base_dir.path_join("pose-%04d.png"%frame))
                frame_report.append({"frame":frame,"clip":clip,"time":elapsed,"root_position":[model.position.x,model.position.y,model.position.z]})
        var tris := 0
        for part in inventory:tris+=int(part.triangles)
        var report := {"probe_only":"--probe" in OS.get_cmdline_user_args(),"model_sha256":FileAccess.get_sha256(base_dir.path_join("octopus-motion.glb")),"kind":"octopus_motion_godot_cold_load","ok":inventory.size()==9 and tris==int(JSON.parse_string(FileAccess.get_file_as_string(base_dir.path_join("build.validation.json"))).triangles) and player.has_animation("ArmExplore") and player.has_animation("JetGlide"),"triangles":tris,"meshes":inventory,"animations":player.get_animation_list(),"frames":612,"fps":30,"duration":20.4,"samples":frame_report,"capture_mode":"hidden GPU deterministic native animation evaluation","user_accepted":false}
        var file := FileAccess.open(base_dir.path_join("godot.validation.json"),FileAccess.WRITE)
        file.store_string(JSON.stringify(report,"  "))
        quit(0 if report.ok else 3)

func find_player(node: Node) -> AnimationPlayer:
    if node is AnimationPlayer:return node
    for child in node.get_children():
        var found := find_player(child)
        if found != null:return found
    return null

func set_clip(name: String) -> void:
    clip=name;elapsed=0
    if player.has_animation(clip):
        player.get_animation(clip).loop_mode=Animation.LOOP_LINEAR
        player.play(clip)
        player.pause()
    if title_label!=null:title_label.text="章鱼 · "+("舒展卷腕" if clip=="ArmExplore" else "小幅收腕滑行")
    apply_pose()

func apply_pose() -> void:
    if player==null or not player.has_animation(clip):return
    var duration := player.get_animation(clip).length
    player.seek(fposmod(elapsed,duration),true)
    if clip=="JetGlide":
        model.quaternion=Quaternion(Vector3(0,.70710678,-.70710678),Vector3.RIGHT)
        # Positive root velocity throughout; cyclic acceleration, no backward reset.
        model.position=Vector3(.38*elapsed+.14*sin(TAU*elapsed/4.8),0,0)
    else:
        model.quaternion=Quaternion.IDENTITY;model.position=Vector3.ZERO
    camera_offset=model.position
    update_camera()

func _process(delta: float) -> bool:
    if not capture_mode and not playback_paused and player!=null:
        elapsed+=delta*speed;apply_pose()
    return false

func collect(node: Node) -> void:
    if node is MeshInstance3D:
        var tris := 0
        for s in range(node.mesh.get_surface_count()):
            var a: Array = node.mesh.surface_get_arrays(s)
            tris += a[Mesh.ARRAY_INDEX].size()/3 if a[Mesh.ARRAY_INDEX]!=null else a[Mesh.ARRAY_VERTEX].size()/3
        inventory.append({"name":node.name,"triangles":tris})
    for child in node.get_children():collect(child)

func update_camera() -> void:
    if camera==null:return
    if stage_grid!=null:stage_grid.visible=pitch>-.3
    camera.size = zoom*(1.45 if pitch< -1.2 else 1.0)
    var rotation := model.quaternion if model!=null else Quaternion.IDENTITY
    var target := rotation*center+camera_offset
    camera.position = target + rotation*(8*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch)))
    camera.look_at(target,rotation*Vector3.UP)

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
