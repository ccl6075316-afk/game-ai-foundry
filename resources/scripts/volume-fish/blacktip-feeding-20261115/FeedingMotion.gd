extends RefCounted
## Species-local preview control. Do not install as a shared shark default.
var skeleton: Skeleton3D
var lower: int
var upper: int
var floor_bone: int
var floor_base: Vector3
var floor_delta: Vector3
var head: int
var head_base: Quaternion
var cfg: Dictionary
var lower_base: Quaternion
var upper_rotation: Quaternion
var upper_base: Vector3
var upper_delta: Vector3
func configure(sk: Skeleton3D, data: Dictionary) -> void:
	skeleton=sk;cfg=data
	lower=sk.find_bone("jaw_lower");upper=sk.find_bone("jaw_upper")
	head=sk.find_bone("feeding_head");assert(lower>=0 and upper>=0 and head>=0)
	head_base=sk.get_bone_rest(head).basis.get_rotation_quaternion()
	floor_bone=sk.find_bone("oral_floor");assert(floor_bone>=0)
	floor_base=sk.get_bone_rest(floor_bone).origin
	var fd=cfg.floor_translation_native
	floor_delta=sk.get_bone_global_rest(sk.get_bone_parent(floor_bone)).basis.inverse()*Vector3(fd[0],fd[2],-fd[1])
	lower_base=sk.get_bone_rest(lower).basis.get_rotation_quaternion()
	upper_base=sk.get_bone_rest(upper).origin
	upper_rotation=sk.get_bone_rest(upper).basis.get_rotation_quaternion()
	var shift=cfg.upper_translation_native
	# Translation is expressed in the original rig (glTF) frame, then parent local.
	var delta:=Vector3(float(shift[0]),float(shift[2]),-float(shift[1]))
	var parent:=sk.get_bone_parent(upper)
	upper_delta=sk.get_bone_global_rest(parent).basis.inverse()*delta
func bend(t: float) -> float:
	var keys: Array=cfg.bend_keys
	for i in range(keys.size()-1):
		if t<=float(keys[i+1][0]):
			return lerpf(keys[i][1],keys[i+1][1],smoothstep(keys[i][0],keys[i+1][0],t))
	return float(keys[-1][1])
func values(t: float) -> Dictionary:
	var keys: Array=cfg.keyframes
	var result: Dictionary=keys[-1].duplicate()
	for i in range(keys.size()-1):
		var a: Dictionary=keys[i];var b: Dictionary=keys[i+1]
		if t<=float(b.t):
			var dt:=float(b.t)-float(a.t)
			var u:=clampf((t-float(a.t))/dt,0.,1.)
			var f:=smoothstep(0.,1.,u)
			result={"gape":lerpf(a.gape,b.gape,f),"protrusion":lerpf(a.protrusion,b.protrusion,f),"head":lerpf(a.head,b.head,f)}
			result.travel=(2*u*u*u-3*u*u+1)*float(a.travel)+(u*u*u-2*u*u+u)*dt*float(a.travel_speed)+(-2*u*u*u+3*u*u)*float(b.travel)+(u*u*u-u*u)*dt*float(b.travel_speed)
			break
	result.shake=bend(t)
	result.body_yaw=0.
	result.body_blend=smoothstep(cfg.blend_window[0],cfg.blend_window[1],t)*(1.-smoothstep(cfg.blend_window[2],cfg.blend_window[3],t))
	result.body_angles=[]
	var previous:=0.
	for i in range(8):
		var absolute:=float(cfg.body_degrees[i])*bend(t-float(cfg.body_delay[i]))
		result.body_angles.append(absolute-previous)
		previous=absolute
	return result
func apply(t: float) -> Dictionary:
	var v:=values(t)
	# Blend out the unrelated swim pose during the grip/bend/recovery event.
	for i in range(8):
		var bid:=skeleton.find_bone("body_%02d"%i)
		assert(bid>=0)
		var axis:=skeleton.get_bone_global_rest(bid).basis.inverse()*Vector3.UP
		var rest:=skeleton.get_bone_rest(bid).basis.get_rotation_quaternion()
		var target:=rest*Quaternion(axis.normalized(),deg_to_rad(v.body_angles[i]))
		skeleton.set_bone_pose_rotation(bid,skeleton.get_bone_pose_rotation(bid).slerp(target,v.body_blend))
	# Gate at closed mouth, and counter-rotate the lower child: upper closure
	# must not rotate the whole jaw carriage equally.
	var amount:=float(v.protrusion)*minf(1.,float(v.gape)/.25)
	var upper_angle:=deg_to_rad(float(cfg.upper_max_degrees))*amount
	skeleton.set_bone_pose_rotation(head,head_base*Quaternion(Vector3(0,0,1),deg_to_rad(float(cfg.shake_degrees))*float(v.shake))*Quaternion(Vector3.UP,deg_to_rad(-float(cfg.head_max_degrees))*float(v.head)))
	skeleton.set_bone_pose_rotation(upper,upper_rotation*Quaternion(Vector3.UP,upper_angle))
	skeleton.set_bone_pose_rotation(lower,lower_base*Quaternion(Vector3.UP,deg_to_rad(float(cfg.jaw_max_degrees))*float(v.gape)-upper_angle))
	skeleton.set_bone_pose_position(upper,upper_base+upper_delta*amount)
	skeleton.set_bone_pose_position(floor_bone,floor_base+floor_delta*float(v.gape))
	skeleton.force_update_all_bone_transforms()
	return v
