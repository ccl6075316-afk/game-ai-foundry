## Opt-in actual-pose surface merge. Base scheduling/selection/limits unchanged.
extends "export_fin_poses.gd"
const MERGE_BASE = preload("export_fin_poses.gd")
const MERGE_BASE_SHA := "0dffe432a891ca54447c6138954c05c5ed0a6b5ab1bb9760e808fdac53ccaa99"
var merged_inventory: Dictionary = {}
var declared_merge_inventory: Dictionary = {}
var merge_inventory_ready := false
var source_surface_inventory: Dictionary = {}

func _assert_merge_base() -> bool:
	var matches: bool=FileAccess.get_sha256((MERGE_BASE as Script).resource_path)==MERGE_BASE_SHA
	if not matches:push_error("Merged exporter base changed; review opt-in adapter")
	return matches

func _initialize() -> void:
	if not _assert_merge_base():quit(1);return
	super._initialize()

func actual_surface_inventory(entry: Dictionary) -> Dictionary:
	var result: Dictionary={}
	for surface in surfaces:
		var name: String=surface.name
		if not result.has(name):result[name]={"surface_count":0,"vertices":0,"triangles":0,"root_vertex_count":0,"root_edge_count":0,"surfaces":[]}
		var row: Dictionary=result[name]
		row.surface_count+=1;row.vertices+=surface.vertices.size();row.triangles+=surface.triangles.size()/3
		row.root_vertex_count+=surface.ids.size();row.root_edge_count+=surface.edges.size()
		var skin_names: Array=[]
		for bone in surface.bindings:skin_names.append(str(entry.skeleton.get_bone_name(bone)))
		row.surfaces.append({"mesh_path":str(entry.model.get_path_to(surface.mesh)),"vertices":surface.vertices.size(),"triangles":surface.triangles.size()/3,"root_vertex_count":surface.ids.size(),"root_edge_count":surface.edges.size(),"skin_bindings":skin_names})
	return result

func independent_source_inventory(entry: Dictionary,spec: Dictionary) -> Dictionary:
	# Read the logical source independently, not from potentially partial
	# `surfaces` left behind when a base prepare assertion returns early.
	var logical: Dictionary=PACKED_PARTS.surfaces(entry,spec) if spec.get("packed_parts_manifest","")!="" else {"ok":true,"surfaces":PACKED_PARTS.ordinary_surfaces(entry)}
	if not logical.get("ok",false):return {"ok":false,"failure":"Original logical surface helper rejected input","parts":{}}
	var planned: Dictionary={str(spec.body):true}
	for name in spec.fins:planned[str(name)]=true
	var parts: Dictionary={}
	for source in logical.surfaces:
		var name: String=source.name
		for token in ["Dorsal","Anal","Caudal","Pectoral","Pelvic","Tail_Fin","Adipose"]:
			if token in name and not spec.fins.has(name):return {"ok":false,"failure":"Original logical source contains an omitted fin: "+name,"parts":parts}
		if not planned.has(name):continue
		var vertex_count: int=source.arrays[Mesh.ARRAY_VERTEX].size();var index_count: int=source.arrays[Mesh.ARRAY_INDEX].size()
		if vertex_count<=0 or index_count<=0 or index_count%3!=0:return {"ok":false,"failure":"Empty/invalid original logical surface: "+name,"parts":parts}
		if not parts.has(name):parts[name]={"surface_count":0,"vertices":0,"triangles":0,"surfaces":[]}
		var row: Dictionary=parts[name];row.surface_count+=1;row.vertices+=vertex_count;row.triangles+=index_count/3
		row.surfaces.append({"mesh_path":str(entry.model.get_path_to(source.mesh)),"source_surface":source.get("source_surface",-1),"vertices":vertex_count,"triangles":index_count/3})
	if parts.size()!=planned.size():return {"ok":false,"failure":"Original logical source misses a planned body/fin","parts":parts}
	for name in planned:
		if not parts.has(name):return {"ok":false,"failure":"Original logical source misses planned part: "+name,"parts":parts}
	return {"ok":true,"parts":parts}

