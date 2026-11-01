extends "export_fin_poses.gd"
## Compact actual-pose diagnostic. This is NOT a177/490 completion receipt.
var rest_written:=false
func save_json(path: String,value: Variant) -> void:
	if path.ends_with("export.validation.json"):
		value["kind"]="compact_actual_fin_skin_diagnostic"
		value["diagnostic_only"]=true
		value["formal_acceptance"]=false
		value["sample_limit"]="Actual unchanged pose schedule, compact rest skin and joint matrices; specialized validators have not run on this format."
	super.save_json(path,value)
func sample(entry: Dictionary,label: String,seconds: float) -> void:
	var skeleton: Skeleton3D=entry.skeleton
	skeleton.force_update_all_bone_transforms()
	var relative: Transform3D=entry.carrier.global_transform.affine_inverse()*skeleton.global_transform
	var first: Dictionary=surfaces[0]
	for surface in surfaces:
		assert(surface.bindings==first.bindings and surface.mesh.skin==first.mesh.skin,"Compact diagnostic requires one actually shared packed skin")
	if not rest_written:
		var rows: Array=[]
		for surface in surfaces:
			var points: Array=[]
			for p in surface.vertices:points.append([p.x,p.y,p.z])
			rows.append({"name":surface.name,"body":surface.body,"vertices_native":points,"joints":Array(surface.joints),"weights":Array(surface.weights),"triangles":Array(surface.triangles),"root_ids":surface.ids,"root_edges":surface.edges})
		var joint_names: Array=[]
		for binding in first.bindings:joint_names.append(str(skeleton.get_bone_name(binding)))
		save_json(out.path_join("rest-skin.json"),{"surfaces":rows,"joint_names":joint_names,"model_sha256":FileAccess.get_sha256(plan.items[0].model),"diagnostic_only":true})
		rest_written=true
	var matrices: Array=[]
	for j in first.bindings.size():
		var t: Transform3D=relative*skeleton.get_bone_global_pose(first.bindings[j])*first.mesh.skin.get_bind_pose(j)
		matrices.append([[t.basis.x.x,t.basis.y.x,t.basis.z.x,t.origin.x],[t.basis.x.y,t.basis.y.y,t.basis.z.y,t.origin.y],[t.basis.x.z,t.basis.y.z,t.basis.z.z,t.origin.z]])
	var filename:=out.path_join("matrices-%03d.json"%samples.size())
	save_json(filename,{"action":label,"seconds":seconds,"joint_matrices_m_per_native":matrices})
	samples.append({"action":label,"seconds":seconds,"posed_mesh_json":filename,"sha256":FileAccess.get_sha256(filename)})
