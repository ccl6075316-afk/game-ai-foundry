extends RefCounted
## Foundry bounded existing-rig motion. No assets, saves or external services are loaded.
## Hall owns visibility/pause; only step() advances. set_action/replay queue until step.

var _carrier: Node3D
var _model: Node3D
var _player: AnimationPlayer
var _skeleton: Skeleton3D
var _profile: Dictionary
var _origin := Vector3.ZERO
var _bones: Array[int] = []
var _yaw_axes: Array[Vector3] = []
var _pitch_axes: Array[Vector3] = []
var _rest_rotations: Array[Quaternion] = []
var _base_rotations: Array[Quaternion] = []
var _bend_weights: Array[float] = []
var _head_anchor := Vector3.ZERO
var _time := 0.0
var _clip_time := 0.0
var _action := "Swim"
var _action_epoch := 0.0
var _blend_start := -100.0
var _blend_clip_start := 0.0
var _from: Dictionary = {}
var _to: Dictionary = {}
var _pending_action := ""
var _pending_restart := false
var _ready := false
var _computed_envelope := 0.0
var _bend_sum := 0.0
var _joint_max := 0.0
var _head_path := Vector3.ZERO
var _heading := Vector3.RIGHT
var _pitch := 0.0
var _bone_overlay: Array[Dictionary] = []

func configure(carrier: Node3D, model: Node3D, player: AnimationPlayer, skeleton: Skeleton3D, profile: Dictionary, tank_origin: Vector3 = Vector3.ZERO) -> Dictionary:
    _ready = false
    _carrier = carrier
    _model = model
    _player = player
    _skeleton = skeleton
    _profile = profile.duplicate(true)
    _origin = tank_origin
    _bones.clear()
    _yaw_axes.clear()
    _pitch_axes.clear()
    _rest_rotations.clear()
    _base_rotations.clear()
    _bend_weights.clear()
    var failures: Array[String] = []
    for key in ["species", "real_length_cm", "head_sign", "base_clip", "body_bones", "tank_size_m", "path_radii_m", "vertical_amplitude_m", "envelope_radius_m", "period_seconds", "transition_seconds", "body_delay_seconds", "base_body_gain", "actions"]:
        if not profile.has(key): failures.append("Missing profile field: " + key)
    if not failures.is_empty(): return {"ok":false,"failures":failures}
    if not _player.has_animation(profile.base_clip): return {"ok":false,"failures":["Base clip missing"]}
    for bone_name in profile.body_bones:
        var index := _skeleton.find_bone(str(bone_name))
        if index < 0: failures.append("Missing bone: " + str(bone_name))
        else: _bones.append(index)
    if not failures.is_empty() or _bones.size() < 4: return {"ok":false,"failures":failures + ["Body chain incomplete"]}
    var model_to_skeleton: Basis = (_model.global_basis.inverse() * _skeleton.global_basis).inverse().orthonormalized()
    var weight_total := 0.0
    for i in _bones.size():
        var rest := _skeleton.get_bone_global_rest(_bones[i])
        _yaw_axes.append((rest.basis.inverse() * model_to_skeleton * Vector3.UP).normalized())
        _pitch_axes.append((rest.basis.inverse() * model_to_skeleton * Vector3.BACK).normalized())
        _rest_rotations.append(_skeleton.get_bone_rest(_bones[i]).basis.get_rotation_quaternion())
        _base_rotations.append(_skeleton.get_bone_pose_rotation(_bones[i]))
        var weight := 0.0 if i == 0 else pow(float(i) / (_bones.size() - 1), 0.65)
        _bend_weights.append(weight)
        weight_total += weight
    for i in _bend_weights.size(): _bend_weights[i] /= weight_total
    var skeleton_to_carrier := _carrier.global_transform.affine_inverse() * _skeleton.global_transform
    _head_anchor = skeleton_to_carrier * _skeleton.get_bone_global_rest(_bones[0]).origin
    var tail_anchor := skeleton_to_carrier * _skeleton.get_bone_global_rest(_bones[-1]).origin
    if signf(_head_anchor.x - tail_anchor.x) != float(profile.head_sign):
        return {"ok":false,"failures":["head_sign disagrees with actual rest head/tail direction"]}
    _computed_envelope = _skin_envelope(skeleton_to_carrier)
    var length_m := float(profile.real_length_cm) / 100.0
    if _computed_envelope <= 0.0 or _computed_envelope * 1.05 + 0.02 * length_m > float(profile.envelope_radius_m):
        return {"ok":false,"failures":["Declared envelope cannot contain computed skin/bone-chain envelope"],"required_envelope_m":_computed_envelope * 1.05 + 0.02 * length_m}
    var tank: Array = profile.tank_size_m
    var radii: Array = profile.path_radii_m
    var envelope := float(profile.envelope_radius_m)
    if float(tank[0]) * .5 < float(radii[0]) + envelope or float(tank[2]) * .5 < float(radii[1]) + envelope or float(tank[1]) * .5 < float(profile.vertical_amplitude_m) + envelope:
        return {"ok":false,"failures":["Tank too small for path plus posed envelope"]}
    _player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
    _player.get_animation(profile.base_clip).loop_mode = Animation.LOOP_LINEAR
    _player.speed_scale = 1.0
    _player.play(profile.base_clip)
    _ready = true
    _action = "Swim"
    _pending_action = ""
    _pending_restart = false
    seek(0.0)
    return {"ok":true,"failures":[],"envelope_radius_m":envelope,"computed_skin_envelope_m":_computed_envelope}

