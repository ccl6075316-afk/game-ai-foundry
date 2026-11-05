extends RefCounted
## Explicit engine filtering only. No script hooks or static asset construction.

static func apply(meshes: Array, viewer: Dictionary) -> Dictionary:
    if not viewer.has("engine_materials"):
        return {"ok":true,"applied":false,"rows":[]}
    var requested=viewer.engine_materials
    if not requested is Dictionary or requested.size()!=1 or typeof(requested.get("texture_filter"))!=TYPE_STRING or requested.get("texture_filter")!="nearest":
        return {"ok":false,"error":"engine_materials must be exactly {texture_filter: nearest}"}
    var pending: Array=[]
    for mesh in meshes:
        if not mesh is MeshInstance3D or mesh.mesh==null:
            return {"ok":false,"error":"engine_materials requires a MeshInstance3D with a mesh"}
        for surface in mesh.mesh.get_surface_count():
            var original=mesh.get_active_material(surface)
            if not original is BaseMaterial3D:
                return {"ok":false,"error":"Nearest binding requires BaseMaterial3D at "+str(mesh.name)+":"+str(surface)}
            pending.append({"mesh":mesh,"surface":surface,"original":original})
    if pending.is_empty():
        return {"ok":false,"error":"Nearest binding has no material surfaces"}
    # Preflight the whole set before changing any effective material binding.
    var rows: Array=[]
    for item in pending:
        var original: BaseMaterial3D=item.original
        var material: BaseMaterial3D=original.duplicate()
        material.texture_filter=BaseMaterial3D.TEXTURE_FILTER_NEAREST
        item.mesh.set_surface_override_material(item.surface,material)
        rows.append({"mesh":str(item.mesh.name),"surface":item.surface,"source_filter":original.texture_filter,"effective_filter":material.texture_filter,"transparency":material.transparency,"emission_enabled":material.emission_enabled})
    # A pre-existing mesh-wide material has already been copied per surface.
    # Clearing its priority also makes the existing gray/null round trip exact.
    for mesh in meshes:mesh.material_override=null
    return {"ok":true,"applied":true,"kind":"nearest_engine_material_binding","rows":rows,"scope":"Clone each actual active BaseMaterial3D; only texture_filter changes. Original resources/textures and mesh/UV/skin untouched."}
