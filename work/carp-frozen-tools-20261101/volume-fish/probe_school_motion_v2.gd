extends SceneTree
## Phase1 evidence only. No production model/controller/viewer edits.
const SPECIES := ["atlantic_sailfish", "whale_shark", "bluegill", "pacific_bluefin_tuna"]
var output := ""
var factory
var wrapper
var world: Node3D
var entries: Array = []
var before: Dictionary = {}
var failures: Array = []
var results: Dictionary = {}

func _initialize() -> void: call_deferred("run")

func run() -> void:
    output = ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2").simplify_path()
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--probe-output="): output = arg.trim_prefix("--probe-output=")
    var allowed := ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2").simplify_path()
    if not output.is_absolute_path() or output != output.simplify_path() or not (output == allowed or output.begins_with(allowed + "/")):
        push_error("Probe output must be absolute inside fish-school-motion-v2")
        quit(2)
        return
    if DirAccess.make_dir_recursive_absolute(output) != OK:
        push_error("Cannot create diagnostic output")
        quit(2)
        return
    wrapper = load("res://scripts/aquarium/fish_school/FishSchoolReview.gd").new()
    before = wrapper._bindings()
    world = Node3D.new()
    root.add_child(world)
    wrapper.info = Label.new()
    wrapper.add_child(wrapper.info)
    preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
    factory = load("res://scripts/aquarium/VolumeFishExhibit.gd").new()
    factory._load_profiles()
    for species in SPECIES:
        var parent := Node3D.new()
        world.add_child(parent)
        var count_before: int = factory.fish.size()
        factory._add_fish(parent, species, float(factory.profiles[species].real_length_cm) / 100.0, factory.profiles[species])
        if factory.fish.size() != count_before + 1 or factory.fish[-1].species != species:
            failures.append({"kind":"validation","code":"factory_load_failed","message":species})
            await finish()
            return
        entries.append(factory.fish[-1])
        entries[-1]["motion_root"] = parent
        print("PROBE_LOADED ", species)
        await process_frame
    wrapper.entries = entries
    wrapper.count = entries.size()
    wrapper.loaded = true
    wrapper.benchmark = false
    wrapper.inventory = {"fish_count":entries.size(),"species_counts":{},"skeleton_bones":0,"visible_surfaces":0,"base_triangles":0}
    wrapper.motion_pending.resize(entries.size())
    results.native_clips = {}
    for entry in entries: results.native_clips[entry.species] = raw_clip(entry)
    results.native_direct = native_direct()
    results.interactive_wrapper = []
    for delta in [1.0 / 60.0, 1.0 / 15.0, 0.1]:
        for tier in [-1, 0, 1, 2]:
            results.interactive_wrapper.append(wrapper_case(delta, tier))
            await process_frame
    results.controlled_heading_inputs = []
    for speed in [0.5, 1.0]:
        results.controlled_heading_inputs.append(controlled_paths(speed))
        await process_frame
    await finish()

func poses(entry: Dictionary) -> Array:
    var values: Array = []
    for bone in entry.skeleton.get_bone_count(): values.append(entry.skeleton.get_bone_pose_rotation(bone))
    return values

func rotation_distance(a: Quaternion, b: Quaternion) -> float:
    var delta := (a.normalized().inverse() * b.normalized()).normalized()
    return 2.0 * atan2(Vector3(delta.x,delta.y,delta.z).length(), absf(delta.w))

func pose_delta(entry: Dictionary, a: Array, b: Array) -> Dictionary:
    var body := 0.0
    var fin := 0.0
    for bone in a.size():
        var angle := rotation_distance(a[bone], b[bone])
        if bone in entry.controller._bones: body = maxf(body, angle)
        else: fin = maxf(fin, angle)
    return {"body_deg":rad_to_deg(body),"nonbody_deg":rad_to_deg(fin)}

