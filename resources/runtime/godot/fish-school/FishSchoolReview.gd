extends Node3D
## Isolated experiment. Uses the existing assembled production fish without editing them.
const SIMULATION = preload("res://scripts/aquarium/fish_school/FishSchoolSimulation.gd")
const SCHOOL_MOTION = preload("res://scripts/aquarium/fish_school/FishSchoolMotionAdapter.gd")
const FACTORY_PATH := "res://scripts/aquarium/VolumeFishExhibit.gd"
const ALL_SPECIES := ["black_seabream", "red_seabream", "yellow_croaker", "zander", "atlantic_salmon", "red_emperor", "bluegill", "brown_trout", "blacktip_reef_shark", "scalloped_hammerhead", "great_hammerhead", "smooth_hammerhead", "silver_arowana", "hairtail", "piranha", "arapaima", "mahi_mahi", "peacock_bass", "crucian", "carp", "grass_carp", "nile_tilapia", "sea_bass", "rainbow_trout", "african_catfish", "atlantic_sailfish", "pacific_bluefin_tuna", "whale_shark"]
const MAC_UNVERIFIED := ["scalloped_hammerhead", "great_hammerhead", "smooth_hammerhead"]
const FIXED_STEP_SECONDS := 1.0 / 60.0
const MAX_INTERACTIVE_TICKS := 8
const MODES := ["static", "motion", "school-full", "school-tiered", "simulation"]
var simulation = SIMULATION.new()
var factory
var entries: Array = []
var motion_pending := PackedFloat64Array()
var camera: Camera3D
var info: Label
var count := 50
var roster: Array = []
var requested_species := ""
var exclude_species := ""
var setup_error := ""
var seed_value := 731
var mode := "school-full"
var samples := 120
var warmup := 30
var output := ""
var capture := false
var benchmark := false
var paused := false
var loaded := false
var finishing := false
var frame_index := 0
var yaw := 0.22
var pitch := 0.35
var distance := 44.0
var target := Vector3.ZERO
var elapsed := 0.0
var metrics: Dictionary = {}
var frame_values: Array = []
var sim_values: Array = []
var motion_values: Array = []
var work_values: Array = []
var draw_values: Array = []
var primitive_values: Array = []
var bindings_start: Dictionary = {}
var inventory: Dictionary = {}
var loading_ms := 0.0
var hashing_ms := 0.0
var dragging := false
var panning := false
var world: Node3D
var benchmark_started := 0
var last_frame_usec := 0
var sample_wall_ms := 0.0
var full_decisions := false
var controller_steps := 0
var controller_steps_tier := [0, 0, 0]
var simulation_totals: Dictionary = {}
var visible_centers: Array = []
var batch_wall_ms := 0.0
var clock_accumulator := 0.0
var accepted_input_seconds := 0.0
var fixed_ticks_total := 0
var last_frame_ticks := 0
var catchup_limited_frames := 0
var invalid_delta_frames := 0
var max_backlog_seconds := 0.0

func _ready() -> void:
    set_process(false)
    if not _arguments():
        get_tree().quit(2)
        return
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    get_tree().root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
    if benchmark:
        DisplayServer.window_set_size(Vector2i(1280, 720))
        get_tree().root.size = Vector2i(1280, 720)
    _build_world()
    if benchmark:
        var started := Time.get_ticks_usec()
        bindings_start = _bindings()
        hashing_ms = (Time.get_ticks_usec() - started) / 1000.0
    if not await _populate(): return
    benchmark_started = Time.get_ticks_usec()
    last_frame_usec = benchmark_started
    set_process(true)

