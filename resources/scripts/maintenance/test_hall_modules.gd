extends SceneTree
## Native contract checks independent of rendering or player saves.
const History=preload("res://scripts/aquarium/hall/HallEditHistory.gd")
const Rules=preload("res://scripts/aquarium/hall/HallLayoutRules.gd")
const Store=preload("res://scripts/aquarium/hall/HallLayoutStore.gd")
var checks: Dictionary={}

func _same(a: Variant,b: Variant) -> bool:
    if (a is int or a is float) and (b is int or b is float):return absf(float(a)-float(b))<.000001
    if a is Dictionary and b is Dictionary:
        if a.size()!=b.size():return false
        for key in a:
            if not b.has(key) or not _same(a[key],b[key]):return false
        return true
    if a is Array and b is Array:
        if a.size()!=b.size():return false
        for i in a.size():
            if not _same(a[i],b[i]):return false
        return true
    return a==b

func _initialize() -> void:
    var directory := ""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--maintenance-dir="):directory=arg.trim_prefix("--maintenance-dir=")
    if directory.is_empty():quit(2);return
    DirAccess.make_dir_recursive_absolute(directory)
    var history=History.new()
    var state := {"nested":{"value":0}}
    history.remember(state);state.nested.value=99
    checks.snapshot_is_deep_copy=history.undo(state).nested.value==0
    checks.redo_preserves_current=history.redo({"nested":{"value":0}}).nested.value==99
    history.undo(state);history.remember(state)
    checks.edit_invalidates_redo=history.future.is_empty()
    for i in 25:history.remember({"n":i})
    checks.history_bounded=history.past.size()==20 and history.past.front().n==5
    history.past.clear();history.future.clear()
    checks.empty_history_no_transition=history.undo(state)==null and history.redo(state)==null
    var rules=Rules.new()
    var legacy := {"schema_version":1,"floor_style":0,"wall_style":0,"objects":[]}
    checks.legacy_schema_valid=rules._valid_state(legacy)
    var current := legacy.duplicate(true);current.schema_version=2;current.parcels=rules.Footprint.initial()
    checks.current_schema_valid=rules._valid_state(current)
    checks.save_round_trip=Store.write_layout(directory+"/layout.json",current,rules) and _same(Store.read_layout(directory+"/layout.json",rules),current)
    var before := FileAccess.get_file_as_string(directory+"/layout.json")
    current.floor_style=NAN
    checks.invalid_save_preserves_destination=not Store.write_layout(directory+"/layout.json",current,rules) and FileAccess.get_file_as_string(directory+"/layout.json")==before
    checks.load_missing_no_state=Store.read_layout(directory+"/missing.json",rules)==null
    var file=FileAccess.open(directory+"/bad.json",FileAccess.WRITE);file.store_string("[]");file.close()
    checks.load_invalid_no_state=Store.read_layout(directory+"/bad.json",rules)==null
    var okay := not checks.values().has(false)
    file=FileAccess.open(directory+"/modules.validation.json",FileAccess.WRITE)
    file.store_string(JSON.stringify({"ok":okay,"checks":checks},"  "));file.close()
    print("HALL_MODULES ",okay," ",checks.size());quit(0 if okay else 1)
