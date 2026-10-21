extends "../../../scripts/volume-fish/capture_surface_mouth_audit.gd"
func _initialize():
    OS.set_environment("FISH_EYE_MODE","0")
    call_deferred("run")
func xyz(v:Vector3)->Array:return [v.x,v.y,v.z]
func transform_array(t:Transform3D)->Array:return [xyz(t.basis.x),xyz(t.basis.y),xyz(t.basis.z),xyz(t.origin)]
func ray_at(position:Vector2)->Dictionary:
    return {"screen_position":[position.x,position.y],"origin_world":xyz(hall.camera.project_ray_origin(position)),"direction_world":xyz(hall.camera.project_ray_normal(position))}
func run():
    root.size=Vector2i(1200,800)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true;hall.header.hide();hall.footer.hide()
    hall.screen.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT);hall.screen.position=Vector2.ZERO;hall.screen.size=Vector2(1200,800)
    hall.viewport.size=Vector2i(1200,800);hall.viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS
    ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles
    for mesh in hall.world.find_children("*","MeshInstance3D",true,false):intrinsic[mesh.get_instance_id()]=mesh.visible
    for label in hall.world.find_children("*","Label3D",true,false):label.hide()
    hall._select_display("zander");var entry:Dictionary=hall._selected()
    for tank in hall.tanks:tank.root.visible=tank.species=="zander"
    for node in hall.world.find_children("*","MeshInstance3D",true,false):node.visible=entry.model.is_ancestor_of(node) and intrinsic[node.get_instance_id()]
    entry.controller.set_motion_controls({"body_amplitude":0.,"body_frequency":1.,"fin_amplitude":0.,"fin_frequency":1.},true)
    assert(entry.controller.set_action("Swim",true));entry.controller.step(0.);entry.controller.seek(0.)
    if entry.has("jaw_controller"):entry.jaw_controller.apply(1.)
    await process_frame
    var r:Dictionary=region(entry);camera(entry,r,true,0.,1.56)
    var mesh:MeshInstance3D=entry.model.find_child("Closed_body",true,false)
    var skeleton:Skeleton3D=entry.skeleton;skeleton.force_update_all_bone_transforms()
    var arrays:Array=mesh.mesh.surface_get_arrays(0)
    var vertices:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var uvs:PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV]
    var joints:PackedInt32Array=arrays[Mesh.ARRAY_BONES];var weights:PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS]
    var normals:PackedVector3Array=arrays[Mesh.ARRAY_NORMAL];var indices:PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
    var transforms:Array[Transform3D]=[];var bindings:Array=[]
    for index in mesh.skin.get_bind_count():
        var bone:int=mesh.skin.get_bind_bone(index)
        if bone<0:bone=skeleton.find_bone(mesh.skin.get_bind_name(index))
        assert(bone>=0);bindings.append(bone)
        transforms.append(skeleton.global_transform*skeleton.get_bone_global_pose(bone)*mesh.skin.get_bind_pose(index))
    var count:int=joints.size()/vertices.size()
    var rest:Array=[];var uv:Array=[];var world:Array=[];var normal:Array=[];var world_local:Array=[];var weight_sums:Array=[]
    for index in vertices.size():
        var point:=Vector3.ZERO
        for j in count:
            var at:int=index*count+j
            point+=(transforms[joints[at]]*vertices[index])*weights[at]
        var local_point:=Vector3.ZERO;var weight_sum:float=0.
        for j in count:
            var at:int=index*count+j
            local_point+=(mesh.global_transform.affine_inverse()*transforms[joints[at]]*vertices[index])*weights[at]
            weight_sum+=weights[at]
        world_local.append(xyz(mesh.global_transform*local_point));weight_sums.append(weight_sum)
        rest.append(xyz(vertices[index]));uv.append([uvs[index].x,uvs[index].y]);world.append(xyz(point));normal.append(xyz(normals[index]))
    var rays:Array=[]
    for pixel in [Vector2(600,350),Vector2(600,400),Vector2(640,350),Vector2(680,360),Vector2(665,362),Vector2(640,440),Vector2(770,400),Vector2(620,350),Vector2(660,360)]:
        rays.append({"pixel":[int(pixel.x),int(pixel.y)],"integer_coordinate":ray_at(pixel),"pixel_center":ray_at(pixel+Vector2(.5,.5))})
    var data:Dictionary=RenderingServer.mesh_get_surface(mesh.mesh.get_rid(),0)
    var width:int=data.index_data.size()/data.index_count;var lods:Array=[]
    for lod in data.get("lods",[]):
        var bytes:PackedByteArray=lod.index_data;var triangles:Array=[]
        for offset in range(0,bytes.size(),width):triangles.append(bytes.decode_u16(offset) if width==2 else bytes.decode_u32(offset))
        lods.append({"edge_length":lod.edge_length,"indices":triangles})
    var material:ShaderMaterial=mesh.get_active_material(0)
    var context:=HashingContext.new();context.start(HashingContext.HASH_SHA256)
    for key in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_INDEX]:context.update(arrays[key].to_byte_array())
    var result:Dictionary={"schema_version":1,"ok":true,"command":"fish.eye107-pixel-trace-export","stage":"validate","status":"done","next_action":"human_review",
        "inputs":{"model_sha256":FileAccess.get_sha256("res://assets/models/fish/zander.glb"),"head_source_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/head-source.json")},
        "outputs":["/tmp/fish107-pixel-trace.json"],"summary":{"pose":"zero body/fin amplitude Swim0; same102 Hall/region/head-top yaw0 pitch1.56 camera","viewport_size":[1200,800],
        "camera_world_transform":transform_array(hall.camera.global_transform),"camera_fov":hall.camera.fov,"camera_near":hall.camera.near,"camera_far":hall.camera.far,"camera_keep_aspect":hall.camera.keep_aspect,
        "model_world_transform":transform_array(entry.model.global_transform),"mesh_world_transform":transform_array(mesh.global_transform),"skeleton_world_transform":transform_array(skeleton.global_transform),
        "region_body":str(r.body),"region_head":str(r.head),"mesh":"Closed_body","surface":0,"vertex_order_sha256":context.finish().hex_encode(),
        "rest_xyz":rest,"source_uv":uv,"rest_normals":normal,"indices":Array(indices),"skinned_world_xyz":world_local,"world_weighted_translation_xyz":world,"skinned_local_then_world_xyz":world_local,"weight_sums":weight_sums,"lods":lods,"rays":rays,
        "friendly_eye_scale":material.get_shader_parameter("friendly_eye_scale"),"friendly_eye_center":str(material.get_shader_parameter("friendly_eye_center")),"friendly_eye_radius":str(material.get_shader_parameter("friendly_eye_radius")),
        "skinning_method":"Blend mesh.global_transform.affine_inverse * skeleton.global_transform * skeleton.get_bone_global_pose(bind_bone) * skin.get_bind_pose(bind_index) per original arrays in local space, then apply mesh.global_transform once. Original weight sums preserved, no renormalization. world_weighted_translation_xyz is the older diagnostic comparison only.",
        "limits":"CPU export, not GPU selected-LOD proof. Both integer and center-of-pixel rays provided. No shader/profile/mesh changes."},"failures":[]}
    var file:=FileAccess.open("/tmp/fish107-pixel-trace.json",FileAccess.WRITE);file.store_string(JSON.stringify(result));file.close()
    print("107_PIXEL_TRACE ",vertices.size()," ",context)
    hall.queue_free();await process_frame
    if RenderingServer.has_method("force_sync"):RenderingServer.force_sync()
    await process_frame;quit()
