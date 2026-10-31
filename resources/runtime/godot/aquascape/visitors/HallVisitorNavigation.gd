extends RefCounted
## Shared conservative grid. Every edge stays inside the inflated free-cell union.
const Footprint = preload("res://scripts/aquarium/HallFootprint.gd")
const CELL := .2
# V2's eighteen appearance/pose sweeps reach .3567 m; reserve over 13 mm.
const RADIUS := .37
const CLEARANCE := RADIUS + CELL * .5
const NEIGHBORS := [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]
var grid := AStarGrid2D.new()
var cells: Array[Vector2i] = []
var components: Dictionary = {}
var component_cells: Dictionary = {}
var viewing_goals: Dictionary = {}
var obstacles: Array = []
var parcels: Array = []
var rebuild_usec := 0
var revision := 0

func rebuild(new_parcels: Array, rows: Array) -> void:
    var started := Time.get_ticks_usec()
    revision += 1
    parcels = new_parcels.duplicate(true)
    cells.clear(); components.clear(); component_cells.clear(); viewing_goals.clear(); obstacles.clear()
    if parcels.is_empty():
        rebuild_usec = Time.get_ticks_usec() - started
        return
    var extent: Rect2 = Footprint.extent(parcels)
    var first := Vector2i(floori(extent.position.x / CELL), floori(extent.position.y / CELL))
    var last := Vector2i(ceili(extent.end.x / CELL), ceili(extent.end.y / CELL))
    grid.region = Rect2i(first, last - first)
    grid.cell_size = Vector2.ONE * CELL
    grid.offset = Vector2.ZERO
    grid.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_NEVER
    grid.default_compute_heuristic = AStarGrid2D.HEURISTIC_MANHATTAN
    grid.default_estimate_heuristic = AStarGrid2D.HEURISTIC_MANHATTAN
    grid.update()
    for row in rows:
        var data: Dictionary = row.get("data", row)
        var scale_factor := float(data.get("scale", 1.0))
        var transform := Transform2D(float(data.get("yaw", 0)), Vector2(float(data.at[0]), float(data.at[1])))
        # Godot 3D positive Y rotation maps (x,z) with the opposite 2D angle.
        transform = Transform2D(-float(data.get("yaw", 0)), transform.origin).scaled_local(Vector2.ONE * scale_factor)
        if data.kind == "wall":
            var length := float(data.length)
            if data.get("door", false):
                _obstacle(transform, Rect2(-length / 2, -.09, (length - 1.2) / 2, .18))
                _obstacle(transform, Rect2(.6, -.09, (length - 1.2) / 2, .18))
            else: _obstacle(transform, Rect2(-length / 2, -.09, length, .18))
        elif data.kind == "tank": _obstacle(transform, Rect2(-3.1, -1.6, 6.2, 3.2))
        elif data.kind == "bench": _obstacle(transform, Rect2(-1, -.34, 2, .68))
        else: _obstacle(transform, Rect2(-.55, -.55, 1.1, 1.1))
    for y in range(first.y, last.y):
        for x in range(first.x, last.x):
            var id := Vector2i(x, y)
            var point := position_of(id)
            # Include the .1 m exterior half-wall width, including concave parcel corners.
            var radius := CLEARANCE + .1
            var box := AABB(Vector3(point.x - radius, 0, point.y - radius), Vector3(radius * 2, 1, radius * 2))
            grid.set_point_solid(id, not Footprint.contains(parcels, box, 0))
    # Rasterize only each obstacle's inflated bounding rectangle; no scene scans during walking.
    for obstacle in obstacles:
        var rect: Rect2 = obstacle.inflated_bounds
        var lo := Vector2i(floori(rect.position.x / CELL), floori(rect.position.y / CELL))
        var hi := Vector2i(ceili(rect.end.x / CELL), ceili(rect.end.y / CELL))
        for y in range(maxi(lo.y, first.y), mini(hi.y + 1, last.y)):
            for x in range(maxi(lo.x, first.x), mini(hi.x + 1, last.x)):
                var id := Vector2i(x, y)
                if obstacle.rect.grow(CLEARANCE / obstacle.scale).has_point(obstacle.inverse * position_of(id)):
                    grid.set_point_solid(id)
    for y in range(first.y, last.y):
        for x in range(first.x, last.x):
            var id := Vector2i(x, y)
            if not grid.is_point_solid(id): cells.append(id)
    _label_components()
    for row in rows:
        var data: Dictionary = row.get("data", row)
        if data.kind != "tank": continue
        var transform := Transform2D(-float(data.get("yaw", 0)), Vector2(float(data.at[0]), float(data.at[1]))).scaled_local(Vector2.ONE * float(data.get("scale", 1)))
        for local in [Vector2(-2, -2.8), Vector2(0, -2.8), Vector2(2, -2.8), Vector2(-2, 2.8), Vector2(0, 2.8), Vector2(2, 2.8), Vector2(-4.3, 0), Vector2(4.3, 0)]:
            var id := cell_at(transform * local)
            if not components.has(id): continue
            var component: int = components[id]
            if not viewing_goals.has(component): viewing_goals[component] = []
            viewing_goals[component].append({"point": position_of(id), "face": transform.origin})
    rebuild_usec = Time.get_ticks_usec() - started

