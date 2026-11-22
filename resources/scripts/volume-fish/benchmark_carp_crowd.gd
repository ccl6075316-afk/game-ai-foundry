extends SceneTree
## Use the game project, Compatibility renderer and --fixed-fps 60. Pass
## -- --carp-group --count=200 (or another count). One physics step per draw.
const Carp = preload("res://scripts/aquarium/carp_behaviour.gd")
const WARMUP := 60
const SAMPLES := 180

class TimedTank extends "res://scripts/aquarium/CarpBehaviourReview.gd":
    var behaviour_usec := 0
    func _step_motion(dt: float) -> void:
        var start := Time.get_ticks_usec()
        super._step_motion(dt)
        behaviour_usec = Time.get_ticks_usec()-start

func _initialize() -> void:
    run.call_deferred()

func stats(times: Array[float]) -> Array:
    times.sort()
    return [times[times.size()/2],times[ceili(.95*times.size())-1]]

func run() -> void:
    var count := 200
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--count="):
            count = arg.trim_prefix("--count=").to_int()
    assert(count >= 18 and "--carp-group" in OS.get_cmdline_user_args())
    DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
    var tank := TimedTank.new()
    root.add_child(tank)
    current_scene = tank
    tank.set_physics_process(false)
    var layers := clampi(ceili(count/72.0),1,5)
    var columns := ceili(sqrt(count*1.34/layers))
    var rows := ceili(float(count)/(layers*columns))
    var bounds := tank._decor_bounds()
    for i in count:
        var f: Carp = tank.agents[i] if i < 18 else Carp.new()
        var level := floori(float(i)/(rows*columns))
        var row := floori(float(i)/columns)%rows
        var x := (i%columns+.35+.25*(level%2))/columns
        var z := (row+.35+.25*(level%2))/rows
        var p := Vector3(lerpf(-2.65,2.65,x),lerpf(.15,1.39,(level+.5)/layers),lerpf(-2.66,1.27,z))
        f.tank_scale = tank.tank_scale
        f.obstacles = bounds
        f.setup(i,.24+.15*float(i*7%18)/17.0,p)
        f.pos = f.bounded(p)
        f.planning_due = fmod(i*.047,.12)
        if i >= 18:
            tank._mount_fish(f)
    assert(tank.entries.size() == count and tank.agents.size() == count)
    tank._feed()
    tank.food_left = tank.pellets.get_child_count()/2
    var behaviour: Array[float] = []
    var updates: Array[float] = []
    var frames: Array[float] = []
    var draws: Array[float] = []
    var previous := 0
    for i in WARMUP+SAMPLES+1:
        await process_frame
        var start := Time.get_ticks_usec()
        if i > WARMUP:
            frames.append((start-previous)/1000.0)
            draws.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
        if i == WARMUP+SAMPLES:
            break
        previous = start
        tank._advance(1.0/60.0)
        if i >= WARMUP:
            updates.append((Time.get_ticks_usec()-start)/1000.0)
            behaviour.append(tank.behaviour_usec/1000.0)
    var visible := 0
    for f: Carp in tank.agents:
        visible += int(tank.camera.is_position_in_frustum(f.pos))
    print("CARP_BENCH ",JSON.stringify({"count":count,"visible_centres":visible,"samples":SAMPLES,
        "behaviour_ms":stats(behaviour),"whole_update_ms":stats(updates),
        "frame_ms":stats(frames),"draw_calls":stats(draws)}))
    quit(0 if visible == count else 1)