func _arguments() -> bool:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--count="): count = arg.get_slice("=", 1).to_int()
        elif arg.begins_with("--seed="): seed_value = arg.get_slice("=", 1).to_int()
        elif arg.begins_with("--mode="): mode = arg.get_slice("=", 1)
        elif arg.begins_with("--samples="): samples = arg.get_slice("=", 1).to_int()
        elif arg.begins_with("--warmup="): warmup = arg.get_slice("=", 1).to_int()
        elif arg.begins_with("--output="): output = arg.trim_prefix("--output=")
        elif arg.begins_with("--species="): requested_species = arg.trim_prefix("--species=")
        elif arg.begins_with("--exclude-species="): exclude_species = arg.trim_prefix("--exclude-species=")
        elif arg == "--capture": capture = true
        elif arg == "--full-decisions": full_decisions = true
    benchmark = not output.is_empty()
    if mode not in MODES or count < 1 or count > 16000 or samples < 1 or warmup < 0:
        push_error("Invalid school benchmark input")
        return false
    if mode != "simulation" and count > 224:
        push_error("Real fish experiment safety limit is 224; use simulation for larger counts")
        return false
    if benchmark:
        var normalized := output.simplify_path()
        var review_root := ProjectSettings.globalize_path("res://../plans/reviews/fish-school-v1").simplify_path()
        var motion_review_root := ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2").simplify_path()
        var foundry_root := ProjectSettings.globalize_path("res://../../../output").simplify_path()
        if not output.is_absolute_path() or normalized != output or not (output.begins_with(review_root + "/") or output.begins_with(motion_review_root + "/") or output.begins_with(foundry_root + "/")):
            push_error("Output must be absolute and inside fish-school-v1, fish-school-motion-v2 or Foundry output")
            return false
        if DirAccess.make_dir_recursive_absolute(output) != OK:
            push_error("Cannot create benchmark output directory")
            return false
    roster = ALL_SPECIES.duplicate() if requested_species in ["", "all"] else Array(requested_species.split(",", false))
    var unique := {}
    for species in roster:
        if species not in ALL_SPECIES or unique.has(species):
            _setup_failure("invalid_species_roster", "Unknown or duplicate requested species: " + str(species))
            return false
        unique[species] = true
    var exclusions := Array(exclude_species.split(",", false))
    if requested_species.is_empty() and exclude_species.is_empty() and mode != "simulation" and OS.get_name() == "macOS":
        exclusions = MAC_UNVERIFIED.duplicate()
    for species in exclusions:
        if species not in ALL_SPECIES:
            _setup_failure("invalid_species_exclusion", "Unknown exclusion: " + str(species))
            return false
        roster.erase(species)
    if roster.is_empty():
        _setup_failure("empty_species_roster", "At least one species is required")
        return false
    return true

func _setup_failure(code: String, message: String) -> void:
    setup_error = message
    loaded = false
    set_process(false)
    push_error(message)
    if is_instance_valid(info): info.text = "实验停止：" + message
    if benchmark:
        var report := {"schema_version":1,"command":"fish.school.benchmark","stage":"validate","ok":false,"status":"failed","next_action":"fix_input","inputs":{"count":count,"seed":seed_value,"mode":mode,"full_decisions":full_decisions,"warmup_frames":warmup,"sample_frames":samples,"species":requested_species,"exclude_species":exclude_species,"requested_roster":roster,"bindings_sha256":bindings_start},"summary":{"actual_fish_count":entries.size(),"actual_roster_counts":inventory.get("species_counts",{})},"outputs":[output.path_join("benchmark.validation.json")],"failures":[{"kind":"validation","code":code,"message":message}]}
        var file := FileAccess.open(output.path_join("benchmark.validation.json"), FileAccess.WRITE)
        if file != null: file.store_string(JSON.stringify(report,"  ") + "\n")
        get_tree().quit(2)

func _preflight() -> bool:
    for species in roster:
        if OS.get_name() == "macOS" and species in MAC_UNVERIFIED:
            _setup_failure("hammer_imported_guard_unverified", "macOS imported hammerhead rest snapshot does not match reviewed137 guard: " + species + "; retain guard and exclude until cross-platform review")
            return false
        var source: String = "res://assets/models/fish/" + str(species) + ".glb"
        var importer := ConfigFile.new()
        if not FileAccess.file_exists(source) or importer.load(source + ".import") != OK:
            _setup_failure("fish_import_missing", "Missing fish source or importer: " + source)
            return false
        var imported: String = importer.get_value("remap", "path", "")
        if imported.is_empty() or not FileAccess.file_exists(imported) or not ResourceLoader.exists(source):
            _setup_failure("fish_import_missing", "Imported PackedScene unavailable: " + imported + "; import project before benchmark")
            return false
    if RenderingServer.get_current_rendering_method() == "gl_compatibility" and OS.get_name() == "macOS":
        _setup_failure("macos_shader_sampler_limit", "Production fish shaders require17/18 samplers; Apple OpenGL limit16. Run isolated prototype with Forward+ Metal; no shader edits")
        return false
    return true

