extends "res://scripts/aquarium/HallLightingReview.gd"

func _floor_rgb() -> Color:
    var img := viewport.get_texture().get_image()
    var sum := Color(0,0,0,0);var count := 0
    for at in [Vector3(3,0,4),Vector3(5.5,0,3.2),Vector3(-3,0,4.8)]:
        var center := Vector2i(editor_camera.unproject_position(at))
        for dx in range(-4,5):
            for dy in range(-4,5):
                sum+=img.get_pixelv(center+Vector2i(dx,dy));count+=1
    return sum/float(count)

func _capture() -> void:
    for i in 35:await get_tree().process_frame
    var layout := _state()
    var revised: Dictionary=hall_lighting.profile.duplicate(true)
    var previous: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/aquarium-hall-lighting-v4/lighting.json"))
    for row in objects:
        if row.tank!=null:row.tank.paused=true
    hall_lighting.apply_profile(previous)
    notice="对照：上一版冷白缸灯、灰暗大厅。"
    await _image("18-v4-build")
    var before := _floor_rgb()
    hall_lighting.apply_profile(revised)
    notice="暗蓝布展：保留材质纹理，缸边带少量蓝光。"
    await _image("19-blue-build")
    var after := _floor_rgb()
    _check("floor_blue_red_ratio_increases",after.b/maxf(after.r,.001)>before.b/maxf(before.r,.001)*1.25)
    _check("atmosphere_keeps_layout_identical",_same(layout,_state()))
    _check("spill_has_no_extra_shadow_map",not objects[0].tank.get_node("ExhibitLighting/BlueSpill").shadow_enabled)
    var before_pos: Vector3=objects[1].tank.get_node("ExhibitLighting/BlueSpill").global_position
    _check("spill_follows_scaled_rotated_tank",before_pos.distance_to(objects[1].tank.global_transform*Vector3(0,.45,1.72))<.00001)
    _mode(false)
    hall_lighting.apply_profile(previous)
    notice="对照：上一版逛馆照明。";await _image("20-v4-walk")
    hall_lighting.apply_profile(revised)
    notice="暗蓝逛馆：蓝色环境，保留鱼身自然色。";await _image("21-blue-walk")
    player.position=Vector3(-3.6,.88,3.8);player.rotation.y=-.5;eye.rotation.x=-.10
    await _image("22-blue-side")
    _mode(true)
    for row in objects:
        if row.tank!=null:row.tank.paused=false
    var file := FileAccess.open(directory+"/blue-measurements.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"floor_v4_rgb":[before.r,before.g,before.b],"floor_v5_rgb":[after.r,after.g,after.b],"sampling":"Same three floor patches and camera, fish paused during matched views; display RGB, not physical lux.","profile":revised,"user_acceptance":"pending"},"  "));file.close()
    await super._capture()
