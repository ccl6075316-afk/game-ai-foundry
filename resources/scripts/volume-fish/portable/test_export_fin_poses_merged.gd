## Small real Godot skin/surface fixtures; never loads or changes a fish asset.
extends "export_fin_poses_merged.gd"
const ORIGINAL = preload("export_fin_poses.gd")
var test_out: String
var checks: Array=[]

func _initialize() -> void:
	_assert_merge_base()
	var args:=OS.get_cmdline_user_args();assert(args.size()==1)
	test_out=args[0].simplify_path();assert(test_out.is_absolute_path() and test_out.contains("/output/"))
	DirAccess.make_dir_recursive_absolute(test_out);call_deferred("test_run")

func fixture_surface(model: Node3D,name: String,bone: int,bind: Transform3D,x_offset: float) -> Dictionary:
	var node:=MeshInstance3D.new();node.name=name;model.add_child(node)
	node.skin=Skin.new();node.skin.add_bind(bone,bind)
	var vertex:=PackedVector3Array([Vector3(x_offset,0,0),Vector3(x_offset+.1,0,0),Vector3(x_offset,.1,0)])
	var index:=PackedInt32Array([0,1,2]);var joints:=PackedInt32Array([0,0,0,0,0,0,0,0,0,0,0,0]);var weights:=PackedFloat32Array([1,0,0,0,1,0,0,0,1,0,0,0])
	var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=vertex;arrays[Mesh.ARRAY_INDEX]=index;arrays[Mesh.ARRAY_BONES]=joints;arrays[Mesh.ARRAY_WEIGHTS]=weights
	var mesh:=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);node.mesh=mesh
	return {"name":name,"body":false,"mesh":node,"vertices":vertex,"joints":joints,"weights":weights,"triangles":index,"bindings":[bone],"count":4,"ids":[0,1],"edges":[[0,1]],"outward_axis":[0,0,1]}

func set_fixture(rows: Array,entry: Dictionary,folder: String) -> void:
	surfaces=rows;faces=[[0,1,2]];samples=[];variant="full-fin";export_membranes=true;plan={"items":[{}]};out=test_out.path_join(folder);DirAccess.make_dir_recursive_absolute(out)
	merged_inventory=actual_surface_inventory(entry)
	merge_inventory_ready=true # Direct-method fixture only; real prepare tested below.

