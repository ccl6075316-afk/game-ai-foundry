extends "preview_lip_uv135.gd"
## Restore skin binding on frozen135 geometry. Isolated candidate, no install.
var original_skin:Skin
var original_skeleton:NodePath
var joint_names:Array=[]
var binding_records:Array=[]

func _initialize():
    super._initialize()
    var receipt=JSON.parse_string(FileAccess.get_file_as_string(plan.skinning_report))
    assert(receipt.ok and receipt.summary.species=="black_seabream")
    joint_names=receipt.summary.skin_joint_names

func bind_mesh(mesh:MeshInstance3D,data:Dictionary):
    var skeleton=e.skeleton as Skeleton3D
    var mapping:Array=[]
    for source_name in joint_names:
        var found=-1
        for i in original_skin.get_bind_count():
            var actual=String(original_skin.get_bind_name(i))
            if actual.is_empty():actual=skeleton.get_bone_name(original_skin.get_bind_bone(i))
            if actual==source_name or actual==source_name+"_2":
                assert(found<0,"Ambiguous skin bind")
                found=i
        assert(found>=0,"Missing skin bind "+source_name)
        mapping.append(found)
    var next=ArrayMesh.new();var saved=[]
    for si in mesh.mesh.get_surface_count():
        var arrays=mesh.mesh.surface_get_arrays(si)
        var part=data.parts[si]
        assert(part.vertices.size()==arrays[Mesh.ARRAY_VERTEX].size())
        var bones=PackedInt32Array();var weights=PackedFloat32Array()
        var normals=PackedVector3Array()
        for n in part.normals:normals.append(Vector3(n[0],n[1],n[2]))
        for i in part.joints.size():
            assert(part.joints[i].size()==4 and part.weights[i].size()==4)
            for k in 4:
                bones.append(mapping[int(part.joints[i][k])]);weights.append(part.weights[i][k])
        arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights
        arrays[Mesh.ARRAY_NORMAL]=normals
        var mat=mesh.get_active_material(si);saved.append(mat)
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
        next.surface_set_material(si,mat)
    mesh.mesh=next
    mesh.skin=original_skin
    mesh.skeleton=mesh.get_path_to(skeleton)
    for si in saved.size():mesh.set_surface_override_material(si,saved[si])
    binding_records.append({"mesh":str(mesh.name),"skin_bind_count":original_skin.get_bind_count(),"source_to_actual_skin_bind":mapping,"skeleton_path":str(mesh.skeleton)})

func transfer_body_materials():
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    if original_skin==null:
        original_skin=body.skin;original_skeleton=body.skeleton
    var result=super.transfer_body_materials()
    var data=JSON.parse_string(FileAccess.get_file_as_string(plan.bound_body))
    bind_mesh(body,data)
    return result

func add_lip_band():
    super.add_lip_band()
    if not records.is_empty():
        var data=JSON.parse_string(FileAccess.get_file_as_string(plan.bound_lips))
        bind_mesh(lip_node,data)

