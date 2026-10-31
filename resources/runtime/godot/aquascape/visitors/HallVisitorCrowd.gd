extends Node3D
## Six archetype draw groups share three appearances; visitors are data, never nodes.
const Navigation = preload("res://scripts/aquarium/visitors/HallVisitorNavigation.gd")
# Session trial limit; this does not define future hall or simulation capacity.
const MAX_VISITORS := 200
const ROUTES_PER_FRAME := 2
const BUCKET := .8
const SEPARATION := Navigation.RADIUS * 2.0 + .02
const MESH_NAMES := ["adult_male", "adult_female", "elderly_male", "elderly_female", "boy", "girl"]
const APPEARANCE_NAMES := ["white", "east_asian", "black"]
const ASSET_ROOT := "res://assets/visitors-v2/"
const VARIANT_COUNT := 18
var navigation = Navigation.new()
var requested_count := 24
var agents: Array = []
var groups: Array[MultiMeshInstance3D] = []
var material: ShaderMaterial
var resources_ready := false
var resource_error := ""
var rng := RandomNumberGenerator.new()
var layout_parcels: Array = []
var layout_rows: Array = []
var layout_signature := ""
var dirty := true
var rebuild_delay := 0.0
var paused := false
var crowd_time := 0.0
var last_update_usec := 0
var last_route_requests := 0
var route_cursor := 0
var occupancy: Dictionary = {}

func _ready() -> void:
    rng.seed = 810260
    var meshes: Array = []
    for mesh_name in MESH_NAMES:
        var mesh_path := ASSET_ROOT + "visitor_%s.res" % mesh_name
        meshes.append(load(mesh_path) if ResourceLoader.exists(mesh_path) else null)
    var material_path := ASSET_ROOT + "visitor_material.tres"
    var paint = load(material_path) if ResourceLoader.exists(material_path) else null
    var atlas = paint.get_shader_parameter("visitor_atlas") if paint is ShaderMaterial else null
    if not validate_resources(meshes, paint, atlas): return
    material = paint.duplicate()
    for index in MESH_NAMES.size():
        var node := MultiMeshInstance3D.new()
        node.name = "Visitors_" + MESH_NAMES[index]
        var multimesh := MultiMesh.new()
        multimesh.transform_format = MultiMesh.TRANSFORM_3D
        multimesh.use_custom_data = true
        multimesh.mesh = meshes[index]
        multimesh.instance_count = ceili(float(MAX_VISITORS) / MESH_NAMES.size())
        multimesh.visible_instance_count = 0
        node.multimesh = multimesh
        node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        node.custom_aabb = AABB(Vector3(-24, -.1, -22), Vector3(48, 3, 44))
        node.material_override = material
        add_child(node); groups.append(node)

func validate_resources(meshes: Array, paint: Variant, atlas: Variant) -> bool:
    resource_error = ""
    if meshes.size() != MESH_NAMES.size(): resource_error = "缺少游客模型。"
    else:
        for index in meshes.size():
            if not meshes[index] is Mesh or meshes[index].get_surface_count() == 0:
                resource_error = "游客模型无效：" + MESH_NAMES[index]
                break
    if resource_error.is_empty() and (not paint is ShaderMaterial or paint.shader == null):
        resource_error = "游客共享材质无效。"
    if resource_error.is_empty() and (not atlas is Texture2D or atlas.get_width() < 1 or atlas.get_height() < 1):
        resource_error = "游客像素贴图无效。"
    resources_ready = resource_error.is_empty()
    if not resources_ready:
        agents.clear(); occupancy.clear(); _hide_groups()
    return resources_ready

func set_visitor_count(count: int) -> void:
    requested_count = clampi(count, 0, MAX_VISITORS)
    agents.clear(); occupancy.clear(); _hide_groups()
    # The navigation snapshot remains usable when only the population changes.
    if not dirty: _populate()

