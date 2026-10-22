extends SceneTree
## Actual project load/selection probe; does not change production assets.
var report: String
func _initialize() -> void:
    report = OS.get_cmdline_user_args()[0]
    call_deferred("run")
func run() -> void:
    var started := Time.get_ticks_msec()
    var hall = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(hall)
    hall.paused = true
    hall.set_process(false)
    var items: Array = []
    for species in hall.SPECIES:
        hall._select_display(species)
        var entry: Dictionary = hall._selected()
        var item := {"species":species,"present":not entry.is_empty()}
        if not entry.is_empty():
            item["visible"] = entry.carrier.is_visible_in_tree()
            item["mesh_count"] = entry.model.find_children("*","MeshInstance3D",true,false).size()
            item["controller"] = entry.controller.get_script().resource_path
        items.append(item)
    var result := {"schema_version":1,"command":"fish.review113.load-probe","ok":items.size()==23,"status":"done","next_action":"human_review","load_msec":Time.get_ticks_msec()-started,"items":items,"failures":[]}
    for item in items:
        if not item.present:
            result.ok = false
            result.failures.append({"kind":"validation","code":"missing_species","message":item.species})
    if not result.ok: result.status = "failed"
    DirAccess.make_dir_recursive_absolute(report.get_base_dir())
    var file := FileAccess.open(report,FileAccess.WRITE)
    file.store_string(JSON.stringify(result,"  ")+"\n")
    print("REVIEW113_PROBE "+JSON.stringify(result))
    quit(0 if result.ok else 1)
