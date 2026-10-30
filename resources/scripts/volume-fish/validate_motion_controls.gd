extends SceneTree
var reports: Array=[]
var output: String
var standalone: Dictionary={}
var standalone_path: String
var bindings: Dictionary={}
const PACKED_PARTS = preload("PackedFishValidation.gd")
func _initialize() -> void:
    var args:=OS.get_cmdline_user_args()
    assert(args.size()==1 or (args.size()==3 and args[1]=="--standalone-plan"),"Expected output JSON path and optional --standalone-plan JSON")
    output=args[0]
    if args.size()==3:
        standalone_path=args[2];standalone=JSON.parse_string(FileAccess.get_file_as_string(standalone_path))
        bindings=standalone.frozen_inputs.duplicate()
        for key in ["model","motion_profile","motion_runtime"]:
            assert(FileAccess.get_sha256(standalone[key])==standalone[key+"_sha256"],"Stale standalone motion dependency")
            bindings[standalone[key]]=standalone[key+"_sha256"]
        for path in bindings:assert(FileAccess.get_sha256(path)==bindings[path])
    call_deferred("run")

static func static_binding_digest(model: Node3D) -> String:
    var values: Array=[]
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        for s in mesh.mesh.get_surface_count():
            var material: StandardMaterial3D=mesh.get_active_material(s) as StandardMaterial3D;assert(material!=null)
            values.append([str(mesh.name),s,mesh.mesh.surface_get_arrays(s),material.get_instance_id(),material.albedo_color,material.transparency,material.texture_filter,material.albedo_texture.get_image().get_data() if material.albedo_texture!=null else PackedByteArray()])
    return var_to_bytes(values).hex_encode().sha256_text()

func run() -> void:
    var profiles: Dictionary={}
    if standalone.is_empty():profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
    else:profiles[standalone.species]=JSON.parse_string(FileAccess.get_file_as_string(standalone.motion_profile))
    for species in profiles:
        var carrier:=Node3D.new();root.add_child(carrier)
        var model_path: String="res://assets/models/fish/"+species+".glb" if standalone.is_empty() else standalone.model
        var model: Node3D
        if standalone.is_empty():model=load(model_path).instantiate()
        else:
            var document: GLTFDocument=GLTFDocument.new();var state: GLTFState=GLTFState.new();assert(document.append_from_file(model_path,state)==OK)
            model=document.generate_scene(state);assert(model!=null)
        carrier.add_child(model)
        var bounds:=AABB();var first:=true
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            var box: AABB=(model.global_transform.affine_inverse()*mesh.global_transform)*mesh.get_aabb();bounds=box if first else bounds.merge(box);first=false
        if standalone.is_empty():
            model.scale=Vector3.ONE*float(profiles[species].real_length_cm)/100./bounds.size.x;model.position=-bounds.get_center()*model.scale
        else:
            assert(is_finite(float(standalone.model_scale)) and float(standalone.model_scale)>0);model.scale=Vector3.ONE*float(standalone.model_scale)
        var skeleton: Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]
        var player: AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0]
        var controller=load("res://scripts/aquarium/FoundryFishMotion.gd" if standalone.is_empty() else standalone.motion_runtime).new()
        assert(controller.configure(carrier,model,player,skeleton,profiles[species]).ok)
        var packed_partition: Dictionary={}
        if standalone.has("packed_parts_manifest"):
            packed_partition=PACKED_PARTS.surfaces({"model":model,"skeleton":skeleton},standalone).proof
        var static_before: String="" if standalone.is_empty() else static_binding_digest(model)
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
                    if not standalone.is_empty():assert(rotation.is_finite(),"Nonfinite actual fin pose")
                    var neutral: Quaternion=item.get("neutral",item.rest)
                    peak=maxf(peak,neutral.angle_to(rotation));fins.append([rotation.x,rotation.y,rotation.z,rotation.w])
                    if label=="zero":neutral_error=maxf(neutral_error,neutral.angle_to(rotation))
                for bone in controller._bones:
                    var rotation:=skeleton.get_bone_pose_rotation(bone);bodies.append([rotation.x,rotation.y,rotation.z,rotation.w])
                    if not standalone.is_empty():assert(rotation.is_finite(),"Nonfinite actual body pose")
                    if label=="zero":neutral_error=maxf(neutral_error,controller._rest_rotations[controller._bones.find(bone)].angle_to(rotation))
                for i in skeleton.get_bone_count():
                    if not standalone.is_empty():assert(skeleton.get_bone_pose_position(i).is_finite(),"Nonfinite actual pivot")
                    pivot_error=maxf(pivot_error,skeleton.get_bone_pose_position(i).distance_to(pivot_positions[i]))
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
            if standalone.is_empty():controller.set_action(action)
            else:assert(controller.set_action(action),"Standalone action rejected: "+action)
            for k in 16:controller.step(.0625)
            assert(controller.snapshot().inside_envelope)
            var actual_snapshot: Dictionary=controller.snapshot()
            if not standalone.is_empty():assert(actual_snapshot.action==action and actual_snapshot.pending_action=="","Requested standalone action did not execute")
            transitions.append(actual_snapshot)
        var row: Dictionary={"species":species,"model_sha256":FileAccess.get_sha256(model_path),"ok":true,"fin_tracks":controller._fin_tracks.size(),"cases":results,"smooth_parameter_change":true,"actions":transitions.size()}
        if not standalone.is_empty():
            var static_after: String=static_binding_digest(model);assert(static_before==static_after,"Runtime changed rest arrays, UVs or actual material bindings")
            row["static_arrays_uv_material_digest"]=static_after;row["rest_arrays_uv_materials_unchanged"]=true
            row["actual_transition_snapshots"]=transitions
        if not packed_partition.is_empty():row["packed_partition_proof"]=packed_partition
        reports.append(row)
        print("MOTION_RANGE_TEST ",species," ",controller._fin_tracks.size()," ",results.wide.fin_peak_rad)
        carrier.queue_free();await process_frame
    var result: Dictionary={"ok":true,"checks":reports,"samples_per_case":96,"controller_sha256":FileAccess.get_sha256("res://scripts/aquarium/FoundryFishMotion.gd" if standalone.is_empty() else standalone.motion_runtime),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json" if standalone.is_empty() else standalone.motion_profile)}
    if not standalone.is_empty():
        for path in bindings:assert(FileAccess.get_sha256(path)==bindings[path],"Motion dependency changed during validation")
        result.merge({"kind":"standalone_motion_controls","standalone_plan_sha256":FileAccess.get_sha256(standalone_path),"frozen_inputs":bindings,"direct_GLTFDocument":true,"static_builders":false,"validator_sha256":FileAccess.get_sha256(get_script().resource_path),"cases_per_species":5,"transitions":["Turn","Ascend","Dive","Swim"],"scope":"Same five control cases ×96 phases and four transitions as installed validation; finite discrete coverage, not full membrane/visual acceptance."})
    var f:=FileAccess.open(output,FileAccess.WRITE);f.store_string(JSON.stringify(result));f.close();quit()
