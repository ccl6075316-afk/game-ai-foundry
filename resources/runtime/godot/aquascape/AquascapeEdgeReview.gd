extends "res://scripts/aquarium/AquascapeCatalogLab.gd"
## Compare old/new paint on the SAME imported mesh, bones, camera and phase.
func _capture(directory: String) -> void:
    capture_active=true
    plant_current.running=false
    DirAccess.make_dir_recursive_absolute(directory)
    for child in world.get_children():
        if child is MeshInstance3D:child.visible=false
        if child is WorldEnvironment:child.environment.background_color=Color("101a20")
    var outputs: Array=[]
    var failures: Array=plant_current.failures.duplicate()
    var transform_error := 0.0
    for i in entries.size():
        var row: Dictionary=entries[i]
        if not row.animated:continue
        _focus(i);_mode(0)
        var box: AABB=bounds[row.id]
        var fixed_size: float=view_size
        var model: Node3D=art_nodes[row.id]
        # Load old materials only; use the current model for both renderings.
        var old: Node3D=(load(row.pre_rim_rebuild_model) as PackedScene).instantiate()
        var old_meshes: Dictionary={}
        for mesh in old.find_children("*","MeshInstance3D",true,false):old_meshes[mesh.name]=mesh
        await _settle(0)
        var base: Array=plant_current.sample_probes()
        for factor in [.5,1.0,2.0,4.0]:
            _resize_selected(factor)
            view_size=fixed_size
            target=Vector3(0,box.position.y+box.size.y*.62,0)*factor+Vector3(view_size*.10,0,0)
            for side in ["front","back"]:
                if side=="back" and factor!=4.0:continue
                yaw=.25 if side=="front" else PI+.25
                pitch=.12
                _camera()
                for variant in ["before","after"]:
                    for mesh in model.find_children("*","MeshInstance3D",true,false):
                        for s in mesh.mesh.get_surface_count():
                            if variant=="after":mesh.set_surface_override_material(s,art_originals[mesh][s])
                            else:
                                var paint: StandardMaterial3D=old_meshes[mesh.name].get_active_material(s).duplicate()
                                paint.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
                                paint.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
                                mesh.set_surface_override_material(s,paint)
                    selection_label.text=row.name_zh+"  · 素材 %.1f×  · " % factor+("旧材质" if variant=="before" else "重建边缘")
                    await _settle(2.5)
                    var path: String=directory+"/"+row.id+"-"+str(factor)+"x-"+side+"-"+variant+".png"
                    if get_viewport().get_texture().get_image().save_png(path)!=OK:failures.append(path)
                    outputs.append(path)
            for phase in [0.0,2.5,5.0,7.5,10.0]:
                await _settle(phase)
                var probes: Array=plant_current.sample_probes()
                for j in probes.size():
                    if probes[j].id!=row.id or not probes[j].anchor:continue
                    var b: Array=base[j].position
                    var p: Array=probes[j].position
                    transform_error=maxf(transform_error,(Vector3(b[0],b[1],b[2])*factor).distance_to(Vector3(p[0],p[1],p[2])))
        old.free()
        _resize_selected(1.0)
    if transform_error>.000002:failures.append("scaled native skin roots drift")
    var data := {"schema_version":1,"command":"aquascape.native-enlarged-edge-review","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","outputs":outputs,"failures":failures,"plant_count":10,"model_scales":[.5,1,2,4],"native_phase_samples":[0,2.5,5,7.5,10],"max_scaled_root_error_m":transform_error,"comparison":"Only material overrides differ; mesh, pose, camera, nearest filter and dark background are identical per pair.","visual_review":"pending","user_acceptance":"pending"}
    var file := FileAccess.open(directory+"/render.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify(data,"  "))
    print(JSON.stringify({"ok":data.ok,"images":outputs.size(),"max_scaled_root_error_m":transform_error,"failures":failures}))
    get_tree().quit(0 if failures.is_empty() else 1)