func state(entry: Dictionary) -> Dictionary:
    var controller = entry.controller
    var heading: Vector3 = entry.carrier.basis.x * float(entry.profile.head_sign)
    var signed := 0.0
    var overlay := 0.0
    var by_bone := {}
    for i in controller._bones.size():
        var bone: int = controller._bones[i]
        var q: Quaternion = (controller._rest_rotations[i].inverse() * entry.skeleton.get_bone_pose_rotation(bone)).normalized()
        var value := 2.0 * atan2(Vector3(q.x,q.y,q.z).dot(controller._yaw_axes[i]), q.w)
        signed += value
        by_bone[entry.skeleton.get_bone_name(bone)] = value
    for item in controller._bone_overlay: overlay += float(item.yaw_radians)
    return {"native_action":controller._action,"controller_seconds":controller._time,"body_clock":controller._body_clock,"fin_clock":controller._fin_clock,"carrier_yaw_rad":atan2(-heading.z,heading.x),"native_path_yaw_rad":controller._yaw(controller._time),"native_steering_bend_sum_rad":overlay,"actual_body_signed_joint_sum_rad":signed,"actual_body_signed_joints_rad":by_bone}

func raw_clip(entry: Dictionary) -> Dictionary:
    var animation: Animation = entry.player.get_animation(entry.profile.base_clip)
    var ranges := {}
    var body_max := 0.0
    var fin_max := 0.0
    for track in animation.get_track_count():
        if animation.track_get_type(track) != Animation.TYPE_ROTATION_3D: continue
        var path := animation.track_get_path(track)
        if path.get_subname_count() < 1: continue
        var bone: int = entry.skeleton.find_bone(str(path.get_subname(0)))
        if bone < 0: continue
        var initial: Quaternion = animation.rotation_track_interpolate(track, 0.0)
        var peak := 0.0
        for k in range(1, 129):
            var q: Quaternion = animation.rotation_track_interpolate(track, animation.length * k / 128.0)
            peak = maxf(peak, rotation_distance(initial,q))
        ranges[entry.skeleton.get_bone_name(bone)] = rad_to_deg(peak)
        if bone in entry.controller._bones: body_max = maxf(body_max, peak)
        else: fin_max = maxf(fin_max, peak)
    var p: Dictionary = entry.profile
    return {"real_length_m":entry.length_m,"clip":entry.profile.base_clip,"clip_length_seconds":animation.length,"bone_count":entry.skeleton.get_bone_count(),"rotation_track_count":ranges.size(),"samples_per_track":129,"max_body_delta_from_clip_start_deg":rad_to_deg(body_max),"max_nonbody_delta_from_clip_start_deg":rad_to_deg(fin_max),"per_bone_delta_from_clip_start_deg":ranges,"prepared_native_fin_tracks":entry.controller._fin_tracks.size(),"profile":{"period_seconds":p.period_seconds,"path_radii_m":p.path_radii_m,"body_delay_seconds":p.body_delay_seconds,"base_body_gain":p.base_body_gain,"body_wave_radians":p.get("body_wave_radians",0.0),"paired_fin_radians":p.get("paired_fin_radians",0.0),"median_fin_radians":p.get("median_fin_radians",0.0),"swim":p.actions.Swim,"turn":p.actions.Turn}}

func reset() -> void:
    for entry in entries:
        entry.controller.seek(0.0)
        entry.motion_root.position = Vector3.ZERO
    wrapper.elapsed = 0.0
    wrapper.frame_index = 1
    wrapper.motion_pending.fill(0.0)
    wrapper.simulation.configure(entries.size(), 731, entries.size())
    wrapper.last_frame_usec = Time.get_ticks_usec()
    for i in entries.size(): wrapper._place(i)

