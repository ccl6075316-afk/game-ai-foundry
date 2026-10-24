extends "res://scripts/aquarium/AquariumHall3D.gd"
var checks: Dictionary={}
var outputs: Array=[]
var directory := ""

func _ready() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--capture-dir="):directory=arg.trim_prefix("--capture-dir=")
    assert(not directory.is_empty(),"Native review requires an explicit evidence directory")
    DirAccess.make_dir_recursive_absolute(directory)
    save_path=directory+"/not-a-user-save.json";read_only=true
    super._ready()
    capture_active=true
    call_deferred("_capture")

func _check(id: String,okay: bool) -> void:
    checks[id]=okay;print("HALL_CHECK ",id," ",okay)

func _same(a: Variant,b: Variant) -> bool:
    # JSON stores numeric values without preserving int/float Variant types.
    # Compare all fields recursively, with a sub-micron floating tolerance.
    if (a is float or a is int) and (b is float or b is int):return absf(float(a)-float(b))<.000001
    if a is Dictionary and b is Dictionary:
        if a.size()!=b.size():return false
        for key in a:
            if not b.has(key) or not _same(a[key],b[key]):return false
        return true
    if a is Array and b is Array:
        if a.size()!=b.size():return false
        for i in a.size():
            if not _same(a[i],b[i]):return false
        return true
    return a==b

func _image(name: String) -> void:
    status.text=notice
    for i in 6:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var path := directory+"/"+name+".png"
    _check("screenshot_"+name,get_viewport().get_texture().get_image().save_png(path)==OK);outputs.append(path)

