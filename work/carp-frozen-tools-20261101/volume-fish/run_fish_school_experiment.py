"""Run sequential, source-bound fish school experiments; never edit production assets."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def bindings(game, mode):
    roots = [game / "scripts/aquarium", game / "assets/models/fish"] if mode != "simulation" else []
    files = [p for root in roots for p in root.rglob("*") if p.is_file() and not p.name.endswith(".uid") and not any(v.startswith(".") for v in p.relative_to(root).parts)]
    if mode == "simulation": files += list((game / "scripts/aquarium/fish_school").glob("*.gd"))
    files += [game / "project.godot", game / "scenes/fish_school_review.tscn"]
    return {"res://" + str(p.relative_to(game)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def allowed_review_root(game, review):
    # Compare a resolved target to only these two canonical in-project roots.
    # A nested folder, sibling version, or symlink escaping the project is invalid.
    base = game.resolve().parent / "plans/reviews"
    return review.resolve() in {base / "fish-school-v1", base / "fish-school-motion-v2"}


def protect_historical_v1(game, review):
    if review.name != "fish-school-v1": return
    current = {}
    for path in review.glob("*/benchmark.validation.json"):
        report = read(path)
        if report.get("ok") is not True or report.get("status") != "done": continue
        mode = report.get("inputs", {}).get("mode")
        if mode not in ("simulation", "static", "motion", "school-full", "school-tiered"): continue
        group = "simulation" if mode == "simulation" else "actual"
        if group not in current: current[group] = bindings(game, mode)
        if report["inputs"].get("bindings_sha256") != current[group]:
            raise ValueError("Historical fish-school-v1 evidence is frozen under its original sources; use fish-school-motion-v2 for changed source runs")


def log_errors(paths):
    errors, warnings = [], []
    for path in paths:
        if not path.exists(): continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            if not re.match(r"\s*(SCRIPT ERROR:|ERROR:)", line) and not re.search(r"SHADER ERROR:|shader compilation (?:error|failed)|Failed to load resource|Assertion failed", line, re.I): continue
            block = "\n".join(lines[i:i + 3])
            if line.strip() == 'ERROR: Condition "ret != noErr" is true. Returning: ""' and i + 1 < len(lines) and "get_system_ca_certificates (platform/macos/os_macos.mm:" in lines[i + 1]:
                warnings.append("macOS system CA certificate lookup warning")
            else: errors.append(str(path) + ": " + block)
    return sorted(set(errors)), sorted(set(warnings))


def valid(report, settings, current):
    actual = report.get("inputs", {})
    matches = all((isinstance(actual.get(k), (int, float)) and math.isclose(actual[k], v, rel_tol=0, abs_tol=1e-14)) if k == "fixed_simulation_delta_seconds" else actual.get(k) == v for k, v in settings.items())
    return report.get("ok") is True and report.get("status") == "done" and not actual.get("changed_during_run") and matches and actual.get("bindings_sha256") == current


def execute(args, settings, folder):
    command = [str(args.godot), "--path", str(args.game), "--audio-driver", "Dummy", "--disable-vsync", "--delta-smoothing", "disable", "--log-file", str(folder / "engine.log")]
    if settings["mode"] != "simulation": command += ["--rendering-method", args.rendering_method, "--rendering-driver", args.rendering_driver]
    command += ["--headless"] if settings["mode"] == "simulation" else ["--windowed", "--resolution", "1280x720"]
    command += ["res://scenes/fish_school_review.tscn", "--", f"--output={folder}", f"--count={settings['count']}", f"--mode={settings['mode']}", f"--samples={args.samples}", f"--warmup={args.warmup}", f"--seed={args.seed}"]
    command += ["--exclude-species=" + args.exclude_species]
    if settings["full_decisions"]: command.append("--full-decisions")
    if settings["mode"] == "school-tiered" and settings["count"] in (50, 200): command.append("--capture")
    env = dict(os.environ, DOTNET_ROOT=str(args.dotnet))
    env["PATH"] = str(args.dotnet) + os.pathsep + env.get("PATH", "")
    with (folder / "stdout.log").open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try: return process.wait(timeout=args.timeout), ""
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            # Kill the entire dedicated process group, including engine children.
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
            return -9, "timeout" if isinstance(exc, subprocess.TimeoutExpired) else "interrupted"


def summarize(review, state):
    # One complete source read per distinct binding set, reused as a frozen
    # summary snapshot. Never infer content identity from timestamps.
    snapshots = {}
    for case in state["cases"]:
        if case["status"] == "done":
            try:
                report = read(Path(case["report"]))
                key = "simulation" if case["settings"]["mode"] == "simulation" else "actual"
                if key not in snapshots: snapshots[key] = bindings(Path(state["game"]), case["settings"]["mode"])
                if not valid(report, case["settings"], snapshots[key]): raise ValueError("Case inputs are stale")
            except (OSError, ValueError, KeyError) as exc:
                case.update(status="failed", error=str(exc))
        if case["status"] == "failed" and not any(f.get("case") == case["id"] for f in state["failures"]):
            state["failures"].append({"case": case["id"], "code": "case_invalid", "kind": "validation", "message": case.get("error", "failed")})
    comparisons = []
    for prefix in ("sim", "school"):
        full = [c for c in state["cases"] if c["id"].startswith(prefix + "-full-") and c["status"] == "done"]
        for left in full:
            right = next((c for c in state["cases"] if c["id"] == left["id"].replace("-full-", "-tiered-") and c["status"] == "done"), None)
            if right is None: continue
            a, b = read(Path(left["report"])), read(Path(right["report"]))
            keys = ("count", "seed", "warmup_frames", "sample_frames", "fixed_simulation_delta_seconds", "bindings_sha256", "requested_roster", "actual_roster_counts")
            environment = ("processor", "gpu", "godot", "rendering_method", "rendering_driver", "headless", "viewport_size")
            if any(a["inputs"].get(k) != b["inputs"].get(k) for k in keys) or any(a["environment"].get(k) != b["environment"].get(k) for k in environment):
                state["failures"].append({"code": "comparison_binding_mismatch", "kind": "validation", "message": left["id"] + " / " + right["id"]})
                continue
            key = "simulation_cpu_ms" if prefix == "sim" else "total_work_cpu_ms"
            comparisons.append({"full": left["id"], "tiered": right["id"], "cpu_median_ratio_full_over_tiered": a["summary"][key]["median"] / max(b["summary"][key]["median"], 0.000001)})
    state["comparisons"] = comparisons
    rows = ["当前 Apple 主机实测；不能与旧 RTX 报告直接横比。固定 1/60 秒模拟步长，每引擎帧一步，无墙钟追赶。", "", "| 测试 | 数量 | 帧中位/p95 ms | 行为CPU中位 ms | 动作与摆放CPU中位 ms | 绘制提交中位 |", "|---|---:|---:|---:|---:|---:|"]
    for case in state["cases"]:
        if case["status"] != "done":
            rows.append(f"| {case['id']} ({case['status']}) | {case['settings']['count']} | — | — | — | — |")
            continue
        s = case["summary"]
        frame = "—（headless）" if case["settings"]["mode"] == "simulation" else f"{s['frame_ms']['median']:.2f} / {s['frame_ms']['p95']:.2f}"
        rows.append(f"| {case['id']} | {case['settings']['count']} | {frame} | {s['simulation_cpu_ms']['median']:.3f} | {s['motion_and_placement_cpu_ms']['median']:.3f} | {s['renderer_draw_calls'].get('median', 0):.0f} |")
    motion_scope = "当前原型将群体实际轨迹用于身体转向，保留原生循环和物种参数；这不是仿生游动或正式动作验收。" if review.name == "fish-school-motion-v2" else "历史v1原型沿用原生循环，身体转向仍按原生椭圆路径，群体位移另行覆盖载体；此轮结果仅代表当时实现。"
    rows += ["", motion_scope + "分层是固定工作量分组；骨骼低频更新期间保持姿态，无插值。0.18m 点代理不能代表不同体长或完整鳍部碰撞，不据此宣称容纳量。未增加正式寻路或正式资产验收；不包含水、玻璃、阴影和完整玩法AI。", "环境、来源哈希、固定步长、控制器更新数与紧急约束次数见逐案例报告及 validation-report.json。"]
    rows += [f"渲染设置：{state['rendering_method']} / {state['rendering_driver']}；请求排除：{state['exclude_species']}。旧28鱼Compatibility/OpenGL预检因着色器采样器超限、导入及双髻鲨来源门失败，保留render28-static.engine.log，只作为失败证据，不纳入性能比较。"]
    if state["failures"]: rows += ["", "部分案例失败或来源不匹配，失败项不进入比较。"]
    (review / "performance-review.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("godot", "game", "review", "dotnet"): parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--group", choices=("simulation", "rendered", "all"), default="all")
    parser.add_argument("--counts", help="Comma-separated override for selected groups")
    parser.add_argument("--modes", help="Comma-separated rendered modes override")
    parser.add_argument("--rendering-method", default="forward_plus"); parser.add_argument("--rendering-driver", default="metal")
    parser.add_argument("--exclude-species", default="scalloped_hammerhead,great_hammerhead,smooth_hammerhead")
    parser.add_argument("--samples", type=int, default=120); parser.add_argument("--warmup", type=int, default=30)
    parser.add_argument("--seed", type=int, default=731); parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args()
    if not all(getattr(args, k).is_absolute() for k in ("game", "review", "godot", "dotnet")): parser.error("Paths must be absolute")
    args.game = args.game.resolve(); args.review = args.review.resolve(); args.godot = args.godot.resolve(); args.dotnet = args.dotnet.resolve()
    if not allowed_review_root(args.game, args.review): parser.error("Review must be exactly game.parent/plans/reviews/fish-school-v1 or fish-school-motion-v2")
    if not args.godot.is_file() or not args.dotnet.is_dir() or not (args.game / "project.godot").is_file(): parser.error("Missing Godot, .NET directory or game project")
    if args.samples < 1 or args.warmup < 0 or args.timeout <= 0: parser.error("Invalid sampling or timeout")
    try: counts = [int(v) for v in args.counts.split(",")] if args.counts else None
    except ValueError: parser.error("Counts must be comma-separated integers")
    if counts and (min(counts) < 1 or max(counts) > (16000 if args.group == "simulation" else 224)): parser.error("Count exceeds experimental safety limit")
    modes = args.modes.split(",") if args.modes else None
    if modes and any(v not in ("static", "motion", "school-full", "school-tiered") for v in modes): parser.error("Unknown rendered mode")
    try: protect_historical_v1(args.game, args.review)
    except (OSError, ValueError, KeyError) as exc: parser.error(str(exc))
    args.review.mkdir(parents=True, exist_ok=True)
    target = args.review / "validation-report.json"
    state = read(target) if target.exists() else {"schema_version": 1, "command": "fish.school.experiment", "cases": []}
    roster_text = (args.game / "scripts/aquarium/VolumeFishExhibit.gd").read_text(encoding="utf-8-sig")
    roster = json.loads(re.search(r"const SPECIES := (\[[^\r\n]+\])", roster_text).group(1))
    exclusions = [v for v in args.exclude_species.split(",") if v]
    if any(v not in roster for v in exclusions): parser.error("Unknown excluded species")
    selected = [v for v in roster if v not in exclusions]
    if not selected: parser.error("Cannot exclude every species")
    state.update(status="pending", ok=False, next_action="run", failures=[], outputs=[str(target), str(args.review / "performance-review.md")])
    state.update(review_root=str(args.review), source_generation=args.review.name, game=str(args.game), rendering_method=args.rendering_method, rendering_driver=args.rendering_driver, exclude_species=exclusions, requested_roster=selected)
    preflight = args.review / "render28-static.engine.log"
    if preflight.exists(): state["invalid_preflight_evidence"] = {"status": "failed", "performance_metrics_usable": False, "log": str(preflight), "source_report": str(args.review / "render28-static/benchmark.validation.json"), "reason": "28-fish Compatibility preflight: import, shader sampler and hammerhead source-gate errors; never aggregate its timings"}
    schedule = []
    if args.group in ("simulation", "all"):
        schedule += [(f"sim-{variant}-{n}", n, "simulation", variant == "full") for n in (counts or [50, 200, 500, 2000, 16000]) for variant in ("full", "tiered")]
    if args.group in ("rendered", "all"):
        schedule += [(f"{mode}-{n}", n, mode, False) for n in (counts or [25, 50, 100, 200]) for mode in (modes or (["static", "motion", "school-full", "school-tiered"] if n <= 50 else ["school-full", "school-tiered"]))]
    state["scheduled_case_ids"] = [v[0] for v in schedule]
    write(target, state)
    for name, count, mode, full in schedule:
        folder = args.review / name; folder.mkdir(exist_ok=True)
        settings = dict(count=count, mode=mode, full_decisions=full, seed=args.seed, sample_frames=args.samples, warmup_frames=args.warmup, fixed_simulation_delta_seconds=1 / 60)
        settings.update(requested_roster=selected, exclude_species=args.exclude_species)
        row = dict(id=name, status="running", settings=settings, report=str(folder / "benchmark.validation.json"))
        state["cases"] = [c for c in state["cases"] if c["id"] != name] + [row]
        state.update(status="running", next_action="poll"); write(target, state)
        print("START " + name, flush=True)
        try:
            current = bindings(args.game, mode)
            existing = read(Path(row["report"])) if Path(row["report"]).exists() else {}
            if existing.get("ok") is True and not args.rerun:
                if not valid(existing, settings, current): raise ValueError("Existing successful report has stale bindings/settings; use --rerun after review")
                code, reason = 0, "resumed"
            else: code, reason = execute(args, settings, folder)
            report = read(Path(row["report"])) if Path(row["report"]).exists() else {}
            errors, warnings = log_errors([folder / "engine.log", folder / "stdout.log"])
            if code or errors or not valid(report, settings, bindings(args.game, mode)): raise ValueError(reason or "; ".join(errors) or f"Engine exit {code}; invalid, missing or changed-source report")
            if mode != "simulation" and (report["environment"].get("rendering_method") != args.rendering_method or report["environment"].get("rendering_driver") != args.rendering_driver): raise ValueError("Renderer differs from requested settings")
            if mode == "school-tiered" and count in (50, 200) and not (folder / "overview.png").is_file(): raise ValueError("Requested capture missing")
            row.update(status="done", summary=report["summary"], environment=report["environment"], warnings=warnings, resumed=reason == "resumed")
            print("DONE " + name + (" (resumed)" if reason == "resumed" else ""), flush=True)
        except (OSError, ValueError, KeyError) as exc:
            row.update(status="failed", error=str(exc)); print("FAILED " + name + ": " + str(exc), flush=True)
            state["failures"].append({"case": name, "code": "case_failed", "kind": "validation", "message": name + ": " + str(exc)})
            write(target, state); break
        write(target, state)
    summarize(args.review, state)
    state.update(ok=not state["failures"], status="failed" if state["failures"] else "done", next_action="fix_input" if state["failures"] else "human_review")
    write(target, state)
    return 0 if state["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
