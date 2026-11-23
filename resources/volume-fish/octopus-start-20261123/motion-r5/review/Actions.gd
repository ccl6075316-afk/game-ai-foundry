extends SceneTree

var camera: Camera3D
var model: Node3D
var yaw := 0.63
var pitch := 0.65
var zoom := 6.7
var player: AnimationPlayer
var clip := "ProbeTouch"
var elapsed := 0.0
var playback_paused := false
var speed := 1.0
var camera_offset := Vector3.ZERO
var title_label: Label
var frame_report: Array = []
var stage_grid: MeshInstance3D
var center := Vector3(0, -0.35, 0)
var inventory: Array = []
var capture_mode := false
var panel: CanvasLayer
var base_dir := ""

func _initialize() -> void:
    call_deferred("setup")

func setup() -> void:
    base_dir = ProjectSettings.globalize_path("res://").get_base_dir().get_base_dir()
    capture_mode = "--capture" in OS.get_cmdline_user_args()
    root.title = "章鱼动作试版 · 完整卷伸"
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
    var input_model := base_dir.path_join("octopus-actions.glb")
    if "--baseline" in OS.get_cmdline_user_args():input_model=base_dir.get_base_dir().path_join("motion-r4/octopus-actions.glb")
    var result := doc.append_from_file(input_model, state)
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
    set_clip("ProbeTouch")
    var env := WorldEnvironment.new()
    env.environment = Environment.new()
    env.environment.background_mode = Environment.BG_COLOR
    env.environment.background_color = Color(0.12, 0.15, 0.18)
    env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    env.environment.ambient_light_color = Color(0.87, 0.92, 1)
    env.environment.ambient_light_energy = 0.45
    world.add_child(env)
    for angles in [Vector3(-45,-25,0), Vector3(35,150,0)]:
        var light := DirectionalLight3D.new()
        light.rotation_degrees = angles
        light.light_energy = 0.5
        light.shadow_enabled = false
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
    title.text = "章鱼 · 腕足体积试版 05"
    title.position = Vector2(24,18)
    title.add_theme_font_size_override("font_size",24)
    panel.add_child(title)
    title_label = title
    var subtitle := Label.new()
    subtitle.text = "50,000 三角面 · 513 骨 · 试探 → 触底 → 抬离回卷 · 根位固定的接触试验"
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
    for item in [["单腕试探触底","ProbeTouch"],["双腕交替接触","AlternatingTouch"],["紧卷对照","TightRoll"]]:
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
    var pose_row := HBoxContainer.new()
    pose_row.position = Vector2(24,134)
    panel.add_child(pose_row)
    for item in [["收腕",0.0],["触底",6.0],["抬尖",7.0],["抬离",9.0]]:
        var button := Button.new()
        button.text = str(item[0])
        var moment := float(item[1])
        button.pressed.connect(func():set_clip("ProbeTouch");elapsed=moment;playback_paused=true;apply_pose())
        pose_row.add_child(button)
    var floor := MeshInstance3D.new()
    var floor_mesh := PlaneMesh.new();floor_mesh.size=Vector2(40,40);floor.mesh=floor_mesh
    var floor_mat := StandardMaterial3D.new();floor_mat.albedo_color=Color(.16,.19,.21);floor_mat.roughness=1.0
    floor.material_override=floor_mat;floor.position.y=-.25;world.add_child(floor)
    stage_grid=MeshInstance3D.new()
    var grid_mesh := ImmediateMesh.new();grid_mesh.surface_begin(Mesh.PRIMITIVE_LINES)
    for n in range(-9,10):
        var v := n*.5
        for point in [Vector3(v,-.248,-4.5),Vector3(v,-.248,4.5),Vector3(-4.5,-.248,v),Vector3(4.5,-.248,v)]:grid_mesh.surface_add_vertex(point)
    grid_mesh.surface_end();stage_grid.mesh=grid_mesh
    var grid_mat := StandardMaterial3D.new();grid_mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;grid_mat.albedo_color=Color(.20,.24,.26)
    stage_grid.material_override=grid_mat;world.add_child(stage_grid)
    var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(base_dir.path_join("build.validation.json")))
    for key in config.contact_targets:
        var p: Array = config.contact_targets[key]
        var line_mesh := ImmediateMesh.new();line_mesh.surface_begin(Mesh.PRIMITIVE_LINES)
        for j in range(64):
            for angle in [TAU*j/64.0,TAU*(j+1)/64.0]:line_mesh.surface_add_vertex(Vector3(.12*cos(angle),0,.12*sin(angle)))
        line_mesh.surface_end()
        var marker := MeshInstance3D.new();marker.mesh=line_mesh;marker.position=Vector3(p[0],-.249,p[1]*-1)
        var mat := StandardMaterial3D.new();mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;mat.albedo_color=Color(.38,.65,.57);marker.material_override=mat;world.add_child(marker)
    var help := Label.new()
    help.text = "左键拖动旋转 · 滚轮缩放 · R 复位\n可暂停、半速 · 地面标记对应实际接触点；不代表吸附或行走。"
    help.position = Vector2(24, root.size.y-66)
    panel.add_child(help)
    root.window_input.connect(input_event)
    root.close_requested.connect(func():quit())
    await process_frame
    await process_frame
    if "--closeup" in OS.get_cmdline_user_args() or "--tip-closeup" in OS.get_cmdline_user_args():
        set_clip("TightRoll");playback_paused=true;elapsed=4.5 if "--tip-closeup" in OS.get_cmdline_user_args() else 0.0;apply_pose()
        await process_frame
        await process_frame
        var skeleton := find_skeleton(model)
        center=Vector3.ZERO
        for i in range(33,64):
            center+=skeleton.get_bone_global_pose(skeleton.find_bone("R_IV_%02d"%i)).origin
        center/=31.0
        isolate_arm(model,skeleton)
        yaw=2.03444;pitch=0.0;zoom=1.25
        title_label.text="章鱼 · 加粗后的紧卷局部（仅显示右四腕）"
        if "--tip-closeup" in OS.get_cmdline_user_args():
            center=skeleton.get_bone_global_pose(skeleton.find_bone("R_IV_50")).origin;zoom=.85
            title_label.text="章鱼 · 展开腕尖局部（仅显示右四腕）"
        if "--baseline" in OS.get_cmdline_user_args():title_label.text+=" · 修改前"
        else:title_label.text+=" · 修改后"
        update_camera()
        stage_grid.visible=false
        await process_frame
        RenderingServer.force_draw(false)
        var output_name := "tip-straight-close.png" if "--tip-closeup" in OS.get_cmdline_user_args() else "tight-coil-close.png"
        if "--baseline" in OS.get_cmdline_user_args():output_name="baseline-"+output_name
        root.get_texture().get_image().save_png(base_dir.path_join(output_name))
        quit()
        return
    if "--controls" in OS.get_cmdline_user_args():
        var skeleton := find_skeleton(model)
        var samples: Array = []
        for button in pose_row.get_children():
            button.pressed.emit()
            await process_frame
            await process_frame
            var tip := skeleton.get_bone_global_pose(skeleton.find_bone("R_IV_63")).origin
            samples.append({"button":button.text,"tip":[tip.x,tip.y,tip.z],"time":elapsed})
        var moved := Vector3(samples[0].tip[0],samples[0].tip[1],samples[0].tip[2]).distance_to(Vector3(samples[2].tip[0],samples[2].tip[1],samples[2].tip[2]))
        var report := {"ok":moved>1.0 and skeleton.get_bone_count()==513,"bones":skeleton.get_bone_count(),"tip_displacement":moved,"buttons":samples,"model_sha256":FileAccess.get_sha256(base_dir.path_join("octopus-actions.glb"))}
        FileAccess.open(base_dir.path_join("controls.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
        quit(0 if report.ok else 5)
        return
    if capture_mode:
        var frame_dir := base_dir.path_join("frames")
        DirAccess.make_dir_recursive_absolute(frame_dir)
        var frame_indices = [0,90,135,180,210,270,360,450,480,570,660,720,810,900,959] if "--probe" in OS.get_cmdline_user_args() else range(960)
        for frame in frame_indices:
            if frame==0:set_clip("ProbeTouch")
            if frame==480:set_clip("AlternatingTouch")
            elapsed=frame/30.0 if frame<480 else (frame-480)/30.0
            yaw=2.03;pitch=.20;zoom=6.7
            if frame>=480:yaw=.12;pitch=.60;zoom=8.0
            apply_pose()
            await process_frame
            RenderingServer.force_draw(false)
            root.get_texture().get_image().save_png(frame_dir.path_join("%04d.png"%frame))
            if frame in [0,90,135,180,210,270,360,450,480,570,660,720,810,900,959]:
                root.get_texture().get_image().save_png(base_dir.path_join("pose-%04d.png"%frame))
                frame_report.append({"frame":frame,"clip":clip,"time":elapsed})
        var tris := 0
        for part in inventory:tris+=int(part.triangles)
        var report := {"probe_only":"--probe" in OS.get_cmdline_user_args(),"model_sha256":FileAccess.get_sha256(base_dir.path_join("octopus-actions.glb")),"kind":"octopus_motion_godot_cold_load","ok":inventory.size()==9 and tris==int(JSON.parse_string(FileAccess.get_file_as_string(base_dir.path_join("build.validation.json"))).triangles) and player.has_animation("ProbeTouch") and player.has_animation("AlternatingTouch") and player.has_animation("TightRoll"),"triangles":tris,"meshes":inventory,"animations":player.get_animation_list(),"frames":960,"fps":30,"duration":32.0,"samples":frame_report,"capture_mode":"hidden GPU deterministic native animation evaluation","user_accepted":false}
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
        player.advance(0)
        player.pause()
    if title_label!=null:title_label.text="章鱼 · "+("单腕紧卷展开" if clip=="ProbeTouch" else "八腕交替伸展")
    apply_pose()

func apply_pose() -> void:
    if player==null or not player.has_animation(clip):return
    var duration := player.get_animation(clip).length
    player.seek(fposmod(elapsed,duration),true)
    model.quaternion=Quaternion.IDENTITY;model.position=Vector3.ZERO
    camera_offset=model.position
    if title_label!=null:
        if clip=="TightRoll":title_label.text="章鱼 · 更贴近的卷伸"
        else:
            var t := fposmod(elapsed,16.0)
            var phase := "收腕停留"
            if t<1.5:phase="腕尖试探"
            elif t<4.5:phase="向外伸展"
            elif t<6:phase="下放接触"
            elif t<8:phase="触底保持 · 腕尖抬起"
            elif t<10:phase="抬腕离开"
            elif t<13.5:phase="收回卷紧"
            title_label.text=("单腕 · " if clip=="ProbeTouch" else "双腕交替 · ")+phase
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

func find_skeleton(node: Node) -> Skeleton3D:
    if node is Skeleton3D:return node
    for child in node.get_children():
        var found := find_skeleton(child)
        if found!=null:return found
    return null

func isolate_arm(node: Node, skeleton: Skeleton3D) -> void:
    if node is MeshInstance3D:
        if node.skin==null:
            node.visible=false
        else:
            var allowed: Dictionary = {}
            for i in range(node.skin.get_bind_count()):
                var bone_name: String = str(node.skin.get_bind_name(i))
                if bone_name.is_empty():bone_name=str(skeleton.get_bone_name(node.skin.get_bind_bone(i)))
                if bone_name.begins_with("R_IV_"):allowed[i]=true
            var filtered := ArrayMesh.new()
            for surf in range(node.mesh.get_surface_count()):
                var arrays: Array = node.mesh.surface_get_arrays(surf)
                var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
                var bones: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
                var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
                var count: int = bones.size()/vertices.size()
                var keep: Array[bool] = []
                for v in range(vertices.size()):
                    var weight := 0.0
                    for k in range(count):
                        if allowed.has(bones[v*count+k]):weight+=weights[v*count+k]
                    keep.append(weight>.01)
                var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
                var selected := PackedInt32Array()
                for i in range(0,idx.size(),3):
                    if keep[idx[i]] and keep[idx[i+1]] and keep[idx[i+2]]:
                        selected.append_array(PackedInt32Array([idx[i],idx[i+1],idx[i+2]]))
                if selected.size()>0:
                    arrays[Mesh.ARRAY_INDEX]=selected
                    filtered.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
                    filtered.surface_set_material(filtered.get_surface_count()-1,node.mesh.surface_get_material(surf))
            if filtered.get_surface_count()==0:node.visible=false
            else:node.mesh=filtered
    for child in node.get_children():isolate_arm(child,skeleton)
