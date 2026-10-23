extends RefCounted
## Opt-in trial adapter for VolumeFishMotion / FoundryFishMotion, revision 132.
## Path time is warped; body and fin clocks remain independent wall-time clocks.
## Coupled to bounded controller's _time/_clip_time/_integrated_clip contract.
## No production installation, species dispatch, asset changes, or random state.

var controller
var config: Dictionary
var elapsed := 0.0
var dropped_seconds := 0.0
var substeps := 0
var travel_rate := 1.0
var body_amplitude := 1.0
var fin_amplitude := 1.0
var _remainder := 0.0
var _clip_length := 1.0
var _drive := 0.0

func configure(motion, settings: Dictionary, clip_length: float) -> Dictionary:
    controller = motion
    config = settings.duplicate(true)
    _clip_length = clip_length
    for key in ["cycle_seconds", "propel_seconds", "edge_seconds", "speed_floor", "speed_peak", "speed_response_seconds", "amplitude_response_seconds", "body_hz", "fin_hz", "body_coast", "body_propel", "fin_coast", "fin_propel"]:
        if not config.has(key) or not is_finite(float(config[key])):
            return {"ok":false,"failures":["Missing/nonfinite gait setting: " + key]}
    if not is_finite(_clip_length) or _clip_length <= 0.0 or float(config.speed_floor) <= 0.0 or float(config.speed_peak) < float(config.speed_floor) or float(config.propel_seconds) <= 2.0 * float(config.edge_seconds) or float(config.cycle_seconds) <= float(config.propel_seconds) or float(config.edge_seconds) <= 0.0 or float(config.speed_response_seconds) <= 0.0 or float(config.amplitude_response_seconds) <= 0.0:
        return {"ok":false,"failures":["Invalid gait timing or travel bounds"]}
    for key in ["body_coast", "body_propel", "fin_coast", "fin_propel"]:
        if float(config[key]) < 0.0 or float(config[key]) > 2.5:
            return {"ok":false,"failures":["Amplitude outside controller range"]}
    # Reject configurations that would silently clamp during any action.
    var minimum_clip_speed := INF
    for action in controller._profile.actions.values():
        var speed := float(action.clip_speed)
        if not is_finite(speed) or speed <= 0.0:
            return {"ok":false,"failures":["Gait requires positive finite action clip speeds"]}
        minimum_clip_speed = minf(minimum_clip_speed, speed)
    for key in ["body_hz", "fin_hz"]:
        if float(config[key]) < 0.0 or float(config[key]) * _clip_length / (float(config.speed_floor) * minimum_clip_speed) > 3.0:
            return {"ok":false,"failures":["Frequency exceeds independent controller range"]}
    restart()
    return {"ok":true,"failures":[]}

func restart() -> void:
    elapsed = 0.0
    dropped_seconds = 0.0
    substeps = 0
    _remainder = 0.0
    travel_rate = float(config.speed_floor)
    body_amplitude = float(config.body_coast)
    fin_amplitude = float(config.fin_coast)
    _drive = 0.0
    controller.set_motion_controls({"body_amplitude":body_amplitude,"body_frequency":float(config.body_hz) * _clip_length / travel_rate,"fin_amplitude":fin_amplitude,"fin_frequency":float(config.fin_hz) * _clip_length / travel_rate}, true)
    controller.set_action("Swim", true)
    controller.step(0.0)
    _retain_steering()

func set_action(action: String) -> bool:
    # Match native queue-until-step semantics: no intermediate posed frame.
    return controller.set_action(action)

func _envelope(at: float) -> float:
    var phase := fposmod(at, float(config.cycle_seconds))
    var edge := float(config.edge_seconds)
    return smoothstep(0.0, edge, phase) * (1.0 - smoothstep(float(config.propel_seconds) - edge, float(config.propel_seconds), phase))

func step(delta: float) -> void:
    if not is_finite(delta) or delta <= 0.0: return
    # Bound work after stalls. Pause slows the trial instead of fast-forwarding.
    var accepted := minf(delta, 0.25)
    dropped_seconds += delta - accepted
    _remainder += accepted
    var h := 1.0 / 120.0
    var count := mini(30, floori((_remainder + 0.00000001) / h))
    for i in count:
        _tick(h)
    _remainder = maxf(0.0, _remainder - count * h)

func _tick(h: float) -> void:
    # Resolve action clip integration before computing exact clock compensation.
    # The zero-delta internal pose is never presented or sampled separately.
    if not controller._pending_action.is_empty(): controller.step(0.0)
    _drive = _envelope(elapsed + h * 0.5)
    var target := lerpf(float(config.speed_floor), float(config.speed_peak), _drive)
    var tau := float(config.speed_response_seconds)
    var decay := exp(-h / tau)
    var travel_delta := target * h + (travel_rate - target) * tau * (1.0 - decay)
    travel_rate = target + (travel_rate - target) * decay
    var blend := 1.0 - exp(-h / float(config.amplitude_response_seconds))
    body_amplitude = lerpf(body_amplitude, lerpf(float(config.body_coast), float(config.body_propel), _drive), blend)
    fin_amplitude = lerpf(fin_amplitude, lerpf(float(config.fin_coast), float(config.fin_propel), _drive), blend)
    var clip_delta: float = controller._integrated_clip(controller._time + travel_delta) - controller._clip_time
    assert(clip_delta > 0.0, "Gait requires a positive clip rate")
    var body_frequency := float(config.body_hz) * _clip_length * h / clip_delta
    var fin_frequency := float(config.fin_hz) * _clip_length * h / clip_delta
    assert(body_frequency <= 3.000001 and fin_frequency <= 3.000001, "Gait frequency would be clipped")
    controller.set_motion_controls({"body_amplitude":body_amplitude,"body_frequency":body_frequency,"fin_amplitude":fin_amplitude,"fin_frequency":fin_frequency}, true)
    controller.step(travel_delta)
    _retain_steering()
    elapsed += h
    substeps += 1

func _retain_steering() -> void:
    # Native amplitude scales steering as well as propulsion. Preserve its exact
    # delayed curvature while coasting; reduce base clip and wave only.
    for i in controller._bones.size():
        var overlay: Dictionary = controller._bone_overlay[i]
        var neutral: Quaternion = controller._rest_rotations[i].slerp(controller._base_rotations[i], float(controller._profile.base_body_gain) * body_amplitude)
        var yaw: float = float(overlay.yaw_radians) + float(overlay.wave_radians) * body_amplitude
        var pitch: float = float(overlay.pitch_radians)
        controller._skeleton.set_bone_pose_rotation(controller._bones[i], (neutral * Quaternion(controller._yaw_axes[i], yaw) * Quaternion(controller._pitch_axes[i], pitch)).normalized())
    controller._skeleton.force_update_all_bone_transforms()

func snapshot() -> Dictionary:
    return {"wall_seconds":elapsed,"drive":_drive,"gait":"propel" if fposmod(elapsed, float(config.cycle_seconds)) < float(config.propel_seconds) else "coast","travel_rate":travel_rate,"body_amplitude":body_amplitude,"fin_amplitude":fin_amplitude,"body_hz":config.body_hz,"fin_hz":config.fin_hz,"substeps":substeps,"dropped_seconds":dropped_seconds}
