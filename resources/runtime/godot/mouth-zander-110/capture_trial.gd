extends "../../../scripts/volume-fish/capture_surface_mouth_audit.gd"
## Same 47-view Hall/region/camera capture as102; explicit107 mode control.
var eye_trial_mode: int = -1
var eye_shots: int = 0
var eye_trial_probe: int = 0
var eye_retired_probe: int = 0
var baseline_reference: bool = false

func _initialize():
    var args := OS.get_cmdline_user_args()
    if args.is_empty():
        push_error("Usage: <output> --eye-mode=0|1|2 [zander]")
        quit(1)
        return
    out = args[0]
    for index in range(1, args.size()):
        if args[index].begins_with("--eye-mode="):
            var value: String = args[index].trim_prefix("--eye-mode=")
            if value not in ["0", "1", "2"]:
                push_error("107 capture permits exactly --eye-mode=0,1,2")
                quit(1)
                return
            eye_trial_mode = int(value)
        elif args[index].begins_with("--eye-probe="):
            var value: String = args[index].trim_prefix("--eye-probe=")
            if value not in ["0","1","2","3"]:
                push_error("Invalid --eye-probe, requires0/1/2/3")
                quit(1)
                return
            eye_trial_probe = int(value)
        elif args[index] == "--baseline-reference":
            baseline_reference = true
        elif args[index].begins_with("--retired-probe="):
            var value: String = args[index].trim_prefix("--retired-probe=")
            if value not in ["0","1","2","3"]:
                push_error("Invalid retirement probe")
                quit(1)
                return
            eye_retired_probe=int(value)
        else:
            requested.append(args[index])
    if eye_trial_mode not in [0,1,2]:
        push_error("Explicit --eye-mode=0|1|2 is required")
        quit(1)
        return
    if requested.is_empty(): requested = ["zander"]
    if eye_trial_probe != 0 and eye_trial_mode != 2:
        push_error("Nonzero RGB probe is allowed only in mode2")
        quit(1)
        return
    if eye_retired_probe != 0 and (eye_trial_mode != 2 or eye_trial_probe != 0):
        push_error("Retirement-only probe requires mode2/globalprobe0")
        quit(1)
        return
    if baseline_reference and (eye_trial_mode != 0 or eye_trial_probe != 0 or eye_retired_probe != 0):
        push_error("Baseline reference requires mode0 and both probes0")
        quit(1)
        return
    if requested != ["zander"]:
        push_error("107 capture is frozen to zander only")
        quit(1)
        return
    OS.set_environment("FISH_EYE_MODE", str(eye_trial_mode))
    OS.set_environment("FISH_EYE_PROBE",str(eye_trial_probe))
    OS.set_environment("FISH_EYE_RETIRED_PROBE",str(eye_retired_probe))
    call_deferred("run")

func set_mode(entry: Dictionary, stored: Array, mode: String):
    super.set_mode(entry, stored, mode)
    for item in stored:
        var active: Material = item[0].get_active_material(item[1])
        if active is ShaderMaterial and active.shader.code.contains("eye_reference_rest"):
            active.set_shader_parameter("eye_mode", eye_trial_mode)
            active.set_shader_parameter("eye_probe", eye_trial_probe)
            active.set_shader_parameter("eye_retired_probe",eye_retired_probe)

func shot(path: String):
    await super.shot(path)
    eye_shots += 1
    _write_eye_capture_receipt(47)

func _write_eye_capture_receipt(expected: int):
    var receipt: Dictionary = hall._selected().model.get_meta("eye_ownership_107_receipt", {})
    var valid: bool = receipt.is_empty() if baseline_reference else (not receipt.is_empty() and receipt.get("all_original_lods_retained",false) and receipt.get("lod_geometry_gate",{}).get("status","")=="pending")
    var file := FileAccess.open(out + "/eye-capture.validation.json", FileAccess.WRITE)
    file.store_string(JSON.stringify({"schema_version":1, "ok":valid, "command":"fish.eye-ownership107-capture",
        "stage":"validate", "status":"done" if eye_shots == expected else "running", "next_action":"human_review" if eye_shots == expected else "poll",
        "inputs":{"eye_mode":eye_trial_mode,"eye_probe":eye_trial_probe,"retired_probe":eye_retired_probe,"baseline_reference":baseline_reference}, "outputs":[], "summary":{"images":eye_shots, "expected_images":expected,
        "mode1_implemented":true, "install_receipt":receipt,"baseline_reference":baseline_reference, "capture_script_sha256":FileAccess.get_sha256(get_script().resource_path),
        "scope":"Explicit mode0/2 actual47-view capture. All6 originalLOD retained; LOD5 gate failed. CPU install does not accept GPU lookup or morphology."}, "failures":[]}, "  "))
    file.close()

# Same native camera envelope for before/after; never refit the mouth ROI.
func region(entry:Dictionary)->Dictionary:
    var body=AABB(Vector3(-.367,-.098616,-.043),Vector3(.863,.181437,.086))
    var head=AABB(Vector3(.326552,-.081284,-.032345),Vector3(.169447,.134129,.064689))
    var ext:Vector3=head.size*entry.model.global_transform.basis.get_scale()
    return {"body":body,"head":head,"extent_m":maxf(ext.x,maxf(ext.y,ext.z))}