func test_run() -> void:
	var carrier:=Node3D.new();root.add_child(carrier);carrier.position=Vector3(.3,.2,-.1)
	var model:=Node3D.new();carrier.add_child(model)
	var skeleton:=Skeleton3D.new();model.add_child(skeleton)
	skeleton.add_bone("body");skeleton.add_bone("fin")
	skeleton.set_bone_rest(0,Transform3D.IDENTITY);skeleton.set_bone_rest(1,Transform3D(Basis.IDENTITY,Vector3(.1,0,0)))
	skeleton.set_bone_pose_position(0,Vector3(.01,.02,.03));skeleton.set_bone_pose_rotation(1,Quaternion(Vector3.UP,.4));skeleton.force_update_all_bone_transforms()
	var entry={"model":model,"carrier":carrier,"skeleton":skeleton}
	var body=fixture_surface(model,"Body",0,Transform3D.IDENTITY,-.4);body.body=true;body.ids=[];body.edges=[]
	var first=fixture_surface(model,"Fin",0,Transform3D.IDENTITY,.2)
	var one=[body,first];set_fixture(one,entry,"single-new")
	var original=ORIGINAL.new();original.surfaces=one;original.faces=faces;original.samples=[];original.variant=variant;original.export_membranes=true;original.plan=plan;original.out=test_out.path_join("single-old");DirAccess.make_dir_recursive_absolute(original.out)
	original.sample(entry,"Static",0.);sample(entry,"Static",0.)
	var before: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(original.out.path_join("sample-000.json")));var after: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(out.path_join("sample-000.json")))
	assert(before==after,"Single surface must preserve every numeric value/key/index/root sample")
	checks.append({"name":"single_surface_every_field_exact","ok":true,"old_sample_sha256":FileAccess.get_sha256(original.out.path_join("sample-000.json")),"new_sample_sha256":FileAccess.get_sha256(out.path_join("sample-000.json"))})
	# Same logical Fin but a different mesh, bone binding and inverse bind space.
	var native_b:=Node3D.new();native_b.name="DifferentNativeSpace";model.add_child(native_b)
	var second=fixture_surface(native_b,"Fin",1,Transform3D(Basis.from_euler(Vector3(.1,.2,.3)),Vector3(-.2,.05,.1)),.5)
	set_fixture([body,first,second],entry,"multi-new");sample(entry,"Native",.25)
	var actual: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(out.path_join("sample-000.json")));var membrane: Dictionary=actual.membranes.Fin
	assert(membrane.vertices_m.size()==6 and membrane.triangles.size()==6)
	for i in 6:assert(int(membrane.triangles[i])==i)
	assert(actual.roots.Fin.vertex_count==4 and actual.roots.Fin.edge_count==2 and actual.roots.Fin.points_m.size()==18)
	assert(membrane.outward_gain_m_per_native_unit.size()==6 and membrane.rest_vertices_native.size()==6)
	var relative: Transform3D=carrier.global_transform.affine_inverse()*skeleton.global_transform
	var expected_b: Transform3D=relative*skeleton.get_bone_global_pose(1)*second.mesh.skin.get_bind_pose(0)
	for i in 3:
		var p: Vector3=expected_b*second.vertices[i];var q: Array=membrane.vertices_m[i+3];assert(p.distance_to(Vector3(q[0],q[1],q[2]))<.0000001)
		var gain: Vector3=expected_b.basis*Vector3(0,0,1);var actual_gain: Array=membrane.outward_gain_m_per_native_unit[i+3];assert(gain.distance_to(Vector3(actual_gain[0],actual_gain[1],actual_gain[2]))<.0000001)
		var rest: Vector3=second.vertices[i];var actual_rest: Array=membrane.rest_vertices_native[i+3];assert(rest.distance_to(Vector3(actual_rest[0],actual_rest[1],actual_rest[2]))<.0000001)
	for i in 2:
		var expected_root: Vector3=expected_b*second.vertices[i];var actual_root: Array=actual.roots.Fin.points_m[i+9];assert(expected_root.distance_to(Vector3(actual_root[0],actual_root[1],actual_root[2]))<.0000001)
	assert(membrane.vertices_m.slice(0,3)!=membrane.vertices_m.slice(3,6),"Native spaces were incorrectly merged before skinning")
	checks.append({"name":"multi_surface_all_geometry_roots_gain_rest_and_native_spaces","ok":true,"inventory":merged_inventory})
	var declaration={"model_sha256":"fixture-sha","parts":{"Body":{"surface_count":1,"triangles":1},"Fin":{"surface_count":2,"triangles":2}}}
	assert(merge_inventory_matches(declaration,merged_inventory,"fixture-sha"));var wrong: Dictionary=declaration.duplicate(true);wrong.parts.Fin.surface_count=1
	assert(not merge_inventory_matches(wrong,merged_inventory,"fixture-sha"));wrong=declaration.duplicate(true);wrong.parts.Fin.triangles=1;assert(not merge_inventory_matches(wrong,merged_inventory,"fixture-sha"));wrong=declaration.duplicate(true);wrong.parts.erase("Body");assert(not merge_inventory_matches(wrong,merged_inventory,"fixture-sha"));wrong=declaration.duplicate(true);wrong.model_sha256="wrong";assert(not merge_inventory_matches(wrong,merged_inventory,"fixture-sha"))
	wrong=declaration.duplicate(true);wrong.parts.Fin.surface_count=2.5;assert(not merge_inventory_matches(wrong,merged_inventory,"fixture-sha"))
	checks.append({"name":"wrong_surface_triangle_missing_part_and_model_inventory_rejected","ok":true})
	# Exercise inherited actual preparation as well as direct sample fixtures.
	var token:=test_out.path_join("fixture-identity.json");FileAccess.open(token,FileAccess.WRITE).store_string('{"fixture":"actual memory skin arrays; no fish asset"}')
	var model_sha: String=FileAccess.get_sha256(token);declaration.model_sha256=model_sha
	var basal: Array=[]
	for row in [first,second]:
		var rest_transform: Transform3D=skeleton.global_transform*skeleton.get_bone_global_rest(row.bindings[0])*row.mesh.skin.get_bind_pose(0)
		for i in [0,1]:
			var p: Vector3=rest_transform*row.vertices[i];basal.append([p.x,p.y,p.z])
	var spec={"species":"memory_fixture","model":token,"model_sha256":model_sha,"body":"Body","length_native":1.,"fins":{"Fin":{"rest_points_gltf":basal,"diagnostic_outward_axis":[0,0,1]}},"surface_merge_inventory":declaration}
	out=test_out.path_join("prepared");DirAccess.make_dir_recursive_absolute(out);prepare(entry,spec)
	assert(merged_inventory.Fin.surface_count==2 and merged_inventory.Fin.triangles==2 and merged_inventory.Fin.root_vertex_count==4)
	checks.append({"name":"real_inherited_prepare_complete_surface_and_root_inventory","ok":true,"inventory":merged_inventory})
	# Base prepare may return after an assertion. Its caller must not accept
	# a matching partial declaration as proof of original source completeness.
	var negative=load((MERGE_BASE as Script).resource_path.get_base_dir().path_join("export_fin_poses_merged.gd")).new()
	negative.faces=faces;negative.samples=[];negative.variant=variant;negative.export_membranes=true;negative.plan=plan
	negative.out=test_out.path_join("negative-missing-planned-fin");DirAccess.make_dir_recursive_absolute(negative.out)
	var missing_spec: Dictionary=spec.duplicate(true);missing_spec.fins["MissingFin"]={"rest_points_gltf":basal}
	negative.prepare(entry,missing_spec) # actual original source has no MissingFin
	negative.sample(entry,"Static",0.);negative.save_json(negative.out.path_join("export.validation.json"),{"ok":true,"samples":negative.samples})
	var missing_receipt: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(negative.out.path_join("export.validation.json")))
	assert(not negative.merge_inventory_ready and negative.samples.is_empty() and not missing_receipt.ok and not FileAccess.file_exists(negative.out.path_join("sample-000.json")))
	checks.append({"name":"missing_planned_fin_original_inventory_blocks_samples_and_receipt","ok":true,"actual_export_ok":missing_receipt.ok,"samples":negative.samples.size()})
	negative.out=test_out.path_join("negative-partial-same-name");DirAccess.make_dir_recursive_absolute(negative.out)
	negative.surfaces=[body,first] # simulate super.prepare early return before same-name second surface
	var partial_spec: Dictionary=spec.duplicate(true);partial_spec.surface_merge_inventory.parts.Fin={"surface_count":1,"vertices":3,"triangles":1}
	assert(negative.merge_inventory_matches(partial_spec.surface_merge_inventory,negative.actual_surface_inventory(entry),model_sha),"Control declaration must really match the partial prepared result")
	assert(not negative.validate_prepared_inventory(entry,partial_spec),"Original two-surface source must defeat caller's partial declaration")
	negative.sample(entry,"Static",0.);negative.save_json(negative.out.path_join("export.validation.json"),{"ok":true,"samples":negative.samples})
	var partial_receipt: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(negative.out.path_join("export.validation.json")))
	assert(not negative.merge_inventory_ready and negative.samples.is_empty() and not partial_receipt.ok and not FileAccess.file_exists(negative.out.path_join("sample-000.json")))
	checks.append({"name":"omitted_same_name_second_surface_even_partial_declaration_blocks_samples","ok":true,"actual_export_ok":partial_receipt.ok,"samples":negative.samples.size(),"original_surface_count":negative.source_surface_inventory.parts.Fin.surface_count,"partial_surface_count":negative.merged_inventory.Fin.surface_count})
	var report={"ok":true,"kind":"opt_in_merged_fin_exporter_small_runtime_fixture_validation","base_sha256":MERGE_BASE_SHA,"sidecar_sha256":FileAccess.get_sha256((MERGE_BASE as Script).resource_path.get_base_dir().path_join("export_fin_poses_merged.gd")),"test_sha256":FileAccess.get_sha256(get_script().resource_path),"checks":checks,"scope":"Actual Godot Skeleton3D/Skin/ArrayMesh sample methods in small in-memory fixtures. No fish asset loaded/edited and no production pose gate implied."}
	FileAccess.open(test_out.path_join("validation.json"),FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n");print("MERGED_SURFACE_FIXTURES_OK ",checks.size());negative.free();original.free();quit()
