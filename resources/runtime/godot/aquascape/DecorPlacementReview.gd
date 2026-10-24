extends "res://scripts/aquarium/DecorPlacementLab.gd"
## Native interaction, persistence and bounded-object regression evidence.
var checks: Dictionary={}
var outputs: Array=[]
var gravel_stress_p95 := 0.0
var gravel_follow_error := 0.0

func _check(name: String,value: bool) -> void:
    checks[name]=value
    print("SAND_CHECK ",name," ",value)

func _nodes() -> int:
    var stack: Array=[world]
    var count := 0
    while not stack.is_empty():
        var node: Node=stack.pop_back()
        if node.is_queued_for_deletion():continue
        count+=1
        stack.append_array(node.get_children())
    return count

func _equal(a: Dictionary,b: Dictionary) -> bool:
    if a.heights.size()!=b.heights.size() or a.rocks.size()!=b.rocks.size():return false
    if a.get("materials")!=b.get("materials") or a.get("selected_substrate")!=b.get("selected_substrate"):return false
    for i in a.heights.size():
        if absf(a.heights[i]-b.heights[i])>1e-7:return false
    for i in a.rocks.size():
        if a.rocks[i].id!=b.rocks[i].id or absf(a.rocks[i].scale-b.rocks[i].scale)>1e-6 or absf(a.rocks[i].yaw-b.rocks[i].yaw)>1e-6:return false
        for j in 3:
            if absf(a.rocks[i].position[j]-b.rocks[i].position[j])>1e-6:return false
    return true

func _mouse(button: MouseButton,pressed: bool,at: Vector2,shift:=false) -> void:
    var event := InputEventMouseButton.new()
    event.position=at;event.button_index=button;event.pressed=pressed;event.shift_pressed=shift
    _input_canvas(event)

func _motion(at: Vector2) -> void:
    var event := InputEventMouseMotion.new()
    event.position=at
    _input_canvas(event)

func _key(code: Key) -> void:
    var event := InputEventKey.new()
    event.keycode=code;event.pressed=true
    _unhandled_key_input(event)

func _screen(x: float,z: float) -> Vector2:
    return camera.unproject_position(Vector3(x,bed.sample(x,z),z))

func _image(directory: String,name: String) -> void:
    status_label.text=notice
    selected_label.text="摆件："+(rock_specs[rocks[selected].id].name_zh if selected>=0 else "点击选取后可移动")
    detail_label.text="右键旋转 · 滚轮拉近 · 底沙 %.1f L · %d 件摆件 · 16 块地形" % [bed.volume()*1000,rocks.size()]
    for i in 4:await get_tree().process_frame
    await RenderingServer.frame_post_draw
    var path := directory+"/"+name+".png"
    _check("screenshot_"+name,get_viewport().get_texture().get_image().save_png(path)==OK)
    outputs.append(path)

