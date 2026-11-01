extends "preview_full_material130.gd"
## Species-specific skinned candidate with transported original material references.
var source_skin:Skin
var source_names:Array
var capture_rows:Array=[]
var focus:Vector3
var extent:float
var binding_map:Array=[]
func transfer_body_materials():
    var aliases:Dictionary=plan.get("source_material_aliases",{})
    if not aliases.is_empty():
        var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
        for target in aliases:body.set_surface_override_material(int(target),body.get_active_material(int(aliases[target])))
    var result=super.transfer_body_materials()
    var active_body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    var source_parts=JSON.parse_string(FileAccess.get_file_as_string(plan.body)).parts
    for si in active_body.mesh.get_surface_count():
        var material=active_body.get_active_material(si)
        if not material is ShaderMaterial:continue
        var code:String=material.shader.code
        if code.contains("front112_rest=VERTEX;front112_normal=NORMAL;"):
            assert(code.count("// rest114_vertex_end")==1)
            code=code.replace("front112_rest=VERTEX;front112_normal=NORMAL;","")
            code=code.replace("// rest114_vertex_end","// rest114_vertex_end\nfront112_rest=rest114_position;front112_normal=rest114_normal;")
        if code.contains("// rest114_vertex_end"):
            code=code.replace("rest_position=VERTEX;","rest_position=rest114_position;")
        elif code.contains("rest_position=VERTEX;") and (material.get_shader_parameter("head_source_repair")==true or material.get_shader_parameter("head_blend")==true):
            # Oral surfaces can share the source-head shader without a112
            # chart. They still need their own immutable position table.
            assert(code.count("void vertex()")==1)
            var values:Array=source_parts[si].reference_positions
            var width=256;var height=ceili(values.size()/256.)
            var im=Image.create(width,height,false,Image.FORMAT_RGBAF)
            for i in values.size():var v=values[i];im.set_pixel(i%width,i/width,Color(v[0],v[1],v[2],1.))
            code=code.replace("void vertex()","uniform sampler2D material139_positions:filter_nearest,repeat_disable;\nuniform ivec2 material139_size;\nvoid vertex()")
            code=code.replace("rest_position=VERTEX;","rest_position=texelFetch(material139_positions,ivec2(VERTEX_ID%material139_size.x,VERTEX_ID/material139_size.x),0).xyz;")
            material.set_meta("material139_positions",ImageTexture.create_from_image(im));material.set_meta("material139_size",Vector2i(width,height))
        var shader=Shader.new();shader.code=code;material.shader=shader
        if material.has_meta("material139_positions"):
            material.set_shader_parameter("material139_positions",material.get_meta("material139_positions"));material.set_shader_parameter("material139_size",material.get_meta("material139_size"))
    if plan.has("extend_dorsal_chart"):
        var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
        var mat=body.get_active_material(0) as ShaderMaterial
        var old="amount*=1.-smoothstep(chart112_longitudinal.z,chart112_longitudinal.w,u);"
        assert(mat.shader.code.count(old)==1,"Unsupported dorsal chart")
        var limits:Array=plan.extend_dorsal_chart.section_height
        assert(limits.size()==2 and limits[0]>=0. and limits[1]>limits[0] and limits[1]<=1.)
        var shader=Shader.new()
        shader.code=mat.shader.code.replace(old,"amount*=max(1.-smoothstep(chart112_longitudinal.z,chart112_longitudinal.w,u),smoothstep(%s,%s,y));"%[limits[0],limits[1]])
        mat.shader=shader
        if plan.get("retire_eye_chart_guard",false):
            assert(plan.has("source_texture_overrides"),"Eye guard retirement needs a separately cleaned underlying source")
            mat.set_shader_parameter("chart112_eye_rect_native",Vector4.ZERO)
    if plan.has("source_texture_overrides"):
        var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
        for key in plan.source_texture_overrides:
            var cfg:Dictionary=plan.source_texture_overrides[key]
            var mat=body.get_active_material(int(key)) as ShaderMaterial
            for parameter in cfg:
                assert(FileAccess.get_sha256(cfg[parameter].path)==cfg[parameter].sha256)
                mat.set_shader_parameter(parameter,ImageTexture.create_from_image(Image.load_from_file(cfg[parameter].path)))
    return result
func _initialize():
    var args=OS.get_cmdline_user_args();plan_path=args[0];out=args[1]
    plan=JSON.parse_string(FileAccess.get_file_as_string(plan_path))
    assert(FileAccess.get_sha256(plan.body)==plan.body_sha256)
    assert(FileAccess.get_sha256(plan.skinning_report)==plan.skinning_report_sha256)
    var receipt=JSON.parse_string(FileAccess.get_file_as_string(plan.skinning_report))
    assert(receipt.ok and receipt.summary.species==plan.species)
    source_names=receipt.summary.skin_joint_names
    plan.textured_body_mesh=plan.body;plan.textured_body_mesh_sha256=plan.body_sha256
    call_deferred("run")