func _build_world() -> void:
    world = Node3D.new()
    add_child(world)
    var environment := WorldEnvironment.new()
    environment.environment = Environment.new()
    environment.environment.background_mode = Environment.BG_COLOR
    environment.environment.background_color = Color("10232d")
    environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color = Color("d9eff0")
    environment.environment.ambient_light_energy = 0.85
    world.add_child(environment)
    var light := DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-55, -25, 0)
    light.light_energy = 0.6
    light.shadow_enabled = false
    world.add_child(light)
    camera = Camera3D.new()
    camera.fov = 52
    camera.near = 0.05
    camera.far = 180
    world.add_child(camera)
    camera.current = true
    _camera_update()
    var canvas := CanvasLayer.new()
    add_child(canvas)
    var panel := VBoxContainer.new()
    panel.position = Vector2(18, 15)
    canvas.add_child(panel)
    var title := Label.new()
    title.text = "鱼群性能原型 · %d种现有鱼 / 独立实验" % roster.size()
    title.add_theme_font_size_override("font_size", 22)
    panel.add_child(title)
    var controls := HBoxContainer.new()
    panel.add_child(controls)
    for value in [roster.size(), roster.size() * 2, roster.size() * 4, mini(224, roster.size() * 8)]:
        var button := Button.new()
        button.text = "%d 条" % value
        button.disabled = benchmark
        button.pressed.connect(_request_count.bind(value))
        controls.add_child(button)
    var toggle := Button.new()
    toggle.text = "切换全频 / 分层动作"
    toggle.disabled = benchmark
    toggle.pressed.connect(func(): mode = "school-full" if mode == "school-tiered" else "school-tiered")
    controls.add_child(toggle)
    var pause := Button.new()
    pause.text = "暂停 / 继续"
    pause.disabled = benchmark
    pause.pressed.connect(func(): paused = not paused)
    controls.add_child(pause)
    info = Label.new()
    info.text = "准备加载；保留原模型、材质、骨骼与实际体长…"
    panel.add_child(info)
    var note := Label.new()
    note.text = "左拖旋转 / 中或右拖平移 / 滚轮缩放 · 球体为避障区域 · 分层为固定测试分组\n原生摆动 + 鱼群路径身体转向；分层保持姿态，无插值；不包含水、阴影、正式寻路"
    panel.add_child(note)

func _populate() -> bool:
    loaded = false
    var start := Time.get_ticks_usec()
    simulation.configure(count, seed_value, roster.size())
    for child in world.get_children():
        if child.has_meta("school_fish") or child.has_meta("school_obstacle"):
            child.free()
    entries.clear()
    if is_instance_valid(factory): factory.free()
    factory = null
    inventory = {"fish_count":0, "species_counts":{}, "skeleton_bones":0, "visible_surfaces":0, "base_triangles":0}
    if mode != "simulation":
        if not _preflight(): return false
        preload("res://scripts/aquarium/FishAppearanceCache.gd").begin_entry()
        factory = load(FACTORY_PATH).new()
        factory._load_profiles()
        for i in count:
            var species: String = roster[simulation.species_ids[i]]
            var profile: Dictionary = factory.profiles[species]
            var motion_root := Node3D.new()
            motion_root.set_meta("school_fish", true)
            world.add_child(motion_root)
            var before_count: int = factory.fish.size()
            factory._add_fish(motion_root, species, float(profile.real_length_cm) / 100.0, profile, Vector3.ZERO, float(i % 17) * 0.137)
            if factory.fish.size() != before_count + 1:
                _setup_failure("fish_spawn_failed", "Factory failed to append requested species: " + species + "; no previous fish substitution allowed")
                return false
            var entry: Dictionary = factory.fish[-1]
            if entry.get("species", "") != species or not is_instance_valid(entry.get("model")) or not is_instance_valid(entry.get("skeleton")):
                _setup_failure("fish_species_mismatch", "Factory result does not match requested valid model/skeleton: " + species)
                return false
            entry["motion_root"] = motion_root
            entry["school_motion"] = SCHOOL_MOTION.new()
            var adapter: Dictionary = entry.school_motion.configure(entry.controller, simulation.velocities[i])
            if not adapter.ok:
                _setup_failure("school_motion_configuration", str(adapter.get("error", "School motion configuration failed")))
                return false
            entries.append(entry)
            _inventory_fish(entry)
            _place(i)
            info.text = "加载 %d / %d · %s" % [i + 1, count, species]
            await get_tree().process_frame
    for obstacle in simulation.obstacles:
        var mesh := MeshInstance3D.new()
        var sphere := SphereMesh.new()
        sphere.radius = obstacle.radius
        sphere.height = obstacle.radius * 2
        sphere.radial_segments = 16
        sphere.rings = 8
        mesh.mesh = sphere
        var material := StandardMaterial3D.new()
        material.albedo_color = Color("46636b")
        material.roughness = 1
        mesh.material_override = material
        mesh.position = obstacle.center
        mesh.set_meta("school_obstacle", true)
        mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        world.add_child(mesh)
    motion_pending.resize(count)
    motion_pending.fill(0.0)
    loading_ms = (Time.get_ticks_usec() - start) / 1000.0
    frame_index = 0
    elapsed = 0
    clock_accumulator = 0.0
    accepted_input_seconds = 0.0
    fixed_ticks_total = 0
    last_frame_ticks = 0
    catchup_limited_frames = 0
    invalid_delta_frames = 0
    max_backlog_seconds = 0.0
    last_frame_usec = Time.get_ticks_usec()
    if mode != "simulation" and entries.size() != count:
        _setup_failure("fish_count_mismatch", "Actual fish count differs from requested count")
        return false
    loaded = true
    return true

