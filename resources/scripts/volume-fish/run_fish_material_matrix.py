"""Sequential paired material benchmark; resume only exact frozen sources/settings."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def summarize(output, manifest, results):
    rows = []
    for item in results:
        report = json.loads(Path(item['report']).read_text())
        row = {key: item[key] for key in ('round', 'variant', 'count', 'animated')}
        for field in ('frame_ms', 'motion_call_ms', 'draw_calls', 'primitives', 'render_objects', 'renderer_cpu_interval_ms'):
            row[field + '_p50'] = report[field]['p50']
            row[field + '_p95'] = report[field]['p95']
        row['gpu_timer_available'] = report['gpu_timer_available']
        row['renderer_gpu_interval_ms_p50'] = report['renderer_gpu_interval_ms']['p50'] if report['gpu_timer_available'] else None
        row['report'] = item['report']
        row['report_sha256'] = sha(item['report'])
        rows.append(row)
    if rows:
        with (output / 'summary.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    report = {'ok': len(rows) == 36, 'kind': 'fish_material_matrix', 'status': 'done' if len(rows) == 36 else 'running', 'manifest_sha256': sha(output / 'matrix-manifest.json'), 'completed_cases': len(rows), 'expected_cases': 36, 'frozen_inputs': manifest['frozen_inputs'], 'settings': manifest['settings'], 'rows': rows, 'scope': 'Two rounds, second variant order reversed. Actual viewport draw counters exclude display quad; whole-window raw counters retained in each case. Frame cadence is not pure GPU time or normal game FPS. No hardware GPU timer values are inferred when unavailable.'}
    write(output / 'matrix.validation.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('game', 'godot', 'dotnet', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--candidates-dir', type=Path, required=True, help='Explicit adopted candidate directory; failed older candidates remain immutable')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    trial = root / 'projects/fishing-2d/experiments/nile-dorsal-route-trial'
    experiment = trial / 'round10-material-performance'
    args.game = args.game.resolve(); args.godot = args.godot.resolve(); args.dotnet = args.dotnet.resolve(); args.output = args.output.resolve()
    if not args.output.is_relative_to(experiment.resolve()) or args.output == experiment.resolve():
        raise ValueError('Output outside explicit round10 experiment')
    if args.output.exists() and not args.resume:
        raise ValueError('Existing matrix requires explicit --resume and identical sources/settings')
    args.candidates_dir = args.candidates_dir.resolve()
    if not args.candidates_dir.is_relative_to(experiment.resolve()):
        raise ValueError('Candidate directory must remain inside the isolated experiment')
    variants = {'baseline9': trial / 'round9-fin-clearance/final-B-artifacts/fish.glb', 'merged-mask': args.candidates_dir / 'merged-mask.glb', 'merged-opaque': args.candidates_dir / 'merged-opaque.glb'}
    case_runner = Path(__file__).with_name('run_fish_material_case.py')
    script = Path(__file__).with_name('benchmark_fish_materials.gd')
    files = [*variants.values(), case_runner, script, Path(__file__), args.game / 'project.godot', args.game / 'scripts/aquarium/FoundryFishMotion.gd', root / 'resources/volume-fish/motion/nile_tilapia-082.json']
    frozen = {str(p): sha(p) for p in files}
    settings = {'counts': [100, 300, 1000], 'animated': [0, 1], 'rounds': 2, 'samples': 120, 'warmup': 30, 'timeout_seconds_per_process': 180, 'rendering_method': 'gl_compatibility', 'rendering_driver': 'opengl3', 'viewport': [1280, 720], 'always_on_top': True, 'fixed_delta': '1/60', 'variant_order_round1': list(variants), 'variant_order_round2': list(reversed(variants)), 'game': str(args.game), 'godot': str(args.godot), 'dotnet': str(args.dotnet), 'candidates_dir': str(args.candidates_dir)}
    manifest_path = args.output / 'matrix-manifest.json'
    if args.output.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest['frozen_inputs'] != frozen or manifest['settings'] != settings:
            raise ValueError('Frozen matrix sources or settings changed; use a new output directory')
    else:
        args.output.mkdir(parents=True)
        try:
            processes = subprocess.check_output(['ps', '-axo', 'pid=,comm='], text=True)
            godot_processes = [line.strip() for line in processes.splitlines() if 'Godot' in line]
        except (OSError, subprocess.CalledProcessError):
            godot_processes = ['Process inventory unavailable; no user processes closed.']
        manifest = {'kind': 'fish_material_matrix_manifest', 'frozen_inputs': frozen, 'settings': settings, 'host': platform.platform(), 'other_Godot_processes_before_matrix': godot_processes, 'notes': 'Existing user applications are neither closed nor modified; two opposite-order rounds reduce but do not eliminate background/thermal noise.'}
        write(manifest_path, manifest)
    results = []
    for repeat in (1, 2):
        order = list(variants) if repeat == 1 else list(reversed(variants))
        for count in settings['counts']:
            for animated in settings['animated']:
                for variant in order:
                    if any(sha(path) != digest for path, digest in frozen.items()):
                        raise ValueError('Input changed while matrix was running')
                    name = f'r{repeat}-{count}-' + ('motion-' if animated else 'static-') + variant
                    case = args.output / name
                    execution_path = case / 'execution.validation.json'
                    report_path = case / 'benchmark.validation.json'
                    if case.exists():
                        execution = json.loads(execution_path.read_text())
                        report = json.loads(report_path.read_text())
                        expected_case_inputs = {key: frozen[key] for key in map(str, [variants[variant], script, case_runner, args.game / 'scripts/aquarium/FoundryFishMotion.gd', root / 'resources/volume-fish/motion/nile_tilapia-082.json', args.game / 'project.godot'])}
                        if not execution.get('ok') or execution['report_sha256'] != sha(report_path) or execution['frozen_inputs'] != expected_case_inputs or not report.get('ok'):
                            raise ValueError('Incomplete/stale existing case; preserve failure and use a fresh matrix output: ' + name)
                        for key, value in {'count': count, 'animated': bool(animated), 'samples': 120, 'warmup': 30, 'viewport': [1280, 720], 'rendering_method': 'gl_compatibility', 'rendering_driver': 'opengl3', 'always_on_top': True}.items():
                            if report['settings'][key] != value:
                                raise ValueError('Case settings mismatch: ' + name)
                    else:
                        command = [sys.executable, str(case_runner), '--game', str(args.game), '--godot', str(args.godot), '--dotnet', str(args.dotnet), '--model', str(variants[variant]), '--output', str(case), '--count', str(count), '--animated', str(animated), '--samples', '120', '--warmup', '30', '--timeout', '180']
                        completed = subprocess.run(command)
                        if completed.returncode:
                            summarize(args.output, manifest, results)
                            print(json.dumps({'ok': False, 'failed_case': name, 'completed_cases': len(results)}), flush=True)
                            return 1
                    results.append({'round': repeat, 'variant': variant, 'count': count, 'animated': bool(animated), 'report': str(report_path)})
                    current = summarize(args.output, manifest, results)
                    print(json.dumps({'case': name, 'completed': len(results), 'frame_ms_p50': current['rows'][-1]['frame_ms_p50'], 'motion_call_ms_p50': current['rows'][-1]['motion_call_ms_p50'], 'draw_calls': current['rows'][-1]['draw_calls_p50']}), flush=True)
    print(json.dumps({'ok': True, 'completed_cases': len(results), 'output': str(args.output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
