extends SceneTree
## Small adapter contract checks with real Skeleton3D nodes and a tiny fake native
## controller. Actual fish/fin/material gates remain separate regression/GPU work.
class NativeFixture:
    extends RefCounted
    var _ready := true
    var _bones := [0, 1, 2, 3]
    var _profile := {"head_sign": 1, "body_delay_seconds": 0.2, "base_body_gain": 1.0, "actions": {"Turn": {"bend_radians": 0.3}}}
    var _body_distances := [0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0]
    var _rest_rotations := [Quaternion.IDENTITY, Quaternion.IDENTITY, Quaternion.IDENTITY, Quaternion.IDENTITY]
    var _base_rotations := _rest_rotations.duplicate()
    var _yaw_axes := [Vector3.UP, Vector3.UP, Vector3.UP, Vector3.UP]
    var _pitch_axes := [Vector3.BACK, Vector3.BACK, Vector3.BACK, Vector3.BACK]
    var _motion := {"body_amplitude": 1.0}
    var _bone_overlay: Array = []
    var _skeleton := Skeleton3D.new()
    var _time := 0.0
    var calls := 0
    var fin_expected := Quaternion.IDENTITY
    func _init():
        for i in 5:
            _skeleton.add_bone("body_%d" % i if i < 4 else "fin")
            if i > 0: _skeleton.set_bone_parent(i, i - 1)
    func step(delta: float):
        _time += delta; calls += 1; _bone_overlay.clear()
        for i in 4:
            var wave := sin(_time * 3.0 + i) * 0.03
            _base_rotations[i] = Quaternion(Vector3.RIGHT, sin(_time) * 0.02)
            _skeleton.set_bone_pose_rotation(i, _base_rotations[i] * Quaternion(Vector3.UP, wave + 0.1))
            _bone_overlay.append({"wave_radians": wave})
        fin_expected = Quaternion(Vector3.FORWARD, sin(_time * 2.0) * 0.12)
        _skeleton.set_bone_pose_rotation(4, fin_expected)

var adapter_script
var checks: Array = []
var output := ""
func _initialize(): call_deferred("run")
func check(passed: bool, name: String): checks.append({"test": name, "passed": passed})
func fresh(velocity := Vector3.RIGHT) -> Dictionary:
    var native := NativeFixture.new()
    root.add_child(native._skeleton)
    var adapter = adapter_script.new()
    var configured: Dictionary = adapter.configure(native, velocity)
    check(configured.ok, "fixture adapter configuration")
    return {"native": native, "adapter": adapter}
func release(ctx: Dictionary): ctx.native._skeleton.free()
func rotation_error(a: Quaternion, b: Quaternion) -> float:
    var relative := (a.normalized().inverse() * b.normalized()).normalized()
    return 2.0 * atan2(Vector3(relative.x, relative.y, relative.z).length(), absf(relative.w))
