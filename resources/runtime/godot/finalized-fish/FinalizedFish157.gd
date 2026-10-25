extends RefCounted
## Offline geometry is already in GLB. Only load frozen engine materials/meshes.
func apply(model:Node3D,species:String)->Dictionary:
    assert(species=="whale_shark" and model.find_child("Static_fish157",true,false)!=null)
    var cfg=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json"));var p:Dictionary=cfg.profiles[species]
    assert(FileAccess.get_sha256(model.scene_file_path)==p.source_model_sha256)
    var ownership=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/surface-ownership.json")).profiles[species]
    var opacity=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/body-opacity.json")).profiles[species]
    for name in opacity.suppressed_auxiliary:
        var node=model.find_child(name,true,false);assert(node!=null);node.hide()
    for kind in ["body","lips"]:
        var node=model.find_child("Closed_body" if kind=="body" else "Source_lips139",true,false)as MeshInstance3D;assert(node!=null and node.skin!=null)
        assert(FileAccess.get_sha256(p[kind].path)==p[kind].sha256);node.mesh=load(p[kind].path)
        for si in node.mesh.get_surface_count():node.set_surface_override_material(si,null)
        if kind=="lips":node.set_meta("decorative_lip139",{"underlying_body":"Closed_body","resource_sha256":p[kind].sha256})
    var table=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/final157/whale_shark/materials.json"))
    var eyes=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/eye-relief112.json")).profiles[species]
    for name in table.materials:
        var node=model.find_child(name,true,false)as MeshInstance3D;assert(node!=null)
        var rows:Array=table.materials[name];assert(rows.size()==node.mesh.get_surface_count())
        for si in rows.size():
            assert(FileAccess.get_sha256(rows[si].path)==rows[si].sha256);node.set_surface_override_material(si,load(rows[si].path))
        if String(name).begins_with("Eye_relief112"):
            node.set_meta("decorative_relief112",{"underlying_body":"Closed_body","model_sha256":eyes.model_sha256,"profile_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/eye-relief112.json"),"source_rgba_sha256":eyes.source_rgba_sha256})
    var validator=load("res://scripts/aquarium/MouthRepair139.gd").new();var fins=validator.fin_state(model,species);var aux=validator.auxiliary_state(model,species)
    model.set_meta("mouth_repair139_receipt",{"species":species,"source_model_sha256":p.source_model_sha256,"config_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/mouth-repair139.json"),"helper_sha256":FileAccess.get_sha256("res://scripts/aquarium/MouthRepair139.gd"),"body_sha256":p.body.sha256,"lips_sha256":p.lips.sha256,"fins_original":fins,"fins_active":fins,"auxiliary_unchanged":aux,"provenance":"FinalizedFish157 resource loading; original mouth geometry builder not executed."})
    model.set_meta("eye_relief112_receipt",{"species":species,"caps":2,"underlying_body_intact":true,"model_sha256":eyes.model_sha256,"profile_sha256":FileAccess.get_sha256("res://assets/models/fish/motion/eye-relief112.json"),"helper_sha256":FileAccess.get_sha256(get_script().resource_path)})
    model.set_meta("final_asset157_receipt",{"static_build_calls":0,"static_builders_disabled":true,"material_resources":table.materials.size(),"geometry_entry":model.scene_file_path,"source_sha256":p.source_model_sha256})
    assert(validator.validate(model,species).ok)
    return {"skin_surfaces":2,"fin_surfaces":ownership.fins.size(),"eye_relief112":2,"mouth_repair139":1,"final_static_geometry":true}
