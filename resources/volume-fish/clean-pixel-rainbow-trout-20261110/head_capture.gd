extends "material_capture.gd"
func _run():
    load_plan=plan;var box=SubViewportContainer.new();root.add_child(box)
    var entry=super._load("head-reference",box);entries.append(entry)
    entry.player.stop();entry.skeleton.reset_bone_poses();entry.carrier.transform=Transform3D.IDENTITY
    zoom=.35*float(plan.model_scale);focus=Vector3(.43,.01,0)*float(plan.model_scale);direction=Vector3(1,0,0)
    _set_gray(false);await photo("head-front-texture");_set_gray(true);await photo("head-front-clay")
    FileAccess.open(review_out.path_join("capture.validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  "));quit()
