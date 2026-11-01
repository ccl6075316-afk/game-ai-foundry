extends SceneTree
var out:String
func _initialize():
    out=OS.get_cmdline_user_args()[0]
    call_deferred("run")
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(1360,1000)
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(hall)
    await process_frame
    var rows=[]
    for sp in ["scalloped_hammerhead","great_hammerhead","smooth_hammerhead"]:
        hall._select_display(sp)
        for view in ["俯视","看嘴"]:
            hall._on_button(view)
            assert(hall.paused and not hall.overview)
            assert(hall.pitch<-.9 if view=="看嘴" else hall.pitch>1.5)
            await process_frame
            RenderingServer.force_draw()
            await process_frame
            var path=out+"/"+sp+("-mouth.png" if view=="看嘴" else "-top.png")
            assert(hall.viewport.get_texture().get_image().save_png(path)==OK)
            rows.append({"species":sp,"view":view,"file":path,"sha256":FileAccess.get_sha256(path),"pitch":hall.pitch,"camera":str(hall.camera.position),"target":str(hall.target)})
        hall.pitch=-1.3;hall._update_camera();assert(is_equal_approx(hall.pitch,-1.3))
        hall._on_button("复位");assert(hall.pitch>=0.)
    hall._select_display("great_hammerhead")
    var model=hall._selected().model
    var mesh=model.find_child("Closed_body",true,false)
    var material=mesh.get_active_material(0)
    var helper=load("res://scripts/aquarium/HammerSurface136.gd").new()
    assert(helper.validate(model,"great_hammerhead",mesh,0,material).ok)
    var saved=material.get_shader_parameter("hammer136_top")
    material.set_shader_parameter("hammer136_top",null)
    assert(not helper.validate(model,"great_hammerhead",mesh,0,material).ok)
    material.set_shader_parameter("hammer136_top",saved)
    assert(helper.validate(model,"great_hammerhead",mesh,0,material).ok)
    var f=FileAccess.open(out+"/views.validation.json",FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"records":rows,"missing_source_negative_control":true,"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd")},"  "))
    print("HAMMER_VIEWS136_OK")
    quit()
