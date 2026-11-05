extends "../../../runtime/godot/VolumeFishMotion.gd"
## Fish-private normal bone posture channel. Never changes mesh arrays or queries body geometry.
var _support_rows: Array[Dictionary]=[]
var _support_contract: Dictionary={}
var _support_gain:=0.0
func _bone(name: String) -> int:
	var id:=_skeleton.find_bone(name)
	return id if id>=0 else _skeleton.find_bone(name+"_2")
func configure(carrier: Node3D,model: Node3D,player: AnimationPlayer,skeleton: Skeleton3D,profile: Dictionary,tank_origin: Vector3=Vector3.ZERO) -> Dictionary:
	_support_rows.clear();_support_contract={};_support_gain=0.
	var configured: Dictionary=super.configure(carrier,model,player,skeleton,profile,tank_origin)
	if not configured.get("ok",false):return configured
	assert(profile.species=="arapaima" and profile.has("basal_support"))
	_support_contract=profile.basal_support
	assert(FileAccess.get_sha256(_support_contract.base_runtime)==_support_contract.base_runtime_sha256,"Stale parent motion dependency")
	assert(_skeleton.get_bone_count()==int(_support_contract.actual_bone_count))
	var meshes:=model.find_children("*","MeshInstance3D",true,false);var body: MeshInstance3D
	for mesh in meshes:
		if str(mesh.name)=="Closed_body":body=mesh;break
	assert(body!=null and body.skin!=null)
	var binds: Dictionary={}
	for i in body.skin.get_bind_count():
		var bone:=body.skin.get_bind_bone(i)
		if bone<0:bone=_skeleton.find_bone(str(body.skin.get_bind_name(i)))
		assert(bone>=0);binds[bone]=body.skin.get_bind_pose(i)
	for item in _support_contract.bindings:
		var driver:=_bone(str(item.driver));var aux:=_bone(str(item.aux));var parent:=_bone(str(item.body_parent));assert(driver>=0 and aux>=0 and parent>=0 and binds.has(parent))
		assert(_skeleton.get_bone_parent(driver)==parent and _skeleton.get_bone_parent(aux)==parent)
		assert(_skeleton.get_bone_rest(driver).is_equal_approx(_skeleton.get_bone_rest(aux)))
		var sign_side: float=1. if str(item.fin).ends_with("_left") else -1.
		var tv: Array=_support_contract.left_translation_gltf_native;var rv: Array=_support_contract.left_rotation_gltf_radians;var hv: Array=item.head_gltf_native
		_support_rows.append({"driver":driver,"aux":aux,"parent":parent,"bind":binds[parent],"head":Vector3(hv[0],hv[1],hv[2]),"translation":Vector3(tv[0],tv[1],tv[2]*sign_side),"rotation":Vector3(rv[0]*sign_side,rv[1]*sign_side,rv[2])})
	assert(_support_rows.size()==6)
	_apply_support();configured["basal_support_bones"]=6;configured["total_bones"]=_skeleton.get_bone_count();return configured
func _capture_base_and_pose() -> void:
	super._capture_base_and_pose()
	_apply_support()
func _apply_support() -> void:
	if _support_rows.is_empty():return
	_support_gain=clampf((float(_motion.fin_amplitude)-float(_support_contract.gain_start))/(float(_support_contract.gain_end)-float(_support_contract.gain_start)),0.,1.)
	_skeleton.force_update_all_bone_transforms()
	for item in _support_rows:
		if _support_gain==0.:
			_skeleton.set_bone_pose_position(item.aux,_skeleton.get_bone_pose_position(item.driver))
			_skeleton.set_bone_pose_rotation(item.aux,_skeleton.get_bone_pose_rotation(item.driver))
			_skeleton.set_bone_pose_scale(item.aux,_skeleton.get_bone_pose_scale(item.driver))
			continue
		var rotvec: Vector3=item.rotation;var rotation:=Basis(Quaternion(rotvec.normalized(),rotvec.length()*_support_gain));var head: Vector3=item.head
		var source_support:=Transform3D(rotation,head-rotation*head+Vector3(item.translation)*_support_gain)
		var body_frame: Transform3D=_skeleton.get_bone_global_pose(item.parent)*Transform3D(item.bind)
		var target: Transform3D=body_frame*source_support*body_frame.affine_inverse()*_skeleton.get_bone_global_pose(item.driver)
		_skeleton.set_bone_global_pose(item.aux,target)
	_skeleton.force_update_all_bone_transforms()
func snapshot() -> Dictionary:
	var result: Dictionary=super.snapshot()
	result["basal_support"]={"gain":_support_gain,"support_bones":_support_rows.size(),"runtime_body_geometry_queries":0,"mesh_array_changes":0}
	return result
