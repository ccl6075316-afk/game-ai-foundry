extends "res://scripts/aquarium/HallBuildReview.gd"

func _floor_luminance() -> float:
    var img := viewport.get_texture().get_image()
    var sum := 0.0;var count := 0
    for at in [Vector3(3,0,4),Vector3(5.5,0,3.2),Vector3(-3,0,4.8)]:
        var center: Vector2i=Vector2i(editor_camera.unproject_position(at))
        for dx in range(-4,5):
            for dy in range(-4,5):
                var c := img.get_pixelv(center+Vector2i(dx,dy))
                sum+=c.r*.2126+c.g*.7152+c.b*.0722;count+=1
    return sum/count

func _capture() -> void:
    for i in 35:await get_tree().process_frame
    var initial := _state()
    hall_lighting.set_state(false,true);notice="照明对照：原来的均匀亮厅。"
    await _image("14-before-lighting")
    var bright := _floor_luminance()
    hall_lighting.set_state(true,true);notice="布展照明：暗厅、亮缸，保留地面和物件轮廓。"
    await _image("15-build-lighting")
    var dim := _floor_luminance()
    _check("floor_away_from_tanks_visibly_dimmer",dim<bright*.7)
    _check("construction_floor_remains_visible",dim>.045)
    _check("lighting_not_added_to_save_document",_same(initial,_state()))
    _check("two_local_lights_per_tank",objects[0].tank.get_node("ExhibitLighting").find_children("*","SpotLight3D",true,false).size()==2)
    _check("bounded_shadow_lights_per_tank",objects[0].tank.get_node("ExhibitLighting").find_children("*","SpotLight3D",true,false).filter(func(l):return l.shadow_enabled).size()==1)
    var lamp: SpotLight3D=objects[1].tank.get_node("ExhibitLighting/TankTop0")
    _check("local_lights_follow_rotated_scaled_tank",lamp.global_position.distance_to(objects[1].tank.global_transform*Vector3(-1.5,2.72,float(hall_lighting.profile.tank_front_z_m)))<.00001)
    _check("guide_markers_on_perimeter",room_geometry.find_children("LowGuideLight*","MeshInstance3D",true,false).size()>0)
    var build_energy: float=hall_lighting.environment.environment.ambient_light_energy
    var tank_energy: float=lamp.light_energy
    _mode(false)
    _check("walk_uses_dimmer_ambient_than_build",hall_lighting.environment.environment.ambient_light_energy<build_energy)
    _check("walk_preserves_local_tank_light_energy",lamp.light_energy==tank_energy and is_equal_approx(lamp.light_energy,float(hall_lighting.profile.tank_energy)))
    notice="逛馆照明：展缸独立亮起，走道保留微光。"
    await _image("16-walk-lighting")
    player.position=Vector3(-3.6,.88,3.8);player.rotation.y=-.5;eye.rotation.x=-.10
    await _image("17-side-walk-lighting")
    _mode(true)
    _check("mode_round_trip_restores_build_light",hall_lighting.environment.environment.ambient_light_energy==build_energy)
    _check("lighting_mode_changes_preserve_layout",_same(initial,_state()))
    var measurements := {"schema_version":1,"command":"aquarium.hall-lighting-measurements","floor_before":bright,"floor_build_after":dim,"ratio":dim/bright,"profile":hall_lighting.profile,"artwork_shaders":"Shaded fish surfaces, sand and architecture respond to lights; unshaded artwork props preserve their source colors.","user_acceptance":"pending"}
    var file := FileAccess.open(directory+"/lighting-measurements.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(measurements,"  "));file.close()
    await super._capture()
