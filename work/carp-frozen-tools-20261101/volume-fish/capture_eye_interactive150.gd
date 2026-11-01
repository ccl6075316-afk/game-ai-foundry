extends SceneTree
## Cold-load the installed interactive scene and visit every fish selector.
func _initialize():call_deferred("run")
func run():
    var out=OS.get_cmdline_user_args()[0];DirAccess.make_dir_recursive_absolute(out)
    var scene=load("res://scenes/eye_volume150_review.tscn").instantiate();root.add_child(scene)
    scene.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    var rows=[]
    for s in scene.SPECIES:
        scene._select_display(s);scene._eye_close150();assert(scene.eye_focus150)
        assert(scene.distance>0. and scene.target.is_finite());rows.append({"species":s,"focus_native":str(scene.eye_native150),"distance_m":scene.distance})
    scene._select_display("pacific_bluefin_tuna");scene._eye_close150()
    await process_frame;RenderingServer.force_draw();await process_frame;RenderingServer.force_draw()
    assert(root.get_texture().get_image().save_png(out+"/interactive.png")==OK)
    var files={}
    for path in ["scripts/aquarium/EyeVolume150Review.gd","scenes/eye_volume150_review.tscn","scripts/aquarium/EyeRelief112.gd","assets/models/fish/motion/eye-relief112.json"]:files[path]=FileAccess.get_sha256("res://"+path)
    var f=FileAccess.open(out+"/interactive.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":rows.size()==27,"rows":rows,"files":files,"screenshot_sha256":FileAccess.get_sha256(out+"/interactive.png"),"scope":"Cold actual game scene; all27 selector/focus paths, existing action/orbit controls. User appearance acceptance remains pending."}));f.close();scene.queue_free();await process_frame;quit()
