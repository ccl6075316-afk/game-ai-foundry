extends "preview_lip_band129.gd"
## Full actual runtime material on frozen128 +129 static lip experiment.
var reference_receipts:Array=[]

func shade(mode:String):
    if mode=="clay":
        super.shade(mode)
        return
    for row in materials:
        var mesh:MeshInstance3D=row[0]
        var si:int=row[1]
        var mat:Material=row[2]
        if mode=="texture":
            mesh.set_surface_override_material(si,mat)
        else:
            var copy:Material=mat.duplicate()
            if copy is ShaderMaterial:
                var shader=Shader.new()
                var code:String=copy.shader.code
                code=code.replace("render_mode","render_mode unshaded,") if code.contains("render_mode") else code.replace("shader_type spatial;","shader_type spatial;\nrender_mode unshaded;")
                shader.code=code
                copy.shader=shader
            elif copy is StandardMaterial3D:copy.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
            mesh.set_surface_override_material(si,copy)

func bind_reference(material:ShaderMaterial,part:Dictionary,surface:int):
    var rest_lookup=material.shader.code.contains("rest114_vertex_begin")
    var oral_lookup=material.shader.code.contains("material130_positions")
    if not rest_lookup and not oral_lookup:return
    var width=256
    var count=part.vertices.size()
    var height=ceili(float(count)/width)
    if rest_lookup:
        material.set_shader_parameter("rest114_count",count)
        material.set_shader_parameter("rest114_size",Vector2i(width,height))
    if oral_lookup:
        material.set_shader_parameter("material130_count",count)
        material.set_shader_parameter("material130_size",Vector2i(width,height))
    var eye_lookup=material.shader.code.contains("eye_lookup_vertex")
    if eye_lookup:
        material.set_shader_parameter("eye_vertex_count",count)
        material.set_shader_parameter("eye_lookup_size",Vector2(width,height))
    var keys={"positions":"reference_positions","normals":"reference_normals","uvs":"uv"}
    var hashes={}
    for key in keys:
        if not rest_lookup and key!="positions":continue
        var im=Image.create(width,height,false,Image.FORMAT_RGBAF)
        var values:Array=part[keys[key]]
        for i in count:
            var p:Array=values[i]
            im.set_pixel(i%width,i/width,Color(p[0],p[1],p[2] if key!="uvs" else 0.,1.))
        var texture=ImageTexture.create_from_image(im)
        if rest_lookup:material.set_shader_parameter("rest114_"+key,texture)
        if oral_lookup and key=="positions":material.set_shader_parameter("material130_positions",texture)
        if eye_lookup and key=="positions":material.set_shader_parameter("eye_rest_lookup",texture)
        if eye_lookup and key=="uvs":material.set_shader_parameter("eye_uv_lookup",texture)
        var ctx=HashingContext.new();ctx.start(HashingContext.HASH_SHA256);ctx.update(im.get_data());hashes[key]=ctx.finish().hex_encode()
    reference_receipts.append({"surface":surface,"vertices":count,"size":[width,height],"tables_sha256":hashes,"eye_lookup_rebound":eye_lookup,"oral_reference_rebound":oral_lookup,"semantics":"Transported original material reference positions/normals, plus actual transferred UV guard. These are source-material coordinates, not claimed literal128 geometry rest positions. Static only; no114 runtime validation claim."})