func _capture(directory: String) -> void:
    capture_active=true
    DirAccess.make_dir_recursive_absolute(directory)
    for i in 35:await get_tree().process_frame
    var node_count := _nodes()
    var initial := _state()
    await _image(directory,"01-flat-bed")
    var point := _screen(-.35,.13)
    var picked: Variant=_ray_bed(point)
    _check("heightfield_ray_pick",picked!=null and Vector2(picked.x+.35,picked.z-.13).length()<.0002)
    _mouse(MOUSE_BUTTON_LEFT,true,point)
    _check("pour_press_routes_to_brush",painting)
    for i in 50:
        _motion(_screen(-.35+i*.010,.13))
        _stamp(1.0/30)
    _mouse(MOUSE_BUTTON_LEFT,false,pointer)
    _check("pour_release_stops",not painting)
    var poured := _state()
    _check("pour_increases_volume",bed.volume()>.0185)
    _check("pour_keeps_node_count",_nodes()==node_count)
    await _image(directory,"02-poured-ridge")
    _undo()
    _check("stroke_undo_restores_sand_and_rocks",_equal(_state(),initial))
    _redo()
    _check("stroke_redo_restores_sand_and_rocks",_equal(_state(),poured))
    _key(KEY_2)
    _check("remove_shortcut",tool=="remove")
    var before: float=bed.volume()
    _mouse(MOUSE_BUTTON_LEFT,true,_screen(-.15,.13))
    for i in 30:_stamp(1.0/30)
    _mouse(MOUSE_BUTTON_LEFT,false,pointer)
    _check("remove_lowers_volume",bed.volume()<before)
    await _image(directory,"03-excavated-ridge")
    _key(KEY_3)
    var rough_before := _roughness()
    _mouse(MOUSE_BUTTON_LEFT,true,_screen(-.15,.13))
    for i in 50:_stamp(1.0/30)
    _mouse(MOUSE_BUTTON_LEFT,false,pointer)
    _check("smooth_reduces_local_roughness",_roughness()<rough_before)
    _key(KEY_4)
    var first: Dictionary=rocks[0]
    var center: Vector3=first.node.global_transform*first.bounds.get_center()
    _mouse(MOUSE_BUTTON_LEFT,true,camera.unproject_position(center))
    _check("select_stone_by_ray",selected==0 and moving)
    var old_position: Vector3=rocks[0].node.position
    _motion(_screen(-.36,-.09))
    _mouse(MOUSE_BUTTON_LEFT,false,pointer)
    _check("drag_stone_moves",old_position.distance_to(rocks[0].node.position)>.05)
    var old_yaw: float=rocks[0].node.rotation.y
    _key(KEY_E)
    _check("rotate_stone",absf(rocks[0].node.rotation.y-old_yaw-deg_to_rad(15))<1e-6)
    var old_scale: float=rocks[0].factor
    _mouse(MOUSE_BUTTON_WHEEL_UP,true,pointer,true)
    _check("scale_stone",rocks[0].factor>old_scale)
    _key(KEY_6)
    _motion(_screen(.38,.14))
    _check("stone_preview_exists",is_instance_valid(ghost) and ghost.visible)
    var rock_count := rocks.size()
    _mouse(MOUSE_BUTTON_LEFT,true,pointer)
    _mouse(MOUSE_BUTTON_LEFT,false,pointer)
    _check("place_second_type",rocks.size()==rock_count+1 and rocks[-1].id=="river_boulder")
    _key(KEY_4)
    _key(KEY_DELETE)
    _check("delete_selected_stone",rocks.size()==rock_count)
    _undo()
    _check("undo_deleted_stone",rocks.size()==rock_count+1)
    _set_tool("pour")
    var saved := _state()
    _check("save_writes",_write_save(directory+"/test-save.json"))
    _clear()
    _check("clear_changes_state",not _equal(_state(),saved))
    _check("save_load_reads",_read_save(directory+"/test-save.json"))
    _check("save_load_roundtrip",_equal(_state(),saved))
    var bad := FileAccess.open(directory+"/invalid-test-save.json",FileAccess.WRITE)
    bad.store_string('{"schema_version":1,"grid":[129,65],"sand":"fine_sand","heights":[],"rocks":[]}');bad.close()
    _check("invalid_save_rejected",not _read_save(directory+"/invalid-test-save.json") and _equal(_state(),saved))
    _demo(false)
    _set_tool("pour")
    pointer=Vector2(-100,-100);_update_cursor()
    var stable_nodes := _nodes()
    var samples: Array=[]
    for i in 150:
        var start := Time.get_ticks_usec()
        bed.brush(Vector3(-.42+fmod(i*.027,.84),0,.13),.07,.033,"pour" if i%3!=0 else "remove")
        samples.append((Time.get_ticks_usec()-start)/1000.0)
    _check("many_strokes_keep_node_count",_nodes()==stable_nodes)
    var wide_samples: Array=[]
    for i in 30:
        var start := Time.get_ticks_usec()
        bed.brush(Vector3(-.2+fmod(i*.037,.4),0,.05),.15,.033,"pour")
        wide_samples.append((Time.get_ticks_usec()-start)/1000.0)
    wide_samples.sort()
    _check("maximum_brush_keeps_node_count",_nodes()==stable_nodes)
    var finite := true
    for value in bed.heights:finite=finite and is_finite(value) and value>=0 and value<=BED.MAX_HEIGHT
    _check("height_values_bounded",finite)
    var dirty_updates: int=bed.mesh_updates
    var frame_times: Array=[]
    for i in 120:
        var start := Time.get_ticks_usec()
        await get_tree().process_frame
        frame_times.append((Time.get_ticks_usec()-start)/1000.0)
    _check("idle_does_not_rebuild_mesh",bed.mesh_updates==dirty_updates)
    var idle_rebuilds: int=bed.mesh_updates-dirty_updates
    samples.sort();frame_times.sort()
    var hardware := RenderingServer.get_video_adapter_name()
    var draw_calls: float=Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
    var drawn_objects: float=Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)
    _demo(false)
    notice="示例：后侧堆坡，石脚埋进底床；可继续修改。"
    await _image(directory,"04-demo-slope")
    pitch=.28;_camera()
    await _image(directory,"05-low-angle-thickness")
    pitch=1.45;_camera()
    await _image(directory,"06-top")
    pitch=.64;view_size=.82;_camera()
    await _image(directory,"07-close-sand-and-stones")
    view_size=1.30;_camera();_restore(initial)
    var base_y: float=rocks[0].node.position.y
    for i in 70:bed.brush(Vector3(-.2,0,.04),.12,.033,"pour");_settle_rocks()
    _check("sand_buries_stone_without_lifting",bed.sample(-.2,.04)>.065 and absf(rocks[0].node.position.y-base_y)<1e-6)
    notice="实测：在石脚周围倒沙，沙堆掩埋石头底部。"
    await _image(directory,"08-poured-around-stone")
    for i in 100:bed.brush(Vector3(-.2,0,-.02),.15,.033,"remove");_settle_rocks()
    _check("excavated_stone_lowers_to_support",rocks[0].node.position.y<base_y-.005)
    _demo(false)
    await _substrate_checks(directory)
    await _decor_checks(directory)
    var failures: Array=[]
    for name in checks:
        if not checks[name]:failures.append(name)
    var data := {"schema_version":1,"command":"aquascape.native-decor-placement-trial","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","checks":checks,"outputs":outputs,"failures":failures,"summary":{"grid_samples":[BED.NX,BED.NZ],"height_samples":bed.heights.size(),"terrain_chunks":16,"sand_top_triangles":128*64*2,"persistent_grain_nodes":0,"rock_types":ROCK_IDS,"stress_brush_edits":150,"world_nodes_before_stress":stable_nodes,"world_nodes_after_stress":_nodes(),"idle_mesh_rebuilds":idle_rebuilds,"brush_cpu_ms_median":samples[samples.size()/2],"brush_cpu_ms_p95":samples[int(samples.size()*.95)],"sampled_idle_frame_ms_median":frame_times[60],"sampled_idle_frame_ms_p95":frame_times[114],"sampled_draw_calls":draw_calls,"sampled_drawn_objects":drawn_objects,"gpu":hardware},"visual_review":"pending","user_acceptance":"pending","limitations":["The bed has one top height per X/Z position; no terrain caves or true granular mixing.","Three local slope relaxation passes approximate sand spreading, not physical sand simulation.","Rocks use bounding-box selection and sampled support, not rigid-body settling or exact mesh collision.","Performance samples describe this machine and scene, not a minimum-device FPS guarantee.","Native checks route mouse/key handlers; they do not constitute a complete human usability review."]}
    data.summary["maximum_brush_diameter_cm"]=30
    data.summary["maximum_brush_cpu_ms_median"]=wide_samples[wide_samples.size()/2]
    data.summary["maximum_brush_cpu_ms_p95"]=wide_samples[int(wide_samples.size()*.95)]
    data.summary["substrate_types"]=5
    data.summary["gravel_batches"]=32
    data.summary["max_visible_gravel"]=4608
    data.summary["gravel_stress_cpu_ms_p95"]=gravel_stress_p95
    data.summary["gravel_follow_error_m"]=gravel_follow_error
    data.summary["decor_types"]=decor_entries.size()
    data.summary["decor_placement_count"]=10
    var file := FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(data,"  "))
    print(JSON.stringify(data))
    get_tree().quit(0 if failures.is_empty() else 1)