func _obstacle(transform: Transform2D, rect: Rect2) -> void:
    var scale_factor := transform.x.length()
    obstacles.append({"rect": rect, "inverse": transform.affine_inverse(), "scale": scale_factor,
        "inflated_bounds": transform * rect.grow(CLEARANCE / scale_factor)})

func _label_components() -> void:
    var component := 0
    for start in cells:
        if components.has(start): continue
        var queue: Array[Vector2i] = [start]
        components[start] = component
        var head := 0
        while head < queue.size():
            var current := queue[head]; head += 1
            for direction in NEIGHBORS:
                var next: Vector2i = current + direction
                if not grid.region.has_point(next) or grid.is_point_solid(next) or components.has(next): continue
                components[next] = component; queue.append(next)
        component_cells[component] = queue
        component += 1

func cell_at(point: Vector2) -> Vector2i:
    return Vector2i(roundi(point.x / CELL), roundi(point.y / CELL))

func position_of(id: Vector2i) -> Vector2:
    return Vector2(id) * CELL

func is_walkable(point: Vector2) -> bool:
    return components.has(cell_at(point))

func route(start: Vector2, finish: Vector2) -> PackedVector2Array:
    var from := cell_at(start); var to := cell_at(finish)
    if not components.has(from) or not components.has(to) or components[from] != components[to]: return PackedVector2Array()
    return grid.get_point_path(from, to)

func choose_goal(point: Vector2, rng: RandomNumberGenerator) -> Dictionary:
    var component: int = components.get(cell_at(point), -1)
    if component < 0: return {}
    var goals: Array = viewing_goals.get(component, [])
    if not goals.is_empty(): return goals[rng.randi_range(0, goals.size() - 1)]
    var available: Array = component_cells[component]
    if available.is_empty(): return {}
    var target := position_of(available[rng.randi_range(0, available.size() - 1)])
    return {"point": target, "face": target, "wander": true}

func point_clear(point: Vector2, radius: float = RADIUS) -> bool:
    # Independent exact footprint query for verification; walking uses the precomputed grid.
    if parcels.is_empty(): return false
    var box := AABB(Vector3(point.x - radius - .1, 0, point.y - radius - .1), Vector3((radius + .1) * 2, 1, (radius + .1) * 2))
    if not Footprint.contains(parcels, box, 0): return false
    for obstacle in obstacles:
        if obstacle.rect.grow(radius / obstacle.scale).has_point(obstacle.inverse * point): return false
    return true
