extends SceneTree
## Tests the exhibit's actual per-species controllers with installed139 meshes.
var output:String
func control_profiles()->Dictionary:return JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles
func control_binding(model:Node3D,species:String)->Dictionary:return load("res://scripts/aquarium/MouthRepair139.gd").new().validate(model,species)
func body_resource_sha(_model:Node3D,species:String)->String:return control_profiles()[species].body.sha256
func uses_139_material_predicate(_species:String)->bool:return true
func _initialize():
    output=OS.get_cmdline_user_args()[0];call_deferred("run")
func run():
    var hall=load("res://scripts/aquarium/VolumeFishExhibit.gd").new();root.add_child(hall)
    hall.set_process(false);hall.paused=true
    var selected=control_profiles()
    var profiles=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
    var checks=[]
    for species in selected:
        hall._select_display(species);var e:Dictionary=hall._selected();var controller=e.controller;var skeleton:Skeleton3D=e.skeleton
        assert(control_binding(e.model,species).ok)
        var clip:Animation=e.player.get_animation(profiles[species].base_clip)
        var pivots=[]
        for i in skeleton.get_bone_count():pivots.append(skeleton.get_bone_pose_position(i))
        var cases={"zero":[0.,0.,0.,0.],"low":[.5,1.,.5,1.],"wide":[2.5,1.,2.5,1.],"fast_fins":[.5,1.,.5,3.],"fast_body":[.5,3.,.5,1.]};var results={}
        for label in cases:
            var v=cases[label];controller.set_motion_controls({"body_amplitude":v[0],"body_frequency":v[1],"fin_amplitude":v[2],"fin_frequency":v[3]},true)
            var peak=0.;var neutral_error=0.;var pivot_error=0.;var fin_samples=[];var body_samples=[]
            for phase in 96:
                controller.seek(float(phase)*clip.length/96.);var fins=[];var bodies=[]
                for item in controller._fin_tracks:
                    var rotation:Quaternion=skeleton.get_bone_pose_rotation(item.bone);var neutral:Quaternion=item.get("neutral",item.rest)
                    peak=maxf(peak,neutral.angle_to(rotation));fins.append([rotation.x,rotation.y,rotation.z,rotation.w])
                    if label=="zero":neutral_error=maxf(neutral_error,neutral.angle_to(rotation))
                for bone in controller._bones:
                    var rotation=skeleton.get_bone_pose_rotation(bone);bodies.append([rotation.x,rotation.y,rotation.z,rotation.w])
                    if label=="zero":neutral_error=maxf(neutral_error,controller._rest_rotations[controller._bones.find(bone)].angle_to(rotation))
                for i in skeleton.get_bone_count():pivot_error=maxf(pivot_error,skeleton.get_bone_pose_position(i).distance_to(pivots[i]))
                fin_samples.append(fins);body_samples.append(bodies)
            assert(pivot_error<.000001,"Translated pivot: "+species)
            results[label]={"fin_peak_rad":peak,"neutral_error_rad":neutral_error,"pivot_error":pivot_error,"fin_samples":fin_samples,"body_samples":body_samples}
        assert(controller._fin_tracks.size()>0 and results.zero.neutral_error_rad<.001)
        assert(results.wide.fin_peak_rad>results.low.fin_peak_rad*4.7,"Ineffective fin amplitude: "+species)
        assert(absf(results.fast_fins.fin_peak_rad-results.low.fin_peak_rad)<.005,"Frequency changes amplitude: "+species)
        assert(JSON.stringify(results.fast_fins.body_samples)==JSON.stringify(results.low.body_samples),"Fin/body clocks coupled: "+species)
        assert(JSON.stringify(results.fast_body.fin_samples)==JSON.stringify(results.low.fin_samples),"Body/fin clocks coupled: "+species)
        controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true);controller.seek(0.)
        controller.set_motion_controls({"body_amplitude":2.5,"fin_frequency":3.});controller.step(.1)
        assert(controller._motion.body_amplitude>1. and controller._motion.body_amplitude<2.5)
        var actions=[]
        for action in ["Turn","Ascend","Dive","Swim"]:
            controller.set_action(action)
            for k in 16:controller.step(.0625)
            assert(controller.snapshot().inside_envelope);actions.append(controller.snapshot())
        for label in results:results[label].erase("fin_samples");results[label].erase("body_samples")
        var body=e.model.find_child("Closed_body",true,false) as MeshInstance3D
        for si in body.mesh.get_surface_count():
            if not uses_139_material_predicate(species):continue
            var mat=body.get_active_material(si)
            if not mat is ShaderMaterial:continue
            var code:String=mat.shader.code
            assert(not code.contains("front112_rest=VERTEX;front112_normal=NORMAL;"),"Animated front material coordinates: "+species)
            if code.contains("rest_position=VERTEX;"):
                for key in ["head_source_repair","head_blend"]:
                    var active=mat.get_shader_parameter(key)
                    assert(active==null or active==false,"Active legacy posed head projection: "+species+"/"+key)
        assert(control_binding(e.model,species).ok)
        checks.append({"species":species,"ok":true,"cases":results,"actions":actions,"native_loop_samples_per_case":96,"controller":controller.get_script().resource_path,"controller_sha256":FileAccess.get_sha256(controller.get_script().resource_path),"model_sha256":FileAccess.get_sha256("res://assets/models/fish/"+species+".glb"),"resource_body_sha256":body_resource_sha(e.model,species),"139_material_flag_predicate_applicable":uses_139_material_predicate(species),"material_scope":"Original body branches require their own077/chart/GPU and motion visual evidence; this controller check does not accept material coordinates."})
        print("MOUTH_CONTROL139 ",species," actual_controller=",controller.get_script().resource_path)
    var f=FileAccess.open(output,FileAccess.WRITE);f.store_string(JSON.stringify({"ok":checks.size()==selected.size(),"checks":checks,"checker_sha256":FileAccess.get_sha256(get_script().resource_path),"config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/mouth-repair139.json"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json"),"scope":"Actual exhibit controllers and installed139 meshes;96 native-loop samples per parameter case, neutral/max/independent clocks, pivot positions, smooth controls and four action changes. Static material-coordinate declarations checked; GPU captures and full fin gates remain separate."}));f.close()
    hall.queue_free();await process_frame;quit()