func _capture() -> void:
    for i in 35:await get_tree().process_frame
    _check("native_3d_world",viewport.own_world_3d and player is CharacterBody3D)
    _check("default_two_real_tanks",objects.filter(func(r):return r.tank!=null).size()==2)
    _check("default_twelve_swimming_fish",objects[0].tank.fish.size()==8 and objects[1].tank.fish.size()==4)
    _check("default_layout_is_valid",_valid_state(_state()))
    await _image("01-hall-editor")
    var click := InputEventMouseButton.new()
    click.button_index=MOUSE_BUTTON_LEFT;click.pressed=true
    var bench_center: Vector3=objects[2].node.transform*_bounds(objects[2].data).get_center()
    click.position=editor_camera.unproject_position(bench_center)*canvas.size/Vector2(viewport.size)
    canvas.gui_input.emit(click)
    _check("canvas_mouse_selects_real_3d_collider",selected==2 and dragging)
    click.pressed=false;canvas.gui_input.emit(click)
    _check("canvas_mouse_release_stops_drag",not dragging)
    _mode(false)
    var start: Vector3=player.position
    Input.action_press("hall_forward")
    for i in 30:await get_tree().physics_frame
    Input.action_release("hall_forward")
    _check("wasd_walk_changes_position",player.position.distance_to(start)>.6)
    player.position=Vector3(0,.88,-2.2);player.velocity=Vector3.ZERO
    Input.action_press("hall_forward")
    for i in 65:await get_tree().physics_frame
    Input.action_release("hall_forward")
    _check("walk_collides_with_exhibit_glass",player.position.z> -3.0 and player.position.z< -2.5)
    player.position=Vector3(8,.88,5);player.velocity=Vector3.ZERO
    Input.action_press("hall_right")
    for i in 45:await get_tree().physics_frame
    Input.action_release("hall_right")
    _check("walk_collides_with_room_wall",player.position.x<8.7 and player.position.x>8.1)
    _safe_spawn()
    for i in 3:await get_tree().physics_frame
    notice="逛馆：WASD 行走，按住右键转动视线。"
    await _image("02-first-person")
    _mode(true)
    selected=2
    var initial := _state()
    _remember()
    _check("move_selected_snaps_to_grid",_move_selected(Vector3(2.1,0,2.2)) and objects[2].data.at==[2.0,2.25])
    var moved := _state()
    _undo();_check("undo_restores_hall_layout",_same(_state(),initial))
    _redo();_check("redo_restores_hall_layout",_same(_state(),moved))
    selected=2
    var angle: float=objects[2].data.yaw
    _check("rotate_selected_object",_rotate_selected(1) and absf(objects[2].data.yaw-angle-deg_to_rad(15))<.00001)
    _check("resize_selected_object",_resize_selected(1.1) and absf(objects[2].data.scale-1.1)<.00001)
    var before := _state()
    _check("reject_overlapping_tank_placement",not _move_selected(Vector3(0,0,-4.8)) and _same(_state(),before))
    _check("reject_outside_room",not _move_selected(Vector3(20,0,20)))
    _check("add_third_tank",_add_at("tank",Vector3(5.8,0,3.8)) and objects.size()==5 and objects[-1].tank.fish.is_empty())
    _check("new_tank_content_is_editable_3d",objects[-1].tank.bed.chunks.size()==16)
    _delete_selected();_check("delete_selected_object",objects.size()==4)
    _undo();_check("undo_deletion_recreates_exhibit",objects.size()==5)
    _redo();_check("redo_deletion",objects.size()==4)
    _remember();floor_style=1;wall_style=1;_finishes()
    _check("surface_finishes_change",wall_paint.albedo_color==WALL_COLORS[1])
    _undo();_check("surface_finish_undo",floor_style==0 and wall_style==0)
    selected=0;_sync_panel()
    _check("open_real_tank_editor",_open_content_editor() and active_editor!=null)
    for i in 6:await get_tree().process_frame
    _check("embedded_3d_canvas_has_real_extent",active_editor.canvas.size==Vector2(1440,900))
    var original_content: Dictionary=objects[0].tank.content_state()
    var local_heights: PackedFloat32Array=active_editor.bed.heights.duplicate()
    active_editor.bed.brush(Vector3(.02,0,.12),.08,.6,"pour")
    _check("embedded_editor_sculpts_actual_bed",active_editor.bed.heights!=local_heights)
    var prop_count: int=active_editor.rocks.size()
    active_editor._add_rock("terracotta_jar",Vector3(.35,0,.17),.6,.2)
    _check("embedded_editor_places_generated_prop",active_editor.rocks.size()==prop_count+1)
    await _image("03-in-tank-editor")
    var edited: Dictionary=active_editor._state()
    _apply_content_editor(edited)
    _check("apply_updates_selected_tank_contents",objects[0].tank.bed.heights==PackedFloat32Array(edited.heights) and objects[0].tank.props.size()==prop_count+1)
    _check("second_tank_not_modified",objects[1].tank.props.size()==13)
    _undo();_check("undo_tank_content_edit",_same(objects[0].tank.content_state(),original_content))
    _redo();_check("redo_tank_content_edit",objects[0].tank.props.size()==prop_count+1)
    selected=0
    var before_cancel: Dictionary=objects[0].tank.content_state()
    _open_content_editor()
    active_editor.bed.brush(Vector3(.1,0,0),.08,.6,"remove")
    _close_content_editor()
    _check("cancel_discards_tank_edit",_same(objects[0].tank.content_state(),before_cancel))
    var saved := _state()
    _check("atomic_save_written",_write_layout(directory+"/hall-save.json"))
    _check("atomic_save_overwrites_existing",_write_layout(directory+"/hall-save.json"))
    _restore(_default_state())
    var loaded := _load_layout(directory+"/hall-save.json")
    var roundtrip := FileAccess.open(directory+"/loaded-state.json",FileAccess.WRITE)
    roundtrip.store_string(JSON.stringify(_state(),"",true,true));roundtrip.close()
    _check("load_saved_layout_and_tank_contents",loaded and _same(_state(),saved))
    var invalid: Dictionary=saved.duplicate(true);invalid.objects[0].scale=99
    var file := FileAccess.open(directory+"/invalid-hall-save.json",FileAccess.WRITE);file.store_string(JSON.stringify(invalid));file.close()
    _check("invalid_save_rejected_without_mutation",not _load_layout(directory+"/invalid-hall-save.json") and _same(_state(),saved))
    invalid=saved.duplicate(true);invalid.objects[0].content.rocks[0].id="unreviewed_unknown_prop"
    _check("unknown_nested_prop_rejected",not _valid_state(invalid))
    invalid=saved.duplicate(true);invalid.objects[0].content.heights[0]=INF
    _check("nonfinite_nested_height_rejected",not _valid_state(invalid))
    selected=0;_sync_panel();notice="可编辑 3D 大厅：双展缸、独立缸内布景与可保存布局。"
    await _image("04-edited-hall")
    pitch=1.3;yaw=.01;_camera()
    await _image("05-top-layout")
    pitch=.83;yaw=.48;_camera()
    var failures: Array=[]
    for id in checks:
        if not checks[id]:failures.append(id)
    var report := {"schema_version":1,"command":"aquarium.hall-3d-native-review","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","checks":checks,"failures":failures,"outputs":outputs,"summary":{"initial_room_size_m":[18,14],"initial_parcels":6,"parcel_size_m":[6,7],"max_parcels":24,"default_tanks":2,"default_fish":12,"layout_objects":objects.size(),"tested_save":directory+"/hall-save.json","gpu":RenderingServer.get_video_adapter_name()},"visual_review":"pending","user_acceptance":"pending","limitations":["Creative exhibit layout and decorative fish; legacy purchase economy and inventory are preserved separately, not migrated.","Eight tanks and eighty hall objects maximum; fish count is capped at fifteen per tank. No outdoors, second floors, visitors or construction economy in this slice.","Hall collisions use enclosing boxes/capsules. Tank prop support and fish routes inherit existing approximation limits.","Existing fish helpers are reused without new fish model acceptance; inherited export warnings remain."]}
    file=FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    get_tree().quit(0 if failures.is_empty() else 1)
