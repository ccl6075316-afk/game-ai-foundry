"""Exercise the committed fish tree in a separate checkout, without dirty donors."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkout', type=Path, required=True)
    p.add_argument('--godot', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    checkout = a.checkout.resolve()
    game = checkout / 'game'
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '-uno'], cwd=checkout, text=True)
    if dirty.strip():
        raise ValueError('Verification requires a clean committed checkout')
    commands = [
        ('build', ['dotnet', 'build', game / 'GameFactoryDemo.csproj', '--nologo', '-v', 'quiet']),
        ('import', [a.godot, '--headless', '--path', game, '--editor', '--import', '--quit']),
        ('native', [a.godot, '--path', game, '--windowed', '--resolution', '1920x1080',
                    '--quit-after', '3600', 'res://scenes/aquarium_hall_style_review.tscn',
                    '--', '--capture-dir=' + str(out / 'godot')]),
        ('router', [a.godot, '--headless', '--path', game, '--quit-after', '1200',
                    'res://scenes/aquarium_hall_3d_route_review.tscn',
                    '--', '--hall-review-dir=' + str(out)])]
    steps = []
    for name, command in commands:
        log = out / (name + '.log')
        start = time.time_ns()
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run([str(v) for v in command], cwd=checkout,
                                    stdout=stream, stderr=subprocess.STDOUT)
        okay = result.returncode == 0 and 'ERROR:' not in log.read_text(encoding='utf-8')
        if name in ['native', 'router']:
            report = out / ('godot/render.validation.json' if name == 'native' else 'router.validation.json')
            okay = okay and report.is_file() and report.stat().st_mtime_ns >= start
            if okay:
                data = json.loads(report.read_text(encoding='utf-8'))
                okay = data['ok'] and all(data['checks'].values())
        steps.append({'step': name, 'ok': okay, 'exit_code': result.returncode, 'log': str(log)})
        print(json.dumps(steps[-1]), flush=True)
        if not okay:
            break
    okay = len(steps) == len(commands) and all(row['ok'] for row in steps)
    sources = {}
    for path in [*game.glob('scripts/aquarium/*Hall*.gd'), game / 'scripts/aquarium/HallFloor3D.gdshader',
                 game / 'scripts/Main.cs', game / 'scripts/Main.Screens.cs']:
        sources[path.relative_to(checkout).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {'schema_version': 1, 'command': 'aquascape.verify-retained-commit', 'ok': okay,
              'status': 'done' if okay else 'failed', 'next_action': 'human_review' if okay else 'fix_input',
              'tested_commit': commit, 'clean_before_run': True, 'steps': steps, 'source_hashes': sources,
              'scope': 'Only committed code and assets; no local fish repair or rod experiment donors.',
              'user_acceptance': 'pending', 'failures': [] if okay else ['See failed step log']}
    (out / 'validation-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if okay else 1


if __name__ == '__main__':
    raise SystemExit(main())