func run():
    output = ProjectSettings.globalize_path("res://../plans/reviews/fish-school-motion-v2/adapter-contract").simplify_path()
    adapter_script = load("res://scripts/aquarium/fish_school/FishSchoolMotionAdapter.gd")
    var source_hash := FileAccess.get_sha256(adapter_script.resource_path)
    var ctx := fresh(Vector3(cos(3.13), 0, -sin(3.13)))
    ctx.adapter.observe(Vector3(cos(-3.13), 0, -sin(-3.13)), 1.0 / 60.0)
    check(absf(float(ctx.adapter.snapshot().yaw_rate_rad_s)) < 2.0, "yaw seam unwrap avoids false full-circle turn")
    var basis: Basis = ctx.adapter.orientation()
    ctx.adapter.observe(Vector3.ZERO, 1.0 / 60.0)
    check(basis.is_equal_approx(ctx.adapter.orientation()), "stationary velocity retains valid prior orientation")
    var vertical := true
    for velocity in [Vector3.UP, Vector3.DOWN, Vector3.RIGHT]:
        var observed: Dictionary = ctx.adapter.observe(velocity, 1.0 / 60.0)
        basis = ctx.adapter.orientation()
        vertical = vertical and observed.ok and basis.is_finite() and absf(basis.determinant() - 1.0) < 0.0001
    check(vertical, "vertical and reversed headings keep finite right-handed orientation")
    release(ctx)
    ctx = fresh()
    var exact_wave := true
    var exact_fin := true
    for frame in 120:
        ctx.adapter.observe(Vector3.RIGHT, 1.0 / 120.0)
        ctx.adapter.step(1.0 / 120.0)
        for i in 4:
            var expected: Quaternion = ctx.native._base_rotations[i] * Quaternion(Vector3.UP, ctx.native._bone_overlay[i].wave_radians)
            exact_wave = exact_wave and rotation_error(expected, ctx.native._skeleton.get_bone_pose_rotation(i)) < 0.00001
        exact_fin = exact_fin and rotation_error(ctx.native.fin_expected, ctx.native._skeleton.get_bone_pose_rotation(4)) < 0.00001
    check(exact_wave, "straight school motion preserves native base and wave while removing private-path bend")
    check(exact_fin, "native fin local poses survive adapter body recomposition")
    check(ctx.native.calls == 120 and absf(ctx.native._time - 1.0) < 0.000001, "one native pose step per adapter step with unchanged clock delta")
    release(ctx)
    ctx = fresh()
    var before := 0.0
    var after := 0.0
    var mixed := false
    for frame in 120:
        var seconds := float(frame + 1) / 120.0
        var yaw := seconds * 0.8 if seconds <= 0.5 else 0.4 - (seconds - 0.5) * 0.8
        ctx.adapter.observe(Vector3(cos(yaw), 0, -sin(yaw)), 1.0 / 120.0)
        ctx.adapter.step(1.0 / 120.0)
        var rows: Array = ctx.adapter.snapshot().body_steering
        if frame == 47:
            for row in rows: before += float(row.yaw_radians)
        if frame == 107:
            for row in rows: after += float(row.yaw_radians)
        if frame == 65: mixed = float(rows[1].yaw_radians) > 0.0 and float(rows[3].yaw_radians) < 0.0
    check(before < -0.1 and after > 0.1 and mixed, "turn reversal propagates down delayed body instead of flipping whole chain together")
    release(ctx)
    ctx = fresh()
    for frame in 60:
        var pitch := float(frame + 1) / 60.0 * 0.4
        ctx.adapter.observe(Vector3(cos(pitch), sin(pitch), 0), 1.0 / 60.0)
        ctx.adapter.step(1.0 / 60.0)
    var pitch_sum := 0.0
    for row in ctx.adapter.snapshot().body_steering: pitch_sum += float(row.pitch_radians)
    check(pitch_sum < -0.05, "rising path pitch produces delayed pitch bend")
    for frame in 2000: ctx.adapter.observe(Vector3.RIGHT, 0.00001)
    var snapshot: Dictionary = ctx.adapter.snapshot()
    check(snapshot.history_samples <= adapter_script.MAX_HISTORY and snapshot.history_cap_reached, "dense observations have bounded history and explicit cap evidence")
    check(not ctx.adapter.observe(Vector3(NAN, 0, 0), 0.01).ok, "nonfinite observation is rejected explicitly")
    release(ctx)
    check(source_hash == FileAccess.get_sha256(adapter_script.resource_path), "adapter source unchanged during test")
    var ok := true
    for entry in checks: ok = ok and entry.passed
    DirAccess.make_dir_recursive_absolute(output)
    var report := {"schema_version": 1, "command": "fish.school.motion.adapter-contract", "ok": ok, "status": "done" if ok else "failed", "next_action": "human_review" if ok else "fix_input", "source_sha256": source_hash, "checks": checks, "scope": "External tiny native fixture plus actual Skeleton3D; no production fish geometry, fin-contact or visual acceptance", "failures": []}
    FileAccess.open(output.path_join("adapter-contract.validation.json"), FileAccess.WRITE).store_string(JSON.stringify(report, "  ") + "\n")
    print(JSON.stringify({"ok": ok, "checks": checks}))
    quit(0 if ok else 1)
