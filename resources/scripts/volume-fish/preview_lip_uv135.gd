extends "preview_lip_pixels134.gd"
## Join full source pixel cells to actual body UV; share charts across skin/lip.

func add_lip_band():
    if records.is_empty():
        records.append({"temporary_baseline134":true})
        super.add_lip_band()
        records.pop_back()
        return
    super.add_lip_band()
    var cfg=JSON.parse_string(FileAccess.get_file_as_string(plan.uv135_plan))
    var data=JSON.parse_string(FileAccess.get_file_as_string(cfg.aligned_lips))
    var next=ArrayMesh.new();var mats=[]
    for si in data.parts.size():
        var part=data.parts[si];var before=lip_node.mesh.surface_get_arrays(si)
        var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
        var v=PackedVector3Array();var n=PackedVector3Array();var uv=PackedVector2Array();var uv2=PackedVector2Array();var colors=PackedColorArray()
        for p in part.vertices:v.append(Vector3(p[0],p[1],p[2]))
        for p in part.normals:n.append(Vector3(p[0],p[1],p[2]))
        for p in part.uv:uv.append(Vector2(p[0],p[1]))
        for p in part.uv2:uv2.append(Vector2(p[0],p[1]))
        for p in part.colors:colors.append(Color(p[0],p[1],p[2],p[3]))
        arrays[Mesh.ARRAY_VERTEX]=v;arrays[Mesh.ARRAY_NORMAL]=n;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_TEX_UV2]=uv2;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        var actual=next.surface_get_arrays(si)
        for attribute in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_INDEX]:assert(actual[attribute]==before[attribute],"UV repair changed actual lip geometry")
        var mat=ShaderMaterial.new();mat.shader=load(get_script().resource_path.get_base_dir().path_join("lip_uv135.gdshader"))
        mat.set_shader_parameter("original_source",ImageTexture.create_from_image(Image.load_from_file(cfg.source_image)))
        mat.set_shader_parameter("original_opaque",ImageTexture.create_from_image(Image.load_from_file(cfg.opaque_skin)))
        mat.set_shader_parameter("continuation",ImageTexture.create_from_image(Image.load_from_file(cfg.continuation_atlases[part.name])))
        next.surface_set_material(si,mat);mats.append(mat)
    lip_node.mesh=next
    for si in next.get_surface_count():lip_node.set_surface_override_material(si,mats[si])
    for row in materials:
        if row[0]==lip_node:row[2]=mats[row[1]]
    apply_skin_chart(cfg)

func apply_skin_chart(cfg:Dictionary):
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    var mat=body.get_active_material(0) as ShaderMaterial
    var records135=JSON.parse_string(FileAccess.get_file_as_string(cfg.skin_records))
    assert(records135.size()==body.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size())
    var width=256;var height=ceili(records135.size()/256.)
    var image=Image.create(width,height,false,Image.FORMAT_RGBAF)
    for i in records135.size():
        var p=records135[i];image.set_pixel(i%width,i/width,Color(p[0],p[1],p[2],p[3]))
    var code:String=mat.shader.code
    var declarations="""
uniform sampler2D uv135_records:filter_nearest,repeat_disable;
uniform sampler2D uv135_skin:source_color,filter_nearest,repeat_disable;
uniform ivec2 uv135_size;
uniform float uv135_probe=0.;
varying vec4 uv135_chart;
vec3 uv135_color(vec3 base){
    vec3 pigment=texture(uv135_skin,uv135_chart.xy).rgb;
    return mix(base,uv135_probe>.5?vec3(0.,0.,1.):pigment,clamp(uv135_chart.z,0.,1.));
}
"""
    assert(not code.contains("uv135_color"))
    code=code.replace("void vertex(){",declarations+"\nvoid vertex(){uv135_chart=texelFetch(uv135_records,ivec2(VERTEX_ID%uv135_size.x,VERTEX_ID/uv135_size.x),0);")
    var marker="ALBEDO=ink132_color(lip115_color(color.rgb,chart112_color(color.rgb)),UV,tint.rgb*COLOR.rgb);"
    assert(code.count(marker)==1)
    code=code.replace(marker,marker+"\nALBEDO=uv135_color(ALBEDO);")
    var shader=Shader.new();shader.code=code;mat.shader=shader
    mat.set_shader_parameter("uv135_records",ImageTexture.create_from_image(image));mat.set_shader_parameter("uv135_size",Vector2i(width,height))
    mat.set_shader_parameter("uv135_skin",ImageTexture.create_from_image(Image.load_from_file(cfg.skin_atlas)))
    mat.set_shader_parameter("uv135_probe",0.)
    body.set_surface_override_material(0,mat)
    for row in materials:
        if row[0]==body and row[1]==0:row[2]=mat
    var file=FileAccess.open(out.path_join("actual-skin135.gdshader"),FileAccess.WRITE);file.store_string(code);file.close()

func shade(mode:String):
    super.shade(mode)
    for row in materials:
        var mat=row[0].get_active_material(row[1])
        if mat is ShaderMaterial and mat.shader.code.contains("uv135_color"):
            mat.set_shader_parameter("uv135_probe",1. if mode=="edge_probe" else 0.)

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
    var folder=out.path_join("baseline134" if name=="original" else "candidate135")
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
    records.append({"variant":"baseline134" if name=="original" else "candidate135","modes":["clay","texture","albedo"],"views":8,"native_source_canvas":[1986,991],"same_camera_and_scale":true})

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
    var report={"schema_version":1,"ok":true,"command":"fish.lip-uv-preview135","stage":"validate","status":"done","next_action":"human_review","inputs":{"plan_sha256":FileAccess.get_sha256(plan_path),"renderer_sha256":FileAccess.get_sha256(get_script().resource_path),"base_renderer129_sha256":FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("preview_lip_band129.gd")),"original_model_sha256":trial.source_sha256,"textured_body_sha256":FileAccess.get_sha256(plan.textured_body_mesh),"lip_band_sha256":trial.candidate_sha256,"lip_atlas_sha256":FileAccess.get_sha256(plan.lip_band_atlas)},"outputs":[],"summary":{"records":records,"source_materials":material_dump,"material_reference_tables":reference_receipts,"production_installed":false,"scope":"Rejected134 dabs compared against full original material cells aligned to actual body UV joins. Shared lip/skin continuation, frozen geometry and132 nose cleanup. Static visual trial only."},"failures":[]}
    var file=FileAccess.open(out.path_join("preview.validation.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    hall.queue_free();await process_frame;quit()
