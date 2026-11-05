"""Prepare immutable, source-audited inputs for the 24-fish reference review."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/fish-reference-compare-20261105'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(record):
    path = Path(record['path']).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), path
    assert sha(path) == record['sha256'], path
    return path


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def asset(record):
    path = checked(record)
    result = {'path': str(path), 'sha256': sha(path), 'uniform_scale': 1,
              'pose': 'bind_rest',
              'canonical_from_source_axes': ['+X', '+Y', '+Z'],
              'alpha_policy': 'preserve_embedded'}
    if path.suffix == '.obj':
        # All 26 actual reference meshes were independently viewed in the raw
        # source-axis contact sheets before these final inputs were frozen.
        result['canonical_from_source_axes'] = ['-Y', '+Z', '+X']
        materials = OUT / 'materials' / record['sha256'] / 'materials.json'
        data = json.loads(materials.read_text(encoding='utf8'))
        assert data['ok'] and data['mesh']['sha256'] == record['sha256']
        result['alpha_policy'] = 'explicit_obj_recipe'
        result['obj_materials'] = data['obj_materials']
        result['material_recovery_record'] = {'path': str(materials), 'sha256': sha(materials)}
    return result


def main():
    assert OUT.resolve().is_relative_to(ROOT / 'output')
    (OUT / 'pairs').mkdir(exist_ok=True)
    (OUT / 'historical-preview').mkdir(exist_ok=True)
    frozen_path = OUT / 'inputs-frozen.json'
    new_path = OUT / 'inputs-new-eleven.json'
    frozen = json.loads(frozen_path.read_text(encoding='utf8'))['fish']
    new = json.loads(new_path.read_text(encoding='utf8'))['entries']
    assert len(frozen) == 13 and len(new) == 11
    registration = json.loads((OUT / 'axis-registration.inputs.json').read_text(encoding='utf8'))
    sources = [dict(row, category='accepted') for row in frozen] + [dict(row, category='candidate') for row in new]
    entries, pairs = [], []
    for row in sources:
        checked(row['current_model'])
        references = []
        for index, original in enumerate(row['references']):
            ref = original.copy()
            path = checked(ref)
            if ref.get('reference_kind') == 'preview_only':
                previews = []
                for image in ref['existing_side_top_images']:
                    source = checked(image)
                    target = OUT / 'historical-preview' / image['original_filename']
                    if not target.exists():
                        shutil.copyfile(source, target)
                    assert sha(target) == image['sha256']
                    previews.append(dict(image, presentation_path=str(target.relative_to(OUT)).replace('\\', '/')))
                ref.update(pair_id=None, previews=previews)
            else:
                assert path.suffix in ('.obj', '.glb', '.blend'), path
                case_id = row['species'] + '--r' + str(index + 1).zfill(2)
                pair = {'id': case_id, 'resolution': [1200, 720],
                        'ours': asset(row['current_model']), 'reference': asset(ref)}
                pair_path = OUT / 'pairs' / (case_id + '.json')
                save(pair_path, pair)
                pairs.append({'id': case_id, 'species': row['species'],
                              'pair': str(pair_path), 'pair_sha256': sha(pair_path)})
                ref['pair_id'] = case_id
            references.append(ref)
        entries.append(dict(row, references=references))
    assert len(entries) == 24 and len(pairs) == 27
    sheets = [OUT / f'axis-registration-{i}.png' for i in range(1, 5)]
    save(OUT / 'axis-registration.validation.json', {
        'ok': True, 'scope': 'Input orientation only: source raw geometry, alpha deliberately ignored. Not a visible-fin or anatomical acceptance comparison.',
        'manual_review': 'Root actually viewed all four source-axis contact sheets: every one of 26 source OBJ meshes has recognizable anterior at raw negativeY, tail at positiveY, dorsal positiveZ and bilateral X. Original adoption records retain their original nose-registration unknowns; this is new display registration only.',
        'declared_canonical_from_source_axes': ['-Y', '+Z', '+X'],
        'references': registration['records'],
        'actual_contact_images': [{'path': str(p), 'sha256': sha(p)} for p in sheets],
    })
    save(OUT / 'comparison-manifest.json', {
        'kind': 'read_only_current_vs_actual_reference_model_comparison',
        'assets_modified': False, 'accepted_fish': 13, 'candidate_fish': 11,
        'normalization': 'Each complete mesh longitudinal span normalized to1 by uniform scale; whole-mesh bbox centered. Original fin/rest poses retained. This is not anatomical landmark or biological TL/SL registration.',
        'source_fragments': [{'path': str(p), 'sha256': sha(p)} for p in (frozen_path, new_path)],
        'entries': entries, 'pairs': pairs,
        'preview_only_limit': 'Red seabream primary model is represented by its four actual historical uncalibrated oblique screenshots, not an invented orthographic pair. Its available GiltheadBream geometry is a later comparator, not the primary reference.',
    })
    print(json.dumps({'ok': True, 'fish': len(entries), 'pairs': len(pairs), 'output': str(OUT)}))


if __name__ == '__main__':
    main()
