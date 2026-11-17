extends "../smooth/Gait.gd"

const BITE_TIME := 1.47
const INGEST_FINISH := 2.12
const FIXED_UPPER := Vector3(.83069998, -.190940, 0.)
const FIXED_LOWER := Vector3(.82669998, -.191960, 0.)
const CAPTURE_CENTER := Vector3(.822, -.199, -.027)
const SWEEP_STATIONS := [0.7, 2.7, 5.8, 8.4, 11., 13.3, 15., 16.]

func oral_frame() -> Dictionary:
    var high := point(FIXED_UPPER, upper)
    var low := point(FIXED_LOWER, lower)
    var head_basis := skeleton.global_basis * skeleton.get_bone_global_pose(head).basis * skeleton.get_bone_global_rest(head).basis.inverse()
    var along := head_basis.x.normalized()
    var separation := high - low
    var up := separation.normalized()
    var crosswise := -(head_basis.z - head_basis.z.dot(up) * up).normalized()
    var lengthwise_up := (up - along * along.dot(up)).normalized()
    return {
        "upper": high, "lower": low, "center": high.lerp(low, .5),
        "gap": separation.length(), "up": up,
        "crosswise": Basis(crosswise, up, crosswise.cross(up)).orthonormalized(),
        "forward": Basis(along, lengthwise_up, along.cross(lengthwise_up)).orthonormalized(),
    }

func travel(t: float, large: bool) -> float:
    var time := t - BITE_TIME
    var pursuit := .54 * time + .17 * time * time + .037 * time * time * time
    if time <= 0.:
        return pursuit
    var clear_rate := .42 if large else .68
    return clear_rate * time + (.54 - clear_rate) * (1. - exp(-3.6 * time)) / 3.6

func prey_free(t: float, large: bool) -> Vector3:
    var time := t - BITE_TIME
    if large:
        return CAPTURE_CENTER + Vector3(.078 * time, .007 * sin(2.8 * time), .039 * time)
    return CAPTURE_CENTER + Vector3(.092 * time, .012 * sin(4.1 * time), .018 * sin(3.8 * time))

func bend(t: float) -> float:
    var time := t - BITE_TIME
    var envelope := blend(t, BITE_TIME, 1.72) * (1. - blend(t, 2.54, 3.64))
    return sin(TAU * time * (1.02 - .09 * time)) * envelope

func apply(t: float, large: bool) -> Dictionary:
    swim.seek(.31 + 1.12 * t)
    carrier.transform = Transform3D.IDENTITY
    var gape := curve(t, [[0., 0.], [.71, 0.], [1.01, .18], [1.27, .91],
        [BITE_TIME, .69], [1.62, .45], [1.84, .61], [2.16, 0.], [STOP, 0.]])
    if large:
        gape = curve(t, [[0., 0.], [.65, 0.], [1.0, .24], [1.25, 1.],
            [BITE_TIME, .68], [1.62, .56], [2.12, .53], [STOP, .52]])
    var extend := curve(t, [[0., 0.], [1.01, 0.], [1.30, .52], [BITE_TIME, .71],
        [1.70, .26], [2.02, .39 if large else .13], [2.2, .31 if large else 0.]])
    extend = minf(extend, gape * 4.)
    var lift := curve(t, [[0., 0.], [.66, .04], [1.2, .88],
        [BITE_TIME, .72], [1.89, .29], [2.7, 0.]])
    var previous := 0.
    var turn := blend(t, .15, 1.21) * (1. - blend(t, 1.05, 1.67))
    for i in range(chain.size()):
        var bone := chain[i]
        var phase := float(i) * .036
        var sweep := float(SWEEP_STATIONS[i]) * bend(t - phase) if large else 0.
        var direction := sweep + float(i) * .64 * turn
        var axis := skeleton.get_bone_global_rest(bone).basis.inverse() * Vector3.UP
        var addition := Quaternion(axis.normalized(), deg_to_rad(direction - previous))
        skeleton.set_bone_pose_rotation(bone, skeleton.get_bone_pose_rotation(bone) * addition)
        previous = direction

    rotate(head, -2.4 * lift + .37 * sin(t * 5.8) * (1. - gape))
    rotate(lower, 25. * gape)
    rotate(upper, 2.4 * extend)
    offset(upper, Vector3(.005, -.0018, 0.) * extend)
    offset(floor, Vector3(.002, -.0065, 0.) * gape)
    var heading := curve(t, [[0., 14.], [.61, 9.], [1.14, 2.],
        [BITE_TIME, -2.], [2.03, -5.], [3.16, -9.]])
    if large:
        heading += bend(t) * 9.
    carrier.rotation.y = deg_to_rad(heading)
    skeleton.force_update_all_bone_transforms()
    var height := -.035 * (1. - blend(t, .17, 1.43))
    var tailward := -.285 * (1. - blend(t, .05, BITE_TIME)) - .13 * blend(t, 1.85, STOP)
    var match := blend(t, 1.15, BITE_TIME) * (1. - blend(t, BITE_TIME, 1.88))
    var center: Vector3 = oral_frame().center
    carrier.position = Vector3(travel(t, large), height, tailward) + (CAPTURE_CENTER - center) * match
    skeleton.force_update_all_bone_transforms()
    return {"t": t, "gape": gape, "protrusion": extend, "head": lift,
        "bend": bend(t) if large else 0., "travel": travel(t, large),
        "heading": heading, "carrier": carrier.position}