func transfer_body_materials():
    assert(FileAccess.get_sha256(plan.textured_body_mesh)==plan.textured_body_mesh_sha256)
    var data=JSON.parse_string(FileAccess.get_file_as_string(plan.textured_body_mesh))
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    var source_materials=[]
    for si in body.mesh.get_surface_count():source_materials.append(body.get_active_material(si))
    var next=ArrayMesh.new()
    var new_materials=[]
    var material_dump=[]
    for part in data.parts:
        var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
        var vertices=PackedVector3Array();var normals=PackedVector3Array();var uv=PackedVector2Array();var uv2=PackedVector2Array()
        for p in part.vertices:vertices.append(Vector3(p[0],p[1],p[2]))
        for p in part.normals:normals.append(Vector3(p[0],p[1],p[2]))
        for p in part.uv:uv.append(Vector2(p[0],p[1]))
        for p in part.uv2:uv2.append(Vector2(p[0],p[1]))
        arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_TEX_UV2]=uv2;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
        var mat:Material=source_materials[int(part.source_surface)].duplicate()
        if mat is ShaderMaterial:
            var code:String=mat.shader.code
            if code.contains("void vertex(){jaw112_rest=VERTEX;}"):
                assert(code.count("void vertex(){jaw112_rest=VERTEX;}")==1)
                code=code.replace("void vertex(){jaw112_rest=VERTEX;}","uniform sampler2D material130_positions:filter_nearest,repeat_disable;\nuniform ivec2 material130_size;\nuniform int material130_count;\nvoid vertex(){int i=clamp(VERTEX_ID,0,material130_count-1);jaw112_rest=texelFetch(material130_positions,ivec2(i%material130_size.x,i/material130_size.x),0).xyz;}")
                var shader=Shader.new();shader.code=code;mat.shader=shader
            bind_reference(mat,part,next.get_surface_count())
            var file=FileAccess.open(out.path_join("source-body-surface-%d.gdshader"%next.get_surface_count()),FileAccess.WRITE);file.store_string(code);file.close()
            material_dump.append({"surface":next.get_surface_count(),"class":mat.get_class(),"shader_code_unchanged":mat.shader.code==source_materials[int(part.source_surface)].shader.code,"head_blend":mat.get_shader_parameter("head_blend"),"eye_mode":mat.get_shader_parameter("eye_mode"),"oral_fragment_behavior":"Original source color/depth logic retained; vertex reference transported only."})
        else:material_dump.append({"surface":next.get_surface_count(),"class":mat.get_class()})
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        next.surface_set_material(next.get_surface_count()-1,mat)
        new_materials.append(mat)
    body.mesh=next
    body.skin=null
    var keep=[]
    for row in materials:
        if row[0]!=body:keep.append(row)
    for si in new_materials.size():
        body.set_surface_override_material(si,new_materials[si]);keep.append([body,si,new_materials[si]])
    materials=keep
    return material_dump

func whole_camera():
    var tr:Transform3D=e.model.global_transform
    var basis:Basis=tr.basis.orthonormalized()
    var scale:float=tr.basis.get_scale().x
    var target=tr*Vector3.ZERO
    hall.camera.projection=Camera3D.PROJECTION_ORTHOGONAL
    hall.camera.size=.58*scale
    hall.camera.near=.05*scale;hall.camera.far=5.*scale
    hall.camera.global_position=target+basis*Vector3(1.,.15,1.)*scale
    hall.camera.look_at(target,basis*Vector3.UP)

func capture_variant(name:String):
    var folder=out.path_join(name);DirAccess.make_dir_recursive_absolute(folder)
    hall.viewport.size=Vector2i(1200,800)
    var modes=["texture"] if name=="original" else ["texture","albedo"]
    for close in [false,true]:
        for view in ["side","front","top","oblique"]:
            camera(view,close)
            for mode in modes:
                shade(mode);await shot(folder.path_join(("mouth-" if close else "head-")+view+"-"+mode+".png"))
    whole_camera();shade("texture");await shot(folder.path_join("whole-oblique-texture.png"))
    hall.viewport.size=Vector2i(1986,991);source_camera()
    for mode in modes:
        shade(mode);await shot(folder.path_join("source-canvas-"+mode+".png"))
    hall.viewport.size=Vector2i(1200,800)
    records.append({"variant":name,"modes":modes,"views":8,"full_fish_view":true,"native_source_canvas":[1986,991]})

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
    var report={"schema_version":1,"ok":true,"command":"fish.full-material-preview130","stage":"validate","status":"done","next_action":"human_review","inputs":{"plan_sha256":FileAccess.get_sha256(plan_path),"renderer_sha256":FileAccess.get_sha256(get_script().resource_path),"base_renderer129_sha256":FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("preview_lip_band129.gd")),"original_model_sha256":trial.source_sha256,"textured_body_sha256":FileAccess.get_sha256(plan.textured_body_mesh),"lip_band_sha256":trial.candidate_sha256,"lip_atlas_sha256":FileAccess.get_sha256(plan.lip_band_atlas)},"outputs":[],"summary":{"records":records,"source_materials":material_dump,"material_reference_tables":reference_receipts,"production_installed":false,"scope":"Full actual runtime source material transferred onto static128 gray, plus129 lip. Source-reference LUT semantics recorded explicitly; no original114 validation or rig/motion/fin/body/LOD delivery acceptance claim. Original GLB/config unchanged."},"failures":[]}
    var file=FileAccess.open(out.path_join("preview.validation.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    hall.queue_free();await process_frame;quit()
