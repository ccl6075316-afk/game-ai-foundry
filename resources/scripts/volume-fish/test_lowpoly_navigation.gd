extends SceneTree
## Regression for root-viewport input dispatch, pan, cursor anchor and sync.
var viewer
var checks={}
func _initialize():call_deferred("run")
func frames(count:int=2):
    for i in count:await process_frame
func mouse_button(at:Vector2,button:MouseButton,pressed:bool,shift:bool=false):
    var window_at=root.get_final_transform()*at
    var event=InputEventMouseButton.new();event.position=window_at;event.global_position=window_at;event.button_index=button;event.pressed=pressed;event.shift_pressed=shift
    Input.parse_input_event(event);await frames()
func motion(at:Vector2,relative:Vector2):
    var transform=root.get_final_transform()
    var window_at=transform*at
    var event=InputEventMouseMotion.new();event.position=window_at;event.global_position=window_at;event.relative=transform.basis_xform(relative)
    Input.parse_input_event(event);await frames()
func run():
    root.size=Vector2i(1536,1000)
    viewer=load("res://scenes/fish_lowpoly_review.tscn").instantiate();root.add_child(viewer)
    await frames(24);viewer.toggle_pause()
    var at=viewer.panels[0].get_global_rect().get_center()
    var initial=viewer.pan
    await mouse_button(at,MOUSE_BUTTON_LEFT,true)
    await motion(at+Vector2(90,-35),Vector2(90,-35))
    await mouse_button(Vector2(0,0),MOUSE_BUTTON_LEFT,false)
    checks.left_drag_dispatch_moves_pan=viewer.pan.distance_to(initial)>0.001
    checks.release_outside_clears_drag=viewer.active_panel==-1 and not viewer.panning and not viewer.dragging
    var sync=true
    for camera in viewer.cameras:
        sync=sync and camera.position.distance_to(viewer.cameras[0].position)<1e-6
    checks.all_four_cameras_synced=sync
    var cursor=at+Vector2(160,0)
    var world_before=viewer.cursor_world(cursor,0)
    var native_pixel=viewer.cameras[0].unproject_position(world_before)
    var old_zoom=viewer.zoom
    await mouse_button(cursor,MOUSE_BUTTON_WHEEL_UP,true)
    await mouse_button(cursor,MOUSE_BUTTON_WHEEL_UP,false)
    checks.wheel_dispatch_zooms=viewer.zoom<old_zoom
    checks.cursor_anchor_error=viewer.cursor_world(cursor,0).distance_to(world_before)
    checks.cursor_anchor_stable=checks.cursor_anchor_error<1e-5
    checks.rendered_anchor_pixel_error=viewer.cameras[0].unproject_position(world_before).distance_to(native_pixel)
    checks.rendered_anchor_stable=checks.rendered_anchor_pixel_error<.1
    checks.zoom_trace=viewer.last_zoom_trace.duplicate()
    viewer.pan_mode=false;viewer.pan_button.button_pressed=false
    var old_yaw=viewer.yaw;initial=viewer.pan
    await mouse_button(at,MOUSE_BUTTON_LEFT,true)
    await motion(at+Vector2(45,15),Vector2(45,15))
    await mouse_button(at,MOUSE_BUTTON_LEFT,false)
    checks.rotation_mode_still_rotates=absf(viewer.yaw-old_yaw)>.1 and viewer.pan.distance_to(initial)<1e-6
    for button in [MOUSE_BUTTON_RIGHT,MOUSE_BUTTON_MIDDLE]:
        initial=viewer.pan
        await mouse_button(at,button,true)
        await motion(at+Vector2(40,0),Vector2(40,0))
        await mouse_button(at,button,false)
        checks["pan_button_"+str(button)]=viewer.pan.distance_to(initial)>.001
    initial=viewer.pan
    await mouse_button(at,MOUSE_BUTTON_LEFT,true,true)
    await motion(at+Vector2(40,0),Vector2(40,0))
    await mouse_button(at,MOUSE_BUTTON_LEFT,false)
    checks.shift_left_pans=viewer.pan.distance_to(initial)>.001
    initial=viewer.pan
    var key=InputEventKey.new();key.keycode=KEY_D;key.physical_keycode=KEY_D;key.pressed=true;Input.parse_input_event(key)
    await frames(6)
    key=key.duplicate();key.pressed=false;Input.parse_input_event(key);await frames()
    checks.keyboard_pan=viewer.pan.distance_to(initial)>.0001
    viewer.reset_view()
    checks.reset_clears_pan_and_zoom=viewer.pan==Vector3.ZERO and viewer.zoom==1.0
    # A useful close-up after panning: same target in all four panes.
    viewer.pan_mode=true;viewer.pan_button.button_pressed=true
    for i in 5:await mouse_button(cursor,MOUSE_BUTTON_WHEEL_UP,true)
    await mouse_button(cursor,MOUSE_BUTTON_WHEEL_UP,false)
    await frames();await RenderingServer.frame_post_draw
    var directory=ProjectSettings.globalize_path(viewer.REVIEW).simplify_path()
    root.get_texture().get_image().save_png(directory.path_join("navigation.png"))
    var passed=true
    for name in checks:
        if checks[name] is bool:passed=passed and checks[name]
    var report={"schema_version":1,"ok":passed,"status":"done" if passed else "failed","checks":checks,"script_sha256":FileAccess.get_sha256(viewer.get_script().resource_path),"test_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Engine-dispatched mouse/key navigation regression only. No fish assets or acceptance changed."}
    var file=FileAccess.open(directory.path_join("navigation.validation.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    print("NAVIGATION_TEST ",JSON.stringify(report))
    viewer.queue_free();await frames();quit(0 if passed else 1)
