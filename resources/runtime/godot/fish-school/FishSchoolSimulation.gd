extends RefCounted
## Experimental CPU workload only: no asset/controller edits and no biological swim claim.
## Tiers are deterministic workload cohorts, NOT visibility or distance LOD.
## Caller supplies a fixed tick (normally 1/60 s). Decisions run every 1/3/6
## ticks, staggered by fish ID; all fish integrate at every fixed tick.

const MAX_NEIGHBORS := 24
const MAX_CANDIDATES := 96
const NEIGHBOR_RADIUS := 2.8
const MIN_SPEED := 0.55
const MAX_SPEED := 2.2
const MAX_ACCELERATION := 1.8
const MAX_TURN_RATE := 1.7
# Point-agent exclusion proxy only: not diverse fish lengths or fin/body meshes.
# Species sizes change density and avoidance cost; this is not capacity validation.
const FISH_RADIUS := 0.18
const TIER_INTERVALS := [1, 3, 6]

var positions := PackedVector3Array()
var velocities := PackedVector3Array()
var species_ids := PackedInt32Array()
var tier_ids := PackedInt32Array()
var speeds := PackedFloat32Array()
var curvatures := PackedFloat32Array()
var route_indices := PackedInt32Array()
var route_points: Array[PackedVector3Array] = []
var obstacles: Array[Dictionary] = []
var bounds_min := Vector3(-20, -8, -14)
var bounds_max := Vector3(20, 8, 14)
var schooling_enabled := true
var configuration_error := ""
var route_planning_ms := 0.0
var _commands := PackedVector3Array()
var _grid: Dictionary = {}
var _offsets: Array[Vector3i] = []
var _tick := 0
var _tier_counts := [0, 0, 0]
var _visits := 0
var _comparisons := 0
var _max_visits := 0
var _max_neighbors := 0
var _truncations := 0

func configure(count: int, seed_value: int = 731, species_count: int = 28) -> void:
    configuration_error = ""
    positions.clear(); velocities.clear(); species_ids.clear(); tier_ids.clear()
    speeds.clear(); curvatures.clear(); route_indices.clear(); _commands.clear()
    route_points.clear(); _grid.clear(); _offsets.clear(); _tick = 0
    _tier_counts = [0, 0, 0]
    if count <= 0 or species_count <= 0 or species_count > 28:
        configuration_error = "count must be positive; species_count must be in 1..28"
        return
    var rng := RandomNumberGenerator.new()
    rng.seed = seed_value
    obstacles = [{"center": Vector3.ZERO, "radius": 2.6},
        {"center": Vector3(9, 0, 7), "radius": 1.5},
        {"center": Vector3(-9, 1, -7), "radius": 1.8}]
    for x in range(-1, 2):
        for y in range(-1, 2):
            for z in range(-1, 2): _offsets.append(Vector3i(x, y, z))
    var path_start := Time.get_ticks_usec()
    for s in species_count:
        var y := -3.0 + float(s % 7)
        var z := -1.5 + float(s % 4)
        var anchors := PackedVector3Array([Vector3(-14, y, z), Vector3(14, y, z),
            Vector3(14, y, 10), Vector3(-14, y, 10)])
        var route := PackedVector3Array()
        for k in anchors.size():
            var leg := plan_route(anchors[k], anchors[(k + 1) % anchors.size()])
            for n in range(leg.size() - 1): route.append(leg[n])
        route_points.append(route)
    route_planning_ms = (Time.get_ticks_usec() - path_start) / 1000.0
    for i in count:
        var species := i % species_count
        var route: PackedVector3Array = route_points[species]
        # Spread schools across route anchors, while keeping members of the
        # same species close enough to exercise local alignment and cohesion.
        var route_index := species % route.size()
        var position := route[route_index] + Vector3(rng.randf_range(-1.3, 1.3),
            rng.randf_range(-0.5, 0.5), rng.randf_range(-1.3, 1.3))
        var target_index := (route_index + 1) % route.size()
        var velocity := position.direction_to(route[target_index]) * rng.randf_range(0.9, 1.5)
        positions.append(position); velocities.append(velocity); species_ids.append(species)
        var cohort := i % 10
        var tier := 0 if cohort < 2 else (1 if cohort < 5 else 2)
        tier_ids.append(tier); _tier_counts[tier] += 1
        speeds.append(velocity.length()); curvatures.append(0.0)
        route_indices.append(target_index); _commands.append(velocity)

