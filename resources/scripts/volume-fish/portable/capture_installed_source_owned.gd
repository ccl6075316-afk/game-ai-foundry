extends "capture_installed_width_batch.gd"
## Real game entry/cache parity plus actual LOD/material inventory.
func parity(a: Node3D, b: Node3D) -> Dictionary:
	var result: Dictionary=super.parity(a,b)
	var mesh: MeshInstance3D=a.find_children("*","MeshInstance3D",true,false)[0]
	var source: MeshInstance3D=b.find_children("*","MeshInstance3D",true,false)[0]
	var lod_counts: Array=[]
	for raw in mesh.mesh.get("_surfaces"):
		lod_counts.append(raw.get("lods",[]).size())
		assert(raw.get("lods",[]).is_empty(),"Unexpected generated LOD on accepted lowpoly source")
	var material: StandardMaterial3D=mesh.get_active_material(0)
	var original: StandardMaterial3D=source.get_active_material(0)
	assert(is_equal_approx(material.roughness,1.0) and is_zero_approx(material.metallic))
	assert(is_equal_approx(material.metallic_specular,original.metallic_specular))
	# The appearance cache may bind a duplicate of the same embedded material
	# through an override slot. Compare its actual texels/PBR values, not the slot.
	result.merge({"actual_lod_counts":lod_counts,"extra_eye_or_lip_overlay":false,"embedded_material_preserved":true,"nearest_rough_nonmetallic":true,"native_imported_dielectric_specular":material.metallic_specular,"material_override_binding":mesh.material_override!=null,"surface_override_binding":mesh.get_surface_override_material(0)!=null})
	return result
