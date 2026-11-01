extends RefCounted
## Independent lower-jaw control, applied after body animation each frame.
var skeleton: Skeleton3D
var index := -1
var limit := 0.0
var base := Quaternion.IDENTITY
func configure(target: Skeleton3D, degrees: float) -> void:
    skeleton=target
    index=skeleton.find_bone("jaw_lower")
    assert(index>=0 and degrees>0.0 and degrees<=18.0)
    limit=deg_to_rad(degrees)
    base=skeleton.get_bone_rest(index).basis.get_rotation_quaternion()
func apply(amount: float) -> void:
    # Exported bone local Y is the Blender transverse hinge direction.
    skeleton.set_bone_pose_rotation(index,base*Quaternion(Vector3.UP,clampf(amount,0.0,1.0)*limit))
