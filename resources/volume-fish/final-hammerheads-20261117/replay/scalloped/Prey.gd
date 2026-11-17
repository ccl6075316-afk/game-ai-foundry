extends "../smooth/Prey.gd"

const ScallopedGait = preload("Gait.gd")

func pose(gait, t: float, large: bool) -> Dictionary:
    var lip: Dictionary = gait.oral_frame()
    var center: Vector3 = lip.center
    var gather: float = gait.blend(t, 1.32, ScallopedGait.BITE_TIME)
    var orientation: Basis = lip.crosswise if large else lip.forward
    var neutral := Basis(Vector3.UP, 1.18 if large else -.16)
    var native: Vector3 = gait.prey_free(t, large)
    position = native.lerp(center, gather)
    basis = neutral.slerp(orientation, gather)

    var pad: float = lip.gap * .5
    var past := 0.
    if large:
        var twist: float = gait.bend(t - .10) - gait.bend(t)
        mesh_instance.mesh = fish(t, pad, gather, twist)
    else:
        mesh_instance.mesh = squid
        past = gait.blend(t, ScallopedGait.BITE_TIME, ScallopedGait.INGEST_FINISH)
        var interior: Vector3 = gait.point(Vector3(.752, -.166, 0.), gait.head)
        position = position.lerp(interior, past)
    for eye in fish_eye:
        eye.visible = large

    var result := {
        "mouth_gap_m": lip.gap, "prey_center_to_mouth_m": position.distance_to(center),
        "prey_world": position, "inside_progress": past, "prey_rendered": mesh_instance.visible,
    }
    if large and t >= ScallopedGait.BITE_TIME:
        var half_gap := basis.y * pad
        result["upper_grip_m"] = (position + half_gap).distance_to(lip.upper)
        result["lower_grip_m"] = (position - half_gap).distance_to(lip.lower)
        result["visual_pad_m"] = pad
    return result
