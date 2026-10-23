extends "preview_nose_ink132.gd"
## Keep132 nose repair; add a source-colored stroke on actual lip-band edges.

func apply_nose_patch(_enabled:bool):
    super.apply_nose_patch(true)

func add_lip_band():
    super.add_lip_band()
    if records.is_empty():return
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(plan.edge133_plan))
    var source_data=JSON.parse_string(FileAccess.get_file_as_string(plan.lip_band_mesh))
    var next=ArrayMesh.new()
    var ink=ShaderMaterial.new()
    ink.shader=load(get_script().resource_path.get_base_dir().path_join("lip_edge133.gdshader"))
    ink.set_shader_parameter("lip_atlas",lip_material.albedo_texture)
    ink.set_shader_parameter("lip_ink",Color(cfg.ink_rgb[0]/255.,cfg.ink_rgb[1]/255.,cfg.ink_rgb[2]/255.))
    var receipts=[]
    for si in lip_node.mesh.get_surface_count():
        var arrays=lip_node.mesh.surface_get_arrays(si)
        var before=arrays.duplicate(true)
        # Repack from the frozen input rather than decoding and re-encoding
        # already quantized normals, which can slightly change clay lighting.
        var original=source_data.parts[si]
        var original_vertices=PackedVector3Array();var original_normals=PackedVector3Array();var original_uv=PackedVector2Array()
        for p in original.vertices:original_vertices.append(Vector3(p[0],p[1],p[2]))
        for p in original.normals:original_normals.append(Vector3(p[0],p[1],p[2]))
        for p in original.uv:original_uv.append(Vector2(p[0],p[1]))
        arrays[Mesh.ARRAY_VERTEX]=original_vertices;arrays[Mesh.ARRAY_NORMAL]=original_normals;arrays[Mesh.ARRAY_TEX_UV]=original_uv;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(original.triangles)
        var vertices:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
        var colors=PackedColorArray();colors.resize(vertices.size())
        assert(vertices.size()==2+255*17)
        colors[0]=Color(0.,0.,0.,1.);colors[vertices.size()-1]=Color(0.,0.,0.,1.)
        var minimum_width=1.;var maximum_width=0.
        for i in 255:
            var start=1+i*17
            var distances=[];distances.resize(17);distances[16]=0.
            for j in range(15,-1,-1):distances[j]=distances[j+1]+vertices[start+j].distance_to(vertices[start+j+1])
            var width:float=distances[0]
            minimum_width=minf(minimum_width,width);maximum_width=maxf(maximum_width,width)
            var taper=smoothstep(0.,cfg.width_native*4.,width)
            for j in 17:colors[start+j]=Color(clampf(distances[j]/(cfg.width_native*4.),0.,1.),taper,0.,1.)
        arrays[Mesh.ARRAY_COLOR]=colors
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        var actual=next.surface_get_arrays(si)
        for attribute in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_INDEX]:
            assert(actual[attribute]==before[attribute],"Adding edge coordinates changed actual source mesh attributes")
        next.surface_set_material(si,ink)
        receipts.append({"surface":si,"vertices":vertices.size(),"outer_edge_vertex_count":255,"stroke_width_native":cfg.width_native,"cross_row_width_min_max":[minimum_width,maximum_width],"positions_normals_uv_indices_unchanged":true})
    lip_node.mesh=next
    for si in next.get_surface_count():lip_node.set_surface_override_material(si,ink)
    for row in materials:
        if row[0]==lip_node:row[2]=ink
    var file=FileAccess.open(out.path_join("lip-edge.validation.json"),FileAccess.WRITE)
    file.store_string(JSON.stringify({"schema_version":1,"ok":true,"command":"fish.lip-edge133","stage":"validate","status":"done","next_action":"human_review","inputs":{"plan_sha256":FileAccess.get_sha256(plan.edge133_plan),"shader_sha256":FileAccess.get_sha256(ink.shader.resource_path),"lip_band_sha256":trial.candidate_sha256},"outputs":[],"summary":{"surfaces":receipts,"edge":"Outer boundary of each actual upper/lower lip strip; inner edge retains its existing mouth/slit contrast.","production_installed":false},"failures":[]},"  "));file.close()

func shade(mode:String):
    super.shade("texture" if mode=="edge_probe" else mode)
    if not is_instance_valid(lip_node):return
    for si in lip_node.mesh.get_surface_count():
        var mat=lip_node.get_active_material(si)
        if mat is ShaderMaterial and mat.shader.code.contains("uniform float edge_probe"):
            mat.set_shader_parameter("edge_probe",1. if mode=="edge_probe" else 0.)

