extends SceneTree
var reports: Array=[]
var output: String
func _initialize() -> void:
    var args:=OS.get_cmdline_user_args()
    assert(args.size()==1,"Expected absolute output JSON path")
    output=args[0]
    call_deferred("run")
func run() -> void:
    var profiles: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
    for species in profiles:
        var carrier:=Node3D.new();root.add_child(carrier)
        var model: Node3D=load("res://assets/models/fish/"+species+".glb").instantiate();carrier.add_child(model)
        var bounds:=AABB();var first:=true
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            var box: AABB=(model.global_transform.affine_inverse()*mesh.global_transform)*mesh.get_aabb();bounds=box if first else bounds.merge(box);first=false
        model.scale=Vector3.ONE*float(profiles[species].real_length_cm)/100./bounds.size.x;model.position=-bounds.get_center()*model.scale
        var skeleton: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]
        var player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
        var controller=load("res://scripts/aquarium/FoundryFishMotion.gd").new()
        assert(controller.configure(carrier,model,player,skeleton,profiles[species]).ok)
        var cases: Dictionary={"zero":[0.,0.,0.,0.],"low":[.5,1.,.5,1.],"wide":[2.5,1.,2.5,1.],"fast_fins":[.5,1.,.5,3.],"fast_body":[.5,3.,.5,1.]}
        var results: Dictionary={}
        var clip: Animation=player.get_animation(profiles[species].base_clip)
        var pivot_positions: Array=[]
        for i in skeleton.get_bone_count():pivot_positions.append(skeleton.get_bone_pose_position(i))
        for label in cases:
            var v: Array=cases[label]
            controller.set_motion_controls({"body_amplitude":v[0],"body_frequency":v[1],"fin_amplitude":v[2],"fin_frequency":v[3]},true)
            var peak:=0.;var fin_samples: Array=[];var body_samples: Array=[];var neutral_error:=0.;var pivot_error:=0.
            for phase in 96:
                var seconds:=float(phase)*clip.length/96.;controller.seek(seconds)
                var fins: Array=[];var bodies: Array=[]
                for item in controller._fin_tracks:
                    var rotation:=skeleton.get_bone_pose_rotation(item.bone)
                    var neutral: Quaternion=item.get("neutral",item.rest)
                    peak=maxf(peak,neutral.angle_to(rotation));fins.append([rotation.x,rotation.y,rotation.z,rotation.w])
                    if label=="zero":neutral_error=maxf(neutral_error,neutral.angle_to(rotation))
                for bone in controller._bones:
                    var rotation:=skeleton.get_bone_pose_rotation(bone);bodies.append([rotation.x,rotation.y,rotation.z,rotation.w])
                    if label=="zero":neutral_error=maxf(neutral_error,controller._rest_rotations[controller._bones.find(bone)].angle_to(rotation))
                for i in skeleton.get_bone_count():pivot_error=maxf(pivot_error,skeleton.get_bone_pose_position(i).distance_to(pivot_positions[i]))
                fin_samples.append(fins);body_samples.append(bodies)
            results[label]={"fin_peak_rad":peak,"neutral_error_rad":neutral_error,"pivot_translation_error":pivot_error,"fin_samples":fin_samples,"body_samples":body_samples}
            assert(pivot_error<.000001,"Pivot translated: "+species)
        assert(controller._fin_tracks.size()>0,"No independently animated fins: "+species)
        assert(results.zero.neutral_error_rad<.001,"Zero amplitude does not return to neutral: "+species)
        assert(results.wide.fin_peak_rad>results.low.fin_peak_rad*4.7,"Fin amplitude ineffective: "+species)
        assert(absf(results.fast_fins.fin_peak_rad-results.low.fin_peak_rad)<.005,"Frequency changes amplitude: "+species)
        assert(JSON.stringify(results.fast_fins.body_samples)==JSON.stringify(results.low.body_samples),"Fin frequency changes body: "+species)
        assert(JSON.stringify(results.fast_body.fin_samples)==JSON.stringify(results.low.fin_samples),"Body frequency changes fins: "+species)
        for label in results:
            results[label].erase("fin_samples");results[label].erase("body_samples")
        controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true);controller.seek(0.)
        controller.set_motion_controls({"body_amplitude":2.5,"fin_frequency":3.})
        controller.step(.1)
        assert(controller._motion.body_amplitude>1. and controller._motion.body_amplitude<2.5,"Controls jump or do not blend")
        var transitions: Array=[]
        for action in ["Turn","Ascend","Dive","Swim"]:
            controller.set_action(action)
            for k in 16:controller.step(.0625)
            assert(controller.snapshot().inside_envelope)
            transitions.append(controller.snapshot())
        reports.append({"species":species,"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"ok":true,"fin_tracks":controller._fin_tracks.size(),"cases":results,"smooth_parameter_change":true,"actions":transitions.size()})
        print("MOTION_RANGE_TEST ",species," ",controller._fin_tracks.size()," ",results.wide.fin_peak_rad)
        carrier.queue_free();await process_frame
    var f:=FileAccess.open(output,FileAccess.WRITE);f.store_string(JSON.stringify({"ok":true,"checks":reports,"samples_per_case":96,"controller_sha256":FileAccess.get_sha256("res://scripts/aquarium/FoundryFishMotion.gd"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json")}));f.close();quit()