func capture_variant(variant:String):
    var folder=out.path_join(variant)
    DirAccess.make_dir_recursive_absolute(folder)
    hall.viewport.size=Vector2i(1200,800)
    for view in ["side","front","top","oblique"]:
        camera(view,false)
        for mode in ["clay","texture"]:
            shade(mode);await shot(folder.path_join("head-"+view+"-"+mode+".png"))
    shade("texture")
    records.append({"variant":variant})
    if variant!="candidate":return
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
    var portable=load(get_script().resource_path.get_base_dir().path_join("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd"))
    for node in [body,lip_node]:
        for si in node.mesh.get_surface_count():
            node.mesh.surface_set_material(si,portable.freeze(node.get_active_material(si)))
    assert(ResourceSaver.save(body.mesh,out.path_join("candidate-body.res"),ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    assert(ResourceSaver.save(lip_node.mesh,out.path_join("candidate-lips.res"),ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
    var samples=[]
    for action in ["Swim","Turn","Ascend","Dive"]:
        e.controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        assert(e.controller.set_action(action,true))
        e.controller.step(0.)
        for t in [0.,.35,.75,1.25]:
            e.controller.seek(t)
            camera("oblique",false)
            var file=folder.path_join("motion-%s-%.2f.png"%[action,t])
            await shot(file)
            samples.append({"action":action,"time":t,"file":file,"sha256":FileAccess.get_sha256(file),"snapshot":e.controller.snapshot()})
    var coverage=await body_coverage(body)
    var report={"schema_version":1,"ok":true,"command":"fish.preview-bound-mouth","status":"done","next_action":"human_review","inputs":{"plan_sha256":FileAccess.get_sha256(plan_path),"body_sha256":FileAccess.get_sha256(plan.bound_body),"lips_sha256":FileAccess.get_sha256(plan.bound_lips)},"outputs":[],"summary":{"binding":binding_records,"samples":samples,"production_installed":false,"full_fish_accepted":false,"scope":"Actual Godot candidate binding plus16 four-action screenshots. Complete fin/body/LOD validation remains required."},"failures":[]}
    var file=FileAccess.open(out.path_join("binding-preview.validation.json"),FileAccess.WRITE)
    report.summary["candidate_body_coverage"]=coverage
    file.store_string(JSON.stringify(report,"  "));file.close()

func body_coverage(body:MeshInstance3D)->Array:
    var viewport_size=hall.viewport.size;var transparent=hall.viewport.transparent_bg
    var environments=[]
    var visible=[]
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):
        visible.append([mesh,mesh.visible]);mesh.visible=mesh==body
    var actual=[]
    for si in body.mesh.get_surface_count():
        var mat=body.get_active_material(si)
        if mat is ShaderMaterial:
            var tokens=RegEx.new();tokens.compile("(?s)//[^\\n]*|/\\*.*?\\*/|[A-Za-z_][A-Za-z_0-9]*")
            for match in tokens.search_all(mat.shader.code):
                var token=match.get_string()
                if token.begins_with("//") or token.begins_with("/*"):continue
                assert(token!="ALPHA" and not token.begins_with("ALPHA_") and token!="discard","Coverage-changing candidate body shader")
        else:assert(mat is StandardMaterial3D and mat.transparency==BaseMaterial3D.TRANSPARENCY_DISABLED,"Transparent actual body material")
        actual.append(mat)
    for environment in hall.world.find_children("*","WorldEnvironment",true,false):
        environments.append([environment.environment,environment.environment.background_mode])
        environment.environment.background_mode=Environment.BG_CLEAR_COLOR
    hall.viewport.transparent_bg=true;hall.viewport.size=Vector2i(800,600)
    var reference=StandardMaterial3D.new();reference.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    reference.cull_mode=BaseMaterial3D.CULL_DISABLED;reference.albedo_color=Color.WHITE
    var views=[[0.,0.],[PI,0.],[PI/2.,0.],[-PI/2.,0.],[.5,.85],[.5,-.85],[PI+.5,.65],[PI+.5,-.65]]
    var result=[]
    DirAccess.make_dir_recursive_absolute(out.path_join("coverage"))
    for pose in 2:
        e.controller.set_motion_controls({"body_amplitude":0. if pose==0 else 2.5,"fin_amplitude":0. if pose==0 else 2.5},true)
        e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(1.17)
        await process_frame;RenderingServer.force_draw();await process_frame
        for index in views.size():
            var tr:Transform3D=e.carrier.global_transform
            var yaw:float=views[index][0];var pitch:float=views[index][1]
            hall.camera.global_position=tr.origin+tr.basis.orthonormalized()*Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*e.length_m*1.4
            hall.camera.look_at(tr.origin,tr.basis.orthonormalized()*Vector3.UP)
            var stem=out.path_join("coverage/p%d-v%d"%[pose,index])
            for si in actual.size():body.set_surface_override_material(si,actual[si])
            await shot(stem+"-actual.png")
            for si in actual.size():body.set_surface_override_material(si,reference)
            await shot(stem+"-closed.png")
            var a=Image.load_from_file(stem+"-actual.png");var b=Image.load_from_file(stem+"-closed.png")
            var missing=0;var covered=0
            for y in b.get_height():
                for x in b.get_width():
                    if b.get_pixel(x,y).a>.5:
                        covered+=1
                        if a.get_pixel(x,y).a<.5:missing+=1
            assert(covered>30 and missing==0,"Candidate body coverage failed")
            result.append({"pose":pose,"view":index,"missing_pixels":missing,"covered_pixels":covered,"actual_sha256":FileAccess.get_sha256(stem+"-actual.png"),"reference_sha256":FileAccess.get_sha256(stem+"-closed.png")})
    for si in actual.size():body.set_surface_override_material(si,actual[si])
    for row in visible:row[0].visible=row[1]
    for row in environments:row[0].background_mode=row[1]
    hall.viewport.transparent_bg=transparent;hall.viewport.size=viewport_size
    return result
