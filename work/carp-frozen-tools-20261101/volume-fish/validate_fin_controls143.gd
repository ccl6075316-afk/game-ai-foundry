extends "validate_mouth_controls139.gd"
## Same96-phase/control/pivot/switch checks, on actual source-fin configurations.
func control_profiles()->Dictionary:return JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/fin-source141.json")).profiles
func control_binding(model:Node3D,species:String)->Dictionary:
    var fin=load("res://scripts/aquarium/FinSource141.gd").new().validate(model,species);assert(fin.ok);var mouth=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles
    if mouth.has(species):assert(super.control_binding(model,species).ok)
    return fin
func body_resource_sha(model:Node3D,species:String)->String:
    var mouth=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles
    if mouth.has(species):return mouth[species].body.sha256
    var profile:Dictionary=control_profiles()[species]
    return profile.body.sha256 if profile.has("body") else FileAccess.get_sha256(model.scene_file_path)
func uses_139_material_predicate(species:String)->bool:return JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles.has(species)