func _inventory_fish(entry: Dictionary) -> void:
    inventory.fish_count += 1
    inventory.species_counts[entry.species] = inventory.species_counts.get(entry.species, 0) + 1
    inventory.skeleton_bones += entry.skeleton.get_bone_count()
    for node in entry.model.find_children("*", "MeshInstance3D", true, false):
        node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        if not node.is_visible_in_tree() or node.mesh == null: continue
        for surface in node.mesh.get_surface_count():
            inventory.visible_surfaces += 1
            var arrays: Array = node.mesh.surface_get_arrays(surface)
            var indices = arrays[Mesh.ARRAY_INDEX]
            var vertices = arrays[Mesh.ARRAY_VERTEX]
            inventory.base_triangles += (indices.size() if indices != null and indices.size() > 0 else vertices.size()) / 3

func _place(i: int) -> void:
    var entry: Dictionary = entries[i]
    # Preserve the prototype's center placement policy, including zero carrier
    # offset. Native head-anchor path translation is intentionally not restored.
    entry.carrier.transform = Transform3D(entry.school_motion.orientation(), Vector3.ZERO)
    entry.motion_root.position = simulation.positions[i]

func _merge_simulation_metrics(part: Dictionary) -> void:
    for key in ["grid_ms", "decision_ms", "integration_ms", "total_elapsed_ms", "candidate_visits", "neighbor_comparisons", "neighbor_truncations", "obstacle_contacts", "boundary_contacts", "updates"]:
        metrics[key] = metrics.get(key, 0.0) + float(part.get(key, 0.0))
    for key in ["max_candidate_visits", "max_neighbors", "grid_cells"]:
        metrics[key] = maxi(int(metrics.get(key, 0)), int(part.get(key, 0)))
    for key in ["tick", "count", "tier_counts", "ok"]:
        if part.has(key): metrics[key] = part[key]
    if not metrics.has("tier_updates"): metrics["tier_updates"] = [0, 0, 0]
    for tier in 3: metrics.tier_updates[tier] += int(part.get("tier_updates", [0, 0, 0])[tier])

