extends "export_fin_source141.gd"
## Physical body aliases from the actual legacy opacity inventory; exclude eyes.
func is_body_mesh(species:String,name:String)->bool:
    var legacy={"hairtail":"Hairtail_Ribbon_Body","piranha":"Fish_Body_Volume","silver_arowana":"Arowana_closed_laterally_compressed_body"}
    return name=="Closed_body" or legacy.get(species,"")==name
