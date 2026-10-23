extends SceneTree
## Independent single-fish review. Production models/configs are never written.
var hall
var out:String
var trial:Dictionary
var records:Array=[]
var e:Dictionary
var original_mesh:ArrayMesh
var materials:Array=[]
var fixed:Dictionary
var plan:Dictionary
var plan_path:String

func _initialize():
    var args=OS.get_cmdline_user_args()
    out=args[0]
    trial=JSON.parse_string(FileAccess.get_file_as_string(args[1]))
    plan_path=args[2]
    plan=JSON.parse_string(FileAccess.get_file_as_string(plan_path))
    call_deferred("run")

func shot(path:String):
    await process_frame
    RenderingServer.force_draw()
    await process_frame
    RenderingServer.force_draw()
    assert(hall.viewport.get_texture().get_image().save_png(path)==OK)

func shade(mode:String):
    for row in materials:
        var mesh:MeshInstance3D=row[0]
        var si:int=row[1]
        var mat:Material=row[2]
        if mode=="texture":mesh.set_surface_override_material(si,mat);continue
        if mode=="albedo":
            var copy:Material=mat.duplicate()
            if copy is ShaderMaterial:
                var shader=Shader.new()
                var code:String=copy.shader.code
                code=code.replace("render_mode","render_mode unshaded,") if code.contains("render_mode") else code.replace("shader_type spatial;","shader_type spatial;\nrender_mode unshaded;")
                shader.code=code
                copy.shader=shader
            elif copy is StandardMaterial3D:copy.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
            mesh.set_surface_override_material(si,copy)
        else:
            var clay=StandardMaterial3D.new()
            clay.albedo_color=Color(.65,.65,.65)
            clay.roughness=1.
            clay.cull_mode=BaseMaterial3D.CULL_DISABLED
            mesh.set_surface_override_material(si,clay)

func camera(view:String,close:bool):
    var tr:Transform3D=e.model.global_transform
    var scale:float=tr.basis.get_scale().x
    var basis:Basis=tr.basis.orthonormalized()
    var center:Vector3=Vector3(.471,-.031,0.) if close else Vector3(.438,-.012,0.)
    if not close and plan.has("review_head_center"):
        var c=plan.review_head_center
        center=Vector3(c[0],c[1],c[2])
    var offsets={"side":Vector3(0.,0.,1.),"front":Vector3(1.,0.,0.),"top":Vector3(0.,1.,.0001),"oblique":Vector3(.7,.20,.7)}
    var target:Vector3=tr*center
    hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    hall.camera.size=(.075 if close else .18)*scale
    if not close and plan.has("review_head_size"):hall.camera.size=plan.review_head_size*scale
    hall.camera.near=.00001
    hall.camera.global_position=target+basis*offsets[view]*scale
    hall.camera.look_at(target,basis*Vector3.UP if view!="top" else basis*Vector3(0.,0.,-1.))

func source_camera():
    var tr:Transform3D=e.model.global_transform
    var scale:float=tr.basis.get_scale().x
    var basis:Basis=tr.basis.orthonormalized()
    var target:Vector3=tr*Vector3.ZERO
    hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    hall.camera.size=991./1986.*scale
    hall.camera.near=.00001
    hall.camera.global_position=target+basis*Vector3(0.,0.,2.)*scale
    hall.camera.look_at(target,basis*Vector3.UP)

func deform():
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    original_mesh=body.mesh
    var next=ArrayMesh.new()
    if plan.has("gray_topology_mesh"):
        if plan.has("gray_topology_mesh_hashes"):
            assert(FileAccess.get_sha256(plan.gray_topology_mesh)==plan.gray_topology_mesh_hashes[plan.gray_topology_mesh],"Static gray mesh changed after plan freeze")
        var data=JSON.parse_string(FileAccess.get_file_as_string(plan.gray_topology_mesh))
        var vertices=PackedVector3Array()
        var normals=PackedVector3Array()
        for p in data.vertices:vertices.append(Vector3(p[0],p[1],p[2]))
        for n in data.normals:normals.append(Vector3(n[0],n[1],n[2]))
        var arrays=[]
        arrays.resize(Mesh.ARRAY_MAX)
        arrays[Mesh.ARRAY_VERTEX]=vertices
        arrays[Mesh.ARRAY_NORMAL]=normals
        arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(data.triangles)
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        body.mesh=next
        body.skin=null
        var keep=[]
        for row in materials:
            if row[0]!=body:keep.append(row)
        keep.append([body,0,StandardMaterial3D.new()])
        materials=keep
        return [vertices.size()]
    var counts:Array=[]
    for si in original_mesh.get_surface_count():
        var arrays:Array=original_mesh.surface_get_arrays(si)
        var vertices:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
        var normals:PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
        var rows:Dictionary=trial.surfaces[si]
        var matches:Dictionary={}
        for i in vertices.size():
            var p=vertices[i]
            var key="%d,%d,%d"%[roundi(p.x*1e7),roundi(p.y*1e7),roundi(p.z*1e7)]
            if rows.has(key):
                var r:Dictionary=rows[key]
                vertices[i]=Vector3(r.position[0],r.position[1],r.position[2])
                normals[i]=Vector3(r.normal[0],r.normal[1],r.normal[2])
                matches[key]=true
        assert(matches.size()==rows.size(),"Preview map missed imported vertices")
        arrays[Mesh.ARRAY_VERTEX]=vertices
        arrays[Mesh.ARRAY_NORMAL]=normals
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        next.surface_set_material(si,original_mesh.surface_get_material(si))
        counts.append(matches.size())
    body.mesh=next
    for row in materials:
        if row[0]==body:body.set_surface_override_material(row[1],row[2])
    var skin=body.get_active_material(0) as ShaderMaterial
    assert(skin!=null)
    preload("res://scripts/aquarium/RestSurface114.gd").new().bind(e.model,body,0,skin)
    return counts

