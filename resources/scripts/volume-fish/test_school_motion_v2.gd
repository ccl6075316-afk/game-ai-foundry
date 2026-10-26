extends SceneTree
## Phase3 regressions. Exercises unchanged public viewer flow with actual fish.
const SPECIES := ["atlantic_sailfish", "whale_shark"]
var output := ""
var binding_viewer
var before: Dictionary = {}
var checks: Array = []
var steering_cases: Array = []
var clock_cases: Array = []
var setup_failed := false

func _initialize() -> void: call_deferred("run")

func run() -> void:
    output = ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2/regression-baseline").simplify_path()
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--test-output="): output = arg.trim_prefix("--test-output=")
    var allowed := ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2").simplify_path() + "/"
    if not output.is_absolute_path() or output != output.simplify_path() or not output.begins_with(allowed) or DirAccess.make_dir_recursive_absolute(output) != OK:
        push_error("Use absolute --test-output beneath fish-school-motion-v2")
        quit(2); return
    binding_viewer = load("res://scripts/aquarium/fish_school/FishSchoolReview.gd").new()
    before = binding_viewer._bindings()
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    for rate in [0.0, 0.35, -0.35]:
        steering_cases.append(await steering(rate))
        await process_frame
    for species in SPECIES:
        var neutral: float = steering_cases[0].means[species]
        var positive: float = steering_cases[1].means[species] - neutral
        var negative: float = steering_cases[2].means[species] - neutral
        checks.append({"test":"A_actual_route_drives_body_steering","species":species,"passed":positive < -0.002 and negative > 0.002,"positive_turn_response_rad":positive,"negative_turn_response_rad":negative,"assertion":"Subtract straight trajectory at equal phase; +carrier yaw must add negative local body yaw, and inverse turn positive; each magnitude>0.002rad summed joints. Wiring regression, not biological amplitude acceptance."})
    for delta in [1.0/60.0, 1.0/15.0, 0.1]:
        clock_cases.append(await clock(delta,"motion"))
        await process_frame
    clock_cases.append(await clock(0.1,"school-full"))
    await finish()

func context() -> Dictionary:
    # Attach a plain node before script assignment: call actual population without
    # invoking interactive _ready or the benchmark entry point automatically.
    var wrapper := Node3D.new()
    root.add_child(wrapper)
    wrapper.set_script(load("res://scripts/aquarium/fish_school/FishSchoolReview.gd"))
    wrapper.set_process(false)
    wrapper.roster = SPECIES.duplicate(); wrapper.count = SPECIES.size()
    wrapper.mode = "motion"; wrapper.benchmark = false
    wrapper._build_world()
    var populated: bool = await wrapper._populate()
    wrapper.set_process(false)
    if not populated or wrapper.entries.size() != SPECIES.size(): setup_failed = true
    return {"viewer":wrapper}

func release(ctx: Dictionary) -> void:
    var viewer = ctx.viewer
    viewer.loaded = false; viewer.set_process(false)
    viewer.entries.clear()
    if is_instance_valid(viewer.factory):
        viewer.factory.fish.clear(); viewer.factory.free(); viewer.factory = null
    viewer.queue_free()
    for frame in 3: await process_frame

func signed_body_yaw(entry: Dictionary) -> float:
    var value := 0.0
    for i in entry.controller._bones.size():
        var bone: int = entry.controller._bones[i]
        var q: Quaternion = (entry.controller._rest_rotations[i].inverse()*entry.skeleton.get_bone_pose_rotation(bone)).normalized()
        value += 2.0*atan2(Vector3(q.x,q.y,q.z).dot(entry.controller._yaw_axes[i]),q.w)
    return value

func steering(rate: float) -> Dictionary:
    var ctx := await context()
    var viewer = ctx.viewer
    var sums := {}; var samples := 0
    for species in SPECIES: sums[species] = 0.0
    for frame in 240:
        var heading := rate*float(frame+1)/60.0
        for i in viewer.entries.size():
            viewer.simulation.velocities[i] = Vector3(cos(heading),0,-sin(heading))
            viewer.simulation.positions[i] += viewer.simulation.velocities[i]/60.0
        viewer._process(1.0/60.0)
        if frame >= 120:
            samples += 1
            for entry in viewer.entries: sums[entry.species] += signed_body_yaw(entry)
    for species in sums: sums[species] /= maxi(samples,1)
    var result := {"signed_heading_rate_rps":rate,"speed_mps":1.0,"duration_seconds":4,"mean_window_seconds":[2,4],"means":sums,"actual_species":viewer.entries.size()}
    await release(ctx)
    return result