func _tree_distance(first: int, second: int) -> float:
    var ancestors := {}
    var at := first
    var distance := 0.0
    while at >= 0:
        ancestors[at] = distance
        var parent := _skeleton.get_bone_parent(at)
        if parent >= 0: distance += (_skeleton.get_bone_global_rest(at).origin - _skeleton.get_bone_global_rest(parent).origin).length()
        at = parent
    at = second
    distance = 0.0
    while at >= 0:
        if ancestors.has(at): return distance + float(ancestors[at])
        var parent := _skeleton.get_bone_parent(at)
        if parent >= 0: distance += (_skeleton.get_bone_global_rest(at).origin - _skeleton.get_bone_global_rest(parent).origin).length()
        at = parent
    return INF

func _skin_envelope(skeleton_to_carrier: Transform3D) -> float:
    # Triangle inequality bound valid for any rotations: head-to-joint chain length
    # plus the skin bind lever. CLI restricts base animation to rotation-only changes.
    var radius := 0.0
    var scale_max := maxf(skeleton_to_carrier.basis.x.length(), maxf(skeleton_to_carrier.basis.y.length(), skeleton_to_carrier.basis.z.length()))
    var chain_lengths: Array[float] = []
    for i in _skeleton.get_bone_count(): chain_lengths.append(_tree_distance(_bones[0], i))
    for node in _model.find_children("*", "MeshInstance3D", true, false):
        var mesh := node as MeshInstance3D
        var skin := mesh.skin
        if skin == null: return INF
        var mesh_to_skeleton := _skeleton.global_transform.affine_inverse() * mesh.global_transform
        var bind_bones: Array[int] = []
        for bind in skin.get_bind_count():
            var index := skin.get_bind_bone(bind)
            if index < 0: index = _skeleton.find_bone(skin.get_bind_name(bind))
            bind_bones.append(index)
        for surface in mesh.mesh.get_surface_count():
            var arrays := mesh.mesh.surface_get_arrays(surface)
            var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
            var joints: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
            var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
            if vertices.is_empty() or joints.size() == 0: return INF
            var influences: int = joints.size() / vertices.size()
            for v in vertices.size():
                var point := mesh_to_skeleton * vertices[v]
                for j in influences:
                    if weights[v * influences + j] <= 0.000001: continue
                    var bone: int = bind_bones[joints[v * influences + j]]
                    if bone < 0: return INF
                    var lever := (point - _skeleton.get_bone_global_rest(bone).origin).length()
                    radius = maxf(radius, (chain_lengths[bone] + lever) * scale_max)
    return radius

func set_action(action: String, restart: bool = false) -> bool:
    if not _ready or not _profile.actions.has(action): return false
    _pending_action = action
    _pending_restart = restart
    return true

