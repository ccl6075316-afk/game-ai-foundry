extends "/Users/czl/projects/game-ai-foundry/resources/scripts/volume-fish/portable/capture_fish_review.gd"
func _initialize():
    var args=OS.get_cmdline_user_args();assert(args.size()==2)
    plan_path=args[0];review_out=args[1];plan=JSON.parse_string(FileAccess.get_file_as_string(plan_path))
    for key in ["model","motion_profile","motion_runtime","packed_parts_manifest"]:assert(FileAccess.get_sha256(plan[key])==plan[key+"_sha256"])
    DirAccess.make_dir_recursive_absolute(review_out);root.hide();create_timer(120.).timeout.connect(func():quit(2));call_deferred("_run")
func _run():
    load_plan=plan;var box=SubViewportContainer.new();root.add_child(box)
    var entry=super._load("candidate",box);entries.append(entry);entry.view.mesh_lod_threshold=0.
    entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
    packed_partition=PACKED_PARTS.surfaces(entry,plan);assert(packed_partition.ok)
    zoom=float(plan.whole_camera_size);focus=whole_focus();await photo_views("whole")
    for detail in plan.details:
        zoom=float(detail.size);focus=Vector3(detail.at[0],detail.at[1],detail.at[2]);await photo_views(detail.name)
    packed_probes=PACKED_PARTS.make_probes(entry,packed_partition)
    for row in packed_partition.surfaces:row.mesh.hide()
    for key in packed_probes:packed_probes[key].visible=key==plan.body
    zoom=float(plan.whole_camera_size);focus=whole_focus();await photo_views("body")
    if plan.get("capture_fins",false):
        for key in packed_probes:packed_probes[key].visible=key!=plan.body
        direction=Vector3(0,0,1);_set_gray(false);await photo("all-fins-left")
        direction=Vector3(0,0,-1);await photo("all-fins-right")
    PACKED_PARTS.clear_probes(packed_probes)
    for row in packed_partition.surfaces:row.mesh.show()
    _set_gray(false)
    if plan.get("capture_actions",false):
        for action in ["Swim","Turn","Ascend","Dive"]:
            assert(entry.controller.set_action(action,true));entry.controller.step(0.);entry.controller.seek(1.17)
            zoom=float(plan.whole_camera_size);focus=whole_focus();direction=Vector3(.5,.2,1).normalized();await photo("action-"+action)
    report.merge({"ok":true,"model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"packed_partition":packed_partition.proof,"scope":"Local static material capture; representative actions only when requested; no automatic anatomy or full physical acceptance."})
    FileAccess.open(review_out.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  "));quit()