func prepared_inventory_matches_source(source: Dictionary,actual: Dictionary,spec: Dictionary) -> bool:
	if not source.get("ok",false) or not source.get("parts") is Dictionary:return false
	var expected: Dictionary=source.parts
	if expected.size()!=actual.size() or expected.size()!=spec.fins.size()+1:return false
	for name in expected:
		if not actual.has(name):return false
		for field in ["surface_count","vertices","triangles"]:
			if expected[name][field]!=actual[name][field]:return false
		var raw_rows: Array=expected[name].surfaces;var ready_rows: Array=actual[name].surfaces
		if raw_rows.size()!=ready_rows.size():return false
		for i in raw_rows.size():
			for field in ["mesh_path","vertices","triangles"]:
				if raw_rows[i][field]!=ready_rows[i][field]:return false
	for surface in surfaces:
		if not surface.body and (not spec.fins.has(surface.name) or surface.ids.is_empty()):return false
	return true

func validate_prepared_inventory(entry: Dictionary,spec: Dictionary) -> bool:
	merge_inventory_ready=false
	source_surface_inventory=independent_source_inventory(entry,spec)
	merged_inventory=actual_surface_inventory(entry)
	declared_merge_inventory=spec.get("surface_merge_inventory",{})
	merge_inventory_ready=prepared_inventory_matches_source(source_surface_inventory,merged_inventory,spec) and merge_inventory_matches(declared_merge_inventory,merged_inventory,spec.model_sha256)
	return merge_inventory_ready

func merge_inventory_matches(expected: Dictionary, actual: Dictionary, model_sha: String) -> bool:
	if expected.get("model_sha256","")!=model_sha or not expected.get("parts") is Dictionary:return false
	var parts: Dictionary=expected.parts
	if parts.size()!=actual.size():return false
	for name in actual:
		if not parts.has(name) or not parts[name] is Dictionary:return false
		for field in ["surface_count","triangles"]:
			if not parts[name].has(field) or not (parts[name][field] is int or parts[name][field] is float):return false
			if not is_finite(float(parts[name][field])) or float(parts[name][field])!=float(actual[name][field]):return false
		for field in ["vertices","root_vertex_count","root_edge_count"]:
			if parts[name].has(field):
				if not (parts[name][field] is int or parts[name][field] is float):return false
				if not is_finite(float(parts[name][field])) or float(parts[name][field])!=float(actual[name][field]):return false
	return true

func prepare(entry: Dictionary, spec: Dictionary) -> void:
	merge_inventory_ready=false
	if not _assert_merge_base():quit(1);return
	if FileAccess.get_sha256(spec.model)!=spec.model_sha256:push_error("Wrong merged-export candidate");quit(1);return
	source_surface_inventory=independent_source_inventory(entry,spec)
	if not source_surface_inventory.ok:
		super.save_json(out.path_join("surface-inventory.actual.json"),{"kind":"actual_prepared_fin_surface_inventory","ok":false,"model_sha256":spec.model_sha256,"independent_original_logical_inventory":source_surface_inventory,"prepared_matches_original_source":false})
		push_error(str(source_surface_inventory.failure));quit(1);return
	super.prepare(entry,spec)
	validate_prepared_inventory(entry,spec)
	# Missing/wrong declaration emits a small read-only preflight inventory,
	# then fails before the first sample or any expensive pose schedule.
	super.save_json(out.path_join("surface-inventory.actual.json"),{"kind":"actual_prepared_fin_surface_inventory","model":spec.model,"model_sha256":spec.model_sha256,"base_exporter_sha256":MERGE_BASE_SHA,"parts":merged_inventory,"independent_original_logical_inventory":source_surface_inventory,"prepared_matches_original_source":prepared_inventory_matches_source(source_surface_inventory,merged_inventory,spec),"scope":"Prepared body+fin pieces independently checked against all original logical source surfaces; every prepared fin surface must have roots. Caller partial declarations cannot mask partial preparation."})
	if not merge_inventory_ready:push_error("Missing/wrong complete surface_merge_inventory; see surface-inventory.actual.json");quit(1);return

func save_json(path: String,value: Variant) -> void:
	if path.ends_with("export.validation.json"):
		if not merge_inventory_ready:value["ok"]=false;value["failures"]=["Complete model-bound surface inventory was not validated; no pose samples allowed"]
		value["merged_surface_revision"]=1
		value["merged_surface_inventory"]=merged_inventory
		value["declared_surface_merge_inventory"]=declared_merge_inventory
		value["independent_original_logical_inventory"]=source_surface_inventory
		value["base_exporter_sha256"]=MERGE_BASE_SHA
		value["merge_scope"]="Each surface uses its own actual skin bindings and pose transform first; only world-metre coordinates/indices/root samples are concatenated. Native bindings are never merged."
	super.save_json(path,value)

