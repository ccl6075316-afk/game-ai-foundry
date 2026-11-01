"""Prepare fresh optional packed plans from reviewed geometry/control constraints."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from packed_fish_parts import freeze


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def write(path, data): Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('model', 'reference_fin_plan', 'reference_runtime_plan', 'reference_head_plan', 'output'):
        parser.add_argument('--' + key.replace('_', '-'), type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    for key in vars(args): setattr(args, key, getattr(args, key).resolve())
    assert args.output.is_relative_to(root) and any(x in ('experiments', 'work', 'output') for x in args.output.relative_to(root).parts)
    assert not args.output.exists(), 'Fresh plan-set directory required'
    args.output.mkdir(parents=True)
    runtime = read(args.reference_runtime_plan)
    fin = copy.deepcopy(read(args.reference_fin_plan))
    assert len(fin['items']) == 1 and fin['items'][0]['species'] == runtime['species']
    item = fin['items'][0]
    assert item['body'] == runtime['body'] and set(item['fins']) == set(runtime['fins'])
    manifest = args.output / 'packed-parts.json'
    freeze(args.model, runtime['body'], runtime['fins'], manifest)
    packed = {'model': str(args.model), 'model_sha256': sha(args.model), 'packed_parts_manifest': str(manifest), 'packed_parts_manifest_sha256': sha(manifest)}
    scripts = Path(__file__).resolve().parent
    helper_names = ['packed_fish_parts.py', 'PackedFishValidation.gd', 'export_runtime_fin_roots.gd', 'validate_fin_completion.py', 'validate_fin_membrane_clearance.py', 'validate_standalone_body.py', 'capture_standalone_body.gd', 'validate_motion_controls.gd', 'capture_standalone_fish_review.gd', 'preview_nile_ab_textured.gd', 'check_head_form.py']
    dependencies = {str(scripts / name): sha(scripts / name) for name in helper_names}
    dependencies.update({str(args.model): sha(args.model), str(manifest): sha(manifest), runtime['motion_profile']: sha(runtime['motion_profile']), runtime['motion_runtime']: sha(runtime['motion_runtime'])})
    item.update(packed)
    item['packed_validation_dependencies'] = dependencies
    fin_path = args.output / 'fin-gate.plan.json'
    write(fin_path, fin)
    runtime.update(packed)
    runtime['motion_profile_sha256'] = sha(runtime['motion_profile'])
    runtime['motion_runtime_sha256'] = sha(runtime['motion_runtime'])
    runtime['frozen_inputs'] = {**dependencies, str(fin_path): sha(fin_path)}
    runtime['scope'] = 'Fresh actual packed GLB validation. R9 constraints/thresholds reused, no prior pass transferred. Runtime remains one mesh/surface; diagnostic subsets only inside validators.'
    runtime_path = args.output / 'candidate.plan.json'
    write(runtime_path, runtime)
    head = copy.deepcopy(read(args.reference_head_plan))
    assert len(head['items']) == 1
    head['items'][0].update(target=str(args.model), target_sha256=sha(args.model), body=runtime['body'], fins=runtime['fins'], packed_parts_manifest=str(manifest), packed_parts_manifest_sha256=sha(manifest))
    head_path = args.output / 'head.plan.json'
    write(head_path, head)
    plan_set = {'ok': True, 'kind': 'packed_fish_validation_plan_set', 'model_sha256': sha(args.model), 'plans': {key: {'path': str(path), 'sha256': sha(path)} for key, path in [('partition', manifest), ('fin', fin_path), ('runtime', runtime_path), ('head', head_path)]}, 'constraint_sources': {str(path): sha(path) for path in [args.reference_fin_plan, args.reference_runtime_plan, args.reference_head_plan]}, 'source_dependencies': dependencies, 'scope': 'Input preparation only, no gates/visual/user acceptance. Source geometry/collar/tolerances/actions untouched.'}
    write(args.output / 'plan-set.validation.json', plan_set)
    print(json.dumps({'ok': True, 'output': str(args.output), 'model_sha256': plan_set['model_sha256']}))


if __name__ == '__main__': main()
