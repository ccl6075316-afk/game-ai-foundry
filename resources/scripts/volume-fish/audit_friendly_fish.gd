extends SceneTree
## Actual candidate skinning for the finite authored behavior, independent from the standard four-action gate.
var friendly=preload("res://scripts/aquarium/FriendlyFishPresentation.gd")
func _initialize():call_deferred("run")
func run():
    var args=OS.get_cmdline_user_args();var root_out:String=args[0]
    var plan:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args[1]))
    var config:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/presentation.json"))
    var profiles:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
    for spec in plan.items:
        if args.size()>2 and spec.species!=args[2]:continue
        var species:String=spec.species;var settings:Dictionary=config.profiles[species];assert(friendly.validate(settings))
        var out:String=root_out+"/"+species;DirAccess.make_dir_recursive_absolute(out)
        var carrier=Node3D.new();root.add_child(carrier)
        var model:Node3D=load("res://assets/models/fish/"+species+".glb").instantiate();carrier.add_child(model)
        var skeleton:Skeleton3D=model.find_children("*","Skeleton3D",true,false)[0]
        var player:AnimationPlayer=model.find_children("*","AnimationPlayer",true,false)[0];player.stop();skeleton.reset_bone_poses();skeleton.force_update_all_bone_transforms()
        var entry={"carrier":carrier,"model":model,"skeleton":skeleton,"player":player}
        var exporter=load("res://posed_export.gd").new();exporter.out=out;exporter.export_membranes=true;exporter.prepare(entry,spec)
        var bounds:=AABB();var first:=true
        for mesh in model.find_children("*","MeshInstance3D",true,false):
            var box:AABB=(model.global_transform.affine_inverse()*mesh.global_transform)*mesh.get_aabb()
            bounds=box if first else bounds.merge(box);first=false
        var length_m:float=float(profiles[species].real_length_cm)/100.
        assert(absf(bounds.size.x-float(spec.length_native))<float(spec.length_native)*.0001)
        model.scale=Vector3.ONE*length_m/bounds.size.x;model.position=-bounds.get_center()*model.scale
        var controller=load("res://scripts/aquarium/FoundryFishMotion.gd").new();assert(controller.configure(carrier,model,player,skeleton,profiles[species]).ok)
        controller.set_action("Swim",true);controller.seek(0.)
        controller.set_motion_controls({"body_amplitude":1.,"body_frequency":1.,"fin_amplitude":1.,"fin_frequency":1.},true)
        for frame in 192:
            var t:float=float(frame)/12.;var state:Dictionary=friendly.state(t,settings,length_m)
            controller.set_motion_controls(state.controls);controller.step(1./12.)
            carrier.position=state.offset;carrier.rotation=Vector3(0.,state.yaw,0.)
            if frame%6==0 or frame==191:exporter.sample(entry,"Friendly:"+state.label,t)
        var result={"ok":exporter.samples.size()==33,"species":species,"model":spec.model,"model_sha256":FileAccess.get_sha256(spec.model),"controller_sha256":FileAccess.get_sha256("res://scripts/aquarium/FoundryFishMotion.gd"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json"),"behavior_sha256":FileAccess.get_sha256("res://scripts/aquarium/FriendlyFishPresentation.gd"),"presentation_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/presentation.json"),"expected_fins":spec.fins.keys(),"samples":exporter.samples,"scope":"33 actual per-species authored behavior poses, same helper and every-frame controls as GPU capture; physical presentation scale included; not continuous proof or full490."}
        var file=FileAccess.open(out+"/export.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(result,"  "));file.close();print("FRIENDLY_EXPORT_DONE "+species)
        carrier.free()
    quit()
