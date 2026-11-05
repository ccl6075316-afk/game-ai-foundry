extends SceneTree
var context: Dictionary
var report: Dictionary={"kind":"fish_final_asset_cold_load","ok":false,"fresh_process":true,"static_builders_disabled":true,"runtime_static_build_calls":0,"errors":[],"checks":{},"actual_checks":[]}
func ck(value: bool,label: String) -> void:
 report.actual_checks.append({"ok":value,"check":label})
 if not value:report.errors.append(label)
func digest(model: Node3D) -> String:
 var value: Array=[]
 for mesh in model.find_children("*","MeshInstance3D",true,false):
  for s in mesh.mesh.get_surface_count():
   var material=mesh.get_active_material(s)
   value.append([str(mesh.name),s,mesh.mesh.surface_get_arrays(s),material.get_instance_id(),material.albedo_color,material.transparency,material.texture_filter,material.albedo_texture.get_image().get_data() if material.albedo_texture else PackedByteArray()])
 return var_to_bytes(value).hex_encode().sha256_text()
func _initialize() -> void:
 create_timer(25).timeout.connect(func():quit(2))
 call_deferred("run")
func run() -> void:
 var args=OS.get_cmdline_user_args();context=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var c: Dictionary=context.candidate_files;var bound: Dictionary={}
 for role in c:
  ck(FileAccess.get_sha256(c[role].path)==c[role].sha256,"Fresh candidate role "+role);bound[role]=c[role].sha256
 report.species=context.species;report.bound_inputs=bound;report.entry_role="model";report.context_sha256=FileAccess.get_sha256(args[0])
 var document=GLTFDocument.new();var state=GLTFState.new();ck(document.append_from_file(c.model.path,state)==OK,"Independent GLTFDocument append");var model=document.generate_scene(state);ck(model!=null,"Independent full model generated");var carrier=Node3D.new();root.add_child(carrier);carrier.add_child(model);model.scale=Vector3.ONE*float(context.model_scale)
 var names: Array=[];var triangles=0;var materials: Array=[]
 for mesh in model.find_children("*","MeshInstance3D",true,false):
  names.append(str(mesh.name))
  for s in mesh.mesh.get_surface_count():
   var arrays=mesh.mesh.surface_get_arrays(s);triangles+=arrays[Mesh.ARRAY_INDEX].size()/3;var material=mesh.get_active_material(s)as StandardMaterial3D;ck(material!=null,"Actual StandardMaterial "+str(mesh.name)+str(s));ck(material.albedo_texture==null or material.texture_filter==BaseMaterial3D.TEXTURE_FILTER_NEAREST,"Actual nearest donor "+str(mesh.name)+str(s));materials.append({"mesh":str(mesh.name),"surface":s,"material":material.resource_name,"texture":material.albedo_texture!=null,"alpha_mode":material.transparency})
 ck(triangles==int(context.triangles),"Actual complete triangle budget");var expected_names: Array=context.fins.duplicate();expected_names.append(context.body);expected_names.append_array(context.decorative_overlays);expected_names.sort();var actual_names: Array=names.duplicate();actual_names.sort();ck(actual_names==expected_names,"Exact ordinary body/fin/overlay inventory")
 for name in context.fins:ck(name in names,"Complete fin "+name)
 for name in context.decorative_overlays:ck(name in names,"Complete decorative overlay "+name)
 var skeletons=model.find_children("*","Skeleton3D",true,false);var players=model.find_children("*","AnimationPlayer",true,false);ck(skeletons.size()==1 and players.size()==1,"One actual rig/player");var skeleton=skeletons[0];var player=players[0];var before=digest(model);var profile=JSON.parse_string(FileAccess.get_file_as_string(c.motion_config.path));var controller=load(c.motion_controller.path).new();var configured=controller.configure(carrier,model,player,skeleton,profile);ck(configured.ok,"Actual reviewed controller configured");var actions: Array=[]
 for action in ["Swim","Turn","Ascend","Dive"]:
  ck(controller.set_action(action,true),"Actual action accepted "+action);controller.step(.25);controller.seek(.375);var snapshot=controller.snapshot();ck(snapshot.inside_envelope and snapshot.action==action,"Actual action executed "+action);actions.append(snapshot)
 ck(digest(model)==before,"Configure and actions preserve actual geometry/UV/skin/material resources")
 var exported=JSON.parse_string(FileAccess.get_file_as_string(c.source_export_report.path));ck(exported.ok and exported.source_sha256==c.editable_blend.sha256 and exported.output_sha256==c.model.sha256,"Exact fresh editable-source export binding")
 report.actual_mesh_inventory=names;report.actual_triangles=triangles;report.actual_materials=materials;report.actions=actions;report.static_arrays_uv_material_digest=before;report.direct_GLTFDocument=true;report.checks={"independent_load":model!=null,"materials_complete":materials.size()>0,"rig_and_motion":configured.ok and actions.size()==4,"export_matches_candidate":exported.output_sha256==c.model.sha256};report.ok=report.errors.is_empty();FileAccess.open(args[1],FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n");print("FINAL_COLD ",report.ok," checks=",report.actual_checks.size());quit(0 if report.ok else 1)
