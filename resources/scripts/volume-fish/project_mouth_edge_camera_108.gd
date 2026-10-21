extends SceneTree
## Read-only actual game Camera3D projection; no mesh/material/helper mutations.
var hall:Control
func xyz(v:Vector3)->Array:return [v.x,v.y,v.z]
func transform_values(t:Transform3D)->Array:return [xyz(t.basis.x),xyz(t.basis.y),xyz(t.basis.z),xyz(t.origin)]
func _initialize():call_deferred("run")
func v3(a:Array)->Vector3:return Vector3(float(a[0]),float(a[1]),float(a[2]))
func project(p:Vector3)->Dictionary:
    var s:Vector2=hall.camera.unproject_position(p)
    var local:Vector3=hall.camera.global_transform.affine_inverse()*p
    var vp:Vector2i=hall.viewport.size
    return {"world":xyz(p),"screen_subviewport":[s.x,s.y],"camera_local":xyz(local),"behind":hall.camera.is_position_behind(p),"in_frustum":hall.camera.is_position_in_frustum(p),"inside_viewport_rectangle":s.x>=0 and s.y>=0 and s.x<vp.x and s.y<vp.y}
func rotate_to(yy:float,pp:float):
    var down:=InputEventMouseButton.new();down.button_index=MOUSE_BUTTON_LEFT;down.pressed=true;hall._on_view_input(down)
    var motion:=InputEventMouseMotion.new();motion.button_mask=MOUSE_BUTTON_MASK_LEFT;motion.relative=Vector2((hall.yaw-yy)/.006,(pp-hall.pitch)/.004);hall._on_view_input(motion)
    down.pressed=false;hall._on_view_input(down)
func pan_perpendicular_to(p:Vector3)->Dictionary:
    var initial:Vector3=hall.target
    var delta:Vector3=p-initial
    var permitted:Vector3=hall.camera.global_basis.x*delta.dot(hall.camera.global_basis.x)+hall.camera.global_basis.y*delta.dot(hall.camera.global_basis.y)
    var relative:Vector2=Vector2(-permitted.dot(hall.camera.global_basis.x),permitted.dot(hall.camera.global_basis.y))/(hall.distance*.001)
    var down:=InputEventMouseButton.new();down.button_index=MOUSE_BUTTON_MIDDLE;down.pressed=true;hall._on_view_input(down)
    var motion:=InputEventMouseMotion.new();motion.button_mask=MOUSE_BUTTON_MASK_MIDDLE;motion.relative=relative;hall._on_view_input(motion)
    down.pressed=false;hall._on_view_input(down)
    return {"input_middle_pan_relative":[relative.x,relative.y],"target_before":xyz(initial),"requested_target":xyz(initial+permitted),"actual_target_after_clamp":xyz(hall.target),"along_view_depth_translation_requested":0.0}