func _roughness() -> float:
    var total := 0.0
    for z in range(38,53):
        for x in range(38,60):
            var i := z*BED.NX+x
            total+=absf(bed.heights[i]*4-bed.heights[i-1]-bed.heights[i+1]-bed.heights[i-BED.NX]-bed.heights[i+BED.NX])
    return total

func _substrate_checks(directory: String) -> void:
    _set_tool("pour")
    pointer=Vector2(-100,-100);_update_cursor()
    var baseline_nodes := _nodes()
    var geometry: PackedFloat32Array=bed.heights.duplicate()
    for id in 5:
        bed.material_ids.fill(id)
        bed.rebuild_all()
        _choose_substrate(id)
        _check("material_%d_preserves_height" % id,bed.heights==geometry)
        _check("material_%d_fixed_nodes" % id,_nodes()==baseline_nodes)
        _check("material_%d_gravel_density" % id,bed.gravel.visible_count()==(4608 if id>=3 else 0))
        notice=SUBSTRATE_NAMES[id]+" · 同一坡形 / 相机，查看底材与颗粒差别。"
        await _image(directory,"material-%d" % id)
        if id>=3:
            pitch=.25;view_size=.75;_camera()
            await _image(directory,"material-%d-close" % id)
            pitch=.64;view_size=1.30;_camera()
    bed.material_ids.fill(0);bed.rebuild_all();_choose_substrate(4)
    _key(KEY_7)
    _check("paint_tool_shortcut",tool=="paint")
    var original := _state()
    _mouse(MOUSE_BUTTON_LEFT,true,_screen(.05,.13))
    for i in 12:
        _motion(_screen(.05+i*.015,.13));_stamp(1.0/30)
    _mouse(MOUSE_BUTTON_LEFT,false,pointer)
    var painted := _state()
    _check("paint_changes_only_local_material",bed.heights==geometry and bed.material_at(.12,.13)==4 and bed.material_at(-.5,-.2)==0)
    _check("paint_adds_batched_gravel",bed.gravel.visible_count()>0 and bed.gravel.visible_count()<4608)
    _undo();_check("undo_restores_material_map",_equal(_state(),original))
    _redo();_check("redo_restores_material_map",_equal(_state(),painted))
    _mixed_demo()
    var mixed := _state()
    _check("mixed_save_written",_write_save(directory+"/mixed-save.json"))
    bed.material_ids.fill(0);bed.rebuild_all()
    _check("mixed_save_loaded",_read_save(directory+"/mixed-save.json") and _equal(_state(),mixed))
    var legacy: Dictionary=mixed.duplicate(true)
    legacy.erase("materials");legacy.erase("selected_substrate");legacy.schema_version=1
    var file := FileAccess.open(directory+"/legacy-save.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(legacy));file.close()
    _check("legacy_save_loads_as_original_sand",_read_save(directory+"/legacy-save.json") and bed.material_ids.count(0)==BED.NX*BED.NZ)
    var invalid: Dictionary=mixed.duplicate(true)
    invalid.materials[0]=9
    file=FileAccess.open(directory+"/invalid-material-save.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(invalid));file.close()
    var before := _state()
    _check("invalid_material_save_rejected",not _read_save(directory+"/invalid-material-save.json") and _equal(_state(),before))
    _restore(mixed)
    _choose_substrate(4)
    var times: Array=[]
    for i in 100:
        var start := Time.get_ticks_usec()
        bed.brush(Vector3(.25,0,.12),.15,.033,"pour" if i%2==0 else "remove")
        times.append((Time.get_ticks_usec()-start)/1000.0)
    times.sort();gravel_stress_p95=times[95]
    _check("gravel_stress_fixed_nodes",_nodes()==baseline_nodes)
    _check("gravel_count_capped",bed.gravel.visible_count()<=4608)
    # Compare every serialized instance's anchor against the edited heightfield.
    for chunk in 16:
        for kind in 2:
            var node: MultiMeshInstance3D=bed.gravel.batches[chunk][kind]
            var box: AABB=bed.gravel.bounds[kind]
            for i in node.multimesh.visible_instance_count:
                var transform: Transform3D=node.multimesh.get_instance_transform(i)
                var factor: float=transform.basis.x.length()
                var expected: float=bed.sample(transform.origin.x,transform.origin.z)-box.size.y*factor*.38-box.position.y*factor
                gravel_follow_error=maxf(gravel_follow_error,absf(transform.origin.y-expected))
    _check("gravel_follows_edited_height",gravel_follow_error<.000002)
    var updates: int=bed.gravel.refreshes
    for i in 12:await get_tree().process_frame
    _check("idle_does_not_refresh_gravel",bed.gravel.refreshes==updates)
    _mixed_demo()
    pointer=Vector2(-100,-100);_update_cursor()
    notice="混铺示例：石英砂小路、水草泥、砾砂和小碎石。"
    await _image(directory,"mixed-overview")
    pitch=1.45;_camera()
    await _image(directory,"mixed-top")
    pitch=.35;_camera()
    await _image(directory,"mixed-low-angle")

func _decor_checks(directory: String) -> void:
    decor_focus=false
    _clear()
    bed.active_material=0;bed.reset(.025)
    yaw=.1;pitch=1.15;view_size=1.45;_camera()
    for i in decor_entries.size():
        decor_buttons[i].pressed.emit()
        _check("decor_%s_palette_preview" % decor_entries[i].id,tool=="decor" and ghost_id==decor_entries[i].id and is_instance_valid(ghost))
        var at := Vector2((i%5-2)*.235,(i/5-.5)*.29)
        _motion(_screen(at.x,at.y))
        var before := rocks.size()
        _mouse(MOUSE_BUTTON_LEFT,true,pointer);_mouse(MOUSE_BUTTON_LEFT,false,pointer)
        _check("decor_%s_placed" % decor_entries[i].id,rocks.size()==before+1 and rocks[-1].id==decor_entries[i].id)
        _set_tool("select")
        var row: Dictionary=rocks[-1]
        var center: Vector3=row.node.global_transform*row.bounds.get_center()
        _mouse(MOUSE_BUTTON_LEFT,true,camera.unproject_position(center));_mouse(MOUSE_BUTTON_LEFT,false,pointer)
        _check("decor_%s_selectable" % decor_entries[i].id,selected==i)
        var angle: float=row.node.rotation.y
        _key(KEY_E)
        _check("decor_%s_rotates" % decor_entries[i].id,absf(row.node.rotation.y-angle-deg_to_rad(15))<.00001)
        var size: float=row.factor
        _mouse(MOUSE_BUTTON_WHEEL_UP,true,pointer,true)
        _check("decor_%s_scales" % decor_entries[i].id,row.factor>size)
    var all_placed := _state()
    _check("ten_distinct_decor_instances",rocks.size()==10)
    _check("decor_save_written",_write_save(directory+"/decor-save.json"))
    _clear()
    _check("decor_save_roundtrip",_read_save(directory+"/decor-save.json") and _equal(_state(),all_placed))
    selected=9;_key(KEY_DELETE)
    _check("decor_delete",rocks.size()==9)
    _undo();_check("decor_delete_undo",_equal(_state(),all_placed))
    var invalid: Dictionary=all_placed.duplicate(true)
    invalid.rocks[0].id="unknown_unreviewed_prop"
    var file := FileAccess.open(directory+"/invalid-decor-save.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(invalid));file.close()
    _check("unknown_decor_save_rejected",not _read_save(directory+"/invalid-decor-save.json") and _equal(_state(),all_placed))
    # CPU source aperture tests are complemented by actual imported gray and
    # painted native views, not a topology-only completion claim.
    _decor_gallery()
    pointer=Vector2(-100,-100);_update_cursor()
    for i in decor_entries.size():
        for view in ["front","right","back","top","gray"]:
            _focus_decor(i,view)
            var box: AABB=rocks[i].bounds
            var framed := true
            for corner in 8:
                var p: Vector2=camera.unproject_position(rocks[i].node.global_transform*box.get_endpoint(corner))
                framed=framed and p.x>20 and p.x<1110 and p.y>305 and p.y<800
            _check("decor_%s_%s_clear_of_ui" % [decor_entries[i].id,view],framed)
            notice=decor_entries[i].name_zh+" · "+{"front":"正斜视","right":"侧视","back":"背面","top":"俯视","gray":"灰模 / 洞口检查"}[view]
            await _image(directory,decor_entries[i].id+"-"+view)
    _decor_gallery()
    notice="十种独立装饰 · 继续摆放、移动、旋转、缩放或埋沙。"
    await _image(directory,"decor-overview")
    pitch=1.35;_camera()
    await _image(directory,"decor-top-overview")
