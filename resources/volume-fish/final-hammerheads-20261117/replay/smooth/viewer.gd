extends "../../../../scripts/volume-fish/portable/FishListViewer.gd"

const Gait = preload("Gait.gd")
const Prey = preload("Prey.gd")
var gait := Gait.new()
var prey := Prey.new()
var large := false
var near_mouth := false
var playing := false
var stamp := 0.
var progress: HSlider
var branch: OptionButton
var play_button: Button
var zoom_factor := 1.

func run() -> void:
    await super.run()
    assert(ready_for_input and skeleton.get_bone_count()==22)
    viewport.mesh_lod_threshold=0.
    viewport.msaa_3d=Viewport.MSAA_4X
    gait.bind(carrier,skeleton,controller)
    world.add_child(prey)
    var lamp:=DirectionalLight3D.new()
    lamp.rotation_degrees=Vector3(34,-58,0)
    lamp.light_energy=.41
    world.add_child(lamp)
    var content:=camera_node.get_parent()
    for item in content.get_children():
        if item is WorldEnvironment:
            item.environment.background_color=Color("#253a46")
    root.title="无沟双髻鲨 · 完整捕食预览"
    var screen := DisplayServer.get_primary_screen()
    var extent := DisplayServer.screen_get_size(screen)
    root.size=Vector2i(mini(1850,extent.x-80),mini(1130,extent.y-110))
    root.current_screen=screen
    root.position=DisplayServer.screen_get_position(screen)+(extent-root.size)/2
    var sidebar := pause_button.get_parent()
    var heading := sidebar.get_child(0) as Label
    heading.text="无沟双髻鲨"
    fish_list.hide()
    action_choice.hide()
    pause_button.hide()
    info.text="捕食回放"
    info.custom_minimum_size.y=28
    branch=OptionButton.new()
    branch.add_item("小猎物摄入")
    branch.add_item("大猎物夹持")
    branch.item_selected.connect(func(i: int):
        large=i==1
        playing=true
        stamp=0.
        sync_frame()
    )
    var controls := VBoxContainer.new()
    sidebar.add_child(controls)
    sidebar.move_child(controls,info.get_index()+1)
    controls.add_child(branch)
    play_button=_button(controls,"播放",toggle)
    _button(controls,"重播",restart)
    var views := HBoxContainer.new()
    controls.add_child(views)
    _button(views,"整鱼",func():near_mouth=false; update_view())
    _button(views,"口部近景",func():near_mouth=true; update_view())
    progress=HSlider.new()
    progress.min_value=0.
    progress.max_value=Gait.STOP
    progress.step=1./60.
    progress.custom_minimum_size.y=28.
    progress.value_changed.connect(func(t: float):
        stamp=t
        playing=false
        sync_frame()
    )
    controls.add_child(progress)
    motion_paused=true
    var args := OS.get_cmdline_user_args()
    var verification:= "--verify" in args
    if verification or "--video" in args:
        root.size=Vector2i(1390,690)
        await process_frame
        await process_frame
        RenderingServer.render_loop_enabled=false
        await verify_samples("--video" in args)
        _finish()
        return
    large=true
    branch.select(1)
    stamp=0.
    sync_frame()
    if "--background-preview" not in OS.get_cmdline_user_args():
        root.grab_focus()
    await _save_capture("window-start")
    write("startup.validation.json",{"ok":ready_for_input and checks.all(func(item):return item.passed),
        "pid":OS.get_process_id(),"screen":root.current_screen,
        "model_sha256":FileAccess.get_sha256(config.model),"captures":captures})

func _process(delta: float) -> bool:
    if not playing or not ready_for_input: return false
    stamp=minf(stamp+delta,Gait.STOP)
    sync_frame()
    if is_equal_approx(stamp,Gait.STOP):
        playing=false
        play_button.text="重播"
    return false

func toggle() -> void:
    if is_equal_approx(stamp,Gait.STOP):
        restart()
    else:
        playing=not playing
        sync_frame()

func restart() -> void:
    playing=true
    stamp=0.
    sync_frame()