func replay() -> void:
    if _ready:
        _pending_action = _action if _pending_action.is_empty() else _pending_action
        _pending_restart = true

func _target(action: String, epoch: float) -> Dictionary:
    var config: Dictionary = _profile.actions[action]
    var angle := TAU * epoch / float(_profile.period_seconds)
    var amplitude := float(_profile.vertical_amplitude_m) * float(config.vertical_sign)
    return {"radius":float(config.radius_scale),"bend":float(config.bend_radians),"a":amplitude * cos(angle),"b":-amplitude * sin(angle),"clip":float(config.clip_speed)}

func _coefficients(at: float) -> Dictionary:
    var u := clampf((at - _blend_start) / float(_profile.transition_seconds), 0.0, 1.0)
    var weight := u * u * (3.0 - 2.0 * u)
    var result := {}
    for key in _to: result[key] = lerpf(float(_from[key]), float(_to[key]), weight)
    return result

func _integrated_clip(at: float) -> float:
    var duration := float(_profile.transition_seconds)
    var elapsed := maxf(0.0, at - _blend_start)
    var u := clampf(elapsed / duration, 0.0, 1.0)
    var integrated_blend := duration * (u * u * u - 0.5 * pow(u, 4)) + maxf(0.0, elapsed - duration)
    return _blend_clip_start + float(_from.clip) * elapsed + (float(_to.clip) - float(_from.clip)) * integrated_blend

func seek(seconds: float) -> void:
    if not _ready or not is_finite(seconds): return
    _time = maxf(0.0, seconds)
    _action_epoch = 0.0
    _from = _target(_action, 0.0)
    _to = _from.duplicate()
    _blend_start = 0.0
    _blend_clip_start = 0.0
    _clip_time = _time * float(_to.clip)
    _pending_action = ""
    _pending_restart = false
    _restore_base()
    _player.seek(fposmod(_clip_time, _player.get_animation(_profile.base_clip).length), true)
    _player.advance(0.0)
    _capture_base_and_pose()

func step(delta: float) -> void:
    if not _ready or not is_finite(delta) or delta < 0.0: return
    if not _pending_action.is_empty():
        var selected := _pending_action
        var restart := _pending_restart
        _pending_action = ""
        _pending_restart = false
        if restart:
            _action = selected
            seek(0.0)
        elif selected != _action:
            _from = _coefficients(_time)
            _to = _target(selected, _time)
            _blend_start = _time
            _blend_clip_start = _clip_time
            _action_epoch = _time
            _action = selected
    _restore_base()
    var before := _clip_time
    _time += delta
    _clip_time = _integrated_clip(_time)
    _player.advance(maxf(0.0, _clip_time - before))
    _capture_base_and_pose()

func _restore_base() -> void:
    for i in _bones.size(): _skeleton.set_bone_pose_rotation(_bones[i], _base_rotations[i])

func _path(at: float) -> Vector3:
    var coeff := _coefficients(at)
    var angle := TAU * at / float(_profile.period_seconds)
    return _origin + Vector3(float(_profile.path_radii_m[0]) * float(coeff.radius) * sin(angle), float(coeff.a) * sin(angle) + float(coeff.b) * cos(angle), float(_profile.path_radii_m[1]) * float(coeff.radius) * cos(angle))

func _velocity(at: float) -> Vector3:
    return (_path(at + .002) - _path(at - .002)) / .004

func _yaw(at: float) -> float:
    var velocity := _velocity(at)
    return atan2(-velocity.z * float(_profile.head_sign), velocity.x * float(_profile.head_sign))

func _path_pitch(at: float) -> float:
    var velocity := _velocity(at)
    return atan2(velocity.y, Vector2(velocity.x, velocity.z).length())

