"""Run a bounded batch of the same read-only pair renderer, collecting all failures."""
import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/fish-reference-compare-20261105'
RENDERER = ROOT / 'resources/scripts/volume-fish/render_fish_reference_pair.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase', choices=['preflight', 'render'], required=True)
    p.add_argument('--jobs', type=int, default=3)
    p.add_argument('--tag')
    p.add_argument('--only', nargs='+')
    a = p.parse_args()
    tag = a.tag or ('preflight' if a.phase == 'preflight' else 'renders')
    assert re.fullmatch('[a-z0-9-]+', tag) and 1 <= a.jobs <= 4
    manifest_path = OUT / 'comparison-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    cases = [x for x in manifest['pairs'] if not a.only or x['id'] in a.only]
    assert cases and (not a.only or {x['id'] for x in cases} == set(a.only))
    renderer_sha = sha(RENDERER)
    phase_root = OUT / tag
    phase_root.mkdir(exist_ok=True)
    assert phase_root.resolve().is_relative_to(OUT.resolve())

    def run(case):
        config = Path(case['pair'])
        assert sha(config) == case['pair_sha256']
        assert re.fullmatch('[a-z0-9_-]+', case['id'])
        folder = phase_root / case['id']
        assert not folder.exists(), folder
        command = ['E:/blender/blender.exe', '--background', '--factory-startup',
                   '--threads', '4', '--python', str(RENDERER), '--',
                   '--pair', str(config), '--output', str(folder), '--clean-rgba']
        command += ['--preflight-only'] if a.phase == 'preflight' else ['--native']
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding='utf8', errors='replace')
        # The renderer owns creation of its new output directory.
        folder.mkdir(exist_ok=True)
        (folder / 'stdout.log').write_text(result.stdout, encoding='utf8')
        (folder / 'stderr.log').write_text(result.stderr, encoding='utf8')
        path = folder / ('preflight.validation.json' if a.phase == 'preflight' else 'render.validation.json')
        report = json.loads(path.read_text(encoding='utf8')) if path.is_file() else {}
        ok = result.returncode == 0 and report.get('ok') is True and 'Traceback' not in result.stdout + result.stderr
        return dict(case, ok=ok, exit_code=result.returncode, output=str(folder),
                    report=str(path), report_sha256=sha(path) if path.is_file() else None,
                    error=report.get('error'), traceback='Traceback' in result.stdout + result.stderr)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        results = list(pool.map(run, cases))
    assert sha(RENDERER) == renderer_sha, 'Renderer changed during batch'
    report = {'ok': all(x['ok'] for x in results), 'phase': a.phase,
              'renderer': {'path': str(RENDERER), 'sha256': renderer_sha},
              'manifest': {'path': str(manifest_path), 'sha256': sha(manifest_path)},
              'assets_modified': False, 'results': results}
    target = OUT / (tag + '-batch.validation.json')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'ok': report['ok'], 'phase': a.phase, 'cases': len(results),
                      'failures': [x for x in results if not x['ok']], 'report': str(target)}))


if __name__ == '__main__':
    main()