func native_direct() -> Dictionary:
    reset()
    var snapshots := {}
    var initial: Array = []
    var peaks: Array = []
    for entry in entries:
        initial.append(poses(entry))
        peaks.append({"body_deg":0.0,"nonbody_deg":0.0})
        snapshots[entry.species] = []
    for frame in 480:
        for i in entries.size():
            var entry: Dictionary = entries[i]
            entry.controller.step(1.0/60.0)
            var difference := pose_delta(entry, initial[i], poses(entry))
            for key in difference: peaks[i][key] = maxf(peaks[i][key], difference[key])
            if frame + 1 in [120,240,480]:
                var value := state(entry)
                value["input_elapsed_seconds"] = (frame+1)/60.0
                value["max_delta_from_initial_so_far"] = peaks[i].duplicate()
                snapshots[entry.species].append(value)
    return {"scope":"Existing actual factory controller.step, native path retained, supplied1/60s x480; no wrapper","snapshots":snapshots}

func wrapper_case(delta: float, tier: int) -> Dictionary:
    reset()
    wrapper.mode = "school-full" if tier < 0 else "school-tiered"
    if tier >= 0: wrapper.simulation.tier_ids.fill(tier)
    var checkpoints := [2.0,4.0,8.0]
    var snapshots := {}
    var initial: Array = []
    var previous: Array = []
    var steps: Array = []
    var held_turns: Array = []
    var peaks: Array = []
    for entry in entries:
        initial.append(poses(entry)); previous.append(state(entry)); steps.append(0)
        held_turns.append({"held_pose_frames":0,"max_carrier_yaw_change_while_pose_held_rad":0.0})
        peaks.append({"body_deg":0.0,"nonbody_deg":0.0}); snapshots[entry.species] = []
    var checkpoint := 0
    var frames := roundi(8.0 / delta)
    for frame in frames:
        wrapper._process(delta)
        for i in entries.size():
            var entry: Dictionary = entries[i]
            var value := state(entry)
            if value.controller_seconds > previous[i].controller_seconds + 0.000001: steps[i] += 1
            else:
                held_turns[i].held_pose_frames += 1
                held_turns[i].max_carrier_yaw_change_while_pose_held_rad = maxf(held_turns[i].max_carrier_yaw_change_while_pose_held_rad, absf(wrapf(value.carrier_yaw_rad-previous[i].carrier_yaw_rad,-PI,PI)))
            previous[i] = value
            var difference := pose_delta(entry, initial[i], poses(entry))
            for key in difference: peaks[i][key] = maxf(peaks[i][key], difference[key])
            if checkpoint < checkpoints.size() and (frame+1)*delta + 0.000001 >= checkpoints[checkpoint]:
                value["input_elapsed_seconds"] = (frame+1)*delta
                value["viewer_elapsed_seconds"] = wrapper.elapsed
                value["max_delta_from_initial_so_far"] = peaks[i].duplicate()
                value["controller_steps"] = steps[i]
                snapshots[entry.species].append(value)
        if checkpoint < checkpoints.size() and (frame+1)*delta + 0.000001 >= checkpoints[checkpoint]: checkpoint += 1
    var held := {}
    for i in entries.size(): held[entries[i].species] = held_turns[i]
    return {"mode":wrapper.mode,"forced_controlled_tier":tier,"input_frame_delta_seconds":delta,"input_elapsed_seconds":frames*delta,"viewer_elapsed_seconds":wrapper.elapsed,"viewer_time_ratio":wrapper.elapsed/(frames*delta),"scope":"Calls unchanged interactive viewer._process manually with supplied frame deltas; no GPU/actual FPS claim; each species assigned controlled tier","snapshots":snapshots,"held_pose_observations":held}

