"""Run one controlled real-GPU material case, independent of window presentation."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('game', 'godot', 'dotnet', 'model', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--count', type=int, required=True)
    parser.add_argument('--animated', type=int, choices=(0, 1), required=True)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    experiment = root / 'projects/fishing-2d/experiments/nile-dorsal-route-trial/round10-material-performance'
    for name in ('game', 'godot', 'dotnet', 'model', 'output'):
        setattr(args, name, getattr(args, name).resolve())
    if not args.output.is_relative_to(experiment.resolve()) or args.output == experiment.resolve() or args.output.exists():
        raise ValueError('Use a fresh output directory inside this experiment')
    if not 1 <= args.count <= 1000 or not 1 <= args.timeout <= 180:
        raise ValueError('Bounded count/timeout required')
    script = Path(__file__).with_name('benchmark_fish_materials_controlled.gd')
    base = Path(__file__).with_name('benchmark_fish_materials.gd')
    files = [args.model, script, base, Path(__file__), args.game / 'project.godot', args.game / 'scripts/aquarium/FoundryFishMotion.gd', root / 'resources/volume-fish/motion/nile_tilapia-082.json']
    frozen = {str(p): sha(p) for p in files}
    args.output.mkdir(parents=True)
    command = [str(args.godot), '--path', str(args.game), '--audio-driver', 'Dummy', '--rendering-method', 'gl_compatibility', '--rendering-driver', 'opengl3', '--disable-render-loop', '--windowed', '--resolution', '1280x720', '--log-file', str(args.output / 'engine.log'), '--script', str(script), '--', '--model=' + str(args.model), '--output=' + str(args.output), '--mode=benchmark', '--count=' + str(args.count), '--animated=' + str(args.animated), '--samples=60', '--warmup=15']
    env = dict(os.environ, DOTNET_ROOT=str(args.dotnet))
    env['PATH'] = str(args.dotnet) + os.pathsep + env.get('PATH', '')
    started = time.monotonic()
    timed_out = False
    with (args.output / 'stdout.log').open('w') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            code = process.wait(timeout=args.timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            code = process.wait()
    errors = []
    for path in (args.output / 'stdout.log', args.output / 'engine.log'):
        if path.exists():
            errors.extend(line for line in path.read_text(errors='replace').splitlines() if re.search(r'(^\s*(SCRIPT ERROR:|ERROR:)|SHADER ERROR:|Assertion failed|Failed to load resource)', line))
    result = args.output / 'controlled.validation.json'
    report = json.loads(result.read_text()) if result.exists() else {}
    valid = report.get('ok') is True and report.get('kind') == 'fish_material_controlled_case' and report.get('protocol') == 'controlled-v1'
    if valid:
        settings = report['settings']
        valid = all(settings.get(k) == v for k, v in {'count': args.count, 'animated': bool(args.animated), 'samples': 60, 'warmup': 15, 'viewport': [1280, 720], 'automatic_render_loop': False, 'explicit_force_draws_per_step': 1, 'swap_buffers': False, 'readback_every_step': True, 'hidden_own_window': False, 'own_window_minimized': True, 'always_on_top': False, 'rendering_driver': 'opengl3', 'rendering_method': 'gl_compatibility'}.items())
        valid = valid and all(report[state]['minimized'] and not report[state]['always_on_top'] for state in ('first_window_state', 'last_window_state'))
        raw = report.get('raw_samples', [])
        valid = valid and len(raw) == 60 and report.get('explicit_draw_signals_total') == 75 and report.get('actual_pose_changed') is bool(args.animated) and report.get('actual_GPU_image_changed') is bool(args.animated)
        for row in raw:
            valid = valid and row['explicit_draw_signals'] == 1 and row['draw_calls'] == args.count * report['per_fish']['surfaces'] and row['primitives'] == args.count * 1710
            valid = valid and all(math.isfinite(row[k]) and row[k] >= 0 for k in ('motion_call_ms', 'engine_refresh_wait_ms', 'forced_draw_readback_ms', 'controlled_step_ms'))
        valid = valid and all(Path(row['path']).parent == args.output and sha(row['path']) == row['sha256'] for row in report.get('images', [])) and len(report.get('images', [])) == 2
    unchanged = all(sha(path) == digest for path, digest in frozen.items())
    ok = bool(code == 0 and not timed_out and not errors and valid and unchanged and report.get('model_sha256') == frozen[str(args.model)])
    receipt = {'ok': ok, 'kind': 'fish_material_controlled_execution', 'protocol': 'controlled-v1', 'command': command, 'returncode': code, 'timed_out': timed_out, 'wall_seconds': time.monotonic() - started, 'frozen_inputs': frozen, 'inputs_unchanged': unchanged, 'errors': sorted(set(errors)), 'report': str(result), 'report_sha256': sha(result) if result.exists() else None, 'scope': 'One real OpenGL device process with automatic rendering disabled; never headless/dummy rendering. Audio Dummy is unrelated to GPU. No normal-game FPS or pureGPU timing claim.'}
    (args.output / 'controlled-execution.validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': ok, 'output': str(args.output), 'wall_seconds': receipt['wall_seconds'], 'errors': receipt['errors']}))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
