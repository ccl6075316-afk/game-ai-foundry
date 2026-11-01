"""Run one bounded, source-bound GPU material experiment without changing fish assets."""
from __future__ import annotations
import argparse
import hashlib
import json
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
    parser.add_argument('--count', type=int, default=1)
    parser.add_argument('--animated', type=int, choices=(0, 1), default=0)
    parser.add_argument('--samples', type=int, default=120)
    parser.add_argument('--warmup', type=int, default=30)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--mode', choices=('benchmark', 'capture'), default='benchmark')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    experiment = root / 'projects/fishing-2d/experiments/nile-dorsal-route-trial/round10-material-performance'
    args.output = args.output.resolve()
    if not args.output.is_relative_to(experiment.resolve()) or args.output == experiment.resolve():
        raise ValueError('Output must be a child of the explicit round10 experiment')
    if args.output.exists():
        raise ValueError('Each case needs a new output directory; no evidence overwrite')
    if not 1 <= args.count <= 1000 or not 30 <= args.samples <= 300 or not 15 <= args.warmup <= 120 or not 1 <= args.timeout <= 180:
        raise ValueError('Case count/sample/warmup/timeout outside bounded experiment limits')
    for name in ('game', 'godot', 'dotnet', 'model'):
        setattr(args, name, getattr(args, name).resolve())
    script = Path(__file__).with_name('benchmark_fish_materials.gd')
    inputs = [args.model, script, Path(__file__), args.game / 'scripts/aquarium/FoundryFishMotion.gd', root / 'resources/volume-fish/motion/nile_tilapia-082.json', args.game / 'project.godot']
    frozen = {str(p): sha(p) for p in inputs}
    args.output.mkdir(parents=True)
    command = [str(args.godot), '--path', str(args.game), '--audio-driver', 'Dummy', '--rendering-method', 'gl_compatibility', '--rendering-driver', 'opengl3', '--disable-vsync', '--delta-smoothing', 'disable', '--windowed', '--resolution', '1280x720', '--log-file', str(args.output / 'engine.log'), '--script', str(script), '--', '--model=' + str(args.model), '--output=' + str(args.output), '--mode=' + args.mode, '--count=' + str(args.count), '--animated=' + str(args.animated), '--samples=' + str(args.samples), '--warmup=' + str(args.warmup)]
    env = dict(os.environ, DOTNET_ROOT=str(args.dotnet))
    env['PATH'] = str(args.dotnet) + os.pathsep + env.get('PATH', '')
    started = time.monotonic()
    timed_out = False
    with (args.output / 'stdout.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        try:
            returncode = process.wait(timeout=args.timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            returncode = process.wait()
    errors = []
    warnings = []
    for path in [args.output / 'engine.log', args.output / 'stdout.log']:
        if not path.exists():
            continue
        lines = path.read_text(errors='replace').splitlines()
        for i, line in enumerate(lines):
            if not re.search(r'(^\s*(SCRIPT ERROR:|ERROR:)|SHADER ERROR:|Assertion failed|Failed to load resource)', line):
                continue
            if line.strip() == 'ERROR: Condition "ret != noErr" is true. Returning: ""' and i + 1 < len(lines) and 'get_system_ca_certificates (platform/macos/os_macos.mm:' in lines[i + 1]:
                warnings.append('macOS system CA certificate lookup warning')
            else:
                errors.append(line + '\n' + '\n'.join(lines[i + 1:i + 3]))
    result_path = args.output / ('capture.validation.json' if args.mode == 'capture' else 'benchmark.validation.json')
    report = json.loads(result_path.read_text()) if result_path.exists() else {}
    unchanged = all(sha(path) == digest for path, digest in frozen.items())
    ok = bool(returncode == 0 and not timed_out and not errors and report.get('ok') is True and unchanged and report.get('model_sha256') == frozen[str(args.model)])
    receipt = {'ok': ok, 'kind': 'fish_material_case_execution', 'command': command, 'returncode': returncode, 'timed_out': timed_out, 'wall_seconds': time.monotonic() - started, 'frozen_inputs': frozen, 'inputs_unchanged': unchanged, 'errors': sorted(set(errors)), 'warnings': sorted(set(warnings)), 'report': str(result_path), 'report_sha256': sha(result_path) if result_path.exists() else None, 'scope': 'One actual GPU process; errors/assertions reject results even when Godot exits zero.'}
    (args.output / 'execution.validation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ok': ok, 'output': str(args.output), 'wall_seconds': receipt['wall_seconds'], 'errors': receipt['errors']}))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
