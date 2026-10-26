extends RefCounted
## Prototype-only route/body adapter. The factory's original controller remains
## responsible for clips, phase, native waves, fin constraints and species dispatch.
## Only its private-path body steering is replaced after each native pose step.
## Center placement, profile parameters and native timing are not changed here.
const MAX_HISTORY := 512
var native
var error := ""
var _time := 0.0
var _times: Array[float] = []
var _yaws: Array[float] = []
var _pitches: Array[float] = []
var _direction := Vector3.RIGHT
var _back := Vector3.BACK
var _basis := Basis.IDENTITY
var _yaw_rate := 0.0
var _pitch_rate := 0.0
var _steering: Array = []
var _history_capped := false

func configure(controller, initial_velocity: Vector3) -> Dictionary:
    native = controller
    if not native._ready or native._bones.size() < 4:
        return _fail("Factory controller/body chain is not ready")
    if not native._profile.actions.has("Turn") or not is_finite(float(native._profile.actions.Turn.bend_radians)) or float(native._profile.actions.Turn.bend_radians) <= 0.0:
        return _fail("A finite positive authored Turn bend limit is required")
    if not initial_velocity.is_finite(): return _fail("Initial school velocity is nonfinite")
    _direction = initial_velocity.normalized() if initial_velocity.length_squared() > 0.000001 else Vector3.RIGHT
    var yaw := atan2(-_direction.z * float(native._profile.head_sign), _direction.x * float(native._profile.head_sign))
    var pitch := atan2(_direction.y, Vector2(_direction.x, _direction.z).length())
    _times = [0.0]; _yaws = [yaw]; _pitches = [pitch]
    if not _orient(): return _fail("Initial school orientation is invalid")
    return {"ok": true}

func _fail(message: String) -> Dictionary:
    error = message
    return {"ok": false, "error": message}

func _orient() -> bool:
    var right := _direction * float(native._profile.head_sign)
    var back := right.cross(Vector3.UP)
    if back.length_squared() < 0.000001:
        back = _back - right * _back.dot(right)
        if back.length_squared() < 0.000001: back = right.cross(Vector3.RIGHT)
    back = back.normalized()
    var up := back.cross(right).normalized()
    _basis = Basis(right, up, back)
    _back = back
    return _basis.is_finite() and absf(_basis.determinant() - 1.0) < 0.0001

func orientation() -> Basis:
    return _basis

func observe(velocity: Vector3, delta: float) -> Dictionary:
    if not error.is_empty(): return _fail(error)
    if not velocity.is_finite() or not is_finite(delta) or delta <= 0.0:
        return _fail("School observation requires finite velocity and positive delta")
    var yaw := _yaws[-1]
    var pitch := _pitches[-1]
    # A stationary agent retains its last direction; vertical motion retains yaw.
    if velocity.length_squared() > 0.000001:
        _direction = velocity.normalized()
        if Vector2(_direction.x, _direction.z).length_squared() > 0.000001:
            var raw := atan2(-_direction.z * float(native._profile.head_sign), _direction.x * float(native._profile.head_sign))
            yaw += wrapf(raw - yaw, -PI, PI)
        pitch = atan2(_direction.y, Vector2(_direction.x, _direction.z).length())
    _yaw_rate = (yaw - _yaws[-1]) / delta
    _pitch_rate = (pitch - _pitches[-1]) / delta
    _time += delta
    _times.append(_time); _yaws.append(yaw); _pitches.append(pitch)
    var retain := float(native._profile.body_delay_seconds) + 0.25
    while _times.size() > 2 and _times[1] < _time - retain:
        _times.pop_front(); _yaws.pop_front(); _pitches.pop_front()
    if _times.size() > MAX_HISTORY:
        _history_capped = true
        _times.pop_front(); _yaws.pop_front(); _pitches.pop_front()
    if not is_finite(_yaw_rate) or not is_finite(_pitch_rate) or not _orient():
        return _fail("School orientation/rate became nonfinite")
    return {"ok": true}

func _sample(at: float) -> Vector2:
    if at <= _times[0]: return Vector2(_yaws[0], _pitches[0])
    if at >= _times[-1]: return Vector2(_yaws[-1], _pitches[-1])
    var low := 0
    var high := _times.size() - 1
    while high - low > 1:
        var middle := (low + high) / 2
        if _times[middle] <= at: low = middle
        else: high = middle
    var weight := (at - _times[low]) / (_times[high] - _times[low])
    return Vector2(lerpf(_yaws[low], _yaws[high], weight), lerpf(_pitches[low], _pitches[high], weight))

func step(delta: float) -> Dictionary:
    if not error.is_empty(): return _fail(error)
    if not is_finite(delta) or delta < 0.0: return _fail("Native pose step requires finite nonnegative delta")
    native.step(delta) # Exactly one original controller step, no phase rewriting.
    var delay := float(native._profile.body_delay_seconds)
    var bends: Array[Vector2] = []
    var total := 0.0
    var previous := _sample(_time)
    for i in native._bones.size():
        var current := _sample(_time - delay * float(native._body_distances[i]))
        var bend := Vector2(current.x - previous.x, (current.y - previous.y) * float(native._profile.head_sign)) if i > 0 else Vector2.ZERO
        bends.append(bend); total += bend.length(); previous = current
    var amplitude := float(native._motion.body_amplitude)
    # Sum of actual steering joint magnitudes cannot exceed the authored Turn
    # engineering limit. Native wave/base clip are preserved, not amplified.
    var limit := float(native._profile.actions.Turn.bend_radians)
    var scale := minf(1.0, limit / maxf(total * absf(amplitude), 0.000001))
    _steering.clear()
    for i in native._bones.size():
        var bend: Vector2 = bends[i] * scale
        var neutral: Quaternion = native._rest_rotations[i].slerp(native._base_rotations[i], float(native._profile.base_body_gain) * amplitude)
        var wave: float = native._bone_overlay[i].wave_radians
        var pose: Quaternion = (neutral * Quaternion(native._yaw_axes[i], (bend.x + wave) * amplitude) * Quaternion(native._pitch_axes[i], bend.y * amplitude)).normalized()
        if not pose.is_finite(): return _fail("School body pose became nonfinite")
        native._skeleton.set_bone_pose_rotation(native._bones[i], pose)
        _steering.append({"bone": native._skeleton.get_bone_name(native._bones[i]), "yaw_radians": bend.x * amplitude, "pitch_radians": bend.y * amplitude})
    native._skeleton.force_update_all_bone_transforms()
    return {"ok": true}

func snapshot() -> Dictionary:
    return {"source": "actual school velocity heading history", "observed_seconds": _time,
        "yaw_rate_rad_s": _yaw_rate, "pitch_rate_rad_s": _pitch_rate,
        "history_samples": _times.size(), "history_cap_reached": _history_capped,
        "steering_limit_radians": native._profile.actions.Turn.bend_radians,
        "body_steering": _steering.duplicate(true), "error": error,
        "scope": "Prototype route/body coupling; native base wave/fin phases retained; no biomechanics or full-body path guarantee"}