func controlled_paths(speed: float) -> Dictionary:
    var stored: Array = []
    var branches: Array = []
    var largest_difference := 0.0
    var largest_component_difference := 0.0
    var largest_signed_bend_difference := 0.0
    var stored_signed: Array = []
    for sign_value in [1.0,-1.0]:
        reset()
        var heading := 0.0
        var snapshots := {}
        for entry in entries: snapshots[entry.species] = []
        for frame in 480:
            var angular_rate: float = sign_value * (0.35 if frame < 240 else -0.35)
            heading += angular_rate / 60.0
            var frame_poses: Array = []
            var frame_signed: Array = []
            for i in entries.size():
                var entry: Dictionary = entries[i]
                entry.controller.step(1.0/60.0)
                wrapper.simulation.velocities[i] = Vector3(cos(heading),0,-sin(heading))*speed
                wrapper.simulation.positions[i] += wrapper.simulation.velocities[i]/60.0
                wrapper._place(i)
                var current := poses(entry)
                if sign_value > 0:
                    frame_poses.append(current)
                    frame_signed.append(state(entry).actual_body_signed_joint_sum_rad)
                else:
                    var difference := pose_delta(entry, stored[frame][i], current)
                    largest_difference = maxf(largest_difference,maxf(difference.body_deg,difference.nonbody_deg))
                    largest_signed_bend_difference = maxf(largest_signed_bend_difference, absf(state(entry).actual_body_signed_joint_sum_rad - stored_signed[frame][i]))
                    for bone in current.size():
                        var a: Quaternion = stored[frame][i][bone]
                        var b: Quaternion = current[bone]
                        largest_component_difference = maxf(largest_component_difference, maxf(maxf(absf(a.x-b.x),absf(a.y-b.y)),maxf(absf(a.z-b.z),absf(a.w-b.w))))
                if frame+1 in [120,240,360,480]:
                    var value := state(entry)
                    value["input_elapsed_seconds"] = (frame+1)/60.0
                    value["school_speed_mps"] = speed
                    value["school_signed_yaw_rate_rps"] = angular_rate
                    value["school_signed_curvature_per_m"] = angular_rate/speed
                    snapshots[entry.species].append(value)
            if sign_value > 0:
                stored.append(frame_poses)
                stored_signed.append(frame_signed)
        branches.append({"path_turn_sign":sign_value,"snapshots":snapshots})
    return {"speed_mps":speed,"wrapper_call":"Unchanged native controller.step(1/60), then unchanged viewer._place with controlled school velocity; locomotion turn reverses at4s","max_body_or_fin_rotation_difference_between_opposite_paths_deg":largest_difference,"max_quaternion_component_difference_between_opposite_paths":largest_component_difference,"max_signed_body_joint_sum_difference_between_opposite_paths_rad":largest_signed_bend_difference,"observations":branches}

func finish() -> void:
    var after: Dictionary = wrapper._bindings()
    var changed: Array = []
    for path in before:
        if before[path] != after.get(path, ""): changed.append(path)
    for path in after:
        if not before.has(path): changed.append(path)
    if not changed.is_empty(): failures.append({"kind":"validation","code":"source_changed_during_probe","message":str(changed)})
    var report := {"schema_version":1,"command":"fish.school.motion.phase1-probe","stage":"validate","ok":failures.is_empty(),"status":"done" if failures.is_empty() else "failed","next_action":"human_review" if failures.is_empty() else "fix_input","inputs":{"species":SPECIES,"script_sha256":FileAccess.get_sha256(get_script().resource_path),"source_bindings_sha256":before,"changed_sources":changed},"summary":results,"scope":"Headless controlled Phase1 evidence; no visual, model, fin-root, collision, realistic swimming or performance acceptance; no fixes applied","outputs":[output.path_join("diagnostic.validation.json")],"failures":failures}
    wrapper.loaded = false
    wrapper.entries.clear()
    entries.clear()
    if is_instance_valid(factory):
        factory.fish.clear(); factory.free(); factory = null
    preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    wrapper.free(); wrapper = null
    world.queue_free(); world = null
    for frame in 3: await process_frame
    var file := FileAccess.open(output.path_join("diagnostic.validation.json"),FileAccess.WRITE)
    if file == null:
        push_error("Cannot write diagnostic report"); quit(2); return
    file.store_string(JSON.stringify(report,"  ")+"\n"); file.close()
    print("SCHOOL_MOTION_PHASE1_PROBE ",JSON.stringify({"ok":report.ok,"failures":failures,"report":output.path_join("diagnostic.validation.json")}))
    quit(0 if failures.is_empty() else 1)
