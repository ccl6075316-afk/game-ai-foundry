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
    packed_partition=PACKED_PARTS.surfaces(entry,plan);assert(packed_partition.ok,JSON.stringify(packed_partition))
    zoom=float(plan.whole_camera_size);focus=whole_focus()
    for view in [views()[0],views()[1],views()[4],views()[5]]:
        direction=view.dir;_set_gray(false);await photo("whole-"+view.name+"-texture")
    packed_probes=PACKED_PARTS.make_probes(entry,packed_partition)
    for row in packed_partition.surfaces:row.mesh.hide()
    for key in packed_probes:packed_probes[key].visible=key==plan.body
    for view in [views()[0],views()[4],views()[5]]:
        direction=view.dir;_set_gray(true);await photo("body-"+view.name+"-clay")
    PACKED_PARTS.clear_probes(packed_probes)
    for row in packed_partition.surfaces:row.mesh.show()
    zoom=float(plan.front_camera_size);focus=Vector3(plan.front_focus[0],plan.front_focus[1],plan.front_focus[2]);direction=Vector3(1,0,0)
    _set_gray(false);await photo("head-front-texture");_set_gray(true);await photo("head-front-clay")
    report.merge({"ok":true,"model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"packed_partition":packed_partition.proof,"scope":"Local static material evidence, no automatic visual acceptance."})
    FileAccess.open(review_out.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  "));quit()