func update_view() -> void:
    var focus: Vector3 = carrier.position+Vector3(-.28,-.04,0.)
    var direction:=Vector3(.24,-.23,1.)
    var approach: float=1.-gait.blend(stamp,.72,1.48)
    focus.x+=.22*approach
    var span:=3.90+.77*approach
    if near_mouth:
        var lips: Dictionary=gait.oral_frame()
        focus=lips.center
        direction=Vector3(.70,-.68,1.)
        span=.86 if large else .45
    camera_node.projection=Camera3D.PROJECTION_ORTHOGONAL
    camera_node.keep_aspect=Camera3D.KEEP_WIDTH
    camera_node.size=span*zoom_factor
    target=focus
    var norm:=direction.normalized()
    yaw=atan2(norm.x,norm.z)
    pitch=asin(norm.y)
    distance=3.7
    _update_camera()

func _zoom(factor: float) -> void:
    zoom_factor=clampf(zoom_factor*factor,.38,2.25)
    update_view()

func _input(event: InputEvent) -> bool:
    if event is InputEventKey and event.pressed and not event.echo:
        if event.keycode==KEY_SPACE and play_button!=null:
            toggle()
            return true
        if event.keycode==KEY_0 and play_button!=null:
            zoom_factor=1.
            update_view()
            return true
    if event is InputEventMouseMotion and event.button_mask==0:
        return false
    if event is InputEventMouseButton and event.pressed and event.position.x>=sidebar_width:
        if event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
            _zoom(.84 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1.19)
            return true
    return super._input(event)

func frame_at(t: float, use_large: bool) -> Dictionary:
    var data: Dictionary=gait.apply(t,use_large)
    var target_data: Dictionary=prey.pose(gait,t,use_large)
    data.merge(target_data)
    return data

func sync_frame() -> void:
    frame_at(stamp,large)
    update_view()
    progress.set_value_no_signal(stamp)
    play_button.text="暂停" if playing else ("重播" if is_equal_approx(stamp,Gait.STOP) else "播放")

func write(name: String,data: Dictionary) -> void:
    var file:=FileAccess.open(output_directory.path_join(name),FileAccess.WRITE)
    file.store_string(JSON.stringify(data,"  ")+"\n")
    file.close()

func verify_samples(video: bool) -> void:
    var cases: Dictionary={}
    # The sample records use the same actor calls as the interactive timeline.
    for use_large in [false,true]:
        large=use_large
        var kind: String="large" if large else "small"
        var rows: Array=[]
        var grip_error:=0.
        var entered:=false
        var max_bend:=0.
        var frames_dir:=output_directory.path_join(kind)
        if video: DirAccess.make_dir_recursive_absolute(frames_dir)
        for n in 241:
            var t:=float(n)/60.
            stamp=t
            var row:=frame_at(t,large)
            rows.append(row)
            if row.has("upper_grip_m"):
                grip_error=maxf(grip_error,maxf(row.upper_grip_m,row.lower_grip_m))
            if not large and t>=Gait.TAKE_END:
                entered=entered or (row.inside_progress>.9999 and row.prey_rendered and row.prey_center_to_mouth_m>.046)
            max_bend=maxf(max_bend,absf(row.bend))
            if video or n in [42,80,93,117,156,214,240]:
                near_mouth=(n>=73 and n<=104) if large else (n>=60 and n<=133)
                if not video: near_mouth=n in [80,93,117]
                update_view()
                await process_frame
                carrier.force_update_transform()
                camera_node.force_update_transform()
                row["camera_target"]=camera_node.position-camera_node.global_basis.z*3.7
                RenderingServer.force_draw(false)
                var name: String=frames_dir.path_join("frame-%03d.png"%n) if video else output_directory.path_join("%s-%03d.png"%[kind,n])
                assert(viewport.get_texture().get_image().save_png(name)==OK)
        var success: bool=(grip_error<.00001 and max_bend>.6) if large else entered
        _check("feeding_"+kind,success)
        cases[kind]={"model_sha256":FileAccess.get_sha256(config.model),
            "ok":success,"fps":60,"frames":rows,"max_grip_error_m":grip_error,"max_bend":max_bend,"small_ingress":entered}
    write("feeding.validation.json",{"ok":checks.all(func(item):return item.passed),
        "model_sha256":FileAccess.get_sha256(config.model),"cases":cases})
