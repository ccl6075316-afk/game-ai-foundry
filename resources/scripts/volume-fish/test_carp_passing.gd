extends SceneTree
## Run Godot --headless --path projects/fishing-2d/game --script <this file>.
## Deliberately omit the final overlap solver so a push-apart cannot pass as steering.
const Carp = preload("res://scripts/aquarium/carp_behaviour.gd")

func encounter(kind: String) -> bool:
    var first := Carp.new()
    var second := Carp.new()
    first.setup(0,.24,Vector3(-.63,.28,.09))
    second.setup(1,.275,Vector3(.61,.28,.09))
    first.heading = 0
    second.heading = PI
    if kind == "crossing":
        second.pos = Vector3(-.04,.28,-.43)
        second.heading = PI/2
    elif kind == "stationary":
        second.pos = Vector3(-.26,.28,.11)
        second.heading = 0
    var pair := [first,second]
    for fish in pair:
        fish.target = fish.pos + fish.forward()*1.6
        fish.speed = fish.length_m*.7
        fish.timer = 30
        fish.decision = 30
    if kind == "stationary":
        second.mode = Carp.Mode.REST
        second.speed = 0
    var smallest := INF
    var max_rate_change := 0.0
    var previous_rate := 0.0
    for frame in 450:
        var previous_heading := first.heading
        for fish in pair:
            fish.plan_passing(1./60.,pair)
        for fish in pair:
            fish.step(1./60.,pair,Vector3.ZERO,false)
        var yaw_rate := angle_difference(previous_heading,first.heading)*60.0
        max_rate_change = maxf(max_rate_change,absf(yaw_rate-previous_rate))
        previous_rate = yaw_rate
        var gap := Carp.capsule_gap(first.pos,first.axis()*first.length_m*.34,
            second.pos,second.axis()*second.length_m*.34).length()-.16*(first.length_m+second.length_m)
        smallest = minf(smallest,gap)
    print(kind," clearance_m=",smallest," final_x=",first.pos.x," max_yaw_rate_step=",max_rate_change)
    var passed := first.pos.x > second.pos.x+.08
    if kind == "crossing":
        passed = first.pos.x > -.04+first.length_m*.5 and second.pos.z > .09+second.length_m*.5
    return smallest > .025 and passed and max_rate_change < .18

func _initialize() -> void:
    var ok := true
    for kind in ["head_on","crossing","stationary"]:
        if not encounter(kind):
            ok = false
    quit(0 if ok else 1)