func install():
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    source_skin=body.skin
    transfer_body_materials()
    var data=JSON.parse_string(FileAccess.get_file_as_string(plan.body))
    var mapping=[]
    for name in source_names:
        var found=-1
        for i in source_skin.get_bind_count():
            var actual=String(source_skin.get_bind_name(i))
            if actual.is_empty():actual=e.skeleton.get_bone_name(source_skin.get_bind_bone(i))
            if actual==name or actual==name+"_2":assert(found<0);found=i
        assert(found>=0,"Missing bind "+name);mapping.append(found)
    binding_map=mapping
    var next=ArrayMesh.new()
    for si in data.parts.size():
        var part=data.parts[si];var arrays=body.mesh.surface_get_arrays(si)
        var bones=PackedInt32Array();var weights=PackedFloat32Array();var normals=PackedVector3Array()
        for n in part.normals:normals.append(Vector3(n[0],n[1],n[2]))
        for i in part.joints.size():
            for k in 4:bones.append(mapping[int(part.joints[i][k])]);weights.append(part.weights[i][k])
        arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights;arrays[Mesh.ARRAY_NORMAL]=normals
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        next.surface_set_material(si,body.get_active_material(si))
    body.mesh=next;body.skin=source_skin;body.skeleton=body.get_path_to(e.skeleton)
    if plan.has("material_continuity"):install_continuity(body,plan.material_continuity)
    for name in plan.get("retired_runtime_auxiliaries",[]):
        assert(plan.species=="peacock_bass" and String(name).begins_with("Eye_relief112_"))
        var node=e.model.find_child(name,true,false);assert(node!=null);node.hide()
    return body
