extends "res://scripts/aquarium/HallBuildReview.gd"

func _settle() -> void:
    for i in 12:await get_tree().process_frame
    await RenderingServer.frame_post_draw

func _patch(img: Image,camera: Camera3D,at: Vector3) -> Color:
    var p := Vector2i(camera.unproject_position(at));var sum := Color(0,0,0,0)
    if not Rect2i(2,2,img.get_width()-4,img.get_height()-4).has_point(p):
        _check("all_gpu_donors_inside_image",false);return Color.BLACK
    for x in range(-2,3):
        for y in range(-2,3):sum+=img.get_pixelv(p+Vector2i(x,y))
    return sum/25.0

func _capture() -> void:
    await _settle()
    var original := _state();var other_water: Dictionary=objects[1].data.water.duplicate(true)
    var original_content: Dictionary=objects[0].tank.content_state()
    water_renderer.frozen=true;water_renderer.clock=1.0
    for row in objects:
        if row.tank!=null:row.tank.paused=true
    selected=0;_open_water_panel()
    water_panel.sliders.visibility_m.value=4.5
    _check("actual_water_slider_changes_only_selected_tank",objects[0].data.water.visibility_m==4.5 and _same(objects[1].data.water,other_water))
    _undo();_check("undo_restores_water_profile",_same(objects[0].data.water,original.objects[0].water))
    _redo();_check("redo_restores_water_slider",objects[0].data.water.visibility_m==4.5)
    selected=0;_water_preset(2)
    _check("preset_updates_actual_tank",objects[0].data.water.tint=="19547b")
    var edited := _state()
    _check("water_settings_written",_write_layout(directory+"/water-layout.json"))
    _restore(original);_check("water_settings_round_trip",_load_layout(directory+"/water-layout.json") and _same(_state(),edited))
    var bad := _state();bad.objects[0].water.visibility_m=0
    _check("invalid_water_distance_rejected",not _valid_state(bad))
    bad=_state();bad.objects[0].water.strength=NAN
    _check("nonfinite_water_value_rejected",not _valid_state(bad))
    bad=_state();bad.objects[0].water.tint="garbage"
    _check("invalid_water_color_rejected",not _valid_state(bad))
    var legacy := original.duplicate(true)
    for row in legacy.objects:row.erase("water")
    _check("old_layout_without_water_valid",_valid_state(legacy))
    _restore(legacy);_check("old_layout_gets_water_defaults",_same(objects[0].data.water,WaterProfile.DEFAULT))
    _restore(original);selected=0;_sync_panel();water_panel.hide()
    _mode(false)
    water_renderer.enabled=false;notice="对照：关闭水体，保留同样的大厅灯光。"
    await _image("23-water-off")
    water_renderer.enabled=true;notice="水体：按水中距离衰减，保留近处鱼的原画细节。"
    await _image("24-water-outside")
    selected=0;_start_inspection()
    _check("inspection_camera_is_current",inspection_camera.current and inspecting)
    inspection_distance=.55;_update_inspection();await _settle()
    var tank=objects[0].tank
    var local_camera: Vector3=tank.to_local(inspection_camera.global_position)
    _check("inspection_can_enter_water",AABB(Vector3(-3,0,-1.5),Vector3(6,2.775,3)).has_point(local_camera))
    notice="缸内近景：近处鱼清楚，水色随距离积累。";await _image("25-water-fish-close")
    _stop_inspection();_check("inspection_returns_to_walk_without_moving_player",not inspecting and eye.current)
    _check("inspection_does_not_change_layout_or_contents",_same(_state(),original) and _same(tank.content_state(),original_content))

    # Known opaque donors isolate actual GPU water response from fish animation.
    var probes := Node3D.new();tank.add_child(probes)
    for row in objects:
        if row.tank!=null:
            for fish_row in row.tank.fish:fish_row.carrier.hide()
    var locations := [Vector3(-1.8,1.55,1.05),Vector3(0,1.55,-.2),Vector3(1.8,1.55,-1.1)]
    var donor := _paint(Color(.75,.55,.35),true)
    for at in locations:_box(probes,at,Vector3(.34,.34,.025),donor)
    var foreground := Vector3(1.1,.95,2.5);_box(probes,foreground,Vector3(.25,.25,.025),donor)
    inspection_camera.global_position=tank.global_transform*Vector3(0,1.55,4.4)
    inspection_camera.look_at(tank.global_transform*Vector3(0,1.55,0));inspection_camera.current=true
    water_renderer.enabled=false;await _settle()
    var off := viewport.get_texture().get_image()
    water_renderer.enabled=true;await _settle()
    var on := viewport.get_texture().get_image()
    var ratios: Array=[]
    for at in locations:
        var before := _patch(off,inspection_camera,tank.global_transform*at)
        var after := _patch(on,inspection_camera,tank.global_transform*at)
        ratios.append(after.r/maxf(before.r,.001))
    _check("gpu_farther_equal_donors_attenuate_more",ratios[0]>ratios[1]+.015 and ratios[1]>ratios[2]+.015)
    var fg_before := _patch(off,inspection_camera,tank.global_transform*foreground)
    var fg_after := _patch(on,inspection_camera,tank.global_transform*foreground)
    _check("gpu_foreground_outside_tank_unchanged",Vector3(fg_before.r,fg_before.g,fg_before.b).distance_to(Vector3(fg_after.r,fg_after.g,fg_after.b))<.015)
    _check("gpu_room_corner_not_tinted",off.get_pixel(10,10).is_equal_approx(on.get_pixel(10,10)))
    notice="GPU 对照：同材质测试片，近、中、远的水中路径。";await _image("26-water-depth-probes")
    var origin: Vector3=tank.global_transform*Vector3(0,1.55,4.4)
    var direction: Vector3=-tank.global_basis.z.normalized()
    var length: float=water_renderer.ray_length(tank,origin,direction,20)
    _check("water_path_uses_real_world_metres",is_equal_approx(length,3.0))
    var side_tank=objects[1].tank
    origin=side_tank.global_transform*Vector3(0,1.4,4.4);direction=-side_tank.global_basis.z.normalized()
    _check("water_path_follows_rotated_scaled_tank",is_equal_approx(water_renderer.ray_length(side_tank,origin,direction,20),1.95))
    water_renderer.clock=4.2;await _settle()
    var moving := viewport.get_texture().get_image()
    var caustic_difference := 0.0
    for at in locations:
        var a := _patch(on,inspection_camera,tank.global_transform*at);var b := _patch(moving,inspection_camera,tank.global_transform*at)
        caustic_difference+=absf(a.r-b.r)+absf(a.g-b.g)+absf(a.b-b.b)
    _check("gpu_world_anchored_water_pattern_changes_with_time",caustic_difference>.0001)
    probes.hide();probes.queue_free()
    for row in objects:
        if row.tank!=null:
            for fish_row in row.tank.fish:fish_row.carrier.show()
    inspection_camera.global_position=tank.global_transform*Vector3(0,1.6,1.2)
    inspection_camera.look_at(tank.global_transform*Vector3(0,1.3,-1.2))
    notice="缸内观察：水体边界与距离使用同一套规则。";await _image("27-water-underwater")
    inspection_camera.global_position=tank.global_transform*Vector3(1.8,3.6,4.3)
    inspection_camera.look_at(tank.global_transform*Vector3(0,1.4,0))
    water_panel.show();selected=0;_sync_panel()
    notice="逐缸调节：水色、可见距离、衰减、反光与动态光纹。";await _image("28-water-controls")
    water_panel.hide();inspection_camera.current=false;_mode(true)
    var file := FileAccess.open(directory+"/water-measurements.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"schema_version":1,"gpu_donor_red_on_off_ratios":ratios,"gpu_pattern_change":caustic_difference,"profiles":original.objects.filter(func(r):return r.kind=="tank").map(func(r):return r.water),"world_path_length_m":length,"method":"Actual rendered opaque equal-color donors at three known water distances; same camera, frozen fish and explicit water clock. Outside foreground and room control pixels checked separately.","user_acceptance":"pending"},"  "));file.close()
    for row in objects:
        if row.tank!=null:row.tank.paused=false
    water_renderer.frozen=false
    await super._capture()