func set_layout(parcels: Array, rows: Array) -> void:
    var geometry: Array = []
    for row in rows:
        var data: Dictionary = row.get("data", row)
        geometry.append({"kind": data.kind, "at": data.at.duplicate(), "yaw": data.get("yaw", 0.0),
            "scale": data.get("scale", 1.0), "length": data.get("length", 0.0), "door": data.get("door", false)})
    var signature := JSON.stringify([parcels, geometry])
    if signature == layout_signature: return
    layout_signature = signature
    layout_parcels = parcels.duplicate(true)
    layout_rows = geometry
    dirty = true; rebuild_delay = .12
    # Never render or advance people through a newly moved object while waiting for the grid.
    agents.clear(); occupancy.clear(); _hide_groups()

func set_paused(value: bool) -> void:
    paused = value
    visible = not value

func _hide_groups() -> void:
    for group in groups: group.multimesh.visible_instance_count = 0

func _populate() -> void:
    agents.clear(); occupancy.clear()
    if not resources_ready or navigation.cells.is_empty() or requested_count == 0: return
    var candidate_count: int = navigation.cells.size()
    var candidates: Array = navigation.cells.duplicate()
    for index in range(candidate_count - 1, 0, -1):
        var other := rng.randi_range(0, index)
        var swap: Vector2i = candidates[index]
        candidates[index] = candidates[other]; candidates[other] = swap
    # A randomized .8 m sublattice packs the requested stress population without
    # reducing clearance; arbitrary random sequential packing wastes floor space.
    var spaced: Array = []; var remainder: Array = []
    for id in candidates:
        if posmod(id.x, 4) == 0 and posmod(id.y, 4) == 0: spaced.append(id)
        else: remainder.append(id)
    candidates = spaced + remainder
    for attempt in range(candidate_count):
        if agents.size() >= requested_count: break
        var point: Vector2 = navigation.position_of(candidates[attempt])
        if not _space_free(point, -1, SEPARATION + .02): continue
        var index := agents.size()
        var group_index := index % MESH_NAMES.size()
        var agent := {"position": point, "target": point, "face": point, "path": PackedVector2Array(), "waypoint": 0,
            "yaw": rng.randf_range(-PI, PI), "phase": rng.randf_range(0, TAU), "palette": index % 8,
            "appearance": (index / MESH_NAMES.size() + group_index) % APPEARANCE_NAMES.size(), "group": group_index, "motion": 0.0,
            "timer": rng.randf_range(0, 1.5), "stuck": 0.0, "state": "waiting", "speed": rng.randf_range(.62, .9)}
        agents.append(agent); _occupy(point, index)
    _upload()

func _bucket(point: Vector2) -> Vector2i:
    return Vector2i(floori(point.x / BUCKET), floori(point.y / BUCKET))

func _occupy(point: Vector2, index: int) -> void:
    var key := _bucket(point)
    if not occupancy.has(key): occupancy[key] = []
    occupancy[key].append(index)

func _space_free(point: Vector2, except: int, distance: float = SEPARATION) -> bool:
    var key := _bucket(point)
    var reach := ceili(distance / BUCKET)
    for y in range(-reach, reach + 1):
        for x in range(-reach, reach + 1):
            var nearby: Array = occupancy.get(key + Vector2i(x, y), [])
            # Separation and bucket capacity keep this bounded even in crowded layouts.
            for index in nearby:
                if index != except and point.distance_squared_to(agents[index].position) < distance * distance: return false
    return occupancy.get(key, []).size() < 4 or occupancy.get(key, []).has(except)

