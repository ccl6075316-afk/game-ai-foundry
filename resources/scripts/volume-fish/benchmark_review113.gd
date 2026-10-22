extends SceneTree
## Compare identical actual controllers; does not modify runtime assets.
func _initialize() -> void:
    call_deferred("run")
func run() -> void:
    var hall = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    root.add_child(hall)
    hall.set_process(false)
    hall.paused = false
    hall._select_display("black_seabream")
    var iterations := 180
    var trials: Array = []
    for trial in 5:
        var t := Time.get_ticks_usec()
        for i in iterations:hall._process(1.0/60.0)
        var all_us := Time.get_ticks_usec()-t
        var entry: Dictionary=hall._selected()
        t = Time.get_ticks_usec()
        for i in iterations:entry.controller.step(1.0/60.0)
        trials.append({"all_fish_usec_per_frame":float(all_us)/iterations,"selected_controller_usec_per_frame":float(Time.get_ticks_usec()-t)/iterations})
    var report := {"schema_version":1,"command":"fish.review113.cpu-benchmark","ok":true,"status":"done","next_action":"human_review","fish_count":hall.fish.size(),"iterations_each":iterations,"trials":trials,"exhibit_sha256":FileAccess.get_sha256("res://scripts/aquarium/VolumeFishExhibit.gd"),"limitations":"CPU controller work only; no inference about GPU bottleneck or visual quality."}
    var file := FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE)
    file.store_string(JSON.stringify(report,"  ")+"\n")
    print("CPU_BENCHMARK "+JSON.stringify(report))
    quit()
