"""Validate retained evidence/source links, byte identity and native replay reports.

Run prepare_native_input.py first. Does not repeat the ARM64 replay itself.
"""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

E = Path(__file__).resolve().parent
REPO = next(p for p in E.parents if (p / 'cli/gamefactory.py').is_file())
DB = REPO / 'resources/fish-database'
WORK = REPO / 'work/fish-motion-reconstruction-20261102'

def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'Duplicate JSON key: ' + key
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError('Non-standard JSON number: ' + value)

def read(path):
    return json.loads(path.read_text(), object_pairs_hook=unique, parse_constant=reject_constant)

def sha(data):
    return hashlib.sha256(data).hexdigest()

if __name__ == '__main__':
    native = (WORK / 'libil2cpp.so').read_bytes()
    evidence = read(E / 'native-evidence.json')
    assert sha(native) == evidence['native_sha256']
    code = evidence['code_slice']
    code_bytes = (DB / code['path']).read_bytes()
    assert len(code_bytes) == code['bytes'] and sha(code_bytes) == code['sha256']
    assert code_bytes == native[code['source_file_offset']:code['source_file_offset'] + code['bytes']]
    constants = evidence['constants_slice']
    data = (DB / constants['path']).read_bytes()
    assert len(data) == constants['bytes'] and sha(data) == constants['sha256']
    for row in constants['entries']:
        assert data[row['blob_offset']:row['blob_offset'] + row['bytes']] == native[row['file_offset']:row['file_offset'] + row['bytes']]
    for row in evidence['all_methods']:
        assert sha(code_bytes[row['code_artifact_offset']:row['code_artifact_offset'] + row['size']]) == row['sha256']
    reports = [read(E / x) for x in ['kernel-validation-report.json', 'steering-validation-report.json']]
    assert sum(r['tests'] for r in reports) == 395
    for report in reports:
        assert report['native_sha256'] == evidence['native_sha256']
        assert report['passed'] == report['tests'] == len(report['cases']) and not report['failures']
        assert all(c['ok'] for c in report['cases'])
    for path in E.glob('*.json'):
        read(path)
    for path in E.glob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
    baseline = read(E / 'our-code-inputs.json')
    for row in baseline:
        data = (REPO / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], 'Baseline changed: ' + row['path']
    assets = read(DB / 'assets-manifest.json')['artifacts']
    new_paths = [x['path'] for x in (code, constants)]
    ids = set()
    for asset in assets:
        assert asset['id'] not in ids
        ids.add(asset['id'])
        assert (DB / asset['path']).is_file()
        if asset['path'] in new_paths:
            data = (DB / asset['path']).read_bytes()
            assert sha(data) == asset['sha256'] and len(data) == asset['bytes']
    source = read(DB / 'sources/fishing-master-xiaomi-20260814/source.json')
    assert all(i in ids for i in source['artifact_ids'])
    assert all((DB / p).is_file() for p in source['evidence_paths'])
    paths = [str((DB / p).relative_to(REPO)) for p in new_paths]
    attrs = subprocess.check_output(['git', 'check-attr', '-z', 'filter', 'text', '--', *paths], cwd=REPO).decode().split('\0')
    records = [attrs[i:i+3] for i in range(0, len(attrs)-1, 3)]
    assert all(v == ('lfs' if attribute == 'filter' else 'unset') for _, attribute, v in records)
    print(json.dumps({'ok': True, 'native_comparisons': 395, 'mapped_methods': len(evidence['all_methods']), 'new_artifacts': 2, 'original_byte_identity': True, 'lfs_verified': True, 'baseline_hashes_current': True}, indent=2))