func _process(delta: float) -> void:
    var started := Time.get_ticks_usec()
    last_route_requests = 0
    if not resources_ready or paused or requested_count == 0:
        last_update_usec = Time.get_ticks_usec() - started
        return
    if dirty:
        rebuild_delay -= delta
        if rebuild_delay > 0:
            last_update_usec = Time.get_ticks_usec() - started
            return
        navigation.rebuild(layout_parcels, layout_rows)
        dirty = false; _populate()
    var step := minf(delta, .05)
    crowd_time += step
    if material != null: material.set_shader_parameter("crowd_time", crowd_time)
    # Rotate scheduling order so sustained congestion cannot starve later visitors.
    for offset in agents.size():
        var index := (route_cursor + offset) % agents.size()
        var agent: Dictionary = agents[index]
        agent.timer -= step
        if agent.path.is_empty() and agent.timer <= 0 and last_route_requests < ROUTES_PER_FRAME:
            last_route_requests += 1
            var goal: Dictionary = navigation.choose_goal(agent.position, rng)
            if not goal.is_empty():
                agent.target = goal.point; agent.face = goal.face
                agent.path = navigation.route(agent.position, goal.point); agent.waypoint = 0
                agent.state = "walking"
            agent.timer = rng.randf_range(.5, 1.5)
        var moving := false
        if not agent.path.is_empty():
            var target: Vector2 = agent.path[agent.waypoint]
            var next: Vector2 = agent.position.move_toward(target, agent.speed * step)
            if _space_free(next, index):
                var before: Vector2 = agent.position
                occupancy[_bucket(before)].erase(index)
                agent.position = next; _occupy(next, index)
                moving = before.distance_squared_to(next) > .000001
                if moving:
                    var direction := next - before
                    agent.yaw = lerp_angle(agent.yaw, atan2(-direction.x, -direction.y), minf(1, step * 8))
                agent.stuck = 0.0
                if next.distance_squared_to(target) < .000001:
                    agent.waypoint += 1
                    if agent.waypoint >= agent.path.size():
                        agent.path = PackedVector2Array(); agent.state = "watching"
                        agent.timer = rng.randf_range(3, 8)
            else:
                agent.stuck += step
                if agent.stuck > 2:
                    agent.path = PackedVector2Array(); agent.state = "waiting"; agent.timer = rng.randf_range(.1, 1)
                    agent.stuck = 0.0
        elif agent.state == "watching":
            var direction: Vector2 = agent.face - agent.position
            if direction.length_squared() > .01: agent.yaw = lerp_angle(agent.yaw, atan2(-direction.x, -direction.y), minf(1, step * 5))
        agent.motion = move_toward(agent.motion, 1.0 if moving else 0.0, step * 5)
    if not agents.is_empty(): route_cursor = (route_cursor + ROUTES_PER_FRAME) % agents.size()
    _upload()
    last_update_usec = Time.get_ticks_usec() - started

func _upload() -> void:
    var used: Array[int] = []
    used.resize(groups.size()); used.fill(0)
    for agent in agents:
        var group: int = agent.group
        if group >= groups.size(): continue
        var mesh: MultiMesh = groups[group].multimesh
        mesh.set_instance_transform(used[group], Transform3D(Basis(Vector3.UP, agent.yaw), Vector3(agent.position.x, 0, agent.position.y)))
        mesh.set_instance_custom_data(used[group], Color(agent.phase, agent.motion, float(agent.palette), float(agent.appearance)))
        used[group] += 1
    for index in groups.size(): groups[index].multimesh.visible_instance_count = used[index]

func get_review_snapshot() -> Dictionary:
    var walking := 0; var watching := 0; var instances: Array = []
    var variants: Dictionary = {}; var active_groups: Dictionary = {}
    for agent in agents:
        if agent.motion > .1: walking += 1
        if agent.state == "watching": watching += 1
        var archetype: String = MESH_NAMES[agent.group]
        var appearance: String = APPEARANCE_NAMES[agent.appearance]
        var variant := archetype + "_" + appearance
        variants[variant] = true; active_groups[agent.group] = true
        instances.append({"position": [agent.position.x, agent.position.y], "target": [agent.target.x, agent.target.y],
            "state": agent.state, "yaw": agent.yaw, "variant": variant, "archetype": archetype,
            "appearance_group": agent.appearance, "appearance": appearance})
    return {"active_count": agents.size(), "requested_count": requested_count, "walking": walking, "watching": watching,
        "group_count": groups.size(), "active_group_count": active_groups.size() if visible and not paused else 0, "active_variant_count": variants.size(),
        "variant_capacity": VARIANT_COUNT, "trial_population_cap": MAX_VISITORS, "asset_directory": ASSET_ROOT.trim_suffix("/"),
        "last_update_usec": last_update_usec, "nav_rebuild_usec": navigation.rebuild_usec,
        "layout_revision": navigation.revision, "dirty": dirty, "paused": paused, "last_route_requests": last_route_requests,
        "resources_ready": resources_ready, "resource_error": resource_error, "instances": instances}
