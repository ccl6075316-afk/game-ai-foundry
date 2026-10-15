extends SceneTree
## Disposable review only. Both panels instantiate the actual exhibit and motion helper.
## godot --path game --fixed-fps 30 --resolution 1280x720 --script <this> -- \
##   --species arapaima --candidate /absolute/candidate.glb --output /private/tmp/review

var species := "blacktip_reef_shark"
var candidate := ""
var out := "/private/tmp/fish-knowledge-052/arapaima"
var frame_count := 600
var cached_models: Array = []
var exhibits: Array = []
var labels: Array = []
var snapshots: Array = []
var failures: Array = []

func _initialize() -> void:
    var args := OS.get_cmdline_user_args()
    for i in range(0,args.size(),2):
        assert(i+1 < args.size(),"Expected option/value pairs")
        match args[i]:
            "--species": species=args[i+1]
            "--candidate": candidate=args[i+1]
            "--output": out=args[i+1]
            "--frames": frame_count=int(args[i+1])
            _: assert(false,"Unknown option: "+args[i])
    assert(species in ["arapaima","scalloped_hammerhead","blacktip_reef_shark"] and FileAccess.file_exists(candidate))
    call_deferred("run")

func cache_model(path: String, resource_path: String) -> void:
    var document := GLTFDocument.new()
    var state := GLTFState.new()
    assert(document.append_from_file(path,state) == OK,"GLB import failed: "+path)
    var instance := document.generate_scene(state)
    var packed := PackedScene.new()
    assert(packed.pack(instance) == OK)
    packed.take_over_path(resource_path)
    cached_models.append(packed)
    instance.free()

func prepare_panel(index: int) -> void:
    var exhibit = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(exhibit)
    exhibit.set_process(false)
    exhibit.paused=true
    exhibit._select_display(species)
    exhibit.position=Vector2(index*640,0)
    exhibit.size=Vector2(640,720)
    exhibit.header.hide()
    exhibit.footer.hide()
    exhibit.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
    exhibit.screen.position=Vector2(0,66)
    exhibit.screen.size=Vector2(640,630)
    exhibit.viewport.size=Vector2i(640,630)
    exhibit.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    for tank in exhibit.tanks:
        tank.root.visible=tank.species==species
    var label := Label.new()
    label.position=Vector2(index*640+18,10)
    label.add_theme_font_size_override("font_size",21)
    root.add_child(label)
    labels.append(label)
    exhibits.append(exhibit)
    var entry: Dictionary=exhibit._selected()
    entry.controller.set_action("Swim",true)
    entry.controller.step(0.0)

func camera_pose(exhibit, yaw: float, pitch: float) -> void:
    var entry: Dictionary=exhibit._selected()
    var carrier: Node3D=entry.carrier
    var center: Vector3=carrier.global_position
    var length_m: float=entry.length_m
    # Same fish-relative view in both worlds; changing path heading cannot hide a side.
    var offset: Vector3=carrier.global_basis.orthonormalized()*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))
    exhibit.camera.global_position=center+offset*length_m*1.70
    var up: Vector3=carrier.global_basis.orthonormalized()*Vector3.UP
    exhibit.camera.look_at(center,up)

func capture_stills() -> void:
    # Both panels share the same animation phase for direct silhouette comparisons.
    var views: Dictionary={"side":[0.0,0.0],"front":[PI/2.0,0.0],"top":[0.0,1.48],"belly":[0.0,-1.25],"oblique":[0.62,0.38]}
    for view in views:
        for exhibit in exhibits:
            var entry: Dictionary=exhibit._selected()
            entry.controller.seek(0.0)
            camera_pose(exhibit,float(views[view][0]),float(views[view][1]))
        await process_frame
        await RenderingServer.frame_post_draw
        assert(root.get_texture().get_image().save_png(out+"/still-"+view+".png")==OK)

func run() -> void:
    root.size=Vector2i(1280,720)
    root.content_scale_size=Vector2i(1280,720)
    DirAccess.make_dir_recursive_absolute(out)
    for fish_species in ["blacktip_reef_shark","scalloped_hammerhead","silver_arowana","hairtail","piranha","arapaima"]:
        var path: String="res://assets/models/fish/%s.glb"%fish_species
        cache_model(path,path)
    prepare_panel(0)
    cache_model(candidate,"res://assets/models/fish/%s.glb"%species)
    prepare_panel(1)
    for index in exhibits.size():
        var entry: Dictionary=exhibits[index]._selected()
        labels[index].text=("BEFORE  |  " if index==0 else "AFTER  |  ")+species+"  %.0f cm"%(float(entry.length_m)*100.0)
    await capture_stills()
    for exhibit in exhibits:
        var entry: Dictionary=exhibit._selected()
        entry.controller.set_action("Swim",true)
        entry.controller.step(0.0)
    for frame in frame_count:
        var t: float=float(frame)/30.0
        var action := "Swim"
        if t>=17.0: action="Dive"
        elif t>=14.5: action="Ascend"
        elif t>=12.0: action="Turn"
        var yaw: float=TAU*t/12.0 if t<12.0 else 0.62
        var pitch: float=0.80*sin(TAU*t/12.0) if t<12.0 else 0.38
        var row := {"frame":frame,"seconds":t,"requested_action":action,"camera_yaw":yaw,"camera_pitch":pitch,"models":[]}
        for index in exhibits.size():
            var exhibit=exhibits[index]
            var entry: Dictionary=exhibit._selected()
            if entry.requested_action!=action:
                entry.controller.set_action(action)
                entry.requested_action=action
            entry.controller.step(1.0/30.0)
            camera_pose(exhibit,yaw,pitch)
            var snapshot: Dictionary=entry.controller.snapshot()
            row.models.append({"version":"before" if index==0 else "after","motion":snapshot})
            if not snapshot.get("ready",false) or not snapshot.get("inside_envelope",false):
                failures.append({"frame":frame,"panel":index,"reason":"motion not ready or outside envelope"})
            labels[index].text=("BEFORE  |  " if index==0 else "AFTER  |  ")+species+"  %.0f cm\n%s  |  %05.2f s"%[float(entry.length_m)*100.0,action,t]
        snapshots.append(row)
        await process_frame
        await RenderingServer.frame_post_draw
        assert(root.get_texture().get_image().save_png(out+"/frame_%04d.png"%frame)==OK)
    var report := {"schema_version":1,"command":"volume.native-revision.runtime-review","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review","species":species,"candidate":candidate,"fps":30,"frames":frame_count,"size":[1280,720],"same_runtime_exhibit":true,"renderer":RenderingServer.get_video_adapter_name(),"visual_review":"pending","candidate_sha256":FileAccess.get_sha256(candidate),"baseline_sha256":FileAccess.get_sha256("res://assets/models/fish/%s.glb"%species),"controller_sha256":FileAccess.get_sha256("res://scripts/aquarium/FoundryFishMotion.gd"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json"),"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd"),"export_script_sha256":FileAccess.get_sha256(get_script().resource_path),"failures":failures,"snapshots":snapshots}
    var file := FileAccess.open(out+"/validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(report,"  "))
    file.close()
    print("NATIVE_REVISION_REVIEW "+JSON.stringify({"ok":report.ok,"frames":frame_count,"output":out,"failures":failures.size()}))
    quit(0 if failures.is_empty() else 1)
