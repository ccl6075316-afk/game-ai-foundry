extends "export_runtime_fin_roots.gd"
## Read the same prebuilt GLB/resources as the real game, no candidate injection.
func prepare(entry:Dictionary,spec:Dictionary)->void:
    for path in spec.final_asset_dependencies:assert(FileAccess.get_sha256(path)==spec.final_asset_dependencies[path],"Stale final asset dependency")
    var receipt=load("res://scripts/aquarium/FinalizedFish157.gd").new().apply(entry.model,spec.species)
    assert(receipt.final_static_geometry and entry.model.get_meta("final_asset157_receipt").static_build_calls==0)
    super.prepare(entry,spec)
func save_json(path:String,value:Variant)->void:
    if path.ends_with("export.validation.json"):
        value.finalized_resource_loader=true
        value.final_asset_dependencies=plan.items[0].final_asset_dependencies
    super.save_json(path,value)
