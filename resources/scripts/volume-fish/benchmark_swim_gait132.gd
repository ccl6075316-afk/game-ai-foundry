extends "trial_swim_gait132.gd"
## Supplemental CPU update microbenchmark; excludes draw, load, and QA snapshots.
## Run with same arguments as trial, using mode qa; does not modify the trial.

func _qa() -> void:
    var baseline := _spawn(Vector3.ZERO)
    var candidate := _spawn(Vector3.ZERO)
    var wrapper = _make_gait(candidate)
    for k in 60:
        baseline.controller.step(1.0 / 60.0)
        wrapper.step(1.0 / 60.0)
    baseline.controller.set_action("Swim", true)
    baseline.controller.step(0.0)
    wrapper.restart()
    var actions := ["Swim", "Turn", "Ascend", "Dive", "Swim"]
    var results := {}
    for label in ["baseline", "candidate"]:
        var started := Time.get_ticks_usec()
        for frame in 1200:
            if frame % 240 == 0:
                if label == "baseline": baseline.controller.set_action(actions[frame / 240])
                else: wrapper.set_action(actions[frame / 240])
            if label == "baseline": baseline.controller.step(1.0 / 60.0)
            else: wrapper.step(1.0 / 60.0)
        var micros := Time.get_ticks_usec() - started
        results[label] = {"wall_simulated_seconds":20,"updates_presented":1200,"controller_substeps":1200 if label == "baseline" else wrapper.substeps,"total_update_cpu_ms":micros / 1000.0,"mean_presented_update_cpu_ms":micros / 1200000.0}
    var inputs := _inputs()
    inputs["benchmark"] = FileAccess.get_sha256(get_script().resource_path)
    _save("benchmark.validation.json", {"ok":true,"command":"fish.swim-gait132.cpu-microbenchmark","status":"done","next_action":"human_review","inputs":inputs,"summary":results,"scope":"Single headless host run, one fish per loop, actual imported production skeleton. After 1-second warmup. Excludes asset loading, snapshots, GPU rendering and behaviors. Trial uses120Hz fixed stepping plus retained steering; baseline60Hz. Not a shipping performance budget or FPS benchmark."})
    print("GAIT132_CPU_MICROBENCHMARK ", JSON.stringify(results))
    factory.free()
    quit()
