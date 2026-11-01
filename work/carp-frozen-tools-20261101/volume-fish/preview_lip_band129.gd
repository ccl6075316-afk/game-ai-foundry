extends "preview_lip_surface126.gd"
## Focused static lip trial; base body stays gray in all color review views.
var lip_node:MeshInstance3D
var lip_material:StandardMaterial3D

func camera(view:String,close:bool):
    super.camera(view,close)
    var scale=e.model.global_transform.basis.get_scale().x
    hall.camera.near=.05*scale
    hall.camera.far=5.*scale

func source_camera():
    super.source_camera()
    var scale=e.model.global_transform.basis.get_scale().x
    hall.camera.near=.05*scale
    hall.camera.far=5.*scale

func shade(mode:String):
    for row in materials:
        var mesh:MeshInstance3D=row[0]
        var si:int=row[1]
        if mesh==lip_node and mode!="clay":
            var mat=lip_material.duplicate()
            if mode=="albedo":mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
            mesh.set_surface_override_material(si,mat)
        else:
            var clay=StandardMaterial3D.new()
            clay.albedo_color=Color(.65,.65,.65)
            clay.roughness=1.
            clay.cull_mode=BaseMaterial3D.CULL_DISABLED
            mesh.set_surface_override_material(si,clay)

func add_lip_band():
    assert(FileAccess.get_sha256(plan.lip_band_mesh)==trial.candidate_sha256)
    assert(FileAccess.get_sha256(plan.lip_band_atlas)==plan.lip_band_atlas_sha256)
    var data=JSON.parse_string(FileAccess.get_file_as_string(plan.lip_band_mesh))
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    lip_node=MeshInstance3D.new()
    lip_node.name="Source_lip_band_trial129"
    body.add_child(lip_node)
    lip_node.mesh=ArrayMesh.new()
    lip_material=StandardMaterial3D.new()
    lip_material.albedo_texture=ImageTexture.create_from_image(Image.load_from_file(plan.lip_band_atlas))
    lip_material.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
    lip_material.roughness=1.
    lip_material.cull_mode=BaseMaterial3D.CULL_DISABLED
    for part in data.parts:
        var vertices=PackedVector3Array()
        var normals=PackedVector3Array()
        var uv=PackedVector2Array()
        for p in part.vertices:vertices.append(Vector3(p[0],p[1],p[2]))
        for n in part.normals:normals.append(Vector3(n[0],n[1],n[2]))
        for p in part.uv:uv.append(Vector2(p[0],p[1]))
        var arrays=[]
        arrays.resize(Mesh.ARRAY_MAX)
        arrays[Mesh.ARRAY_VERTEX]=vertices
        arrays[Mesh.ARRAY_NORMAL]=normals
        arrays[Mesh.ARRAY_TEX_UV]=uv
        arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
        var si=lip_node.mesh.get_surface_count()
        lip_node.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        lip_node.mesh.surface_set_material(si,lip_material)
        materials.append([lip_node,si,lip_material])

func capture_variant(name:String):
    var folder=out.path_join(name)
    DirAccess.make_dir_recursive_absolute(folder)
    hall.viewport.size=Vector2i(1200,800)
    var modes=["clay"] if name=="base" else ["clay","lip_color","albedo"]
    for close in [false,true]:
        for view in ["side","front","top","oblique"]:
            camera(view,close)
            for mode in modes:
                shade(mode)
                await shot(folder.path_join(("mouth-" if close else "head-")+view+"-"+mode+".png"))
    hall.viewport.size=Vector2i(1986,991)
    source_camera()
    for mode in modes:
        shade(mode)
        await shot(folder.path_join("source-canvas-"+mode+".png"))
    hall.viewport.size=Vector2i(1200,800)
    if name=="candidate":
        var tr:Transform3D=e.model.global_transform
        var basis:Basis=tr.basis.orthonormalized()
        var target=tr*Vector3(.471,-.031,0.)
        camera("oblique",true)
        hall.camera.global_position=target+basis*Vector3(.7,.2,-.7)*tr.basis.get_scale().x
        hall.camera.look_at(target,basis*Vector3.UP)
        for mode in modes:
            shade(mode)
            await shot(folder.path_join("mouth-oblique-left-"+mode+".png"))
    records.append({"variant":name,"source_canvas":[1986,991],"views":8,"modes":modes,"body":"Frozen128 gray in every mode; only lip band shows source color"})

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
    deform()
    await capture_variant("base")
    add_lip_band()
    await capture_variant("candidate")
    assert(FileAccess.get_sha256("res://assets/models/fish/black_seabream.glb")==trial.source_sha256)
    var report={"schema_version":1,"ok":true,"command":"fish.preview-lip-band129","stage":"validate","status":"done","next_action":"human_review","inputs":{"plan_sha256":FileAccess.get_sha256(plan_path),"renderer_sha256":FileAccess.get_sha256(get_script().resource_path),"base_renderer_sha256":FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("preview_lip_surface126.gd")),"original_model_sha256":trial.source_sha256,"gray_body_sha256":FileAccess.get_sha256(plan.gray_topology_mesh),"lip_band_sha256":trial.candidate_sha256,"atlas_sha256":FileAccess.get_sha256(plan.lip_band_atlas)},"outputs":[],"summary":{"records":records,"production_installed":false,"scope":"Static lip-band geometry and native-source atlas preview only; full body stays gray. Original production GLB/config unchanged. No UV/rig transfer or complete fin/body/motion/LOD acceptance."},"failures":[]}
    var file=FileAccess.open(out.path_join("preview.validation.json"),FileAccess.WRITE)
    file.store_string(JSON.stringify(report,"  "));file.close()
    hall.queue_free()
    await process_frame
    quit()
