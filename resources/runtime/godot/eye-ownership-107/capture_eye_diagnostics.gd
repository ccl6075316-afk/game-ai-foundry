extends "capture_trial.gd"
## Additional views under requested LOD pressure, not proof of every selected LOD.
func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size = Vector2i(1200,800)
    hall = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(hall)
    hall.set_process(false)
    hall.paused = true
    hall.header.hide()
    hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
    hall.screen.position = Vector2.ZERO
    hall.screen.size = Vector2(1200,800)
    hall.viewport.size = Vector2i(1200,800)
    hall.viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    ownership = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    hall._select_display("zander")
    var entry: Dictionary = hall._selected()
    for tank in hall.tanks: tank.root.visible = tank.species == "zander"
    for mesh in hall.world.find_children("*", "MeshInstance3D", true, false):
        intrinsic[mesh.get_instance_id()] = mesh.visible
        mesh.visible = entry.model.is_ancestor_of(mesh) and mesh.visible
    for label in hall.world.find_children("*", "Label3D", true, false): label.hide()
    entry.controller.set_motion_controls({"body_amplitude":0., "body_frequency":1., "fin_amplitude":0., "fin_frequency":1.}, true)
    assert(entry.controller.set_action("Swim", true))
    entry.controller.step(0.)
    entry.controller.seek(0.)
    if entry.has("jaw_controller"): entry.jaw_controller.apply(1.)
    await process_frame
    var r: Dictionary = region(entry)
    var stored: Array = []
    for mesh in entry.model.find_children("*", "MeshInstance3D", true, false):
        for surface in mesh.mesh.get_surface_count():
            stored.append([mesh, surface, mesh.get_surface_override_material(surface), mesh.get_active_material(surface)])
    var views := [["head-side-yaw0", 0., 0.], ["head-side-yawPI", PI, 0.],
        ["head-front", PI/2., 0.], ["head-top", 0., 1.56], ["head-oblique-yaw065", .65, .20], ["head-oblique-yawPIminus065", PI-.65, .20]]
    var samples: Array = []
    for pressure in [["full-detail-request", 0., 1.], ["coarse-pressure-request", 100000., .001]]:
        hall.viewport.mesh_lod_threshold = pressure[1]
        for mesh in entry.model.find_children("*", "MeshInstance3D", true, false): mesh.lod_bias = pressure[2]
        for distance in [["near", 1.], ["far", 3.]]:
            for view in views:
                camera(entry, r, true, view[1], view[2])
                if distance[1] > 1.:
                    var basis: Basis = entry.carrier.global_transform.basis.orthonormalized()
                    var center: Vector3 = entry.model.global_transform * r.head.get_center()
                    hall.camera.global_position = center + (hall.camera.global_position-center) * distance[1]
                    hall.camera.look_at(center, basis * Vector3.UP)
                for shading in ["texture", "albedo"]:
                    set_mode(entry, stored, shading)
                    var file: String = out + "/%s-%s-%s-%s.png" % [pressure[0], distance[0], view[0], shading]
                    await process_frame
                    RenderingServer.force_draw()
                    await process_frame
                    RenderingServer.force_draw()
                    assert(hall.viewport.get_texture().get_image().save_png(file)==OK)
                    samples.append({"file":file, "sha256":FileAccess.get_sha256(file), "view":view[0], "shading":shading,
                        "requested_viewport_mesh_lod_threshold":pressure[1], "requested_mesh_lod_bias":pressure[2], "distance_factor":distance[1],
                        "rendered_primitives":hall.viewport.get_render_info(Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_PRIMITIVES_IN_FRAME),
                        "camera_transform":str(hall.camera.global_transform)})
    var receipt: Dictionary = entry.model.get_meta("eye_ownership_107_receipt", {})
    var valid: bool = receipt.is_empty() if baseline_reference else (not receipt.is_empty() and receipt.get("all_original_lods_retained",false) and receipt.get("lod_geometry_gate",{}).get("status","")=="failed")
    var file := FileAccess.open(out + "/extra-capture.validation.json", FileAccess.WRITE)
    file.store_string(JSON.stringify({"schema_version":1, "ok":samples.size()==48 and valid, "command":"fish.eye-ownership107-extra-capture",
        "stage":"validate", "status":"done", "next_action":"human_review", "inputs":{"eye_mode":eye_trial_mode,"eye_probe":eye_trial_probe,"retired_probe":eye_retired_probe,"baseline_reference":baseline_reference}, "outputs":[],
        "summary":{"samples":samples, "images":samples.size(), "install_receipt":receipt,"baseline_reference":baseline_reference, "body_region_native":str(r.body), "head_region_native":str(r.head),
        "scope":"Two true side views plus front/top/two obliques, two distances, full-detail/coarse LOD pressure and lit/unlit. All6LOD retained and LOD5 gate failed. Requested thresholds and aggregate visible primitive counts do not prove six individual LOD levels were each selected."}, "failures":[]}, "  "))
    file.close()
    hall.queue_free()
    await process_frame
    if RenderingServer.has_method("force_sync"): RenderingServer.force_sync()
    await process_frame
    quit()
