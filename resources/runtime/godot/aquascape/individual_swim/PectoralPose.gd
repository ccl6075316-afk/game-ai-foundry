extends RefCounted

# Set both blades relative to their own insertions. Angles refer to the
# carrier's axes. The four observation rigs face +X with the left fin at +Z.
static func apply(entry: Dictionary, spread: float, dip: float, weight: float) -> void:
	if weight <= 0.0: return
	var rig: Skeleton3D = entry.skeleton
	if not entry.has("pectoral_pivots"):
		var pivots := []
		var model_basis: Basis = entry.carrier.global_basis.inverse()*rig.global_basis
		for bone in rig.get_bone_count():
			var name := String(rig.get_bone_name(bone))
			var left := name=="Pectoral_left" or name.begins_with("Pectoral_left_bodyframe_") or name.begins_with("AuxP_L_")
			var right := name=="Pectoral_right" or name.begins_with("Pectoral_right_bodyframe_") or name.begins_with("AuxP_R_")
			if not left and not right: continue
			var local := (model_basis*rig.get_bone_global_rest(bone).basis).inverse()
			pivots.append({"bone":bone,"sign":1.0 if left else -1.0,"up":(local*Vector3.UP).normalized(),
				"side":(local*Vector3.BACK).normalized(),"rest":rig.get_bone_rest(bone).basis.get_rotation_quaternion()})
		entry.pectoral_pivots = pivots
	for p: Dictionary in entry.pectoral_pivots:
		var target: Quaternion = p.rest * Quaternion(p.up,spread*p.sign) * Quaternion(p.side,dip)
		rig.set_bone_pose_rotation(p.bone,rig.get_bone_pose_rotation(p.bone).slerp(target.normalized(),weight))