## Static route planning is separate from per-tick reactive avoidance. Each blocked
## segment receives two explicit side waypoints outside the obstacle's sphere.
func plan_route(start: Vector3, finish: Vector3) -> PackedVector3Array:
    var result := PackedVector3Array([start, finish])
    for obstacle in obstacles:
        var expanded := PackedVector3Array([result[0]])
        var center: Vector3 = obstacle.center
        var clearance: float = obstacle.radius + FISH_RADIUS + 0.8
        for k in range(1, result.size()):
            var a := result[k - 1]
            var b := result[k]
            var segment := b - a
            var distance2 := segment.length_squared()
            var t := clampf((center - a).dot(segment) / maxf(distance2, 0.00001), 0.0, 1.0)
            if t > 0.0 and t < 1.0 and (a + segment * t).distance_to(center) < clearance:
                var direction := segment.normalized()
                var side := direction.cross(Vector3.UP).normalized()
                if side.length_squared() < 0.1: side = Vector3.RIGHT
                # Keep lateral detours toward the center of the finite tank.
                if (center + side * clearance).length_squared() > (center - side * clearance).length_squared():
                    side = -side
                expanded.append(center - direction * clearance + side * clearance)
                expanded.append(center + direction * clearance + side * clearance)
            expanded.append(b)
        result = expanded
    return result

func _cell(position: Vector3) -> Vector3i:
    return Vector3i(floori(position.x / NEIGHBOR_RADIUS), floori(position.y / NEIGHBOR_RADIUS), floori(position.z / NEIGHBOR_RADIUS))

func _neighbors(index: int) -> Vector3:
    var position := positions[index]
    var cell := _cell(position)
    var separation := Vector3.ZERO
    var alignment := Vector3.ZERO
    var center := Vector3.ZERO
    var same := 0
    var accepted := 0
    var visits := 0
    # Rotate both cell traversal and bucket start. Dense buckets do not always
    # select low IDs; candidate reads and accepted neighbors have distinct caps.
    var offset_start := (index * 17 + _tick * 7) % _offsets.size()
    for cell_step in _offsets.size():
        var key := cell + _offsets[(offset_start + cell_step) % _offsets.size()]
        if not _grid.has(key): continue
        var bucket: Array = _grid[key]
        var bucket_start := (index * 13 + _tick * 19) % bucket.size()
        for bucket_step in bucket.size():
            if visits >= MAX_CANDIDATES or accepted >= MAX_NEIGHBORS:
                _truncations += 1
                _max_visits = maxi(_max_visits, visits)
                _max_neighbors = maxi(_max_neighbors, accepted)
                return separation * 2.4 + _social_force(index, same, alignment, center)
            var other: int = bucket[(bucket_start + bucket_step) % bucket.size()]
            visits += 1; _visits += 1
            if other == index: continue
            _comparisons += 1
            var difference := position - positions[other]
            var distance2 := difference.length_squared()
            if distance2 > NEIGHBOR_RADIUS * NEIGHBOR_RADIUS: continue
            accepted += 1
            if distance2 < 1.0:
                if distance2 < 0.000001:
                    difference = Vector3(1 if index > other else -1, 0, 0) * 0.01
                    distance2 = 0.0001
                separation += difference / maxf(distance2, 0.04)
            if species_ids[other] == species_ids[index]:
                same += 1; alignment += velocities[other]; center += positions[other]
    _max_visits = maxi(_max_visits, visits)
    _max_neighbors = maxi(_max_neighbors, accepted)
    return separation * 2.4 + _social_force(index, same, alignment, center)

func _social_force(index: int, same: int, alignment: Vector3, center: Vector3) -> Vector3:
    if same == 0: return Vector3.ZERO
    return (alignment / same - velocities[index]) * 0.8 + (center / same - positions[index]) * 0.32

func _decide(index: int) -> Vector3:
    var p := positions[index]
    var route: PackedVector3Array = route_points[species_ids[index]]
    var target := route_indices[index]
    if p.distance_squared_to(route[target]) < 1.8:
        target = (target + 1) % route.size(); route_indices[index] = target
    var desired := p.direction_to(route[target]) * 1.35
    if schooling_enabled: desired += _neighbors(index)
    for obstacle in obstacles:
        var center: Vector3 = obstacle.center
        var offset := p - center
        var radius: float = obstacle.radius + FISH_RADIUS
        var ahead := p + velocities[index] * 1.1
        if offset.length() < radius + 2.0 or ahead.distance_to(center) < radius + 1.0:
            var outward := offset.normalized() if offset.length_squared() > 0.001 else Vector3.RIGHT
            desired += outward * 5.0
    for axis in 3:
        if p[axis] < bounds_min[axis] + 4.0: desired[axis] += (bounds_min[axis] + 4.0 - p[axis]) * 2.0
        if p[axis] > bounds_max[axis] - 4.0: desired[axis] -= (p[axis] - bounds_max[axis] + 4.0) * 2.0
    return desired.limit_length(MAX_SPEED)

