extends "capture_mouth_delivery139.gd"
## Same complete views/actions/video for source-fin repairs and legacy fish.
func delivery_profiles()->Dictionary:return JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/motion.json")).profiles
func delivery_binding(e:Dictionary,species:String)->Dictionary:
    var fin=load("res://scripts/aquarium/FinSource141.gd").new().validate(e.model,species);assert(fin.ok);var mouth=JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/fish/motion/mouth-repair139.json")).profiles
    if mouth.has(species):
        var result=super.delivery_binding(e,species);result.fin_source143=fin;return result
    return {"ok":true,"fin_source143":fin,"scope":"Original body/rig and source-fin143 resources; this species has no139 mouth replacement."}