func install_continuity(body:MeshInstance3D,cfg:Dictionary):
    for path in cfg.frozen_inputs:assert(FileAccess.get_sha256(path)==cfg.frozen_inputs[path])
    var data=JSON.parse_string(FileAccess.get_file_as_string(cfg.lips))
    var lip=MeshInstance3D.new();lip.name="Source_lips_136";body.add_child(lip)
    lip.mesh=ArrayMesh.new();lip.skin=source_skin;lip.skeleton=lip.get_path_to(e.skeleton)
    for part in data.parts:
        var arrays=[];arrays.resize(Mesh.ARRAY_MAX)
        var vertices=PackedVector3Array();var normals=PackedVector3Array();var uv=PackedVector2Array();var uv2=PackedVector2Array()
        var bones=PackedInt32Array();var weights=PackedFloat32Array();var colors=PackedColorArray()
        for p in part.vertices:vertices.append(Vector3(p[0],p[1],p[2]))
        for p in part.normals:normals.append(Vector3(p[0],p[1],p[2]))
        for p in part.uv:uv.append(Vector2(p[0],p[1]))
        for p in part.uv2:uv2.append(Vector2(p[0],p[1]))
        for p in part.colors:colors.append(Color(p[0],p[1],p[2],p[3]))
        for i in part.joints.size():
            for k in 4:bones.append(binding_map[int(part.joints[i][k])]);weights.append(part.weights[i][k])
        arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_NORMAL]=normals;arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_TEX_UV2]=uv2
        arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
        var mat=ShaderMaterial.new();mat.shader=load(get_script().resource_path.get_base_dir().path_join("lip_uv135.gdshader"))
        mat.set_shader_parameter("original_source",ImageTexture.create_from_image(Image.load_from_file(cfg.source)))
        mat.set_shader_parameter("original_opaque",ImageTexture.create_from_image(Image.load_from_file(cfg.opaque)))
        mat.set_shader_parameter("continuation",ImageTexture.create_from_image(Image.load_from_file(cfg.atlases[part.name])))
        lip.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);var si=lip.mesh.get_surface_count()-1
        lip.mesh.surface_set_material(si,mat);materials.append([lip,si,mat])
    var table=JSON.parse_string(FileAccess.get_file_as_string(cfg.skin_records))
    var stride:int=cfg.get("record_stride",1)
    assert(table.size()==body.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX].size()*stride)
    var width=256;var height=ceili(table.size()/256.);var im=Image.create(width,height,false,Image.FORMAT_RGBAF)
    for i in table.size():var p=table[i];im.set_pixel(i%width,i/width,Color(p[0],p[1],p[2],p[3]))
    var mat=body.get_active_material(0) as ShaderMaterial;var code:String=mat.shader.code
    var declaration="""
uniform sampler2D mouth136_records:filter_nearest,repeat_disable;
uniform sampler2D mouth136_skin:source_color,filter_nearest,repeat_disable;
uniform ivec2 mouth136_size;
uniform int mouth136_stride=1;
varying vec4 mouth136_chart;
varying vec4 mouth136_nose;
"""
    assert(code.count("void vertex(){")==1)
    code=code.replace("void vertex(){",declaration+"\nvoid vertex(){int mouth_i=VERTEX_ID*mouth136_stride;mouth136_chart=texelFetch(mouth136_records,ivec2(mouth_i%mouth136_size.x,mouth_i/mouth136_size.x),0);mouth136_nose=vec4(0.);if(mouth136_stride==2){mouth_i+=1;mouth136_nose=texelFetch(mouth136_records,ivec2(mouth_i%mouth136_size.x,mouth_i/mouth136_size.x),0);}")
    var begin=code.find("void fragment()");assert(begin>=0)
    var start=code.find("{",begin);var depth=1;var end=start+1
    while depth>0:
        if code[end]=="{":depth+=1
        elif code[end]=="}":depth-=1
        end+=1
    code=code.insert(end-1,"\nALBEDO=mix(ALBEDO,texture(mouth136_skin,mouth136_nose.xy).rgb,clamp(mouth136_nose.z,0.,1.));\nALBEDO=mix(ALBEDO,texture(mouth136_skin,mouth136_chart.xy).rgb,clamp(mouth136_chart.z,0.,1.));\n")
    var shader=Shader.new();shader.code=code;mat.shader=shader
    mat.set_shader_parameter("mouth136_records",ImageTexture.create_from_image(im));mat.set_shader_parameter("mouth136_size",Vector2i(width,height))
    mat.set_shader_parameter("mouth136_stride",stride)
    mat.set_shader_parameter("mouth136_skin",ImageTexture.create_from_image(Image.load_from_file(cfg.atlases.skin)))
    var portable=load(get_script().resource_path.get_base_dir().path_join("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd"))
    for si in lip.mesh.get_surface_count():lip.mesh.surface_set_material(si,portable.freeze(lip.get_active_material(si)))
    assert(ResourceSaver.save(lip.mesh,out.path_join("candidate-lips.res"),ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
func view_camera(view:String,whole:bool=false):
    var tr:Transform3D=e.model.global_transform;var basis=tr.basis.orthonormalized()
    var angles={"side":Vector2.ZERO,"front":Vector2(PI/2.,0.),"top":Vector2(0.,1.56),"oblique":Vector2(.65,.2)}
    var a:Vector2=angles[view];var target:Vector3=tr*(Vector3.ZERO if whole else focus)
    var distance:float=e.length_m*1.45 if whole else extent*tr.basis.get_scale().x*1.9
    hall.camera.near=.0005;hall.camera.projection=Camera3D.PROJECTION_PERSPECTIVE
    hall.camera.global_position=target+basis*Vector3(sin(a.x)*cos(a.y),sin(a.y),cos(a.x)*cos(a.y))*distance
    hall.camera.look_at(target,basis*Vector3.UP)
func run():
    DirAccess.make_dir_recursive_absolute(out)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    hall._select_display(plan.species);e=hall._selected()
    assert(FileAccess.get_sha256("res://assets/models/fish/"+plan.species+".glb")==plan.model_sha256)
    for tank in hall.tanks:tank.root.visible=tank.species==plan.species
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):
        if not e.model.is_ancestor_of(mesh):mesh.hide()
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true)
    e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    var bounds=AABB();var first=true
    for si in body.mesh.get_surface_count():
        for v in body.mesh.surface_get_arrays(si)[Mesh.ARRAY_VERTEX]:
            if v.x<.3:continue
            if first:bounds=AABB(v,Vector3.ZERO);first=false
            else:bounds=bounds.expand(v)
    focus=bounds.get_center();extent=maxf(bounds.size.x,maxf(bounds.size.y,bounds.size.z))
    for variant in ["original","candidate"]:
        materials=[]
        for mesh in e.model.find_children("*","MeshInstance3D",true,false):
            for si in mesh.mesh.get_surface_count():materials.append([mesh,si,mesh.get_active_material(si)])
        if variant=="candidate":body=install()
        var folder=out.path_join(variant);DirAccess.make_dir_recursive_absolute(folder)
        for view in ["side","front","top","oblique"]:
            view_camera(view)
            for mode in ["clay","texture","albedo"]:
                shade(mode);await shot(folder.path_join("head-"+view+"-"+mode+".png"))
        view_camera("oblique",true);shade("texture");await shot(folder.path_join("whole-oblique-texture.png"))
    var portable=load(get_script().resource_path.get_base_dir().path_join("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd"))
    for si in body.mesh.get_surface_count():body.mesh.surface_set_material(si,portable.freeze(body.get_active_material(si)))
    assert(ResourceSaver.save(body.mesh,out.path_join("candidate-body.res"),ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    for action in ["Swim","Turn","Ascend","Dive"]:
        e.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        assert(e.controller.set_action(action,true));e.controller.step(0.)
        for t in [0.,.35,.75,1.25]:
            e.controller.seek(t);view_camera("oblique")
            var file=out.path_join("candidate/motion-%s-%.2f.png"%[action,t]);await shot(file)
            capture_rows.append({"action":action,"time":t,"file":file,"sha256":FileAccess.get_sha256(file),"snapshot":e.controller.snapshot()})
    var f=FileAccess.open(out.path_join("preview.validation.json"),FileAccess.WRITE)
    f.store_string(JSON.stringify({"ok":true,"status":"done","next_action":"human_review","species":plan.species,"plan_sha256":FileAccess.get_sha256(plan_path),"body_sha256":plan.body_sha256,"material_references":reference_receipts,"samples":capture_rows,"production_installed":false,"scope":"Actual original material correspondence and rig binding. Visual review and complete fin/body/LOD gates remain required."},"  "));f.close()
    hall.queue_free();await process_frame;quit()
