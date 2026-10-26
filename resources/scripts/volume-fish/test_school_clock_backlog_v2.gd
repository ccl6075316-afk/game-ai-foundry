extends "test_school_motion_v2.gd"
## Bounded catch-up must retain, then consume, all supplied time after a stall.
func run() -> void:
    output = ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2/backlog-before-clock").simplify_path()
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--test-output="): output = arg.trim_prefix("--test-output=")
    var allowed := ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2").simplify_path()+"/"
    if not output.is_absolute_path() or output != output.simplify_path() or not output.begins_with(allowed) or DirAccess.make_dir_recursive_absolute(output) != OK:
        push_error("Use absolute backlog output beneath fish-school-motion-v2"); quit(2); return
    var ctx := await context()
    var viewer = ctx.viewer
    viewer.mode = "school-full"
    var sources: Dictionary = viewer._bindings()
    var initial := {}
    for entry in viewer.entries:
        initial[entry.species] = {"controller":entry.controller._time,"body":entry.controller._body_clock,"fin":entry.controller._fin_clock}
    var max_consumed_per_frame := 0.0
    var first_consumed := 0.0
    for frame in 61:
        var previous: float = viewer.elapsed
        viewer._process(0.5 if frame == 0 else 1.0/120.0)
        var consumed: float = viewer.elapsed-previous
        max_consumed_per_frame = maxf(max_consumed_per_frame,consumed)
        if frame == 0: first_consumed = consumed
    var species := {}
    var phase_preserved := true
    for entry in viewer.entries:
        var clip: float = entry.profile.actions.Swim.clip_speed
        var body_frequency: float = entry.controller._motion.body_frequency
        var fin_frequency: float = entry.controller._motion.fin_frequency
        var actual := {"controller":entry.controller._time-initial[entry.species].controller,"body":entry.controller._body_clock-initial[entry.species].body,"fin":entry.controller._fin_clock-initial[entry.species].fin,"observed":entry.school_motion.snapshot().observed_seconds}
        var expected := {"controller":1.0,"body":clip*body_frequency,"fin":clip*fin_frequency,"observed":1.0}
        for key in expected: phase_preserved = phase_preserved and absf(actual[key]-expected[key]) < 0.0001
        species[entry.species] = {"actual_clock_delta":actual,"expected_clock_delta":expected}
    var after: Dictionary = viewer._bindings()
    var checks := [{"check":"bounded_to_eight_60Hz_ticks_per_frame","passed":max_consumed_per_frame <= 8.0/60.0+0.00001},{"check":"stall_backlog_preserved_and_drained","passed":absf(viewer.elapsed-1.0)<0.0001},{"check":"native_and_observation_phases_preserved","passed":phase_preserved},{"check":"source_bindings_unchanged","passed":sources==after}]
    var passed := not setup_failed
    for check in checks: passed = passed and check.passed
    var report := {"schema_version":1,"command":"fish.school.clock-backlog-regression","stage":"validate","ok":passed,"status":"done" if passed else "failed","next_action":"human_review" if passed else "fix_input","inputs":{"test_sha256":FileAccess.get_sha256(get_script().resource_path),"base_regression_sha256":FileAccess.get_sha256(get_script().resource_path.get_base_dir().path_join("test_school_motion_v2.gd")),"source_binding_count":sources.size(),"source_bindings_before_sha256":JSON.stringify(sources).sha256_text(),"source_bindings_after_sha256":JSON.stringify(after).sha256_text(),"stall_seconds":0.5,"subsequent_frames":60,"subsequent_delta_seconds":1.0/120.0},"summary":{"checks":checks,"supplied_seconds":1.0,"consumed_seconds":viewer.elapsed,"first_frame_consumed_seconds":first_consumed,"max_frame_consumed_seconds":max_consumed_per_frame,"species":species},"scope":"Actual two-fish population; fixed-input timing/backlog regression only, no render or model/animation acceptance","outputs":[output.path_join("backlog.validation.json")],"failures":[]}
    if not passed: report.failures.append({"kind":"validation","code":"clock_backlog_regression_failed","message":"Supplied time was lost or phase/catch-up bound failed"})
    await release(ctx)
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    for frame in 3: await process_frame
    var file := FileAccess.open(output.path_join("backlog.validation.json"),FileAccess.WRITE)
    if file == null: push_error("Cannot save backlog report"); quit(2); return
    file.store_string(JSON.stringify(report,"  ")+"\n");file.close()
    print("SCHOOL_CLOCK_BACKLOG ",JSON.stringify({"ok":passed,"summary":report.summary}))
    quit(0 if passed else 1)
