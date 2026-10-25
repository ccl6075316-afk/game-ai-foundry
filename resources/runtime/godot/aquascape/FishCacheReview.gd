extends SceneTree
func _initialize() -> void:
    call_deferred("_run")
func _run() -> void:
    var output := ""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--report="):output=arg.trim_prefix("--report=")
    assert(not output.is_empty())
    var cache=load("res://scripts/aquarium/FishAppearanceCache.gd")
    cache.begin_entry();var original: String=cache._generation
    var key := "FISH_EYE_RETIRED_PROBE";var existed := OS.has_environment(key);var before := OS.get_environment(key)
    OS.set_environment(key,"991")
    cache.begin_entry()
    var changed: bool=cache._generation!=original
    if existed:OS.set_environment(key,before)
    else:OS.unset_environment(key)
    cache.begin_entry()
    var restored: bool=cache._generation==original
    var report := {"schema_version":1,"ok":changed and restored,"status":"done" if changed and restored else "failed","next_action":"human_review" if changed and restored else "fix_input","checks":{"review_eye_probe_invalidates_appearance":changed,"restored_review_mode_restores_generation":restored},"failures":[]}
    var file := FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    quit(0 if report.ok else 1)
