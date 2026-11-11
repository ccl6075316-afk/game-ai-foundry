extends "/Users/czl/projects/game-ai-foundry/work/clean-pixel-red-seabream-20261111/capture-candidate.gd"
func _run():
    load_plan=plan
    var box=SubViewportContainer.new()
    root.add_child(box)
    var entry=super._load("candidate",box)
    entries.append(entry)
    entry.view.mesh_lod_threshold=0.
    entry.player.stop()
    entry.skeleton.reset_bone_poses()
    entry.carrier.transform=Transform3D.IDENTITY
    packed_partition=PACKED_PARTS.surfaces(entry,plan)
    assert(packed_partition.ok)
    packed_probes=PACKED_PARTS.make_probes(entry,packed_partition)
    for row in packed_partition.surfaces:
        row.mesh.hide()
    for key in packed_probes:
        packed_probes[key].visible=key=="Caudal_mesh"
    zoom=float(plan.model_scale)*.58
    focus=Vector3(-.405*float(plan.model_scale),0,0)
    await photo_views("tail")
    report.merge({"ok":true,"model_sha256":plan.model_sha256,"plan_sha256":FileAccess.get_sha256(plan_path)})
    FileAccess.open(review_out.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
    quit()
