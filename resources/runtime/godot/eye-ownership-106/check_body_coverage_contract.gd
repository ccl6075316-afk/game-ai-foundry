extends SceneTree
var failures:Array[String]=[]
func check(condition:bool,label:String):
 if not condition:failures.append(label)
func _initialize():
 var validator=load(get_script().resource_path.get_base_dir().path_join("../../../scripts/volume-fish/capture_body_coverage.gd").simplify_path())
 var model=load("res://assets/models/fish/black_seabream.glb").instantiate()
 load("res://scripts/aquarium/FishSurfaceOwnership.gd").new().apply(model,"black_seabream")
 var mesh:MeshInstance3D=model.find_child("Closed_body",true,false)
 var material:ShaderMaterial=mesh.get_active_material(0)
 var eye:Dictionary=model.get_meta("eye_ownership_106_receipt").duplicate(true)
 var lod:Dictionary=model.get_meta("eye_lod_106_receipt").duplicate(true)
 check(eye.has("generated_shader_sha256"),"real helper generated-code receipt present")
 var simulated:bool=false
 var good:Dictionary=validator.validate_dynamic_106_shader(model,"black_seabream",mesh,0,material)
 check(good.ok,"valid106 shader authorized")
 model.remove_meta("eye_ownership_106_receipt");check(not validator.validate_dynamic_106_shader(model,"black_seabream",mesh,0,material).ok,"missing eye receipt rejected");model.set_meta("eye_ownership_106_receipt",eye)
 model.remove_meta("eye_lod_106_receipt");check(not validator.validate_dynamic_106_shader(model,"black_seabream",mesh,0,material).ok,"missing LOD receipt rejected");model.set_meta("eye_lod_106_receipt",lod)
 for key in ["model_sha256","helper_sha256","template_sha256","profile_sha256","generated_shader_sha256"]:
  var stale=eye.duplicate(true);stale[key]="0".repeat(64);model.set_meta("eye_ownership_106_receipt",stale)
  check(not validator.validate_dynamic_106_shader(model,"black_seabream",mesh,0,material).ok,"stale "+key+" rejected")
 model.set_meta("eye_ownership_106_receipt",eye)
 check(not validator.validate_dynamic_106_shader(model,"carp",mesh,0,material).ok,"other species rejected")
 check(not validator.validate_dynamic_106_shader(model,"black_seabream",mesh,1,material).ok,"other surface rejected")
 for statement in ["ALPHA=0.5;","ALPHA_SCISSOR_THRESHOLD=0.5;","float ALPHA_FUTURE=0.0;","discard;"]:
  var altered:ShaderMaterial=material.duplicate();var shader:=Shader.new();shader.code=material.shader.code.replace("void fragment() {","void fragment() {\n"+statement);altered.shader=shader
  mesh.set_surface_override_material(0,altered)
  var forged=eye.duplicate(true);forged.generated_shader_sha256=shader.code.sha256_text();model.set_meta("eye_ownership_106_receipt",forged)
  var result:Dictionary=validator.validate_dynamic_106_shader(model,"black_seabream",mesh,0,altered)
  check(not result.ok and str(result.get("reason","")).contains("Forbidden coverage token"),"forged code hash cannot authorize "+statement)
  mesh.set_surface_override_material(0,material)
 model.set_meta("eye_ownership_106_receipt",eye)
 var altered:ShaderMaterial=material.duplicate();var shader:=Shader.new();shader.code=material.shader.code+"\n// harmless code change";altered.shader=shader;mesh.set_surface_override_material(0,altered)
 check(not validator.validate_dynamic_106_shader(model,"black_seabream",mesh,0,altered).ok,"code mutation without updated generated hash rejected")
 var comment_receipt=eye.duplicate(true);comment_receipt.generated_shader_sha256=shader.code.sha256_text();model.set_meta("eye_ownership_106_receipt",comment_receipt)
 shader.code=material.shader.code+"\n// ALPHA ALPHA_SCISSOR_THRESHOLD discard\n/* ALPHA_CUSTOM discard */";comment_receipt.generated_shader_sha256=shader.code.sha256_text();model.set_meta("eye_ownership_106_receipt",comment_receipt)
 check(validator.validate_dynamic_106_shader(model,"black_seabream",mesh,0,altered).ok,"coverage names inside comments ignored")
 shader.code=material.shader.code.replace("uniform vec2 eye_lookup_size;", "uniform vec2  eye_lookup_size;");comment_receipt.generated_shader_sha256=shader.code.sha256_text();model.set_meta("eye_ownership_106_receipt",comment_receipt)
 check(not validator.validate_dynamic_106_shader(model,"black_seabream",mesh,0,altered).ok,"incomplete current template rejected even with generated hash")
 mesh.set_surface_override_material(0,material);model.set_meta("eye_ownership_106_receipt",eye)
 var report={"schema_version":1,"ok":failures.is_empty(),"command":"fish.body-coverage106-auth-contract","stage":"validate","status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","inputs":{},"outputs":["/tmp/fish106-body-gate-check.validation.json"],"summary":{"simulated_generated_metadata_before_candidate_sync":simulated,"positive_authorization":good,"negative_checks":15,"frozen_shader_sampling_changed":false},"failures":[]}
 for message in failures:report.failures.append({"kind":"validation","code":"body106_contract_failed","message":message})
 var file=FileAccess.open("/tmp/fish106-body-gate-check.validation.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
 model.free();print("106_BODY_GATE_CONTRACT ","PASS" if failures.is_empty() else "FAIL",failures);quit(0 if failures.is_empty() else 1)
