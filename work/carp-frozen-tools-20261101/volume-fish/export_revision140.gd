extends "capture_surface_mouth_audit.gd"
## Isolated candidate editor: preserves portable139 materials and the real rig.
var plan:Dictionary
var plan_path:String
func _initialize():
    var args=OS.get_cmdline_user_args();plan_path=args[0];plan=JSON.parse_string(FileAccess.get_file_as_string(plan_path));out=plan.output
    call_deferred("run")
func unlit(material:Material)->Material:
    var copy:Material=material.duplicate()
    if copy is ShaderMaterial:
        var key=material.shader.code.sha256_text()
        if not shaders.has(key):
            var shader=Shader.new();var code:String=material.shader.code
            code=code.replace("render_mode","render_mode unshaded,") if code.contains("render_mode") else code.replace("shader_type spatial;","shader_type spatial;\nrender_mode unshaded;")
            shader.code=code;shaders[key]=shader
        copy.shader=shaders[key]
    elif copy is StandardMaterial3D:copy.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    return copy
func vectors(values:Array)->PackedVector3Array:
    var result=PackedVector3Array()
    for p in values:result.append(Vector3(p[0],p[1],p[2]))
    return result
func image_texture(path:String)->ImageTexture:
    var im=Image.load_from_file(path);assert(im!=null and not im.is_empty());return ImageTexture.create_from_image(im)
func capture(e:Dictionary,r:Dictionary,folder:String):
    DirAccess.make_dir_recursive_absolute(folder);var stored=[]
    for node in e.model.find_children("*","MeshInstance3D",true,false):
        for si in node.mesh.get_surface_count():var mat=node.get_active_material(si);stored.append([node,si,mat,mat])
    for view in {"side":[0.,0.],"front":[PI/2.,0.],"top":[0.,1.56],"bottom":[0.,-1.56],"oblique":[.65,.2]}:
        var a:Dictionary={"side":[0.,0.],"front":[PI/2.,0.],"top":[0.,1.56],"bottom":[0.,-1.56],"oblique":[.65,.2]}
        camera(e,r,true,a[view][0],a[view][1])
        for mode in ["texture","clay","albedo"]:set_mode(e,stored,mode);await shot(folder+"/head-"+view+"-"+mode+".png")
    set_mode(e,stored,"texture")
    for view in {"side":[0.,0.],"oblique":[.65,.2],"bottom":[0.,-1.56],"top":[0.,1.56]}:
        var a:Dictionary={"side":[0.,0.],"oblique":[.65,.2],"bottom":[0.,-1.56],"top":[0.,1.56]};camera(e,r,false,a[view][0],a[view][1]);await shot(folder+"/whole-"+view+".png")
        for name in ownership[e.species].fins:e.model.find_child(name,true,false).hide()
        await shot(folder+"/hidden-fin-"+view+".png")
        for name in ownership[e.species].fins:
            var node=e.model.find_child(name,true,false);node.visible=intrinsic.get(node.get_instance_id(),false)