func capture_variant(name:String):
    var folder=out.path_join(name)
    DirAccess.make_dir_recursive_absolute(folder)
    hall.viewport.size=Vector2i(1200,800)
    for close in [false,true]:
        for view in ["side","front","top","oblique"]:
            camera(view,close)
            for mode in ["clay","texture","albedo"]:
                if name!="baseline" and plan.has("gray_topology_mesh") and mode!="clay":continue
                shade(mode)
                var path=folder.path_join(("mouth-" if close else "head-")+view+"-"+mode+".png")
                await shot(path)
    hall.viewport.size=Vector2i(1986,991)
    source_camera()
    if name=="baseline" or not plan.has("gray_topology_mesh"):
        shade("albedo")
        await shot(folder.path_join("source-canvas-albedo.png"))
    shade("clay")
    await shot(folder.path_join("source-canvas-clay.png"))
    shade("texture")
    hall.viewport.size=Vector2i(1200,800)
    records.append({"variant":name,"source_canvas":[1986,991],"projection":"orthographic; native rest XYZ, fixed source canvas, no local registration","views":8,"modes":["clay","texture","albedo"]})

func supplement():
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    var old=body.get_active_material(0) as ShaderMaterial
    var skin=old.duplicate() as ShaderMaterial
    var code:String=old.shader.code
    var inc=FileAccess.get_file_as_string(get_script().resource_path.get_base_dir().path_join("lip_surface126.gdshaderinc"))
    code=code.replace("void vertex()",inc+"\nvoid vertex()")
    var parser=load("res://scripts/aquarium/FishEyeOwnership.gd").new()
    var fragment:Dictionary=parser._stage_braces(code,"fragment")
    code=code.insert(fragment.close,"\nALBEDO=mouth126_color(ALBEDO);\nif(rest114_error>.001){ALBEDO=vec3(1.,0.,1.);}\n")
    var shader=Shader.new();shader.code=code;skin.shader=shader
    var image=Image.load_from_file(plan.source_image)
    assert(image!=null)
    skin.set_shader_parameter("mouth126_source",ImageTexture.create_from_image(image))
    var side=Image.load_from_file(plan.side_restore.image)
    assert(side!=null and side.get_size()==image.get_size())
    assert(FileAccess.get_sha256(plan.side_restore.image)==plan.side_restore.sha256)
    skin.set_shader_parameter("mouth126_side_skin",ImageTexture.create_from_image(side))
    skin.set_shader_parameter("mouth126_size",Vector2(image.get_size()))
    var spec:Dictionary=plan.supplementary_skin
    for name in ["head","upper","lower"]:
        var rect:Array=spec.donor_rects[name]
        skin.set_shader_parameter("mouth126_"+name+"_rect",Vector4(rect[0],rect[1],rect[2],rect[3]))
    skin.set_shader_parameter("mouth126_region",Vector4(spec.start_x,spec.full_x,plan.geometry.radius_z,plan.geometry.upper_radius_y))
    skin.set_shader_parameter("mouth126_front_lips",Vector2(plan.geometry.upper_center_y,plan.geometry.lower_center_y))
    for key in ["mouth_source_projection","rim_local_source"]:skin.set_shader_parameter(key,false)
    body.set_surface_override_material(0,skin)
    for row in materials:
        if row[0]==body and row[1]==0:row[2]=skin
    var file=FileAccess.open(out.path_join("candidate-skin.gdshader"),FileAccess.WRITE)
    file.store_string(code);file.close()

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
    await capture_variant("baseline")
    if plan.has("previous_gray_topology_mesh"):
        var current=plan.gray_topology_mesh
        plan.gray_topology_mesh=plan.previous_gray_topology_mesh
        deform()
        await capture_variant("previous")
        plan.gray_topology_mesh=current
    var counts=deform()
    await capture_variant("geometry")
    if not plan.get("gray_only",false):
        supplement()
        await capture_variant("candidate")
    var file=FileAccess.open(out.path_join("preview.validation.json"),FileAccess.WRITE)
    assert(FileAccess.get_sha256("res://assets/models/fish/black_seabream.glb")==trial.source_sha256)
    file.store_string(JSON.stringify({"ok":true,"status":"done","next_action":"human_review","gray_geometry_first":plan.get("gray_only",false),"source_model_sha256":trial.source_sha256,"candidate_model_sha256":trial.candidate_sha256,"plan_sha256":FileAccess.get_sha256(plan_path),"renderer_sha256":FileAccess.get_sha256(get_script().resource_path),"supplement_template_sha256":FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("lip_surface126.gdshaderinc")),"side_source_sha256":FileAccess.get_sha256(plan.side_restore.image),"matched_deformation_keys":counts,"records":records,"scope":"Actual current game baseline plus independent candidate geometry in memory; optional source restoration only when gray_only=false. Experimental base mesh, no candidate LOD or fin/body acceptance; production GLB hash checked before/after; no production model/config write."},"  "))
    file.close()
    hall.queue_free()
    await process_frame
    quit()
