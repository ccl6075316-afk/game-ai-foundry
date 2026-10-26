extends SceneTree
## Run with --headless --path <fishing-2d/game> --script <absolute path to this file>.
const Navigation = preload("res://scripts/aquarium/visitors/HallVisitorNavigation.gd")
const Crowd = preload("res://scripts/aquarium/visitors/HallVisitorCrowd.gd")
const Footprint = preload("res://scripts/aquarium/HallFootprint.gd")
var failures: Array[String] = []
var checks := 0
var sampled_segments := 0

func _initialize() -> void:
    call_deferred("_run")

func check(condition: bool, message: String) -> void:
    checks += 1
    if not condition: failures.append(message); push_error(message)

func verify_route(nav, path: PackedVector2Array, message: String) -> void:
    check(not path.is_empty(), message + " exists")
    for index in range(1, path.size()):
        for t in range(11):
            sampled_segments += 1
            if not nav.point_clear(path[index - 1].lerp(path[index], t / 10.0)):
                check(false, message + " crosses geometry"); return
    check(true, message + " continuous segment samples clear")

func _run() -> void:
    var nav = Navigation.new()
    var parcels := Footprint.initial()
    nav.rebuild([], [])
    check(nav.route(Vector2.ZERO, Vector2.ONE).is_empty(), "empty layout rejects routes")
    nav.rebuild(parcels, [])
    verify_route(nav, nav.route(Vector2(-6, -4), Vector2(6, 4)), "open hall path")
    var wall := {"kind": "wall", "at": [0, 0], "yaw": 0.0, "scale": 1.0, "length": 18, "door": false}
    nav.rebuild(parcels, [wall])
    check(nav.route(Vector2(0, -3), Vector2(0, 3)).is_empty(), "solid partition disconnects hall")
    wall.door = true
    nav.rebuild(parcels, [wall])
    var doorway := nav.route(Vector2(0, -3), Vector2(0, 3))
    verify_route(nav, doorway, "actual 1.2m doorway")
    for point in doorway:
        if absf(point.y) < .5: check(absf(point.x) <= .6 - nav.RADIUS, "door jamb clearance")
    wall.yaw = PI / 2; wall.length = 14
    nav.rebuild(parcels, [wall])
    verify_route(nav, nav.route(Vector2(-3, 0), Vector2(3, 0)), "rotated doorway")
    wall.at = [.5, .5]; wall.yaw = 0.0; wall.length = 18
    nav.rebuild(parcels, [wall])
    verify_route(nav, nav.route(Vector2(.5, -3), Vector2(.5, 3)), "doorway between grid columns")
    wall.yaw = PI / 2; wall.length = 14
    nav.rebuild(parcels, [wall])
    verify_route(nav, nav.route(Vector2(-3, .5), Vector2(3, .5)), "rotated doorway between grid rows")
    var tank := {"kind": "tank", "at": [0, 0], "yaw": PI / 4, "scale": .8}
    nav.rebuild(parcels, [tank])
    check(not nav.is_walkable(Vector2.ZERO), "transformed tank occupied")
    verify_route(nav, nav.route(Vector2(-5, 0), Vector2(5, 0)), "rotated scaled tank detour")
    nav.rebuild([[0, 0], [1, 0], [0, 1]], [])
    check(not nav.is_walkable(Vector2(1, 3)), "L-shaped parcel missing corner excluded")
    verify_route(nav, nav.route(Vector2(-6, 4), Vector2(1, -4)), "L-shaped parcel concave seam")
    nav.rebuild([[0, 0], [2, 0]], [])
    check(nav.route(Vector2(-6, -3), Vector2(6, -3)).is_empty(), "disconnected parcels reject route")

    var crowd = Crowd.new()
    root.add_child(crowd); crowd.set_process(false)
    check(crowd.resources_ready, "all current visitor resources load")
    if not crowd.resources_ready:
        print(JSON.stringify({"ok": false, "failures": failures, "resource_error": crowd.resource_error}))
        crowd.free(); quit(1); return
    var rows := [{"kind": "tank", "at": [0, -4.8], "yaw": 0.0, "scale": 1.0},
        {"kind": "tank", "at": [-5.7, -.15], "yaw": PI / 2, "scale": .65},
        {"kind": "bench", "at": [0, .85], "yaw": 0.0, "scale": 1.0},
        {"kind": "plinth", "at": [5.8, -3.5], "yaw": 0.0, "scale": 1.0}]
    crowd.set_layout(parcels, rows); crowd._process(.2)
    check(crowd.agents.size() == 24, "default hall spawns 24")
    check(crowd.groups.size() == 6 and crowd.get_child_count() == 6, "six nodes independent of eighteen appearances")
    var initial_snapshot: Dictionary = crowd.get_review_snapshot()
    check(initial_snapshot.active_variant_count == 18 and initial_snapshot.active_group_count == 6, "default24 covers all18 archetype-appearance variants")
    var observed: Dictionary = {}; var appearance_population := [0, 0, 0]
    for instance in initial_snapshot.instances:
        observed[instance.variant] = true
        appearance_population[instance.appearance_group] += 1
    check(appearance_population == [8, 8, 8], "default24 balances the three appearance groups")
    for archetype in ["adult_male", "adult_female", "elderly_male", "elderly_female", "boy", "girl"]:
        for appearance in ["white", "east_asian", "black"]:
            check(observed.has(archetype + "_" + appearance), "present variant " + archetype + "_" + appearance)
    var material_shared := true; var appearances_uploaded := true
    var gpu_readback := DisplayServer.get_name() != "headless"
    for group in crowd.groups:
        if group.material_override != crowd.material: material_shared = false
        if gpu_readback:
            var appearance_channels: Dictionary = {}
            for index in group.multimesh.visible_instance_count:
                appearance_channels[roundi(group.multimesh.get_instance_custom_data(index).a)] = true
            if not (appearance_channels.has(0) and appearance_channels.has(1) and appearance_channels.has(2)): appearances_uploaded = false
    check(material_shared, "all six groups share exactly one material")
    if gpu_readback: check(appearances_uploaded, "each sharedmesh uploads allthree appearance selectors in INSTANCE_CUSTOM.w")
    var initial_positions: Array = []
    for agent in crowd.agents: initial_positions.append(agent.position)
    var saw_watching := false
    var movement_clear := true
    var budget_held := true
    var separation_held := true
    for frame in 1800:
        var before: Array = []
        for agent in crowd.agents: before.append(agent.position)
        crowd._process(1.0 / 60)
        if crowd.last_route_requests > 2: budget_held = false
        for index in crowd.agents.size():
            var agent: Dictionary = crowd.agents[index]
            if agent.state == "watching": saw_watching = true
            for t in range(3):
                sampled_segments += 1
                if not crowd.navigation.point_clear(before[index].lerp(agent.position, t / 2.0)): movement_clear = false
        if frame % 60 == 0:
            for a in crowd.agents.size():
                for b in range(a + 1, crowd.agents.size()):
                    if crowd.agents[a].position.distance_to(crowd.agents[b].position) < crowd.SEPARATION - .001: separation_held = false
    var moved := 0
    for index in crowd.agents.size():
        if crowd.agents[index].position.distance_to(initial_positions[index]) > 1: moved += 1
    check(moved > 12, "majority of 24 visitors actually traverse hall")
    check(saw_watching, "visitors reach viewing stops")
    check(movement_clear, "actual crowd movement segments clear obstacles and parcel edges")
    check(separation_held, "bounded local occupancy preserves separation")
    check(budget_held, "route budget never exceeds two per frame")
    rows[0].fish_count = 5; rows[0].content = {"irrelevant": true}; rows[0].water = {"depth": .8}
    var content_revision: int = crowd.navigation.revision
    crowd.set_layout(parcels, rows)
    check(not crowd.dirty and crowd.navigation.revision == content_revision, "fish content and water do not invalidate geometry")
    crowd.set_paused(true)
    var previous_time: float = crowd.crowd_time
    crowd._process(.1)
    check(crowd.crowd_time == previous_time and not crowd.visible, "tank editor pause freezes and hides crowd")
    check(crowd.get_review_snapshot().active_group_count == 0, "hidden editor crowd has no active draw groups")
    crowd.set_paused(false)
    var population_revision: int = crowd.navigation.revision
    crowd.set_visitor_count(999)
    check(crowd.requested_count == 200 and crowd.agents.size() == 200, "hard cap 200 and default hall capacity (actual %d)" % crowd.agents.size())
    for frame in 120: crowd._process(1.0 / 60)
    check(crowd.navigation.revision == population_revision, "population and appearance distribution changes reuse geometry navigation")
    check(crowd.get_child_count() == 6, "trial stress population still six nodes")
    var allocated_instances := 0; var visible_instances := 0
    for group in crowd.groups:
        allocated_instances += group.multimesh.instance_count
        visible_instances += group.multimesh.visible_instance_count
        check(group.multimesh.visible_instance_count <= group.multimesh.instance_count, "nondivisible trialcap fits group buffer")
    check(allocated_instances == 204 and visible_instances == crowd.agents.size(), "six shared groups allocate bounded buffers and report actual visible population")
    crowd.set_visitor_count(-1)
    check(crowd.requested_count == 0 and crowd.agents.is_empty(), "negative count clamps to off")
    check(crowd.get_review_snapshot().active_group_count == 0, "off has no active draw groups")
    var revision: int = crowd.navigation.revision
    rows[2].at = [.25, .85]
    crowd.set_layout(parcels, rows); crowd._process(1)
    check(crowd.navigation.revision == revision, "zero crowd skips dirty navigation work")
    crowd.set_visitor_count(24); crowd._process(.2)
    check(crowd.agents.size() == 24 and crowd.navigation.revision > revision, "reenabling rebuilds latest layout")
    var valid_meshes: Array = []
    for group in crowd.groups: valid_meshes.append(group.multimesh.mesh)
    var valid_atlas = crowd.material.get_shader_parameter("visitor_atlas")
    var missing_meshes := valid_meshes.duplicate(); missing_meshes[4] = null
    check(not crowd.validate_resources(missing_meshes, crowd.material, valid_atlas), "missing child mesh rejects entire crowd")
    crowd.set_visitor_count(24); crowd._process(.2)
    var resource_status: Dictionary = crowd.get_review_snapshot()
    check(resource_status.active_count == 0 and not resource_status.resources_ready and not resource_status.resource_error.is_empty(), "invalid resources report zero active visitors with explicit error")
    for group in crowd.groups: check(group.multimesh.visible_instance_count == 0, "resource failure hides all groups")
    check(not crowd.validate_resources(valid_meshes, null, valid_atlas), "missing shared material safely rejected")
    check(not crowd.validate_resources(valid_meshes, crowd.material, null), "missing atlas safely rejected")
    missing_meshes = valid_meshes.duplicate(); missing_meshes[3] = null
    check(not crowd.validate_resources(missing_meshes, crowd.material, valid_atlas), "missing dedicated elderly mesh rejects entire crowd")
    check(crowd.validate_resources(valid_meshes, crowd.material, valid_atlas), "complete actual resources pass validation")
    crowd.set_visitor_count(24)
    check(crowd.agents.size() == 24, "valid resource recovery restores visible population")
    crowd.set_layout(parcels, [{"kind": "tank", "at": [0, 0], "yaw": 0.0, "scale": 20.0}])
    check(crowd.agents.is_empty(), "layout mutation immediately discards stale positions and routes")
    for group in crowd.groups: check(group.multimesh.visible_instance_count == 0, "stale crowd hidden immediately")
    crowd._process(.05)
    check(crowd.dirty, "repeated drag has bounded settle delay")
    crowd._process(.2)
    check(crowd.agents.is_empty() and not crowd.dirty, "fully blocked layout safely has zero actual visitors")
    var report := {"ok": failures.is_empty(), "checks": checks, "segment_samples": sampled_segments,
        "moved_more_than_1m": moved, "saw_watching": saw_watching, "failures": failures,
        "body_radius_m": Navigation.RADIUS, "grid_cell_m": Navigation.CELL,
        "archetypes": Crowd.MESH_NAMES, "appearance_groups": Crowd.APPEARANCE_NAMES, "variant_count": initial_snapshot.active_variant_count,
        "allocated_draw_groups": crowd.groups.size(), "trial_population_cap": Crowd.MAX_VISITORS,
        "gpu_custom_data_readback": "passed" if gpu_readback and appearances_uploaded else "not_run_headless_dummy_renderer",
        "nav_rebuild_usec": crowd.navigation.rebuild_usec}
    report.source_sha256 = {}
    for path in ["res://scripts/aquarium/visitors/HallVisitorNavigation.gd", "res://scripts/aquarium/visitors/HallVisitorCrowd.gd",
        "res://scripts/aquarium/AquariumHall3D.gd", crowd.material.shader.resource_path, get_script().resource_path]:
        report.source_sha256[path] = FileAccess.get_sha256(path)
    for group in crowd.groups:
        var path: String = group.multimesh.mesh.resource_path
        report.source_sha256[path] = FileAccess.get_sha256(path)
    for path in [Crowd.ASSET_ROOT + "visitor_material.tres", valid_atlas.resource_path]:
        report.source_sha256[path] = FileAccess.get_sha256(path)
    print(JSON.stringify(report))
    for argument in OS.get_cmdline_user_args():
        if argument.begins_with("--report="):
            var output := FileAccess.open(argument.trim_prefix("--report="), FileAccess.WRITE)
            output.store_string(JSON.stringify(report, "  ") + "\n")
    crowd.free()
    quit(0 if failures.is_empty() else 1)