func _capture_base_and_pose() -> void:
    _bend_sum = 0.0
    _joint_max = 0.0
    _bone_overlay.clear()
    var delay := float(_profile.body_delay_seconds)
    var reference_rate := TAU / float(_profile.period_seconds) * float(_profile.path_radii_m[0]) / float(_profile.path_radii_m[1])
    for i in _bones.size():
        var base := _skeleton.get_bone_pose_rotation(_bones[i])
        _base_rotations[i] = base
        var t := _time - delay * float(i) / (_bones.size() - 1)
        var yaw_rate := wrapf(_yaw(t + .02) - _yaw(t - .02), -PI, PI) / .04
        var curve := clampf(absf(yaw_rate) / reference_rate, 0.0, 1.0)
        var delayed_coeff := _coefficients(t)
        var bend := -signf(yaw_rate) * float(delayed_coeff.bend) * curve * _bend_weights[i]
        var pitch_bend := 0.0
        if i > 0:
            var previous_t := _time - delay * float(i - 1) / (_bones.size() - 1)
            pitch_bend = clampf(_path_pitch(t) - _path_pitch(previous_t), -.04, .04) * float(_profile.head_sign)
        var neutral := _rest_rotations[i].slerp(base, float(_profile.base_body_gain))
        _skeleton.set_bone_pose_rotation(_bones[i], (neutral * Quaternion(_yaw_axes[i], bend) * Quaternion(_pitch_axes[i], pitch_bend)).normalized())
        _bone_overlay.append({"bone":_skeleton.get_bone_name(_bones[i]),"yaw_radians":bend,"pitch_radians":pitch_bend,"delay_seconds":_time-t})
        _bend_sum += absf(bend)
        _joint_max = maxf(_joint_max, absf(bend))
    _head_path = _path(_time)
    _heading = _velocity(_time).normalized()
    _pitch = _path_pitch(_time)
    var right := _heading * float(_profile.head_sign)
    var back := right.cross(Vector3.UP).normalized()
    var up := back.cross(right).normalized()
    var orientation := Basis(right, up, back)
    _carrier.transform = Transform3D(orientation, _head_path - orientation * _head_anchor)
    _skeleton.force_update_all_bone_transforms()

func snapshot() -> Dictionary:
    if not _ready: return {"ready":false}
    var head_world := _skeleton.global_transform * _skeleton.get_bone_global_pose(_bones[0]).origin
    var tail_world := _skeleton.global_transform * _skeleton.get_bone_global_pose(_bones[-1]).origin
    var remaining := maxf(0.0, float(_profile.transition_seconds) - (_time - _blend_start)) if _from != _to else 0.0
    var half := Vector3(float(_profile.tank_size_m[0]), float(_profile.tank_size_m[1]), float(_profile.tank_size_m[2])) * .5
    var path_local := _head_path - _origin
    var envelope := float(_profile.envelope_radius_m)
    var contained := absf(path_local.x) + envelope <= half.x and absf(path_local.y) + envelope <= half.y and absf(path_local.z) + envelope <= half.z
    var poses := {}
    for i in _bones.size():
        var q := _skeleton.get_bone_pose_rotation(_bones[i])
        poses[_skeleton.get_bone_name(_bones[i])] = [q.x,q.y,q.z,q.w]
    var parent := _carrier.get_parent_node_3d()
    var world_heading := (parent.global_basis * _heading).normalized() if parent != null else _heading
    return {"ready":true,"species":_profile.species,"action":_action,"pending_action":_pending_action,"state":"transition" if remaining > 0.0 else "steady","time":_time,"action_phase":fposmod((_time - _action_epoch) / float(_profile.period_seconds),1.0),"base_clip_time":_player.current_animation_position,"loop_seconds":float(_profile.period_seconds),"position":[_carrier.position.x,_carrier.position.y,_carrier.position.z],"head_path_local":[_head_path.x,_head_path.y,_head_path.z],"heading":[world_heading.x,world_heading.y,world_heading.z],"yaw":_yaw(_time),"pitch":_pitch,"head_world":[head_world.x,head_world.y,head_world.z],"tail_world":[tail_world.x,tail_world.y,tail_world.z],"bend_radians":_bend_sum,"max_bend_rad":_joint_max,"transition_remaining":remaining,"envelope_radius_m":envelope,"computed_skin_envelope_m":_computed_envelope,"inside_envelope":contained,"bone_poses":poses,"bone_overlays":_bone_overlay.duplicate(true)}
