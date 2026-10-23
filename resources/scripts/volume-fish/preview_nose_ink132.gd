extends "preview_full_material130.gd"
## Isolated nose outline correction; geometry is frozen131.

func transfer_body_materials():
    if is_instance_valid(lip_node):
        var keep=[]
        for row in materials:
            if row[0]!=lip_node:keep.append(row)
        materials=keep
        lip_node.get_parent().remove_child(lip_node)
        lip_node.queue_free()
    var receipt=super.transfer_body_materials()
    apply_nose_patch(not records.is_empty())
    return receipt

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
    var folder=out.path_join("baseline131" if name=="original" else "candidate132")
    DirAccess.make_dir_recursive_absolute(folder)
    hall.viewport.size=Vector2i(1200,800)
    for close in [false,true]:
        for view in ["side","front","top","oblique"]:
            camera(view,close)
            for mode in (["clay","texture","albedo","ink_probe"] if name=="candidate" else ["clay","texture","albedo"]):
                shade(mode)
                await shot(folder.path_join(("mouth-" if close else "head-")+view+"-"+mode+".png"))
    whole_camera();shade("texture");await shot(folder.path_join("whole-oblique-texture.png"))
    hall.viewport.size=Vector2i(1986,991);source_camera()
    for mode in ["clay","albedo"]:
        shade(mode);await shot(folder.path_join("source-canvas-"+mode+".png"))
    hall.viewport.size=Vector2i(1200,800)
    # Restore real lit materials before the next variant transfers them.
    shade("texture")
    records.append({"variant":"baseline131" if name=="original" else "candidate132","modes":["clay","texture","albedo"],"views":8,"native_source_canvas":[1986,991],"same_camera_and_scale":true})

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
    var report={"schema_version":1,"ok":true,"command":"fish.nose-ink-preview132","stage":"validate","status":"done","next_action":"human_review","inputs":{"plan_sha256":FileAccess.get_sha256(plan_path),"renderer_sha256":FileAccess.get_sha256(get_script().resource_path),"base_renderer129_sha256":FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("preview_lip_band129.gd")),"original_model_sha256":trial.source_sha256,"textured_body_sha256":FileAccess.get_sha256(plan.textured_body_mesh),"lip_band_sha256":trial.candidate_sha256,"lip_atlas_sha256":FileAccess.get_sha256(plan.lip_band_atlas)},"outputs":[],"summary":{"records":records,"source_materials":material_dump,"material_reference_tables":reference_receipts,"production_installed":false,"scope":"Frozen131 before/after local upper nose source-ink replacement. Geometry and lip/slit materials unchanged. Central source outline only; static review, no production installation or fish delivery claim."},"failures":[]}
    var file=FileAccess.open(out.path_join("preview.validation.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    hall.queue_free();await process_frame;quit()

func apply_nose_patch(enabled:bool):
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(plan.ink132_plan))
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    var mat=body.get_active_material(0) as ShaderMaterial
    var code:String=mat.shader.code
    assert(code.count("void vertex(){")==1)
    var declarations="""
uniform sampler2D ink132_skin:source_color,filter_nearest,repeat_disable;
uniform sampler2D ink132_mask:filter_nearest,repeat_disable;
uniform float ink132_probe=0.;
uniform bool ink132_enabled=false;
uniform vec2 ink132_x;
uniform vec2 ink132_z;
uniform vec4 ink132_y;
uniform vec4 ink132_donor_domain;
varying vec3 ink132_position;
vec3 ink132_color(vec3 base,vec2 source_uv,vec3 modulation){
    if(!ink132_enabled)return base;
    vec3 p=ink132_position;
    float owner=smoothstep(ink132_x.x,ink132_x.y,p.x);
    owner*=1.-smoothstep(ink132_z.x,ink132_z.y,abs(p.z));
    owner*=smoothstep(ink132_y.x,ink132_y.y,p.y)*(1.-smoothstep(ink132_y.z,ink132_y.w,p.y));
    vec2 uv=friendly_eye_uv(source_uv);
    vec2 donor_uv=vec2((p.z-ink132_donor_domain.x)/(ink132_donor_domain.y-ink132_donor_domain.x),(ink132_donor_domain.w-p.y)/(ink132_donor_domain.w-ink132_donor_domain.z));
    vec3 skin=texture(ink132_skin,clamp(donor_uv,vec2(0.),vec2(1.))).rgb*modulation;
    return mix(base,ink132_probe>.5?vec3(1.,0.,0.):skin,owner);
}
"""
    if not code.contains("vec3 ink132_color("):
        code=code.replace("void vertex(){",declarations+"\nvoid vertex(){ink132_position=VERTEX;")
        code=code.replace("ALBEDO=lip115_color(color.rgb,chart112_color(color.rgb));","ALBEDO=ink132_color(lip115_color(color.rgb,chart112_color(color.rgb)),UV,tint.rgb*COLOR.rgb);")
        var shader=Shader.new();shader.code=code;mat.shader=shader
    mat.set_shader_parameter("ink132_skin",ImageTexture.create_from_image(Image.load_from_file(cfg.donor_patch)))
    mat.set_shader_parameter("ink132_mask",ImageTexture.create_from_image(Image.load_from_file(cfg.mask)))
    var support=cfg.nose_support
    mat.set_shader_parameter("ink132_x",Vector2(support.start_x,support.full_x))
    mat.set_shader_parameter("ink132_z",Vector2(support.full_abs_z,support.zero_abs_z))
    mat.set_shader_parameter("ink132_y",Vector4(support.lower_y,support.full_lower_y,support.full_upper_y,support.upper_y))
    var domain=cfg.donor_mapping
    mat.set_shader_parameter("ink132_donor_domain",Vector4(domain.z_min,domain.z_max,domain.y_min,domain.y_max))
    mat.set_shader_parameter("ink132_probe",0.)
    mat.set_shader_parameter("ink132_enabled",enabled)
    body.set_surface_override_material(0,mat)
    for row in materials:
        if row[0]==body and row[1]==0:row[2]=mat
    var file=FileAccess.open(out.path_join("nose132.gdshader"),FileAccess.WRITE);file.store_string(code);file.close()

func shade(mode:String):
    super.shade("texture" if mode=="ink_probe" else mode)
    for row in materials:
        var mat=row[0].get_active_material(row[1])
        if mat is ShaderMaterial and mat.shader.code.contains("ink132_color"):
            mat.set_shader_parameter("ink132_probe",1. if mode=="ink_probe" else 0.)