func _process(delta: float) -> void:
    if not loaded or finishing: return
    # Zero delta can drain retained backlog. Invalid/negative input advances none.
    if not is_finite(delta) or delta < 0.0:
        invalid_delta_frames += 1
        return
    var now := Time.get_ticks_usec()
    if paused:
        last_frame_usec = now
        last_frame_ticks = 0
        _stats(delta, 0, 0)
        return
    var raw_frame_ms := (now - last_frame_usec) / 1000.0
    last_frame_usec = now
    last_frame_ticks = 1
    if benchmark:
        accepted_input_seconds += FIXED_STEP_SECONDS
    else:
        accepted_input_seconds += delta
        clock_accumulator += delta
        last_frame_ticks = mini(MAX_INTERACTIVE_TICKS, floori((clock_accumulator + 0.000000001) / FIXED_STEP_SECONDS))
        clock_accumulator = maxf(0.0, clock_accumulator - last_frame_ticks * FIXED_STEP_SECONDS)
        if clock_accumulator + 0.000000001 >= FIXED_STEP_SECONDS: catchup_limited_frames += 1
        max_backlog_seconds = maxf(max_backlog_seconds, clock_accumulator)
    var work_start := Time.get_ticks_usec()
    var sim_usec := 0
    var motion_usec := 0
    metrics = {}
    # Keep every trajectory observation, including catch-up ticks, then evaluate
    # the native skeleton once at the final consumed time when its cadence is due.
    for tick_index in last_frame_ticks:
        elapsed += FIXED_STEP_SECONDS
        fixed_ticks_total += 1
        if mode in ["school-full", "school-tiered", "simulation"]:
            var sim_start := Time.get_ticks_usec()
            var part: Dictionary = simulation.step(FIXED_STEP_SECONDS, mode in ["school-tiered", "simulation"] and not full_decisions)
            sim_usec += Time.get_ticks_usec() - sim_start
            if not part.get("ok", false):
                _setup_failure("school_simulation_step", str(part.get("error", "Simulation step failed")))
                return
            _merge_simulation_metrics(part)
        if mode not in ["simulation", "static"]:
            var observation_start := Time.get_ticks_usec()
            for i in entries.size():
                var observation: Dictionary = entries[i].school_motion.observe(simulation.velocities[i], FIXED_STEP_SECONDS)
                if not observation.ok:
                    _setup_failure("school_motion_observation", str(observation.get("error", "Invalid school motion observation")))
                    return
                motion_pending[i] += FIXED_STEP_SECONDS
            motion_usec += Time.get_ticks_usec() - observation_start
    var pose_start := Time.get_ticks_usec()
    if mode != "simulation":
        for i in entries.size():
            if mode != "static" and last_frame_ticks > 0:
                var interval_ticks := 1
                if mode == "school-tiered": interval_ticks = [1, 4, 12][simulation.tier_ids[i]]
                var due := frame_index % interval_ticks == i % interval_ticks if benchmark else motion_pending[i] + 0.000001 >= float(interval_ticks) / 60.0
                if due:
                    var posed: Dictionary = entries[i].school_motion.step(motion_pending[i])
                    if not posed.ok:
                        _setup_failure("school_motion_pose", str(posed.get("error", "Invalid school body pose")))
                        return
                    if benchmark and frame_index >= warmup:
                        controller_steps += 1
                        controller_steps_tier[simulation.tier_ids[i]] += 1
                    if entries[i].has("jaw_controller"):
                        entries[i].jaw_controller.apply(0.5 - 0.5 * cos(elapsed * TAU / 3.2))
                    motion_pending[i] = 0.0
            _place(i)
    motion_usec += Time.get_ticks_usec() - pose_start
    var sim_ms := sim_usec / 1000.0
    var motion_ms := motion_usec / 1000.0
    var work_ms := (Time.get_ticks_usec() - work_start) / 1000.0
    metrics["fixed_clock_ticks_this_frame"] = last_frame_ticks
    if benchmark and frame_index >= warmup:
        frame_values.append(raw_frame_ms)
        sample_wall_ms += raw_frame_ms
        var centers := 0
        for position in simulation.positions:
            if camera.is_position_in_frustum(position): centers += 1
        visible_centers.append(centers)
        for key in ["grid_ms", "decision_ms", "integration_ms", "total_elapsed_ms", "candidate_visits", "neighbor_comparisons", "neighbor_truncations", "obstacle_contacts", "boundary_contacts", "updates"]:
            simulation_totals[key] = simulation_totals.get(key, 0.0) + float(metrics.get(key, 0.0))
        for tier in 3:
            var key := "tier_%d_updates" % tier
            simulation_totals[key] = simulation_totals.get(key, 0) + int(metrics.get("tier_updates", [0, 0, 0])[tier])
        sim_values.append(sim_ms)
        motion_values.append(motion_ms)
        work_values.append(work_ms)
        draw_values.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
        primitive_values.append(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
    _stats(delta, sim_ms, motion_ms)
    frame_index += 1
    if benchmark and frame_index >= warmup + samples:
        finishing = true
        set_process(false)
        _finish.call_deferred()

func _stats(delta: float, sim_ms: float, motion_ms: float) -> void:
    if frame_index % 15 != 0: return
    info.text = "%s · %d 条 / %d 种 · 帧 %.2f ms · 行为 %.2f ms · 动作 %.2f ms\n骨骼 %d · surface %d · 基础三角面 %d · 加载 %.1f s" % [mode, count, inventory.species_counts.size(), delta * 1000, sim_ms, motion_ms, inventory.skeleton_bones, inventory.visible_surfaces, inventory.base_triangles, loading_ms / 1000.0]

func _request_count(value: int) -> void:
    if not loaded or benchmark: return
    count = value
    set_process(false)
    if await _populate(): set_process(true)

func _summary(values: Array) -> Dictionary:
    if values.is_empty(): return {}
    var sorted := values.duplicate()
    sorted.sort()
    var total := 0.0
    for value in values: total += float(value)
    return {"mean":total / values.size(), "median":sorted[sorted.size() / 2], "p95":sorted[mini(sorted.size() - 1, ceili(sorted.size() * 0.95) - 1)], "max":sorted[-1]}

func _files(path: String, result: Array[String]) -> void:
    var dir := DirAccess.open(path)
    if dir == null: return
    for child in dir.get_directories(): _files(path.path_join(child), result)
    for file in dir.get_files():
        if file.ends_with(".uid"): continue
        result.append(path.path_join(file))

func _bindings() -> Dictionary:
    var files: Array[String] = []
    if mode != "simulation":
        _files("res://assets/models/fish", files)
        _files("res://scripts/aquarium", files)
    else:
        var folder := "res://scripts/aquarium/fish_school"
        for file in DirAccess.open(folder).get_files():
            if file.ends_with(".gd"): files.append(folder.path_join(file))
    files.append("res://project.godot")
    files.append("res://scenes/fish_school_review.tscn")
    files.sort()
    var result := {}
    for path in files: result[path] = FileAccess.get_sha256(path)
    return result

func _finish() -> void:
    if capture and DisplayServer.get_name() != "headless":
        await RenderingServer.frame_post_draw
        get_viewport().get_texture().get_image().save_png(output.path_join("overview.png"))
    batch_wall_ms = (Time.get_ticks_usec() - benchmark_started) / 1000.0
    var bindings_end := _bindings()
    var changed: Array = []
    for path in bindings_start:
        if bindings_start[path] != bindings_end.get(path, ""): changed.append(path)
    for path in bindings_end:
        if not bindings_start.has(path): changed.append(path)
    var is_headless := DisplayServer.get_name() == "headless"
    var report := {
        "schema_version":1, "command":"fish.school.benchmark", "stage":"validate", "ok":changed.is_empty(),
        "status":"done" if changed.is_empty() else "failed", "next_action":"human_review" if changed.is_empty() else "fix_input",
        "inputs":{"count":count,"seed":seed_value,"mode":mode,"full_decisions":full_decisions,"species":requested_species,"exclude_species":exclude_species,"requested_roster":roster,"actual_roster_counts":inventory.species_counts,"warmup_frames":warmup,"sample_frames":samples,"fixed_simulation_delta_seconds":1.0/60.0,"bindings_sha256":bindings_start,"changed_during_run":changed},
        "environment":{"godot":Engine.get_version_info(),"os":OS.get_name(),"os_version":OS.get_version(),"processor":OS.get_processor_name(),"display_server":DisplayServer.get_name(),"gpu":RenderingServer.get_video_adapter_name(),"gpu_vendor":RenderingServer.get_video_adapter_vendor(),"rendering_method":RenderingServer.get_current_rendering_method(),"rendering_driver":RenderingServer.get_current_rendering_driver_name(),"viewport_size":[get_viewport().get_visible_rect().size.x,get_viewport().get_visible_rect().size.y],"window_size":[DisplayServer.window_get_size().x,DisplayServer.window_get_size().y],"viewport_texture_size":[get_viewport().get_texture().get_size().x,get_viewport().get_texture().get_size().y],"vsync":DisplayServer.window_get_vsync_mode(),"headless":is_headless},
        "summary":{"inventory":inventory,"simulation_agents":count,"requested_species_count":roster.size(),"actual_species_count":inventory.species_counts.size(),"load_ms":loading_ms,"source_hashing_start_ms":hashing_ms,"frame_ms":_summary(frame_values),"simulation_cpu_ms":_summary(sim_values),"motion_and_placement_cpu_ms":_summary(motion_values),"total_work_cpu_ms":_summary(work_values),"renderer_draw_calls":_summary(draw_values),"renderer_primitives":_summary(primitive_values),"last_simulation_metrics":metrics,"simulation_measured_totals":simulation_totals,"controller_step_count":controller_steps,"controller_steps_by_tier":controller_steps_tier,"fish_centers_in_camera_frustum":_summary(visible_centers),"simulated_sample_seconds":samples/60.0,"sample_wall_seconds":sample_wall_ms/1000.0,"benchmark_elapsed_ms":batch_wall_ms,"clock":{"accepted_input_seconds":accepted_input_seconds,"consumed_seconds":elapsed,"pending_seconds":clock_accumulator,"fixed_ticks_total":fixed_ticks_total,"max_ticks_per_interactive_frame":MAX_INTERACTIVE_TICKS,"catchup_limited_frames":catchup_limited_frames,"max_backlog_seconds":max_backlog_seconds,"invalid_delta_frames_ignored":invalid_delta_frames}},
        "scope":{"representation":"none; simulation cost only" if mode == "simulation" else "existing actual final assembled fish, source geometry/materials/bones and real lengths retained", "cohorts":"deterministic index groups: near20%, mid30%, far50%; not camera distances", "motion_cadence_hz":[60,15,5] if mode == "school-tiered" else [60,60,60],"motion_between_updates":"held skeleton pose; accumulated delta advances native phase on next update; no interpolation","native_motion":"actual school velocity heading history drives bounded body steering; existing native base wave, clip and fin phases retained; no new biomechanics solver","pathfinding":"waypoint routes and sphere steering; no production navmesh/path planner; fixed agent radius0.18m independent of actual fish length, no full-body avoidance","clock":"benchmark: one fixed1/60 tick per rendered frame. Interactive: fixed60Hz accumulator, max8ticks per rendered frame, backlog retained, one due native pose evaluation per rendered frame; pause adds no input and retains pending time","concurrent_workloads":"preexisting Godot process PID54404 may run concurrently; test host process inventory must accompany comparisons", "excluded":["water", "glass", "shadows", "gameplay", "production full-body collision", "model/fin/body visual acceptance"],"capacity_claim":false,"gpu_frame_timing":"unavailable; frame_ms is measured host frame interval, no GPU timestamp query","render_metrics_usable":not is_headless,"renderer_culling":"standard engine frustum culling; inspect camera coverage before interpreting draw counters"},
        "outputs":[output.path_join("benchmark.validation.json")],"failures":[]}
    if not changed.is_empty(): report.failures.append({"kind":"validation","code":"source_changed_during_run","message":"Input bindings changed; rerun before comparison"})
    var file := FileAccess.open(output.path_join("benchmark.validation.json"), FileAccess.WRITE)
    if file == null:
        push_error("Cannot write benchmark validation report")
        get_tree().quit(2)
        return
    file.store_string(JSON.stringify(report, "  ") + "\n")
    print("FISH_SCHOOL_BENCHMARK ", JSON.stringify({"ok":report.ok,"mode":mode,"count":count,"summary":report.summary,"report":output.path_join("benchmark.validation.json")}))
    if is_instance_valid(factory): factory.free()
    if mode != "simulation": preload("res://scripts/aquarium/FishAppearanceCache.gd").clear()
    get_tree().quit(0 if changed.is_empty() else 1)

func _camera_update() -> void:
    camera.position = target + Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch)) * distance
    camera.look_at(target)

func _unhandled_input(event: InputEvent) -> void:
    if benchmark: return
    if event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_LEFT: dragging = event.pressed
        if event.button_index in [MOUSE_BUTTON_MIDDLE, MOUSE_BUTTON_RIGHT]: panning = event.pressed
        if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
            distance = clampf(distance * (0.9 if event.button_index == MOUSE_BUTTON_WHEEL_UP else 1.1), 2, 110)
            _camera_update()
    elif event is InputEventMouseMotion:
        if dragging:
            yaw -= event.relative.x * 0.006
            pitch = clampf(pitch + event.relative.y * 0.006, -1.3, 1.3)
            _camera_update()
        elif panning:
            target += (-camera.global_basis.x * event.relative.x + camera.global_basis.y * event.relative.y) * distance * 0.0015
            _camera_update()