func clock(delta: float, mode: String) -> Dictionary:
    var ctx := await context()
    var viewer = ctx.viewer
    viewer.mode = mode
    var inputs := {}
    var initial := {}
    for entry in viewer.entries:
        initial[entry.species] = {"viewer_seconds":viewer.elapsed,"controller_seconds":entry.controller._time,"body_clock":entry.controller._body_clock,"fin_clock":entry.controller._fin_clock}
        inputs[entry.species] = {"clip_speed":float(entry.profile.actions.Swim.clip_speed),"body_frequency":float(entry.controller._motion.body_frequency),"fin_frequency":float(entry.controller._motion.fin_frequency)}
    var frames := roundi(8.0/delta)
    for frame in frames: viewer._process(delta)
    var observed := {}
    for entry in viewer.entries:
        var p: Dictionary = inputs[entry.species]
        var expected := {"viewer_seconds":8.0,"controller_seconds":8.0,"body_clock":8.0*p.clip_speed*p.body_frequency,"fin_clock":8.0*p.clip_speed*p.fin_frequency}
        var actual := {"viewer_seconds":viewer.elapsed,"controller_seconds":entry.controller._time,"body_clock":entry.controller._body_clock,"fin_clock":entry.controller._fin_clock}
        for key in actual: actual[key] -= initial[entry.species][key]
        var passed := true
        for key in expected: passed = passed and absf(actual[key]-expected[key]) < 0.0001
        observed[entry.species] = {"expected_clock_deltas":expected,"actual_clock_deltas":actual,"initial_clock_offsets":initial[entry.species],"profile_rates":p}
        checks.append({"test":"B_elapsed_time_preserved","mode":mode,"input_delta_seconds":delta,"species":entry.species,"passed":passed,"expected":expected,"actual":actual})
    var result := {"mode":mode,"input_delta_seconds":delta,"input_elapsed_seconds":frames*delta,"frames":frames,"simulation_ticks_observed":viewer.simulation._tick,"species":observed}
    await release(ctx)
    return result

func finish() -> void:
    var after: Dictionary = binding_viewer._bindings()
    var stable := before == after
    checks.append({"test":"production_bindings_unchanged_during_test","passed":stable})
    checks.append({"test":"actual_factory_setup","passed":not setup_failed})
    var passed := true
    for check in checks: passed = passed and check.passed
    var critical := {}
    for path in before:
        if path.ends_with("/FishSchoolReview.gd") or path.ends_with("/FishSchoolSimulation.gd") or path.ends_with("/FoundryFishMotion.gd") or path.ends_with("/VolumeFishExhibit.gd") or path.ends_with("/motion.json") or path.ends_with("/atlantic_sailfish.glb") or path.ends_with("/whale_shark.glb"): critical[path] = before[path]
    var report := {"schema_version":1,"command":"fish.school.motion.phase3-regression","stage":"validate","ok":passed,"status":"done" if passed else "failed","next_action":"human_review" if passed else "fix_input","inputs":{"script_sha256":FileAccess.get_sha256(get_script().resource_path),"binding_count":before.size(),"binding_digest_algorithm":"SHA256(Godot JSON.stringify(full sorted path-to-file-SHA256 map))","source_bindings_before_sha256":JSON.stringify(before).sha256_text(),"source_bindings_after_sha256":JSON.stringify(after).sha256_text(),"critical_file_sha256":critical},"summary":{"checks":checks,"steering_cases":steering_cases,"clock_cases":clock_cases},"scope":"Actual existing viewer._build_world and await _populate, then _process and simulation position/velocity buffers, fresh real-fish contexts; regression wiring/time only, no visual/biological/model/collision/performance approval","outputs":[output.path_join("regression.validation.json")],"failures":[]}
    if not passed: report.failures.append({"kind":"validation","code":"motion_regression_failed","message":"Inspect separate A route/body steering and B elapsed-clock assertions"})
    binding_viewer.free(); binding_viewer = null
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    for frame in 3: await process_frame
    var file := FileAccess.open(output.path_join("regression.validation.json"),FileAccess.WRITE)
    if file == null: push_error("Cannot write regression report"); quit(2); return
    file.store_string(JSON.stringify(report,"  ")+"\n"); file.close()
    print("SCHOOL_MOTION_PHASE3_REGRESSION ",JSON.stringify({"ok":passed,"checks":checks,"report":output.path_join("regression.validation.json")}))
    quit(0 if passed else 1)
