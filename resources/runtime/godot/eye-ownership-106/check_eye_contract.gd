extends SceneTree
## Real candidate install checks plus grammar/mode rejection; no GPU acceptance.
class QuietHelper:
    extends "FishEyeOwnership.gd"
    func _fail(message: String) -> int:
        last_error = message
        return 0

var failures: Array[String] = []
func check(condition: bool, label: String):
    if not condition: failures.append(label)

func _initialize():
    var rows: Array = []
    for mode in [0,1,2]:
        OS.set_environment("FISH_EYE_MODE", str(mode))
        OS.set_environment("FISH_EYE_PROBE","0")
        var model = load("res://assets/models/fish/black_seabream.glb").instantiate()
        var changed: Dictionary = load("res://scripts/aquarium/FishSurfaceOwnership.gd").new().apply(model, "black_seabream")
        var receipt: Dictionary = model.get_meta("eye_ownership_106_receipt", {})
        check(changed.get("eye_ownership_surfaces", 0) == 1 and not receipt.is_empty(), "mode%d actual candidate installation" % mode)
        if not receipt.is_empty():
            check(receipt.mesh_before == receipt.mesh_after and receipt.mesh_unchanged, "mode%d all mesh arrays/LOD/binding preserved" % mode)
            check(receipt.mode == mode and receipt.source_base_level_all_rgba_equal, "mode%d source identity" % mode)
            rows.append(receipt)
        model.free()
    for probe in [1,2,3]:
        OS.set_environment("FISH_EYE_MODE","2")
        OS.set_environment("FISH_EYE_PROBE",str(probe))
        var model = load("res://assets/models/fish/black_seabream.glb").instantiate()
        var changed: Dictionary = load("res://scripts/aquarium/FishSurfaceOwnership.gd").new().apply(model,"black_seabream")
        var receipt: Dictionary = model.get_meta("eye_ownership_106_receipt",{})
        check(changed.get("eye_ownership_surfaces",0)==1 and receipt.get("probe",-1)==probe,"mode2 RGBprobe%d installation" % probe)
        if not receipt.is_empty(): rows.append(receipt)
        model.free()
    var helper := QuietHelper.new()
    check(helper.apply(null,"black_seabream",3)==0 and helper.last_error.contains("Invalid mode"),"mode3 refused")
    check(helper.apply(null,"black_seabream",1,helper.DEFAULT_CONFIG,1)==0 and helper.last_error.contains("only in mode2"),"probe outside mode2 refused")
    check(helper.apply(null, "black_seabream", 0) == 0 and helper.last_error.contains("Missing instantiated"), "null model refused")
    var samplers := "uniform sampler2D source_texture:source_color,filter_nearest,repeat_disable;uniform sampler2D opaque_skin:source_color,filter_nearest,repeat_disable;"
    var calls := "texture(source_texture,uv);texture(opaque_skin,uv);"
    for expression in ["texelFetch(source_texture,ivec2(0),0);", "textureLod(opaque_skin,uv,0.);", "arbitrary(source_texture);"]:
        helper.last_error = ""
        check(helper._wrap_samples(samplers + calls + expression).is_empty() and not helper.last_error.is_empty(), "unsupported sampler rejected: " + expression)
    var misleading := "// uniform sampler2D source_texture:source_color,filter_nearest,repeat_disable;\nuniform sampler2D source_texture:source_color,filter_linear,repeat_disable;"
    check(not helper._sampler_is_native_nearest(misleading, "source_texture"), "commented nearest cannot hide linear sampler")
    var output := "/tmp/fish106-install.validation.json"
    for argument in OS.get_cmdline_user_args():
        if argument.begins_with("--output="): output = argument.trim_prefix("--output=")
    var result := {"schema_version":1, "ok":failures.is_empty(), "command":"fish.eye-ownership106-install-check", "stage":"implement",
        "status":"done" if failures.is_empty() else "failed", "next_action":"human_review" if failures.is_empty() else "fix_input",
        "inputs":{}, "outputs":[output], "summary":{"modes_checked":[0,1,2], "mode2_probes_checked":[1,2,3], "non_mode2_probe_rejected":true, "receipts":rows, "gpu_validation":"pending"}, "failures":[]}
    for message in failures: result.failures.append({"kind":"validation", "code":"eye_contract_failed", "message":message})
    var file := FileAccess.open(output, FileAccess.WRITE)
    if file == null:
        push_error("Cannot write install-check report")
        quit(1)
        return
    file.store_string(JSON.stringify(result, "  "))
    file.close()
    print("106_CONTRACT_CHECK ", "PASS" if failures.is_empty() else "FAIL")
    quit(0 if failures.is_empty() else 1)
