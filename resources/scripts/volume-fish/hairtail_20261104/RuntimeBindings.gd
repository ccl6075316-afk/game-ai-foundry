extends RefCounted
## Normal engine image filtering only, matching VolumeFishExhibit.gd:508.
## No geometry, UV, color, alpha, emission, skeleton or animation edits.
func apply(model: Node3D) -> Dictionary:
    var rows: Array=[]
    for mesh in model.find_children("*","MeshInstance3D",true,false):
        for si in mesh.mesh.get_surface_count():
            var original=mesh.get_active_material(si)
            assert(original is BaseMaterial3D)
            var material=original.duplicate()
            material.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
            assert(material.transparency==original.transparency and material.emission_enabled==original.emission_enabled and material.emission==original.emission)
            mesh.set_surface_override_material(si,material)
            rows.append({"mesh":mesh.name,"surface":si,"source_filter":original.texture_filter,"effective_filter":material.texture_filter,"transparency":material.transparency})
    return {"ok":true,"kind":"normal_nearest_engine_binding","rows":rows,"scope":"GLTFDocument leaves emission-only materials at its default filter. This normal filtering binding matches existing actual game behavior; no static appearance reconstruction."}