func edit_body(e:Dictionary,item:Dictionary):
    var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D;var next=ArrayMesh.new()
    var parts:Array=[];var mapping=[]
    if item.has("geometry"):
        var data=JSON.parse_string(FileAccess.get_file_as_string(item.geometry));parts=data.parts
        var receipt=JSON.parse_string(FileAccess.get_file_as_string(item.skinning_report))
        for name in receipt.summary.skin_joint_names:
            var found=-1
            for i in body.skin.get_bind_count():
                var actual=String(body.skin.get_bind_name(i))
                if actual.is_empty():actual=e.skeleton.get_bone_name(body.skin.get_bind_bone(i))
                if actual==name or actual==name+"_2":assert(found<0);found=i
            assert(found>=0);mapping.append(found)
    var portable=load(get_script().resource_path.get_base_dir().path_join("../../runtime/godot/mouth-repair-139/PortableMaterial139.gd"))
    for si in body.mesh.get_surface_count():
        var arrays=body.mesh.surface_get_arrays(si);var material=portable.freeze(body.get_active_material(si))
        if not parts.is_empty():
            var part:Dictionary=parts[si];assert(part.vertices.size()==arrays[Mesh.ARRAY_VERTEX].size())
            arrays[Mesh.ARRAY_VERTEX]=vectors(part.vertices);arrays[Mesh.ARRAY_NORMAL]=vectors(part.normals)
            var bones=PackedInt32Array();var weights=PackedFloat32Array()
            for i in part.joints.size():
                for k in 4:bones.append(mapping[int(part.joints[i][k])]);weights.append(part.weights[i][k])
            arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights
        else:
            # Avoid a second UNORM16 floor when saving an unchanged mesh.
            var ref=JSON.parse_string(FileAccess.get_file_as_string(item.original_geometry)).parts[si]
            var ws=PackedFloat32Array()
            for row in ref.weights:
                for w in row:ws.append(w)
            arrays[Mesh.ARRAY_WEIGHTS]=ws
        if si==0 and item.has("lips"):
            assert(material is ShaderMaterial and material.get_shader_parameter("mouth136_records") is Texture2D)
            var table=JSON.parse_string(FileAccess.get_file_as_string(item.skin_records));assert(table.size()==arrays[Mesh.ARRAY_VERTEX].size())
            var width=256;var height=ceili(table.size()/256.);var image=Image.create(width,height,false,Image.FORMAT_RGBAF)
            for i in table.size():var q=table[i];image.set_pixel(i%width,i/width,Color(q[0],q[1],q[2],q[3]))
            material.set_shader_parameter("mouth136_records",ImageTexture.create_from_image(image));material.set_shader_parameter("mouth136_size",Vector2i(width,height));material.set_shader_parameter("mouth136_stride",1)
            material.set_shader_parameter("mouth136_skin",image_texture(item.skin_atlas))
        if si==0 and item.has("clean_skin"):
            material.set_shader_parameter("source_texture",image_texture(item.clean_skin));material.set_shader_parameter("opaque_skin",image_texture(item.clean_skin));material.set_shader_parameter("patch_count",0)
        next.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);next.surface_set_material(si,material)
    body.mesh=next
    for si in next.get_surface_count():body.set_surface_override_material(si,null)
    if item.has("lip_cap"):
        var data=JSON.parse_string(FileAccess.get_file_as_string(item.lip_cap));var lip=MeshInstance3D.new();lip.name="Source_lips139";body.add_child(lip);lip.skin=body.skin;lip.skeleton=lip.get_path_to(body.get_node(body.skeleton));lip.mesh=ArrayMesh.new()
        var part:Dictionary=data.parts[0];var arrays=next.surface_get_arrays(int(item.lip_cap_surface));arrays[Mesh.ARRAY_VERTEX]=vectors(part.vertices);arrays[Mesh.ARRAY_NORMAL]=vectors(part.normals)
        var bones=PackedInt32Array();var weights=PackedFloat32Array()
        for i in part.joints.size():
            for k in 4:bones.append(mapping[int(part.joints[i][k])]);weights.append(part.weights[i][k])
        arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights
        lip.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);lip.mesh.surface_set_material(0,portable.freeze(body.get_active_material(int(item.lip_cap_surface))))
        assert(ResourceSaver.save(lip.mesh,item.output+"/lips.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK);intrinsic[lip.get_instance_id()]=true
    if item.has("lips"):
        var previous=e.model.find_child("Source_lips139",true,false)
        if previous:previous.get_parent().remove_child(previous);previous.free()
        var lip=MeshInstance3D.new();lip.name="Source_lips139";body.add_child(lip);lip.skin=body.skin;lip.skeleton=lip.get_path_to(body.get_node(body.skeleton));lip.mesh=ArrayMesh.new()
        for part in JSON.parse_string(FileAccess.get_file_as_string(item.lips)).parts:
            var arrays=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vectors(part.vertices);arrays[Mesh.ARRAY_NORMAL]=vectors(part.normals)
            var uv=PackedVector2Array();var uv2=PackedVector2Array();var colors=PackedColorArray();var bones=PackedInt32Array();var weights=PackedFloat32Array()
            for p in part.uv:uv.append(Vector2(p[0],p[1]))
            for p in part.uv2:uv2.append(Vector2(p[0],p[1]))
            for p in part.colors:colors.append(Color(p[0],p[1],p[2],p[3]))
            for i in part.joints.size():
                for k in 4:bones.append(mapping[int(part.joints[i][k])]);weights.append(part.weights[i][k])
            arrays[Mesh.ARRAY_TEX_UV]=uv;arrays[Mesh.ARRAY_TEX_UV2]=uv2;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights;arrays[Mesh.ARRAY_INDEX]=PackedInt32Array(part.triangles)
            var mat=ShaderMaterial.new();mat.shader=load(get_script().resource_path.get_base_dir().path_join("lip_uv135.gdshader"));mat.set_shader_parameter("original_source",image_texture(item.source));mat.set_shader_parameter("original_opaque",image_texture(item.opaque));mat.set_shader_parameter("continuation",image_texture(item.atlases[part.name]))
            lip.mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);lip.mesh.surface_set_material(lip.mesh.get_surface_count()-1,portable.freeze(mat))
        assert(ResourceSaver.save(lip.mesh,item.output+"/lips.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
        intrinsic[lip.get_instance_id()]=true
    assert(ResourceSaver.save(body.mesh,item.output+"/body.res",ResourceSaver.FLAG_BUNDLE_RESOURCES)==OK)
func run():
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide();hall.viewport.size=Vector2i(1000,700);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for node in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[node.get_instance_id()]=node.visible
    var rows=[]
    for item in plan.items:
        for path in item.frozen_inputs:assert(FileAccess.get_sha256(path)==item.frozen_inputs[path])
        var species:String=item.species;hall._select_display(species);var e:Dictionary=hall._selected()
        for tank in hall.tanks:tank.root.visible=tank.species==species
        for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=e.model.is_ancestor_of(node) and intrinsic.get(node.get_instance_id(),false)
        for node in hall.world.find_children("*","Label3D",true,false):node.hide()
        e.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.},true);e.controller.set_action("Swim",true);e.controller.step(0.);e.controller.seek(0.)
        if e.has("jaw_controller"):e.jaw_controller.apply(1.)
        var r=region(e);DirAccess.make_dir_recursive_absolute(item.output)
        await capture(e,r,item.output+"/before");edit_body(e,item);await capture(e,r,item.output+"/after")
        rows.append({"species":species,"body_sha256":FileAccess.get_sha256(item.output+"/body.res"),"lips_sha256":FileAccess.get_sha256(item.output+"/lips.res") if item.has("lips") or item.has("lip_cap") else ""})
    var f=FileAccess.open(out+"/preview.validation.json",FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"plan_sha256":FileAccess.get_sha256(plan_path),"rows":rows,"scope":"Isolated candidates only; full current gates required before install."},"  "));f.close();hall.queue_free();await process_frame;quit()