func run():
    var args:=OS.get_cmdline_user_args();assert(args.size()==2,"Need absolute input/report output")
    var input_path:String=args[0];var output_path:String=args[1]
    var report:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(input_path))
    var contributor:Dictionary=report.failed_knownlip2000_5_PL_contributor
    OS.set_environment("FISH_EYE_MODE","0")
    root.size=Vector2i(1280,720)
    hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall);hall.set_process(false);hall.paused=true;hall._resize()
    var entry:Dictionary=hall._selected();assert(entry.species=="zander")
    entry.controller.set_motion_controls({"body_amplitude":0.,"fin_amplitude":0.,"body_frequency":1.,"fin_frequency":1.},true)
    assert(entry.controller.set_action("Swim",true));entry.controller.step(0.);entry.controller.seek(0.)
    await process_frame
    var snapshot:Dictionary=entry.controller.snapshot();var model_transform:Transform3D=entry.model.global_transform
    var mesh:MeshInstance3D=entry.model.find_child("Closed_body",true,false)
    var arrays:Array=mesh.mesh.surface_get_arrays(0)
    var original:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
    var joints:PackedInt32Array=arrays[Mesh.ARRAY_BONES];var weights:PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS]
    var skeleton:Skeleton3D=entry.skeleton;skeleton.force_update_all_bone_transforms()
    var transforms:Array[Transform3D]=[]
    for j in mesh.skin.get_bind_count():
        var bone:int=mesh.skin.get_bind_bone(j)
        if bone<0:bone=skeleton.find_bone(mesh.skin.get_bind_name(j))
        assert(bone>=0);transforms.append(skeleton.global_transform*skeleton.get_bone_global_pose(bone)*mesh.skin.get_bind_pose(j))
    var width:int=joints.size()/original.size();var endpoints:Array=[];var epworld:Array[Vector3]=[];var blend_basis:=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO)
    var t:float=contributor.edge_parameter
    for k in contributor.edge_vertex_ids.size():
        var id:int=contributor.edge_vertex_ids[k];var detail:Dictionary={}
        for d in contributor.original_origin_vertex_details:
            if int(d.skin_actual_id)==id:detail=d;break
        assert(not detail.is_empty());assert(original[id].distance_to(v3(detail.original_actual_xyz))<.0000001)
        var p:Vector3=v3(detail.mapped_f32_xyz);var pworld:=Vector3.ZERO;var ew:Array=[];var mixw:float=1.-t if k==0 else t
        for j in width:
            var at:int=id*width+j;var weight:float=weights[at]
            if weight==0:continue
            var matrix:Transform3D=transforms[joints[at]];pworld+=(matrix*p)*weight
            blend_basis.x+=matrix.basis.x*weight*mixw;blend_basis.y+=matrix.basis.y*weight*mixw;blend_basis.z+=matrix.basis.z*weight*mixw
            ew.append({"bind_slot":joints[at],"weight":weight,"skin_world_transform":transform_values(matrix)})
        endpoints.append({"actual_id":id,"rest_mapped":xyz(p),"world":xyz(pworld),"binding":ew});epworld.append(pworld)
    var pa:Vector3=v3(endpoints[0].rest_mapped);var pb:Vector3=v3(endpoints[1].rest_mapped)
    var hit:Vector3=pa.lerp(pb,t);var target_rest:=hit;target_rest.y=(371.-407.)/2024.
    var hit_world:Vector3=epworld[0].lerp(epworld[1],t)
    var target_world:Vector3=hit_world+blend_basis*(target_rest-hit)
    var points:Array=[{"role":"right_actual_PL_edge","rest_actual":xyz(hit),"rest_target_sameXZ":xyz(target_rest),"world_actual":xyz(hit_world),"world_target":xyz(target_world),"verified_actual_edge":true}]
    var left:=hit;left.z=-left.z;var left_target:=target_rest;left_target.z=-left_target.z
    points.append({"role":"left_mirrored_sameXY_diagnostic_not_verified_edge","rest_actual":xyz(left),"rest_target_sameXZ":xyz(left_target),"world_actual":xyz(mesh.global_transform*left),"world_target":xyz(mesh.global_transform*left_target),"verified_actual_edge":false})
    var rows:Array=[]
    for viewport_case in [{"name":"configured_default_window","root_size":Vector2i(1280,720)},{"name":"resize_formula_720high_cap_diagnostic_not_host_window_claim","root_size":Vector2i(1280,1062)}]:
        root.size=viewport_case.root_size;hall._resize()
        for preset in ["normal","near","closest"]:
            for view in ["side","front","oblique"]:
                if preset=="normal":hall._focus_selected(true,2.6)
                else:hall._close_view()
                var yy:float=0. if view=="side" else PI/2. if view=="front" else .32 if preset=="normal" else .18
                var pp:float=0. if view!="oblique" else .14 if preset=="normal" else .08
                rotate_to(yy,pp)
                var wheel_steps:int=0
                if preset=="closest":
                    for wheel in 100:
                        var before:float=hall.distance;var e:=InputEventMouseButton.new();e.button_index=MOUSE_BUTTON_WHEEL_UP;e.pressed=true;hall._on_view_input(e);wheel_steps+=1
                        if hall.distance==before:break
                for pan in [false,true] if preset=="closest" else [false]:
                    var pan_receipt:Dictionary={}
                    if pan:pan_receipt=pan_perpendicular_to(hit_world)
                    var projected:Array=[]
                    for pair in points:
                        var actual:Dictionary=project(v3(pair.world_actual));var target:Dictionary=project(v3(pair.world_target));var aa:=Vector2(actual.screen_subviewport[0],actual.screen_subviewport[1]);var bb:=Vector2(target.screen_subviewport[0],target.screen_subviewport[1]);projected.append({"role":pair.role,"actual":actual,"target":target,"screen_error_pixels":aa.distance_to(bb),"delta_screen_xy":[bb.x-aa.x,bb.y-aa.y]})
                    rows.append({"viewport_case":viewport_case.name,"root_size":[root.size.x,root.size.y],"render_viewport_size":[hall.viewport.size.x,hall.viewport.size.y],"preset":preset,"view":view,"pan_to_mouth_perpendicular_only":pan,"pan_receipt":pan_receipt,"wheel_steps":wheel_steps,"yaw":hall.yaw,"pitch":hall.pitch,"distance":hall.distance,"distance_min_clamp":maxf(.16,entry.length_m*.65),"target":xyz(hall.target),"camera_world_transform":transform_values(hall.camera.global_transform),"camera_projection":str(hall.camera.get_camera_projection()),"camera_fov":hall.camera.fov,"camera_near":hall.camera.near,"camera_far":hall.camera.far,"keep_aspect":hall.camera.keep_aspect,"point_pairs":projected})
    assert(entry.controller.snapshot()==snapshot);assert(entry.model.global_transform==model_transform)
    var hashes:Dictionary={}
    for path in ["res://assets/models/fish/zander.glb","res://scripts/aquarium/VolumeFishExhibit.gd","res://scripts/aquarium/FoundryFishMotion.gd","res://assets/models/fish/motion/motion.json","res://scripts/aquarium/FishSurfaceOwnership.gd"]:hashes[path]=FileAccess.get_sha256(path)
    assert(hashes["res://assets/models/fish/zander.glb"]=="c1b10d96c7aa83e41129df16170d7302f4c4335b226785c5f5b5bd562b6e0aef")
    var output:Dictionary={"status":"readonly_actual_game_camera_projection","accepted":false,"mesh_material_helpers_changed":false,"new_candidate_saved":false,"projection_only_no_GPU_visual_claim":true,"input":input_path,"input_sha256":FileAccess.get_sha256(input_path),"script_sha256":FileAccess.get_sha256(get_script().resource_path),"runtime_hashes":hashes,"project_path":ProjectSettings.globalize_path("res://"),"real_length_m":entry.length_m,"model_global_transform":transform_values(entry.model.global_transform),"mesh_global_transform":transform_values(mesh.global_transform),"skeleton_global_transform":transform_values(skeleton.global_transform),"carrier_global_transform":transform_values(entry.carrier.global_transform),"controller_snapshot":snapshot,"skin_bind_endpoint_data":endpoints,"edge_t":t,"point_pairs":points,"source_error_native_pixels":contributor.Y-407.,"gallery_bounds":str(hall.gallery_bounds),"pan_target_limits":str(hall.gallery_bounds.grow(1.)),"camera_projections":rows,"limits":["Actual Camera3D.unproject_position and controls/clamps, no sourcepixel/width scaling estimate.","Right is actualfailededge; left mirror only diagnoses sign/view role, not an independently verified left PLerror.","Current defaultwindow1280x720 yieldsviewportheight378 because342UI;720highcase is explicit responsive resize diagnostic,not current hostwindowassertion.","No arbitrary forwardpan/nearclip optimization; closestpan moves only currentcamera right/up viaactualmiddlemouse path.","No ray visibility/occlusion rendering; frustum flag does not prove unobstructed visible pixel."]}
    var file:=FileAccess.open(output_path,FileAccess.WRITE);assert(file!=null);file.store_string(JSON.stringify(output,"  "));file.close();print("108_CAMERA_PROJECTION_ROWS ",rows.size()," OUTPUT ",output_path);hall.queue_free();await process_frame;quit()
