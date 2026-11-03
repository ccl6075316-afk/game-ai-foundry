extends "capture_transverse_width_trial.gd"
## Read-only identical-illumination diagnostic; original resource files untouched.
func _load(route: String, container: SubViewportContainer) -> Dictionary:
	var entry: Dictionary=super._load(route,container)
	for mesh in entry.model.find_children("*","MeshInstance3D",true,false):
		for surface in mesh.mesh.get_surface_count():
			var mat: StandardMaterial3D=mesh.get_active_material(surface)
			assert(mat!=null)
			mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
	return entry
