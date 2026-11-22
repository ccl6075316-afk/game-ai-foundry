extends SceneTree
## Invoke with --fixed-fps 30 --script <this file> -- <frames directory>.
const Hall = preload("res://scripts/aquarium/AquariumHall3D.gd")

func _initialize() -> void:
    run.call_deferred()

func run() -> void:
    var hall = Hall.new()
    hall.configure_save("user://walk-review-unused-%d.json" % Time.get_ticks_usec(), false)
    root.add_child(hall)
    var crowd = hall.visitor_crowd
    crowd.set_process(false)
    crowd.set_visitor_count(1)
    crowd._process(0.2)
    if crowd.agents.size() != 1:
        quit(1)
        return
    var visitor: Dictionary = crowd.agents[0]
    var start := Vector2(-2.6, -1.6)
    var turn := Vector2(0.0, -1.6)
    var end := Vector2(0.0, -2.0)
    var route: PackedVector2Array = crowd.navigation.route(start, turn)
    var last_leg: PackedVector2Array = crowd.navigation.route(turn, end)
    if route.is_empty() or last_leg.is_empty():
        push_error("No navigable review route")
        quit(1)
        return
    route.append_array(last_leg.slice(1))
    crowd.occupancy.clear()
    crowd._occupy(start, 0)
    visitor.position = start
    visitor.speed = .82
    visitor.yaw = -PI / 2
    visitor.phase = 0.0
    visitor.timer = 999
    visitor.face = Vector2(0, -4.8)
    visitor.motion = 0.0
    var camera := Camera3D.new()
    hall.world.add_child(camera)
    camera.position = Vector3(.65, 1.66, 2.4)
    camera.look_at(Vector3(-1.2, .94, -1.7))
    camera.fov = 40
    camera.make_current()
    var output := OS.get_cmdline_user_args()[0]
    DirAccess.make_dir_recursive_absolute(output)
    hall.viewport.size = Vector2i(960,540)
    for frame in 180:
        if frame == 12:
            visitor.path = route
            visitor.waypoint = 0
            visitor.state = "walking"
            visitor.target = end
        crowd._process(1.0/30)
        await RenderingServer.frame_post_draw
        if hall.viewport.get_texture().get_image().save_png(output.path_join("%04d.png" % frame)) != OK:
            quit(1)
            return
    print("HALL_WALK ", visitor.state, " ", visitor.position)
    var reached_stop: bool = visitor.state == "watching" and visitor.position.is_equal_approx(end)
    crowd.set_visitor_count(24)
    hall.editor_camera.make_current()
    for tick in 150:
        crowd._process(1.0/30)
    await RenderingServer.frame_post_draw
    var result: Error = hall.viewport.get_texture().get_image().save_png(output.path_join("overview.png"))
    hall.queue_free()
    await process_frame
    await process_frame
    quit(0 if reached_stop and result == OK else 1)
