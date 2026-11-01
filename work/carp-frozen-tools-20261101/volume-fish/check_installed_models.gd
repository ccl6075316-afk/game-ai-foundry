extends SceneTree
## Verify actual imported production resources through the exhibit, without GLTF cache overrides.
## --installation-report <validation.json> --output <directory>
var receipt_path := ""
var out := ""
var failures: Array = []
var results: Array = []
var exhibit

func _initialize() -> void:
    var args := OS.get_cmdline_user_args()
    for i in range(0,args.size(),2):
        match args[i]:
            "--installation-report": receipt_path=args[i+1]
            "--output": out=args[i+1]
            _: assert(false,"Unknown option")
    assert(not out.is_empty() and FileAccess.file_exists(receipt_path))
    call_deferred("run")

func click(button: Button) -> void:
    var point := button.get_global_rect().get_center()
    var move := InputEventMouseMotion.new()
    move.position=point;move.global_position=point
    root.push_input(move,true)
    var event := InputEventMouseButton.new()
    event.position=point;event.global_position=point
    event.button_index=MOUSE_BUTTON_LEFT;event.pressed=true
    root.push_input(event,true)
    await process_frame
    event=event.duplicate();event.pressed=false
    root.push_input(event,true)
    await process_frame

func run() -> void:
    root.size=Vector2i(1280,720)
    DirAccess.make_dir_recursive_absolute(out)
    var receipt: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(receipt_path))
    assert(receipt.ok)
    exhibit=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(exhibit)
    exhibit.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    await process_frame
    exhibit.set_process(false);exhibit.paused=true
    for installed in receipt.installed:
        var species: String=installed.species
        var path: String="res://assets/models/fish/%s.glb"%species
        var accepted: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(installed.accepted_handoff))
        assert(accepted.style_visual_review=="accepted")
        assert(FileAccess.get_sha256(path)==accepted.style_review.glb_sha256)
        await click(exhibit.display_buttons[species])
        var entry: Dictionary=exhibit._selected()
        assert(entry.species==species)
        var skeleton: Skeleton3D=entry.skeleton
        assert(skeleton.get_bone_count()>0 and not entry.player.get_animation_list().is_empty())
        for action in ["Swim","Turn","Ascend","Dive"]:
            await click(exhibit.action_buttons[action])
            entry.controller.step(0.0)
            var start: Array=[]
            for i in skeleton.get_bone_count():start.append(skeleton.get_bone_pose_rotation(i))
            var contained := true
            var changed := false
            for frame in 120:
                entry.controller.step(1.0/60.0)
                var state: Dictionary=entry.controller.snapshot()
                contained=contained and state.get("ready",false) and state.get("inside_envelope",false)
                # A complete clip may return exactly to its initial pose at the
                # final sample. Prove motion during the interval, not only at its ends.
                for i in skeleton.get_bone_count():
                    changed=changed or absf(start[i].dot(skeleton.get_bone_pose_rotation(i)))<0.999999
            var state: Dictionary=entry.controller.snapshot()
            if not changed or not contained or state.action!=action:failures.append(species+"/"+action)
            results.append({"species":species,"action":action,"actual_imported_resource":true,"model_sha256":FileAccess.get_sha256(path),"bones":skeleton.get_bone_count(),"bone_motion":changed,"inside_envelope":contained,"steps":120})
        exhibit.target=entry.carrier.global_position
        exhibit.distance=float(entry.length_m)*2.6
        exhibit.yaw=0.62;exhibit.pitch=0.38;exhibit._update_camera()
        await process_frame
        await RenderingServer.frame_post_draw
        assert(root.get_texture().get_image().save_png(out+"/"+species+"-installed.png")==OK)
    var report := {"schema_version":1,"command":"volume.installed-models.runtime-qa","stage":"validate","status":"done" if failures.is_empty() else "failed","next_action":"human_review","ok":failures.is_empty(),"failures":failures,"actual_imported_resources":true,"gltf_cache_override":false,"results":results,"exhibit_snapshot":exhibit.review_snapshot(),"installation_report_sha256":FileAccess.get_sha256(receipt_path),"engine_version":Engine.get_version_info().string}
    var file:=FileAccess.open(out+"/validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(report,"  "));file.close()
    print("INSTALLED_MODELS_QA "+JSON.stringify({"ok":report.ok,"actions":results.size(),"failures":failures}))
    quit(0 if failures.is_empty() else 1)
