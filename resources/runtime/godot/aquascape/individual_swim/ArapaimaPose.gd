extends RefCounted

static func apply(entry: Dictionary, still: float, jaw: float) -> void:
	if still > 0.0:
		var skeleton: Skeleton3D = entry.skeleton
		for bone in skeleton.get_bone_count():
			var rest := skeleton.get_bone_rest(bone).basis.get_rotation_quaternion()
			skeleton.set_bone_pose_rotation(bone,skeleton.get_bone_pose_rotation(bone).slerp(rest,still))
		preload("PectoralPose.gd").apply(entry,-0.48,-0.10,still)
	entry.controller.jaw_controller.apply(jaw)
