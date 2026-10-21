extends "../../../scripts/volume-fish/capture_surface_mouth_audit.gd"
## Same 47-view Hall/region/camera capture as102; explicit106 mode control.
var eye_trial_mode: int = -1
var eye_shots: int = 0
var eye_trial_probe: int = 0
var lod_only_reference: bool = false

func _initialize():
    var args := OS.get_cmdline_user_args()
    if args.is_empty():
        push_error("Usage: <output> --eye-mode=0|1|2 [black_seabream]")
        quit(1)
        return
    out = args[0]
    for index in range(1, args.size()):
        if args[index].begins_with("--eye-mode="):
            var value: String = args[index].trim_prefix("--eye-mode=")
            if value not in ["0", "1", "2"]:
                push_error("106 capture permits exactly --eye-mode=0,1,2")
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
        elif args[index] == "--lod-only-reference":
            lod_only_reference = true
        else:
            requested.append(args[index])
    if eye_trial_mode not in [0,1,2]:
        push_error("Explicit --eye-mode=0|1|2 is required")
        quit(1)
        return
    if requested.is_empty(): requested = ["black_seabream"]
    if eye_trial_probe != 0 and eye_trial_mode != 2:
        push_error("Nonzero RGB probe is allowed only in mode2")
        quit(1)
        return
    if lod_only_reference and (eye_trial_mode != 0 or eye_trial_probe != 0):
        push_error("LOD-only reference permits mode0 only")
        quit(1)
        return
    if requested != ["black_seabream"]:
        push_error("106 capture is frozen to black_seabream only")
        quit(1)
        return
    OS.set_environment("FISH_EYE_MODE", str(eye_trial_mode))
    OS.set_environment("FISH_EYE_PROBE",str(eye_trial_probe))
    call_deferred("run")

func set_mode(entry: Dictionary, stored: Array, mode: String):
    super.set_mode(entry, stored, mode)
    for item in stored:
        var active: Material = item[0].get_active_material(item[1])
        if active is ShaderMaterial and active.shader.code.contains("eye_reference_rest"):
            active.set_shader_parameter("eye_mode", eye_trial_mode)
            active.set_shader_parameter("eye_probe", eye_trial_probe)
        if lod_only_reference and active is ShaderMaterial and active.shader.code.contains("feature_rest_normal"):
            active.set_shader_parameter("feature_mode", 0)

func shot(path: String):
    await super.shot(path)
    eye_shots += 1
    _write_eye_capture_receipt(47)

func _write_eye_capture_receipt(expected: int):
    var receipt: Dictionary = hall._selected().model.get_meta("eye_ownership_106_receipt", {})
    var lod: Dictionary = hall._selected().model.get_meta("eye_lod_106_receipt", {})
    var valid := not lod.is_empty() and (receipt.is_empty() if lod_only_reference else not receipt.is_empty())
    var file := FileAccess.open(out + "/eye-capture.validation.json", FileAccess.WRITE)
    file.store_string(JSON.stringify({"schema_version":1, "ok":valid, "command":"fish.eye-ownership106-capture",
        "stage":"validate", "status":"done" if eye_shots == expected else "running", "next_action":"human_review" if eye_shots == expected else "poll",
        "inputs":{"eye_mode":eye_trial_mode,"eye_probe":eye_trial_probe,"lod_only_reference":lod_only_reference}, "outputs":[], "summary":{"images":eye_shots, "expected_images":expected,
        "mode1_implemented":not lod_only_reference, "install_receipt":receipt, "lod_install_receipt":lod, "capture_script_sha256":FileAccess.get_sha256(get_script().resource_path),
        "scope":"Explicit mode0/2 actual47-view capture. CPU install does not accept GPU lookup or morphology."}, "failures":[]}, "  "))
    file.close()
