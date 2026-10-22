extends "capture_trial.gd"
##107 eye layer followed by109's separately verified LOD exception.
func _write_eye_capture_receipt(expected: int):
    var model: Node3D=hall._selected().model
    var eye: Dictionary=model.get_meta("eye_ownership_107_receipt",{})
    var lod: Dictionary=model.get_meta("eye_lod_107_receipt",{})
    var valid: bool=not eye.is_empty() and not lod.is_empty() and not baseline_reference
    var file=FileAccess.open(out+"/eye-capture.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"schema_version":1,"ok":valid,"command":"fish.eye109-capture",
        "status":"done" if eye_shots==expected else "running","next_action":"human_review" if eye_shots==expected else "poll",
        "inputs":{"eye_mode":eye_trial_mode,"eye_probe":eye_trial_probe},
        "summary":{"images":eye_shots,"expected_images":expected,"eye_install_before_lod_exception":eye,
        "lod_install_receipt":lod,"all_original_lods_retained":false,"originalLOD5":"failed and excluded",
        "capture_script_sha256":FileAccess.get_sha256(get_script().resource_path)},"failures":[]},"  "))
    file.close()