func capture_variant(name:String):
    if name=="original":
        var saved_body=plan.textured_body_mesh
        var saved_hash=plan.textured_body_mesh_sha256
        var saved_lips=plan.lip_band_mesh
        var saved_lips_hash=trial.candidate_sha256
        plan.textured_body_mesh=plan.baseline_body
        plan.textured_body_mesh_sha256=plan.baseline_body_sha256
        plan.lip_band_mesh=plan.baseline_lips
        trial.candidate_sha256=plan.baseline_lips_sha256
        transfer_body_materials()
        add_lip_band()
        plan.textured_body_mesh=saved_body
        plan.textured_body_mesh_sha256=saved_hash
        plan.lip_band_mesh=saved_lips
        trial.candidate_sha256=saved_lips_hash
    var folder=out.path_join("baseline132" if name=="original" else "candidate133")
    DirAccess.make_dir_recursive_absolute(folder)
    hall.viewport.size=Vector2i(1200,800)
    for close in [false,true]:
        for view in ["side","front","top","oblique"]:
            camera(view,close)
            for mode in (["clay","texture","albedo","edge_probe"] if name=="candidate" else ["clay","texture","albedo"]):
                shade(mode)
                await shot(folder.path_join(("mouth-" if close else "head-")+view+"-"+mode+".png"))
    whole_camera();shade("texture");await shot(folder.path_join("whole-oblique-texture.png"))
    hall.viewport.size=Vector2i(1986,991);source_camera()
    for mode in ["clay","albedo"]:
        shade(mode);await shot(folder.path_join("source-canvas-"+mode+".png"))
    hall.viewport.size=Vector2i(1200,800)
    # Restore real lit materials before the next variant transfers them.
    shade("texture")
    records.append({"variant":"baseline132" if name=="original" else "candidate133","modes":["clay","texture","albedo"],"views":8,"native_source_canvas":[1986,991],"same_camera_and_scale":true})

func run():
    DirAccess.make_dir_recursive_absolute(out)
    root.size=Vector2i(1200,800)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(hall)
    hall.set_process(false)
    hall.paused=true
    hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
    hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800)
    hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    hall._select_display("black_seabream")
    e=hall._selected()
    for tank in hall.tanks:tank.root.visible=tank.species=="black_seabream"
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    e.controller.set_motion_controls({"body_amplitude":0.,"body_frequency":1.,"fin_amplitude":0.,"fin_frequency":1.},true)
    e.controller.set_action("Swim",true)
    e.controller.step(0.);e.controller.seek(0.)
    e.player.stop()
    e.skeleton.reset_bone_poses()
    if plan.get("neutral_studio",false):
        for mesh in hall.world.find_children("*","MeshInstance3D",true,false):
            if not e.model.is_ancestor_of(mesh):mesh.hide()
        for light in hall.world.find_children("*","Light3D",true,false):light.hide()
        for environment in hall.world.find_children("*","WorldEnvironment",true,false):
            environment.environment.ambient_light_color=Color.WHITE
            environment.environment.ambient_light_energy=.28
            environment.environment.background_color=Color("24333c")
        var tr:Transform3D=e.model.global_transform
        for spec in [[Vector3(1.,.55,.8),.9],[Vector3(.1,.25,-1.),.3]]:
            var light=DirectionalLight3D.new()
            hall.world.add_child(light)
            light.global_position=tr*spec[0]
            light.look_at(tr*Vector3(.44,-.01,0.),tr.basis.orthonormalized()*Vector3.UP)
            light.light_energy=spec[1]
            light.light_color=Color.WHITE
    for mesh in e.model.find_children("*","MeshInstance3D",true,false):
        mesh.lod_bias=1000.
        for si in mesh.mesh.get_surface_count():materials.append([mesh,si,mesh.get_active_material(si)])
    assert(FileAccess.get_sha256("res://assets/models/fish/black_seabream.glb")==trial.source_sha256)
    await capture_variant("original")
    var material_dump=transfer_body_materials()
    add_lip_band()
    await capture_variant("candidate")
    assert(FileAccess.get_sha256("res://assets/models/fish/black_seabream.glb")==trial.source_sha256)
    var report={"schema_version":1,"ok":true,"command":"fish.lip-edge-preview133","stage":"validate","status":"done","next_action":"human_review","inputs":{"plan_sha256":FileAccess.get_sha256(plan_path),"renderer_sha256":FileAccess.get_sha256(get_script().resource_path),"base_renderer129_sha256":FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("preview_lip_band129.gd")),"original_model_sha256":trial.source_sha256,"textured_body_sha256":FileAccess.get_sha256(plan.textured_body_mesh),"lip_band_sha256":trial.candidate_sha256,"lip_atlas_sha256":FileAccess.get_sha256(plan.lip_band_atlas)},"outputs":[],"summary":{"records":records,"source_materials":material_dump,"material_reference_tables":reference_receipts,"production_installed":false,"scope":"Frozen132 nose repair before/after source-color stroke on actual upper/lower lip-band outer boundaries. Geometry/atlas/inner slit retained. Static review only; no production installation or full fish delivery claim."},"failures":[]}
    var file=FileAccess.open(out.path_join("preview.validation.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    hall.queue_free();await process_frame;quit()
