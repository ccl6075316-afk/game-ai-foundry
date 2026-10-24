extends "res://scripts/aquarium/HallBuildReview.gd"

func _capture() -> void:
    for i in 35:await get_tree().process_frame
    var layout := _state()
    for name in ["hall_floor","hall_wall","hall_wood"]:
        var texture: Texture2D=load(HALL_ART+name+".png")
        _check("native_1024_art_"+name,texture.get_size()==Vector2(1024,1024))
    _check("nearest_material_filter",wall_paint.texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST_WITH_MIPMAPS)
    _set_pixel_materials(false);notice="材质对照：原来的大厅。"
    await _image("10-before-materials")
    _set_pixel_materials(true);notice="材质对照：生成的像素地砖、墙面和木材。"
    await _image("11-after-materials")
    _check("art_toggle_preserves_layout",_same(layout,_state()))
    _mode(false);player.position=Vector3(7,.88,-.6);player.rotation.y=-.40;eye.rotation.x=-.35
    notice="近距离查看：墙面、地砖与石灯展示台。"
    await _image("12-materials-walk-close")
    _mode(true);camera_target=Vector3(1,0,1.5);view_size=5;pitch=.9;yaw=.4;_camera()
    notice="近距离查看：木凳与地砖。"
    await _image("13-materials-furniture-close")
    eye.rotation.x=0;_fit_hall();pitch=.83;yaw=.48;_camera()
    await super._capture()