func sample(entry: Dictionary,label: String,seconds: float) -> void:
	if not merge_inventory_ready:return
	if not _assert_merge_base():merge_inventory_ready=false;quit(1);return
	if variant=="diagnostic" and label!="Static" and not (label in ["Native","Range:WideFast","Clearance:Independent"] and is_equal_approx(seconds,3.75)):return
	if variant=="envelope":
		var selected := label=="Static"
		for row in plan.items[0].get("diagnostic_pose_filter",[]):
			if row.action==label and is_equal_approx(float(row.seconds),seconds):selected=true
		if not selected:return
	var s: Skeleton3D=entry.skeleton;s.force_update_all_bone_transforms()
	var relative: Transform3D=entry.carrier.global_transform.affine_inverse()*s.global_transform
	var body: Array=[];var roots: Dictionary={};var membranes: Dictionary={}
	for surface in surfaces:
		# This is deliberately inside the per-surface loop. Different native
		# meshes/skins may bind the same logical fin in different spaces.
		var transforms: Array[Transform3D]=[]
		for j in surface.bindings.size():transforms.append(relative*s.get_bone_global_pose(surface.bindings[j])*surface.mesh.skin.get_bind_pose(j))
		var coords: Array[Vector3]=[]
		for i in surface.vertices.size():
			var point=Vector3.ZERO
			for j in surface.count:
				var at: int=i*int(surface.count)+j
				point+=(transforms[surface.joints[at]]*surface.vertices[i])*surface.weights[at]
			coords.append(point)
		if surface.body:
			for p in coords:body.append([p.x,p.y,p.z])
			continue
		var name: String=surface.name
		if export_membranes:
			if not membranes.has(name):membranes[name]={"vertices_m":[],"triangles":[]}
			var membrane: Dictionary=membranes[name];var vertex_offset: int=membrane.vertices_m.size()
			for p in coords:membrane.vertices_m.append([p.x,p.y,p.z])
			for index in surface.triangles:membrane.triangles.append(int(index)+vertex_offset)
			var axis:=Vector3(surface.outward_axis[0],surface.outward_axis[1],surface.outward_axis[2])
			if axis.length_squared()>0:
				if not membrane.has("outward_gain_m_per_native_unit"):membrane["outward_gain_m_per_native_unit"]=[];membrane["rest_vertices_native"]=[]
				for vi in surface.vertices.size():
					var gain:=Vector3.ZERO
					for slot in surface.count:
						var at: int=vi*int(surface.count)+slot
						gain+=(transforms[surface.joints[at]].basis*axis)*surface.weights[at]
					membrane.outward_gain_m_per_native_unit.append([gain.x,gain.y,gain.z]);var v: Vector3=surface.vertices[vi];membrane.rest_vertices_native.append([v.x,v.y,v.z])
		if not roots.has(name):roots[name]={"vertex_count":0,"edge_count":0,"points_m":[]}
		var root_row: Dictionary=roots[name];root_row.vertex_count+=surface.ids.size();root_row.edge_count+=surface.edges.size()
		for i in surface.ids:
			var p: Vector3=coords[i];root_row.points_m.append([p.x,p.y,p.z])
		for edge in surface.edges:
			for k in [1,2,3,4,5,6,7]:
				var p: Vector3=coords[edge[0]].lerp(coords[edge[1]],float(k)/8.);root_row.points_m.append([p.x,p.y,p.z])
	for name in merged_inventory:
		if not roots.has(name):continue # body inventory
		assert(roots[name].vertex_count==merged_inventory[name].root_vertex_count and roots[name].edge_count==merged_inventory[name].root_edge_count,"Incomplete merged root samples")
		if export_membranes:
			assert(membranes[name].vertices_m.size()==merged_inventory[name].vertices and membranes[name].triangles.size()==int(merged_inventory[name].triangles)*3,"Incomplete merged membrane")
	var filename=out+"/sample-%03d.json"%samples.size();var data={"body_vertices_m":body,"body_triangles":faces,"roots":roots}
	if export_membranes:data["membranes"]=membranes
	save_json(filename,data);samples.append({"action":label,"seconds":seconds,"posed_mesh_json":filename,"sha256":FileAccess.get_sha256(filename)})
