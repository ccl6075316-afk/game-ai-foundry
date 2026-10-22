extends SceneTree
var failures:Array[String]=[]
func check(condition:bool,label:String):
 if not condition:failures.append(label)
func _initialize():
 var validator=load(get_script().resource_path.get_base_dir().path_join("capture_body_coverage.gd").simplify_path())
 var model=load("res://assets/models/fish/zander.glb").instantiate()
 load("res://scripts/aquarium/FishSurfaceOwnership.gd").new().apply(model,"zander")
 var mesh:MeshInstance3D=model.find_child("Closed_body",true,false)
 var material:ShaderMaterial=mesh.get_active_material(0)
 var eye:Dictionary=model.get_meta("eye_ownership_107_receipt").duplicate(true)
 check(eye.has("generated_shader_sha256"),"real helper generated-code receipt present")
 var simulated:bool=false
 var good:Dictionary=validator.validate_dynamic_107_shader(model,"zander",mesh,0,material)
 check(good.ok,"valid107 shader authorized")
 model.remove_meta("eye_ownership_107_receipt");check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,material).ok,"missing eye receipt rejected");model.set_meta("eye_ownership_107_receipt",eye)
 for key in ["model_sha256","helper_sha256","template_sha256","profile_sha256","generated_shader_sha256","original_shader_file_sha256","head_include_sha256","head_profile_sha256","fallback_texture_sha256","clean_source_sha256"]:
  var stale=eye.duplicate(true);stale[key]="0".repeat(64);model.set_meta("eye_ownership_107_receipt",stale)
  check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,material).ok,"stale "+key+" rejected")
 model.set_meta("eye_ownership_107_receipt",eye)
 check(not validator.validate_dynamic_107_shader(model,"carp",mesh,0,material).ok,"other species rejected")
 check(not validator.validate_dynamic_107_shader(model,"zander",mesh,1,material).ok,"other surface rejected")
 for statement in ["ALPHA=0.5;","ALPHA_SCISSOR_THRESHOLD=0.5;","float ALPHA_FUTURE=0.0;","discard;"]:
  var altered:ShaderMaterial=material.duplicate();var shader:=Shader.new();shader.code=material.shader.code.replace("void fragment() {","void fragment() {\n"+statement);altered.shader=shader
  mesh.set_surface_override_material(0,altered)
  var forged=eye.duplicate(true);forged.generated_shader_sha256=shader.code.sha256_text();model.set_meta("eye_ownership_107_receipt",forged)
  var result:Dictionary=validator.validate_dynamic_107_shader(model,"zander",mesh,0,altered)
  check(not result.ok and str(result.get("reason","")).contains("Forbidden coverage token"),"forged code hash cannot authorize "+statement)
  mesh.set_surface_override_material(0,material)
 model.set_meta("eye_ownership_107_receipt",eye)
 var altered:ShaderMaterial=material.duplicate();var shader:=Shader.new();shader.code=material.shader.code+"\n// harmless code change";altered.shader=shader;mesh.set_surface_override_material(0,altered)
 check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,altered).ok,"code mutation without updated generated hash rejected")
 var comment_receipt=eye.duplicate(true);comment_receipt.generated_shader_sha256=shader.code.sha256_text();model.set_meta("eye_ownership_107_receipt",comment_receipt)
 shader.code=material.shader.code+"\n// ALPHA ALPHA_SCISSOR_THRESHOLD discard\n/* ALPHA_CUSTOM discard */";comment_receipt.generated_shader_sha256=shader.code.sha256_text();model.set_meta("eye_ownership_107_receipt",comment_receipt)
 check(validator.validate_dynamic_107_shader(model,"zander",mesh,0,altered).ok,"coverage names inside comments ignored")
 shader.code=material.shader.code.replace("uniform vec2 eye_lookup_size;", "uniform vec2  eye_lookup_size;");comment_receipt.generated_shader_sha256=shader.code.sha256_text();model.set_meta("eye_ownership_107_receipt",comment_receipt)
 check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,altered).ok,"incomplete current template rejected even with generated hash")
 mesh.set_surface_override_material(0,material);model.set_meta("eye_ownership_107_receipt",eye)
 # Actual donor mutations cannot be authorized by a valid-looking shader receipt.
 var original_opaque:Texture2D=material.get_shader_parameter("opaque_skin")
 var changed_image:Image=original_opaque.get_image().duplicate()
 changed_image.convert(Image.FORMAT_RGBA8)
 var pixel:Color=changed_image.get_pixel(0,0);pixel.a=0.;changed_image.set_pixel(0,0,pixel)
 material.set_shader_parameter("opaque_skin",ImageTexture.create_from_image(changed_image))
 check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,material).ok,"actual opaqueRGBA mutation rejected")
 material.set_shader_parameter("opaque_skin",original_opaque)
 var original_mode=material.get_shader_parameter("eye_mode")
 material.set_shader_parameter("eye_mode",0 if original_mode!=0 else 1)
 check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,material).ok,"active mode mutation rejected")
 material.set_shader_parameter("eye_mode",original_mode)
 check(not validator.validate_dynamic_body_shader(model,"unknown_fish",mesh,0,material).ok,"unknown dynamic species rejected by dispatcher")
 var lod:Dictionary=model.get_meta("eye_lod_107_receipt",{}).duplicate(true)
 if not lod.is_empty():
  model.remove_meta("eye_lod_107_receipt")
  check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,material).ok,"runtime LOD copy requires separate receipt")
  for key in ["helper_sha256","config_sha256","model_sha256","actual_after_raw_surfaces_sha256","expected_after_raw_surfaces_sha256","runtime_lods_sha256"]:
   var stale=lod.duplicate(true);stale[key]="0".repeat(64);model.set_meta("eye_lod_107_receipt",stale)
   check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,material).ok,"stale109 LOD "+key+" rejected")
  for key in ["source_mesh_resource_id","runtime_mesh_resource_id"]:
   var stale=lod.duplicate(true);stale[key]=0;model.set_meta("eye_lod_107_receipt",stale)
   check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,material).ok,"wrong109 LOD "+key+" rejected")
  var stale=lod.duplicate(true);stale.retired_lod.index=4;model.set_meta("eye_lod_107_receipt",stale)
  check(not validator.validate_dynamic_107_shader(model,"zander",mesh,0,material).ok,"wrong109 retired level rejected")
  model.set_meta("eye_lod_107_receipt",lod)
 var output:String="/tmp/fish107-body-gate-check.validation.json"
 for argument in OS.get_cmdline_user_args():
  if argument.begins_with("--output="):output=argument.trim_prefix("--output=")
 var report={"schema_version":1,"ok":failures.is_empty(),"command":"fish.body-coverage107-auth-contract","stage":"validate","status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","inputs":{},"outputs":["/tmp/fish107-body-gate-check.validation.json"],"summary":{"simulated_generated_metadata_before_candidate_sync":simulated,"positive_authorization":good,"negative_checks":22,"frozen_shader_sampling_changed":false},"failures":[]}
 for message in failures:report.failures.append({"kind":"validation","code":"body107_contract_failed","message":message})
 report.outputs=[output]
 report.summary["post_eye_lod_exception_negative_checks"]=10 if not lod.is_empty() else 0
 var file=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
 model.free();print("107_BODY_GATE_CONTRACT ","PASS" if failures.is_empty() else "FAIL",failures);quit(0 if failures.is_empty() else 1)
