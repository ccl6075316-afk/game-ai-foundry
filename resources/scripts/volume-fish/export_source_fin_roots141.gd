extends "export_runtime_fin_roots112.gd"
## Load the complete actual configured layer chain, then use unchanged177/490 export.
var frozen_inputs:Dictionary={}
func run():
    var args=OS.get_cmdline_user_args()
    if not "--static-only" in args:
        await super.run()
        return
    plan=JSON.parse_string(FileAccess.get_file_as_string(args[0]));export_membranes=true
    for spec in plan.items:
        if spec.species!=args[3]:continue
        out=args[1].path_join(spec.species);DirAccess.make_dir_recursive_absolute(out);samples=[];var carrier=Node3D.new();root.add_child(carrier);var packed=load(ProjectSettings.localize_path(spec.model.replace("\\","/"))) as PackedScene;assert(packed!=null);var model=packed.instantiate();carrier.add_child(model);var skeleton=model.find_children("*","Skeleton3D",true,false)[0];var player=model.find_children("*","AnimationPlayer",true,false)[0];player.stop();skeleton.reset_bone_poses();skeleton.force_update_all_bone_transforms();var entry={"carrier":carrier,"model":model,"skeleton":skeleton,"player":player};prepare(entry,spec);var profile=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles[spec.species];model.scale=Vector3.ONE*float(profile.real_length_cm)/100./float(spec.length_native);sample(entry,"Static",0.)
        save_json(out.path_join("export.validation.json"),{"ok":true,"model":spec.model,"model_sha256":FileAccess.get_sha256(spec.model),"expected_fins":spec.fins.keys(),"controller_source":spec.controller_script,"controller_sha256":FileAccess.get_sha256(spec.controller_script),"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd"),"motion_config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/motion.json"),"export_script_sha256":FileAccess.get_sha256(get_script().resource_path),"samples":samples,"static_only":true,"scope":"One actual original-rest sample, before expensive177/490. Not full motion completion."});carrier.queue_free();await process_frame
    quit()
func prepare(entry:Dictionary,spec:Dictionary):
    frozen_inputs=spec.mouth_candidate.frozen_inputs
    for path in frozen_inputs:assert(FileAccess.get_sha256(path)==frozen_inputs[path],"Stale141 input "+path)
    var changed=load("res://scripts/aquarium/FishSurfaceOwnership.gd").new().apply(entry.model,spec.species)
    var source_profiles:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/fin-source141.json")).profiles
    var replacements:Dictionary=source_profiles[spec.species].fins
    assert(not replacements.is_empty())
    for name in replacements:assert(spec.fins.has(name),"Replacement missing from full applicable fin inventory")
    assert(changed.get("fin_source141",0)==replacements.size())
    assert(load("res://scripts/aquarium/FinSource141.gd").new().validate(entry.model,spec.species).ok)
    super.prepare(entry,spec)
func save_json(path:String,value:Variant):
    if path.ends_with("export.validation.json"):value.candidate_input_sha256=frozen_inputs;value.fin_source141=true
    super.save_json(path,value)
