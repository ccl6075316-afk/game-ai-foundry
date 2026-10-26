extends SceneTree
## Headless behavioral checks; writes one compact validation report, no assets.
var failures: Array[String] = []
var checks: Array[String] = []
var source_path := ""
var output := ""
var simulation_script: Script

func safe_review_output(path: String) -> bool:
    if not path.is_absolute_path(): return false
    var safe_roots := [ProjectSettings.globalize_path("res://../plans/reviews/fish-school-v1").simplify_path(), ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2").simplify_path()]
    var resolved := path.simplify_path()
    var allowed := false
    for safe_root in safe_roots:
        if resolved == safe_root or resolved.begins_with(safe_root + "/"): allowed = true
    if not allowed: return false
    if not DirAccess.dir_exists_absolute(resolved): return false
    # Reject symlink ancestors rather than trusting lexical prefix containment.
    var directory := DirAccess.open("/")
    if directory == null: return false
    var current := "/"
    for component in resolved.split("/", false):
        current = current.path_join(component)
        if directory.is_link(current): return false
    return true

func _initialize() -> void:
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="): output = arg.trim_prefix("--output=")
        if arg.begins_with("--simulation="): source_path = arg.trim_prefix("--simulation=")
    if source_path.is_empty():
        source_path = ProjectSettings.globalize_path(get_script().resource_path).get_base_dir().path_join("../../runtime/godot/fish-school/FishSchoolSimulation.gd").simplify_path()
    if not safe_review_output(output):
        push_error("--output must be an existing non-symlink directory under the game's plans/reviews/fish-school-v1 or fish-school-motion-v2")
        quit(2); return
    output = output.simplify_path()
    simulation_script = load(source_path)
    if simulation_script == null: quit(2); return
    call_deferred("run")

func check(condition: bool, name: String) -> void:
    checks.append(name)
    if not condition: failures.append(name)

func fresh(count: int = 50, species: int = 28):
    var sim = simulation_script.new()
    sim.configure(count, 731, species)
    return sim

func run() -> void:
    var a = fresh()
    var b = fresh()
    check(a.positions == b.positions and a.velocities == b.velocities, "deterministic initialization")
    var limits_ok := true
    var safe := true
    var emergency_obstacle_contacts := 0
    var emergency_boundary_contacts := 0
    for tick in 1200:
        var old: PackedVector3Array = a.velocities.duplicate()
        var trajectory_metrics: Dictionary = a.step(1.0 / 60.0, true)
        emergency_obstacle_contacts += trajectory_metrics.obstacle_contacts
        emergency_boundary_contacts += trajectory_metrics.boundary_contacts
        b.step(1.0 / 60.0, true)
        for i in a.positions.size():
            var velocity: Vector3 = a.velocities[i]
            limits_ok = limits_ok and velocity.length() >= a.MIN_SPEED - 0.0001 and velocity.length() <= a.MAX_SPEED + 0.0001
            limits_ok = limits_ok and old[i].distance_to(velocity) <= a.MAX_ACCELERATION / 60.0 + 0.0001
            limits_ok = limits_ok and old[i].angle_to(velocity) <= a.MAX_TURN_RATE / 60.0 + 0.0001
            var p: Vector3 = a.positions[i]
            safe = safe and p == p.clamp(a.bounds_min, a.bounds_max) and p.is_finite()
            for obstacle in a.obstacles:
                safe = safe and p.distance_to(obstacle.center) >= obstacle.radius + a.FISH_RADIUS - 0.0001
    check(a.positions == b.positions and a.velocities == b.velocities, "deterministic 1200 tick trajectory")
    check(limits_ok, "bounded speed vector acceleration and turn rate")
    check(safe, "bounds and spherical exclusion for mixed species trajectory")
    var path: PackedVector3Array = a.plan_route(Vector3(-10, 0, 0), Vector3(10, 0, 0))
    var path_safe := path.size() > 2
    for k in range(1, path.size()):
        for obstacle in a.obstacles:
            var segment := path[k] - path[k - 1]
            var t := clampf((obstacle.center - path[k - 1]).dot(segment) / segment.length_squared(), 0.0, 1.0)
            path_safe = path_safe and (path[k - 1] + segment * t).distance_to(obstacle.center) >= obstacle.radius + a.FISH_RADIUS
    check(path_safe, "explicit detour route segments clear obstacles")
    var all_routes_safe := true
    for route in a.route_points:
        for k in route.size():
            var start: Vector3 = route[k]
            var segment: Vector3 = route[(k + 1) % route.size()] - start
            for obstacle in a.obstacles:
                var t := clampf((obstacle.center - start).dot(segment) / maxf(segment.length_squared(), 0.000001), 0.0, 1.0)
                all_routes_safe = all_routes_safe and (start + segment * t).distance_to(obstacle.center) >= obstacle.radius + a.FISH_RADIUS
    check(all_routes_safe, "all 28 species closed route segments clear all obstacles")
    var coverage = fresh(56)
    var species_counts: Dictionary = {}
    for species_id in coverage.species_ids: species_counts[species_id] = species_counts.get(species_id, 0) + 1
    var all_species := species_counts.size() == 28
    for count in species_counts.values(): all_species = all_species and count == 2
    check(all_species, "56 fish cover every configured species twice")
    var schools = fresh(50, 25)
    var local_pairs := 0
    var school_cells: Dictionary = {}
    for species_id in 25:
        if schools.positions[species_id].distance_to(schools.positions[species_id + 25]) <= schools.NEIGHBOR_RADIUS: local_pairs += 1
        school_cells[schools.positions[species_id].snapped(Vector3(4, 4, 4))] = true
    check(local_pairs >= 15 and school_cells.size() >= 4, "50 fish form at least 15 local same-species pairs across multiple route anchors")
    var pair = fresh(2, 1)
    pair.obstacles.clear()
    pair.positions = PackedVector3Array([Vector3.ZERO, Vector3(1.5, 0, 0)])
    pair.velocities = PackedVector3Array([Vector3.FORWARD, Vector3.RIGHT])
    pair._grid = {Vector3i.ZERO: [0, 1]}
    var social: Vector3 = pair._neighbors(0)
    pair.species_ids[1] = 1
    var foreign: Vector3 = pair._neighbors(0)
    check(social.x > 0.5 and social.z > 0.5 and foreign.length() < 0.00001, "alignment and cohesion restricted to same species")
    pair.positions[1] = Vector3(0.2, 0, 0)
    var repulsion: Vector3 = pair._neighbors(0)
    check(repulsion.x < -1.0, "close foreign species produce separation force")
    pair = fresh(2, 1)
    pair.obstacles.clear()
    pair.positions = PackedVector3Array([Vector3(-0.2, 0, 0), Vector3(0.2, 0, 0)])
    pair.velocities = PackedVector3Array([Vector3.FORWARD, Vector3.FORWARD])
    pair.route_points[0] = PackedVector3Array([Vector3(0, 0, -100)])
    pair.route_indices.fill(0)
    for tick in 60: pair.step(1.0 / 60.0, false)
    check(pair.positions[0].distance_to(pair.positions[1]) > 0.4, "close pair increases separation over integration")
    var tiers = fresh(50)
    var full = fresh(50)
    check(tiers.positions == full.positions, "full and tiered workloads share initial conditions")
    var sums := [0, 0, 0]
    for tick in 6:
        var metrics: Dictionary = tiers.step(1.0 / 60.0, true)
        for tier in 3: sums[tier] += metrics.tier_updates[tier]
    check(sums == [60, 30, 25], "staggered tier decision counts over six ticks")
    check(full.step(1.0 / 60.0, false).updates == 50, "full simulation updates every fish")
    var dense = fresh(200, 1)
    dense.positions.fill(Vector3(5, 0, 0))
    var dense_result: Dictionary = dense.step(1.0 / 60.0, false)
    check(dense_result.max_candidate_visits <= 96 and dense_result.max_neighbors <= 24 and dense_result.neighbor_truncations > 0, "dense accepted neighbor cap and truncation reporting")
    # All nearby candidates are outside radius: candidate cap must hold even
    # when the accepted-neighbor limit cannot stop traversal.
    var candidates = fresh(200, 1)
    candidates.positions.fill(Vector3(2.79, 2.79, 2.79))
    candidates.positions[0] = Vector3.ZERO
    var cap_result: Dictionary = candidates.step(1.0 / 60.0, false)
    check(cap_result.max_candidate_visits <= 96 and cap_result.candidate_visits <= 200 * 96, "candidate visits capped independently of accepted neighbors")
    var selection = fresh(200, 1)
    selection.positions.fill(Vector3(1.7, 0, 0)); selection.positions[0] = Vector3.ZERO
    for i in selection.velocities.size(): selection.velocities[i] = Vector3.LEFT if i < 100 else Vector3.RIGHT
    var bucket: Array = []
    for i in 200: bucket.append(i)
    selection._grid = {Vector3i.ZERO: bucket}
    var early: Vector3 = selection._neighbors(0)
    selection._tick = 8
    var rotated: Vector3 = selection._neighbors(0)
    check(rotated.x > early.x + 1.0, "dense neighbor selection rotates beyond low-index candidates")
    var invalid = fresh()
    invalid.configure(-1)
    check(not invalid.configuration_error.is_empty() and not invalid.step(1.0 / 60.0).ok, "reject invalid fish count")
    invalid.configure(2, 731, 29)
    check(not invalid.configuration_error.is_empty(), "reject unknown species counts")
    invalid.configure(2)
    check(not invalid.step(0.0).ok and not invalid.step(-0.1).ok and not invalid.step(INF).ok, "reject invalid delta")
    var scales: Array[Dictionary] = []
    for count in [50, 200, 500, 2000, 16000]:
        var scale_sim = fresh(count)
        var metric: Dictionary = scale_sim.step(1.0 / 60.0)
        check(metric.ok and metric.count == count and metric.max_candidate_visits <= 96, "simulation-only scale %d" % count)
        scales.append({"count": count, "one_tick_ms": metric.total_elapsed_ms, "max_candidates": metric.max_candidate_visits})
    var report := {"schema_version": 1, "command": "fish-school-core-test", "status": "done" if failures.is_empty() else "failed",
        "ok": failures.is_empty(), "next_action": "human_review" if failures.is_empty() else "fix_input",
        "checks": checks, "failures": failures, "source": source_path,
        "source_sha256": FileAccess.get_sha256(source_path), "scale_smoke_only": scales,
        "trajectory": {"ticks": 1200, "seconds": 20, "emergency_obstacle_contacts": emergency_obstacle_contacts, "emergency_boundary_contacts": emergency_boundary_contacts},
        "school_initialization": {"agents": 50, "species": 25, "local_same_species_pairs": local_pairs, "coarse_occupied_cells": school_cells.size()},
        "limitations": ["Controlled cohorts, not visibility/distance LOD", "Basic boid steering, not biomechanical swimming", "One-tick scale smoke checks are not benchmark timings", "Emergency obstacle projection is reported, not physical collision simulation", "Fixed 0.18 m point-agent exclusion proxy does not represent diverse fish body lengths or full fin meshes; species size changes density and avoidance, so this is not capacity validation", "Discrete center checks do not verify swept bodies or continuous collision avoidance"]}
    var file := FileAccess.open(output.path_join("test.validation.json"), FileAccess.WRITE)
    if file == null: push_error("cannot write validation report"); quit(2); return
    file.store_string(JSON.stringify(report, "  ") + "\n")
    print(JSON.stringify({"ok": failures.is_empty(), "checks": checks.size(), "failures": failures}))
    quit(0 if failures.is_empty() else 1)