func step(delta: float, tiered: bool = true) -> Dictionary:
    if not configuration_error.is_empty() or positions.is_empty():
        return {"ok": false, "error": "simulation is not configured"}
    if not is_finite(delta) or delta <= 0.0 or delta > 0.1:
        return {"ok": false, "error": "fixed delta must be finite and in (0, 0.1]"}
    var started := Time.get_ticks_usec()
    _visits = 0; _comparisons = 0; _max_visits = 0; _max_neighbors = 0; _truncations = 0
    _grid.clear()
    if schooling_enabled:
        for i in positions.size():
            var key := _cell(positions[i])
            if not _grid.has(key): _grid[key] = []
            _grid[key].append(i)
    var grid_finished := Time.get_ticks_usec()
    var updates := [0, 0, 0]
    for i in positions.size():
        var tier := tier_ids[i]
        if not tiered or (_tick + i) % TIER_INTERVALS[tier] == 0:
            _commands[i] = _decide(i); updates[tier] += 1
    var decisions_finished := Time.get_ticks_usec()
    var obstacle_contacts := 0
    var boundary_contacts := 0
    for i in positions.size():
        var previous_speed := velocities[i].length()
        var previous_direction := velocities[i].normalized()
        var desired := _commands[i]
        var speed := move_toward(previous_speed, clampf(desired.length(), MIN_SPEED, MAX_SPEED), MAX_ACCELERATION * delta * 0.7)
        var cosine_limit := (previous_speed * previous_speed + speed * speed - pow(MAX_ACCELERATION * delta, 2)) / maxf(2.0 * previous_speed * speed, 0.000001)
        var allowed_turn := minf(MAX_TURN_RATE * delta, acos(clampf(cosine_limit, -1.0, 1.0)))
        var direction := previous_direction
        if desired.length_squared() > 0.000001:
            var target_direction := desired.normalized()
            var angle := previous_direction.angle_to(target_direction)
            if angle > 0.000001:
                # Explicit rotation also handles exactly opposing headings.
                var axis := previous_direction.cross(target_direction).normalized()
                if axis.length_squared() < 0.01:
                    axis = previous_direction.cross(Vector3.UP).normalized()
                    if axis.length_squared() < 0.01: axis = Vector3.RIGHT
                direction = previous_direction.rotated(axis, minf(angle, allowed_turn))
        velocities[i] = direction * speed
        speeds[i] = speed
        curvatures[i] = previous_direction.angle_to(direction) / maxf(speed * delta, 0.000001)
        var next := positions[i] + velocities[i] * delta
        # Explicit emergency constraints, counted separately; this is not a
        # physical collision solver and contacts must remain visible in reports.
        for obstacle in obstacles:
            var offset: Vector3 = next - obstacle.center
            var radius: float = obstacle.radius + FISH_RADIUS
            if offset.length_squared() < radius * radius:
                next = obstacle.center + (offset.normalized() if offset.length_squared() > 0.000001 else Vector3.RIGHT) * radius
                obstacle_contacts += 1
        var clamped := next.clamp(bounds_min, bounds_max)
        if clamped != next: boundary_contacts += 1
        positions[i] = clamped
    _tick += 1
    var finished := Time.get_ticks_usec()
    return {"ok": true, "tick": _tick, "count": positions.size(),
        "total_elapsed_ms": (finished - started) / 1000.0,
        "grid_ms": (grid_finished - started) / 1000.0,
        "decision_ms": (decisions_finished - grid_finished) / 1000.0,
        "integration_ms": (finished - decisions_finished) / 1000.0,
        "tier_counts": _tier_counts.duplicate(), "tier_updates": updates,
        "updates": updates[0] + updates[1] + updates[2],
        "candidate_visits": _visits, "neighbor_comparisons": _comparisons,
        "max_candidate_visits": _max_visits, "max_neighbors": _max_neighbors,
        "neighbor_truncations": _truncations, "grid_cells": _grid.size(),
        "obstacle_contacts": obstacle_contacts, "boundary_contacts": boundary_contacts}
