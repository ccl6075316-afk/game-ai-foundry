"""Inspect/launch a complete, hash-bound single GLB without rewriting its assets."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
from fish_asset_spec import resolve_ref as _resolve_ref, artifact_output

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = Path(__file__).with_name('FishAssetViewer.gd')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_ref(ref, root=ROOT):
    return _resolve_ref(ref, root)


def vector(value, label):
    if not isinstance(value, list) or len(value) != 3 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
        raise ValueError(f'{label} must contain three finite numbers')
    return value


def focus(value):
    if not isinstance(value, dict) or value.get('mode') not in ('model', 'bbox_relative'):
        raise ValueError('Focus needs mode model or bbox_relative')
    vector(value.get('position'), 'focus.position')
    if value['mode'] == 'bbox_relative' and any(v < 0 or v > 1 for v in value['position']):
        raise ValueError('bbox_relative focus coordinates must be in [0,1]')
    return value


def camera(value):
    if not isinstance(value, dict):
        raise ValueError('camera must be an object')
    if 'focus' in value:
        focus(value['focus'])
    for key in ('yaw_degrees', 'pitch_degrees', 'distance_scale', 'time_seconds'):
        if key in value and (isinstance(value[key], bool) or not isinstance(value[key], (int, float)) or not math.isfinite(value[key])):
            raise ValueError(f'{key} must be finite')
    if value.get('distance_scale', 1) <= 0 or value.get('time_seconds', 0) < 0:
        raise ValueError('distance_scale must be positive and time_seconds nonnegative')
    return value


def inventory(path):
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:4] != b'glTF' or struct.unpack_from('<II', raw, 4) != (2, len(raw)):
        raise ValueError('Invalid GLB version/length')
    length, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4e4f534a or 20 + length > len(raw):
        raise ValueError('Invalid GLB JSON chunk')
    doc = json.loads(raw[20:20 + length])
    meshes = doc.get('meshes', [])
    instances = [n['mesh'] for n in doc.get('nodes', []) if 'mesh' in n]
    return {'mesh_count': len(instances), 'mesh_resource_count': len(meshes), 'surface_count': sum(len(meshes[i].get('primitives', [])) for i in instances),
            'clips': [a.get('name', str(i)) for i, a in enumerate(doc.get('animations', []))],
            'skins': len(doc.get('skins', [])), 'nodes': len(doc.get('nodes', []))}


def output_path(path, inputs=(), root=ROOT):
    return artifact_output(path, inputs, root)


def godot_errors(log_text):
    """Godot may print script failures while still exiting zero."""
    return [line.strip() for line in log_text.splitlines()
            if re.search(r'ERROR:|SCRIPT ERROR|Parse Error|Assertion failed', line, re.IGNORECASE)]


def prepare(spec_path, game=None, root=ROOT):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding='utf8'))
    if not isinstance(spec, dict):
        raise ValueError('Spec must be an object')
    if spec.get('kind') != 'fish_asset_finalization_spec' or spec.get('version') not in (1, 2):
        raise ValueError('Expected fish_asset_finalization_spec version 1 or 2')
    viewer = spec.get('viewer', {})
    if not isinstance(viewer, dict):
        raise ValueError('viewer must be an object')
    model_ref = spec.get('model')
    role = 'final_model'
    if model_ref is None and viewer.get('model_role') == 'reference':
        model_ref = spec.get('inputs', {}).get('reference_glb')
        role = 'reference_model'
    if model_ref is None:
        raise ValueError('model reference required (reference display requires viewer.model_role=reference)')
    model = resolve_ref(model_ref, root)
    actual = inventory(model)
    scale = viewer.get('model_scale', 1.0)
    if isinstance(scale, (int, float)) and not isinstance(scale, bool):
        scale = [scale] * 3
    vector(scale, 'viewer.model_scale')
    if any(v <= 0 for v in scale):
        raise ValueError('model_scale must be positive')
    cam = camera(spec.get('camera', viewer.get('camera', {})))
    focuses = viewer.get('focuses', {})
    if not isinstance(focuses, dict):
        raise ValueError('viewer.focuses must be an object')
    for item in focuses.values():
        focus(item)
    captures = viewer.get('captures', [{'name': 'overview'}])
    if not isinstance(captures, list) or not 1 <= len(captures) <= 64:
        raise ValueError('viewer.captures must contain 1..64 entries')
    names = set()
    last_time = 0
    for item in captures:
        camera(item)
        at = item.get('time_seconds', last_time)
        if at < last_time or at > 300:
            raise ValueError('Capture times must be monotonic and at most 300 seconds')
        last_time = at
        name = item.get('name', '')
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name) or name in names:
            raise ValueError('Capture names must be unique safe basenames')
        names.add(name)
    native_clip = viewer.get('native_clip', '')
    if native_clip and native_clip not in actual['clips']:
        raise ValueError(f'Native clip missing: {native_clip}')
    motion = spec.get('motion', {})
    if not isinstance(motion, dict):
        raise ValueError('motion must be an object')
    controller = None
    paths = [spec_path, model]
    if motion:
        if motion.get('api', 'foundry_motion_v1') != 'foundry_motion_v1':
            raise ValueError('Supported controller api is foundry_motion_v1')
        runtime = resolve_ref(motion['runtime'], root)
        profile = resolve_ref(motion['profile'], root)
        controller = {'runtime': str(runtime), 'profile': str(profile), 'action': motion.get('action', 'Swim')}
        paths += [runtime, profile]
    game_path = Path(game or spec.get('game', viewer.get('game', ''))).expanduser()
    if not str(game_path) or str(game_path) == '.':
        raise ValueError('Pass --game or set spec.game to a Godot project')
    game_path = (root / game_path).resolve()
    if not (game_path / 'project.godot').is_file():
        raise ValueError(f'Missing project.godot: {game_path}')
    return {'species': spec.get('species', ''), 'spec': str(spec_path), 'spec_sha256': sha256(spec_path),
            'model': str(model), 'model_sha256': sha256(model), 'model_role': role, 'game': str(game_path),
            'model_scale': scale, 'camera': cam, 'focuses': focuses, 'captures': captures, 'native_clip': native_clip,
            'controller': controller, 'inventory': actual, 'input_paths': [str(p) for p in paths],
            'capabilities': {'orbit': True, 'zoom': True, 'pan': True, 'native_animation': bool(actual['clips']),
                             'live_controller': controller is not None, 'part_diagnostics': False,
                             'part_diagnostics_reason': 'No verified part diagnostic recipe configured; original materials remain intact'}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--game')
    parser.add_argument('--godot')
    parser.add_argument('--output', required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--smoke', action='store_true')
    mode.add_argument('--capture', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--json', action='store_true', help='Output is always one JSON object')
    args = parser.parse_args(argv)
    report = {'schema_version': 1, 'command': 'portable-view', 'stage': 'validate', 'ok': False, 'status': 'failed',
              'next_action': 'fix_input', 'inputs': {'spec': str(Path(args.spec).resolve())}, 'outputs': [], 'summary': {}, 'failures': []}
    try:
        config = prepare(args.spec, args.game)
        output = output_path(args.output, [Path(p) for p in config['input_paths']])
        if not math.isfinite(args.timeout) or args.timeout <= 0 or args.timeout > 300:
            raise ValueError('timeout must be in (0,300] seconds')
        config.update(output=str(output), mode='smoke' if args.smoke else 'capture' if args.capture else 'interactive')
        report['summary'] = config
        if args.dry_run:
            report.update(ok=True, status='done', next_action='none')
        else:
            if not args.godot or not Path(args.godot).is_file():
                raise ValueError('Pass an existing --godot executable')
            output.mkdir(parents=True, exist_ok=True)
            targets = [output / n for n in ('viewer-config.json', 'viewer.log', 'viewer.validation.json')]
            capture_targets = [output / ('smoke-overview.png' if args.smoke else item['name'] + '.png') for item in config['captures']]
            if any(p.exists() for p in targets + capture_targets):
                raise ValueError('Refuse overwriting viewer run; choose a fresh output directory')
            targets[0].write_text(json.dumps(config, indent=2) + '\n')
            report['outputs'] = [str(targets[0]), str(targets[1])]
            cmd = [str(Path(args.godot).resolve()), '--path', config['game'], '--rendering-method', 'gl_compatibility', '--script', str(SCRIPT), '--', '--config=' + str(targets[0])]
            report['summary']['argv'] = cmd
            try:
                with targets[1].open('w') as log:
                    run = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout if config['mode'] != 'interactive' else None)
            except subprocess.TimeoutExpired as error:
                raise ValueError(f'Viewer exceeded bounded timeout {args.timeout}s; log retained') from error
            report['outputs'] = [str(p) for p in targets if p.exists()]
            if not targets[2].is_file():
                raise ValueError(f'Viewer did not produce runtime report (exit {run.returncode}); inspect viewer.log')
            runtime = json.loads(targets[2].read_text())
            report['summary']['runtime'] = runtime
            errors = godot_errors(targets[1].read_text(errors='replace'))
            passed = run.returncode == 0 and runtime.get('ok') is True and not errors
            report.update(ok=passed, status='done' if passed else 'failed', next_action='human_review')
            if errors:
                report['failures'].append({'kind': 'validation', 'code': 'godot_runtime_error', 'message': 'Godot logged errors: ' + '; '.join(errors[:8])})
            if not report['ok']:
                report['failures'].append({'kind': 'validation', 'code': 'viewer_assertion_failed', 'message': 'See runtime checks and retained log'})
    except (ValueError, OSError, KeyError, TypeError, IndexError, json.JSONDecodeError) as error:
        report['failures'].append({'kind': 'validation', 'code': 'viewer_input_or_runtime_error', 'message': str(error)})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
