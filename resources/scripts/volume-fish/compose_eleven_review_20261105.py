"""Compose explicit, hash-verified fish viewer catalogs without modifying assets."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/eleven-fish-review-20261104'
assert OUT.is_relative_to(ROOT / 'output')
PUBLIC_VIEWER = ROOT / 'resources/scripts/volume-fish/portable/FishListViewer.gd'
LEGACY_VIEWER_SHA = '043d713136004b4c1f16f4beb2c64cebeb3a3a7fa59f80898e0c33b26c2f71b1'
CURRENT_VIEWER_SHA = 'cc3b89bac304e7f1db2fc8d24b688413c78812f8516ae5652a9fa952836b5945'
LABELS = {
    'blacktip_reef_shark': '黑鳍礁鲨', 'piranha': '红腹食人鱼',
    'peacock_bass': '孔雀鲈', 'mahi_mahi': '鲯鳅（鬼头刀）',
    'african_catfish': '非洲鲶鱼', 'yellow_croaker': '大黄鱼',
    'zander': '梭鲈', 'hairtail': '带鱼', 'silver_arowana': '银龙鱼',
    'arapaima': '巨骨舌鱼', 'pacific_bluefin_tuna': '太平洋蓝鳍金枪鱼',
}
SOURCES = [
    (ROOT / 'projects/fishing-2d/experiments/blacktip-lowpoly-20261101/finish-review-20261104/eye-restoration-20261104/candidate-r21/catalog.json',
     ROOT / 'projects/fishing-2d/experiments/blacktip-lowpoly-20261101/finish-review-20261104/eye-restoration-20261104/sop-r21.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/four-fish-current-standard-20261101/piranha/eye-volume-20261104/fin-collar-r5/viewer/catalog.json',
     ROOT / 'projects/fishing-2d/experiments/four-fish-current-standard-20261101/piranha/eye-volume-20261104/fin-collar-r5/post-cleanup-sop.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/four-fish-current-standard-20261101/peacock_bass/candidate-r6/catalog.json',
     ROOT / 'projects/fishing-2d/experiments/four-fish-current-standard-20261101/peacock_bass/candidate-r6/sop.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/pacific-bluefin-tuna-static-merge/lowpoly-20261104/ordinary-final-r41/catalog-entry.json',
     ROOT / 'projects/fishing-2d/experiments/pacific-bluefin-tuna-static-merge/lowpoly-20261104/ordinary-final-r41/sop.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/four-fish-current-standard-20261101/mahi_mahi/viewer-entry.catalog.json',
     ROOT / 'projects/fishing-2d/experiments/four-fish-current-standard-20261101/mahi_mahi/final-sop.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/yellow-croaker-portable-trial-20261031/catalog-entry.current.json',
     ROOT / 'projects/fishing-2d/experiments/yellow-croaker-portable-trial-20261031/r48-sop-check.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/zander-finalization-160/lowpoly-20261104/viewer.catalog.json',
     ROOT / 'projects/fishing-2d/experiments/zander-finalization-160/lowpoly-20261104/root-band-patch-r4/sop.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/blender-fish/models/silver_arowana/lowpoly-r4-fin-20261104/barbel-root-r24/viewer.catalog-entry.json',
     ROOT / 'projects/fishing-2d/experiments/blender-fish/models/silver_arowana/lowpoly-r4-fin-20261104/barbel-root-r24/sop.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/hairtail-static-merge/lowpoly-20261104/viewer.catalog.json',
     ROOT / 'projects/fishing-2d/experiments/hairtail-static-merge/lowpoly-20261104/sop-final.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/four-fish-current-standard-20261101/african_catfish/anal-diagonal-r1/viewer.catalog.json',
     ROOT / 'projects/fishing-2d/experiments/four-fish-current-standard-20261101/african_catfish/anal-diagonal-r1/sop-check.validation.json'),
    (ROOT / 'projects/fishing-2d/experiments/arapaima-static-merge/lowpoly-20261104/ventral-skin-r74/catalog-entry.json',
     ROOT / 'projects/fishing-2d/experiments/arapaima-static-merge/lowpoly-20261104/ventral-skin-r74/sop.validation.json'),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def triangle_limit(species, length_cm):
    assert length_cm > 0
    if species == 'blacktip_reef_shark' and length_cm <= 300:
        return 4000
    return 2000 if length_cm <= 120 else 4000 if length_cm <= 300 else 6000 if length_cm <= 600 else 8000


entries, bindings, provenance, canonical_bindings, integration_notes = [], {}, [], {}, {}
viewer_binding_migrations = []
for source, sop_path in SOURCES:
    data = json.loads(source.read_text(encoding='utf-8'))
    sop = json.loads(sop_path.read_text(encoding='utf-8'))
    assert sop['ok'] and sop['status'] == 'done' and sop['next_action'] == 'human_review'
    for role, reference in sop['candidate_files'].items():
        if isinstance(reference, dict) and 'path' in reference and 'sha256' in reference:
            path = Path(reference['path']).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), 'Missing SOP input: ' + role
            assert sha(path) == reference['sha256'], 'Stale SOP candidate: ' + role + ' ' + str(path)
    provenance.append({'path': str(source), 'sha256': sha(source),
                       'sop': {'path': str(sop_path), 'sha256': sha(sop_path)}})
    if 'jaw_integration' in data:
        integration_notes[sop['species']] = {'jaw_integration': data['jaw_integration']}
    for raw_path, digest in data['bindings'].items():
        path = Path(raw_path).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), str(path)
        if path == PUBLIC_VIEWER and digest == LEGACY_VIEWER_SHA:
            # Preserve frozen source catalogs/reports. Upgrade only their UI
            # dependency in this newly generated list, with explicit provenance.
            source_entries = data['entries'] if 'entries' in data else [data['entry']]
            assert all('engine_materials' not in e['viewer'] for e in source_entries)
            assert sha(path) == CURRENT_VIEWER_SHA
            nearest_path = ROOT / 'output/list-nearest-materials-20261105/validation.json'
            scroll_path = ROOT / 'output/list-click-scroll-20261105/binding.validation.json'
            nearest = json.loads(nearest_path.read_text(encoding='utf-8'))
            scroll = json.loads(scroll_path.read_text(encoding='utf-8'))
            assert nearest['ok'] and scroll['ok'] and scroll['viewer_sha256'] == CURRENT_VIEWER_SHA
            assert nearest['inputs'][str(PUBLIC_VIEWER)] == scroll['previous_viewer_sha256']
            default_checks = nearest['checks'][0]['checks'][:3]
            assert all(c['passed'] for c in default_checks)
            viewer_binding_migrations.append({
                'source_catalog': str(source), 'path': raw_path,
                'original_sha256': digest, 'current_sha256': CURRENT_VIEWER_SHA,
                'scope': 'UI only: absent engine_materials remains exact no-op; smoke scroll only. Original catalogs, SOP and model evidence unchanged.',
                'evidence': [{'path': str(p), 'sha256': sha(p)} for p in (nearest_path, scroll_path)],
            })
            digest = CURRENT_VIEWER_SHA
        assert sha(path) == digest, 'Stale input: ' + str(path)
        key = str(path)
        assert key not in canonical_bindings or canonical_bindings[key] == digest
        canonical_bindings[key] = digest
        # Viewer dictionaries address the original spelling in input_paths.
        bindings[raw_path] = digest
    source_entries = data['entries'] if 'entries' in data else [data['entry']]
    for entry in source_entries:
        source_id = entry['id']
        species = entry['viewer']['species']
        assert species in LABELS and sop['species'] == species
        if source_id != species:
            integration_notes.setdefault(species, {})['source_entry_id'] = source_id
            entry['id'] = species
        assert entry['id'] not in {e['id'] for e in entries}
        assert sop['species'] == entry['id']
        assert sop['candidate_files']['model']['sha256'] == entry['viewer']['model_sha256']
        assert 0 < entry['triangles'] <= triangle_limit(entry['id'], entry['length_cm'])
        viewer = entry['viewer']
        for key in ('model', 'spec'):
            path = Path(viewer[key]).resolve()
            assert sha(path) == viewer[key + '_sha256'], 'Stale viewer ' + key
            assert canonical_bindings.get(str(path)) == viewer[key + '_sha256'], 'Unbound viewer ' + key
        for path in viewer['input_paths']:
            assert path in bindings, 'Missing literal input binding: ' + path
        for key in ('runtime', 'profile'):
            path = Path(viewer['controller'][key]).resolve()
            assert canonical_bindings.get(str(path)) == sha(path), 'Unbound controller ' + key
        entry['label'] = LABELS[entry['id']]
        entry['status'] = '技术候选已冻结 · 待十一鱼统一审核'
        entries.append(entry)

assert {e['id'] for e in entries} == set(LABELS), 'Final review requires all eleven species'
entries.sort(key=lambda e: list(LABELS).index(e['id']))
catalog = {'kind': 'existing_fish_review_list', 'entries': entries,
           'bindings': bindings, 'integration_notes': integration_notes,
           'mode': 'interactive', 'output': str(OUT / 'interactive')}
for mode in ('interactive', 'smoke'):
    catalog['mode'] = mode
    catalog['output'] = str(OUT / ('interactive' if mode == 'interactive' else f'smoke-final-{len(entries):02d}'))
    (OUT / ('catalog.json' if mode == 'interactive' else 'smoke-catalog.json')).write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'composition.validation.json').write_text(json.dumps({
    'ok': True, 'scope': 'Review display composition only; fish acceptance remains in original handoffs.',
    'sources': provenance, 'species': [e['id'] for e in entries],
    'viewer_binding_migrations': viewer_binding_migrations,
    'all_bound_inputs_verified': True, 'display_length_triangle_budgets_verified': True,
    'assets_modified': False,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'ok': True, 'species': [e['id'] for e in entries], 'output': str(OUT)}))
