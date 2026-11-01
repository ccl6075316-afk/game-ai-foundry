"""Prepare a fresh hash-bound recipe from explicit logical parts; no anatomy inference."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import tempfile
from fish_asset_spec import ROOT, artifact_output, inspect_reference, preflight, require, resolve_ref, sha
from glb_io import read_glb

PRESENTATION = ('species', 'game', 'motion', 'camera', 'viewer')


def prepare(source_blend, reference_glb, atlas, packing_report, parts, output, source_mesh_name=None, task_type="rebuild"):
    paths = {key: Path(value).resolve() for key, value in
             {'source_blend': source_blend, 'reference_glb': reference_glb,
              'atlas': atlas, 'packing_report': packing_report}.items()}
    refs = {}
    for key, path in paths.items():
        require(path.is_relative_to(ROOT) and path.is_file(), 'Input must be a repository file: ' + str(path))
        refs[key] = {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}
        resolve_ref(refs[key])
    parts_path = Path(parts).resolve()
    require(parts_path.is_relative_to(ROOT) and parts_path.is_file(), 'parts must be a repository file')
    raw = json.loads(parts_path.read_text(encoding='utf8'))
    rows = raw.get('parts') if isinstance(raw, dict) else raw
    require(isinstance(rows, list) and rows, 'Explicit nonempty parts array required')
    inputs = [*paths.values(), parts_path]
    target = artifact_output(output, inputs)
    expected = inspect_reference(paths['reference_glb'])
    doc, _ = read_glb(paths['reference_glb'])
    owner = next(node['name'] for node in doc['nodes'] if 'mesh' in node)
    spec = {'kind': 'fish_asset_finalization_spec', 'version': 1, 'inputs': refs,
            'source_mesh_name': source_mesh_name if source_mesh_name is not None else owner,
            'expected': expected, 'parts': rows}
    if isinstance(raw, dict):
        spec.update({key: raw[key] for key in PRESENTATION if key in raw})
    # Optional presentation references must also be hash-bound; no script is executed here.
    motion = spec.get('motion', {})
    require(isinstance(motion, dict), 'motion must be an object')
    if motion:
        for key in ('runtime', 'profile'):
            inputs.append(resolve_ref(motion[key]))
    target = artifact_output(target, inputs)
    scratch = ROOT / 'work' / 'fish-portable-tools'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='prepare-spec-', dir=scratch) as temporary:
        check_path = Path(temporary) / 'candidate.json'
        check_path.write_text(json.dumps(spec, indent=2) + '\n')
        checked = preflight(check_path)
    sys.path.insert(0, str(ROOT/'cli'))
    from volume_sop import start_production
    spec['production'] = start_production(target, spec.get('species', 'unspecified'), task_type)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x',encoding='utf8') as stream:
        stream.write(json.dumps(spec, indent=2, ensure_ascii=False) + '\n')
    return {'spec': str(target), 'sha256': sha(target), 'inventory': expected,
            'part_count': len(checked['summary']['parts']), 'source_mesh_name': spec['source_mesh_name'],
            'source_mesh_objects': 'not inferred', 'visual_review': 'pending'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-blend', 'reference-glb', 'atlas', 'packing-report', 'parts', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--source-mesh-name')
    parser.add_argument('--task-type',choices=['new','rebuild','repair','local_godot_static_merge'],default='rebuild')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    result = {'schema_version': 1, 'command': 'portable-prepare-spec', 'stage': 'validate',
              'ok': False, 'status': 'blocked', 'next_action': 'fix_input', 'inputs': {},
              'outputs': [], 'summary': {}, 'failures': []}
    result['inputs'] = {key: str(getattr(args, key).resolve()) for key in
                        ('source_blend', 'reference_glb', 'atlas', 'packing_report', 'parts', 'output')}
    try:
        result['summary'] = prepare(args.source_blend, args.reference_glb, args.atlas,
                                    args.packing_report, args.parts, args.output, args.source_mesh_name, args.task_type)
        result.update(ok=True, status='done', next_action='none', outputs=[result['summary']['spec']])
    except (ValueError, AssertionError, OSError, KeyError, TypeError, StopIteration) as error:
        result['failures'].append({'kind': 'validation', 'code': 'spec_preparation_invalid', 'message': str(error)})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
