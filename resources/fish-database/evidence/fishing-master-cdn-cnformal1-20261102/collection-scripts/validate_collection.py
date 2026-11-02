from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
import ast
import hashlib
import json
import math
import subprocess
import sys

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / 'cli/gamefactory.py').is_file())
ROOT = REPO / 'resources/fish-database'
WORK = REPO / 'work/fish-database-complete-20261102'
sys.path.insert(0, str(WORK / 'deps'))
import jsonschema

SID = 'fishing-master-cdn-cnformal1-20261102'
EV = ROOT / 'evidence' / SID
failures = []
checks = []

def load(path):
    return json.loads(path.read_text())

def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]

def check(ok, label):
    if not ok:
        failures.append(label)
    return bool(ok)

def local(path):
    p = (ROOT / path).resolve()
    assert p.is_relative_to(ROOT) and p.is_file(), path
    return p

manifest = load(ROOT / 'manifest.json')
assets = load(ROOT / 'assets-manifest.json')['artifacts']
source_validator = jsonschema.Draft202012Validator(load(ROOT / 'schemas/source.schema.json'))
reference_validator = jsonschema.Draft202012Validator(load(ROOT / 'schemas/reference.schema.json'))
for p in ROOT.rglob('*.json'):
    load(p)
for p in (ROOT / 'schemas').glob('*.schema.json'):
    jsonschema.Draft202012Validator.check_schema(load(p))
source_records = {x['id']: load(local(x['path'])) for x in manifest['sources']}
reference_records = {x['id']: load(local(x['path'])) for x in manifest['references']}
artifact_records = {x['id']: x for x in assets}
check(len(artifact_records) == len(assets), 'Unique artifact IDs')
check(len({x['path'] for x in assets}) == len(assets), 'Unique canonical artifact paths')
for record in source_records.values():
    source_validator.validate(record)
    for artifact_id in record['artifact_ids']:
        check(artifact_id in artifact_records and artifact_records[artifact_id]['source_id'] == record['id'], 'Source artifact link ' + artifact_id)
    for path in record.get('evidence_paths', []):
        local(path)
for record in reference_records.values():
    reference_validator.validate(record)
    check(record['source_id'] in source_records, 'Reference source ' + record['id'])
    for artifact_id in record['artifact_ids']:
        check(artifact_id in artifact_records and artifact_records[artifact_id]['source_id'] == record['source_id'], 'Reference artifact link ' + artifact_id)
    check(not record['measurement_ids'], 'No unperformed measurements claimed ' + record['id'])
checks.append({'check': 'JSON parsing, Draft 2020-12 schemas, source/reference/artifact links', 'ok': not failures,
               'sources': len(source_records), 'references': len(reference_records), 'artifacts': len(assets)})

total_bytes = 0
for i, artifact in enumerate(assets):
    p = local(artifact['path'])
    sha, md5 = hashlib.sha256(), hashlib.md5()
    size = 0
    with p.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            sha.update(block); md5.update(block); size += len(block)
    check(size == artifact['bytes'], 'Artifact length ' + artifact['id'])
    check(sha.hexdigest() == artifact['sha256'], 'Artifact SHA256 ' + artifact['id'])
    if artifact.get('manifest_md5'):
        check(md5.hexdigest() == artifact['manifest_md5'], 'Artifact MD5 ' + artifact['id'])
    total_bytes += size
    if (i + 1) % 250 == 0:
        print(json.dumps({'assets_hashed': i + 1, 'total': len(assets)}), flush=True)
disk_artifacts = {str(p.relative_to(ROOT)) for p in (ROOT / 'artifacts').rglob('*') if p.is_file()}
check(disk_artifacts == {x['path'] for x in assets}, 'Every retained artifact registered exactly once')
checks.append({'check': 'Every retained artifact length/SHA256 and available source MD5', 'ok': not failures, 'bytes': total_bytes})

paths = [str((ROOT / x['path']).relative_to(REPO)) for x in assets]
output = subprocess.check_output(['git', 'check-attr', '-z', '--stdin', 'filter', 'text'], input=('\0'.join(paths) + '\0').encode(), cwd=REPO)
parts = output.decode().split('\0')[:-1]
attributes = {}
for i in range(0, len(parts), 3):
    path, name, value = parts[i:i + 3]
    attributes.setdefault(path, {})[name] = value
for path in paths:
    check(attributes.get(path) == {'filter': 'lfs', 'text': 'unset'}, 'LFS byte preservation ' + path)
checks.append({'check': 'LFS filter and no text normalization for every artifact', 'ok': not failures, 'paths': len(paths)})

exports = {x['path'] for x in assets if x['source_id'] == SID and x['kind'] == 'derived_model'}
for path in sorted(exports):
    counts = Counter()
    faces = []
    for line in local(path).read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        tag = parts[0]
        if tag in ('v', 'vt', 'vn'):
            values = [float(x) for x in parts[1:]]
            check(all(math.isfinite(x) for x in values), 'Finite OBJ coordinates ' + path)
            counts[tag] += 1
        elif tag == 'f':
            faces.append(parts[1:])
    check(counts['v'] > 0 and len(faces) > 0, 'Nonempty OBJ ' + path)
    for face in faces:
        if len(face) != 3:
            check(False, 'Triangular OBJ face ' + path); break
        for vertex in face:
            for tag, value in zip(('v', 'vt', 'vn'), vertex.split('/')):
                if value:
                    index = int(value)
                    if not (index != 0 and abs(index) <= counts[tag]):
                        check(False, 'Valid OBJ index ' + path)
checks.append({'check': 'All unique OBJ exports have finite coordinates, nonempty triangles and valid vertex/UV/normal indices', 'ok': not failures, 'files': len(exports)})

mesh_objects = {x['object_key']: x for x in lines(EV / 'mesh-inventory.jsonl')}
texture_objects = {x['object_key']: x for x in lines(EV / 'texture-inventory.jsonl')}
prefabs = lines(EV / 'prefab-inventory.jsonl')
obj_index = load(WORK / 'object-index.json')
for item in prefabs:
    check(item['model_acquired'] and not item['hierarchy_errors'], 'Prefab acquired ' + item['prefab_path'])
    check(item['root_object'] in obj_index, 'Prefab root ' + item['prefab_path'])
    for key in item['mesh_keys']:
        check(mesh_objects[key]['ok'] and local(mesh_objects[key]['export_path']).is_file(), 'Prefab readable mesh ' + key)
    for key in item['texture_keys']:
        check(texture_objects[key]['ok'] and len(texture_objects[key]['decoded_pixels_sha256']) == 64, 'Prefab decoded texture ' + key)
    for key in item['material_keys']:
        check(obj_index[key]['type'] == 'Material', 'Prefab material ' + key)
    check(item['rigging_status'] in ('skin_bones_resolved', 'mesh_renderer_without_skin_bones'), 'Prefab rig reference state ' + item['prefab_path'])
    check(item['animator_references_resolved'], 'Prefab animator references ' + item['prefab_path'])
coverage = lines(ROOT / 'catalogs' / SID / 'collection-status.jsonl')
check(len(coverage) == 325 and len({x['source_name'] for x in coverage}) == 325, '325 unique lexical base names')
check(len(prefabs) == 646 and len({x['prefab_path'] for x in prefabs}) == 646, '646 unique exact prefabs')
check(all(x['model_acquired'] and x['all_prefabs_acquired'] for x in coverage), 'Every target base name/variant acquired')
check(sum(x['acquired_prefab_count'] for x in coverage) == 646, 'Coverage totals align with prefab evidence')
for item in coverage:
    for ref in item['reference_ids']:
        check(ref in reference_records, 'Coverage reference ' + ref)
    for path in item['preferred_mesh_exports']:
        check(path in exports, 'Coverage exported mesh ' + path)
for catalog in manifest['catalogs']:
    records = lines(local(catalog['path']))
    check(len(records) == catalog['record_count'], 'Registry count ' + catalog['path'])
    check(len({x['id'] for x in records}) == len(records), 'Catalog unique IDs ' + catalog['path'])
check(manifest['measurement_records'] == [], 'No normalized biological/body width data fabricated')
checks.append({'check': '325 base names and all 646 exact prefabs resolve actual meshes, materials, decoded textures and recorded rig/animator references', 'ok': not failures})

class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.rows = 0
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(value for name, value in attrs if name == 'href')
        if tag == 'tr':
            self.rows += 1

page = ROOT / 'catalogs' / SID / 'collection-status.html'
parser = PageLinks(); parser.feed(page.read_text())
check(parser.rows == 326, 'HTML header plus 325 body rows')
for link in parser.links:
    if not link.startswith(('http:', 'https:', '#')):
        p = (page.parent / link).resolve()
        check(p.is_relative_to(ROOT) and p.is_file(), 'HTML local file ' + link)
for p in (EV / 'collection-scripts').glob('*.py'):
    ast.parse(p.read_text())
migration = load(ROOT / 'evidence/fishing-master-xiaomi-20260814/migration.json')
for name, record in migration['file_map'].items():
    p = local(record['path']); check(p.stat().st_size == record['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest() == record['sha256'], 'Historical migration byte identity ' + name)
subprocess.run(['git', 'diff', '--check', '--', 'README.md', '.gitattributes'], cwd=REPO, check=True)
checks.append({'check': 'Current HTML file links, retained script syntax, historical migration hashes and root diff whitespace', 'ok': not failures})
prior = load(ROOT / 'validation-report.json')
collection = load(EV / 'collection-report.json')
report = {'schema_version': 1, 'ok': not failures, 'status': 'running' if not failures else 'failed',
          'next_action': 'cleanup' if not failures else 'fix_input', 'checked_on': '2026-11-02',
          'scope': 'Fish database acquisition/readability/integrity only; not biological accuracy or production fish acceptance',
          'source_count': len(source_records), 'reference_count': len(reference_records),
          'artifact_count': len(assets), 'artifact_bytes': total_bytes,
          'catalog_record_counts': {x['path']: x['record_count'] for x in manifest['catalogs']},
          'collection_report': 'evidence/' + SID + '/collection-report.json', 'collection_summary': collection['summary'],
          'schema_validator': 'jsonschema 4.26.0, Draft 2020-12', 'checks': checks,
          'failures': failures, 'earlier_cleanup': prior.get('cleanup', prior.get('earlier_cleanup')),
          'git': {'lfs_attributes_verified_for_all_artifacts': not failures, 'committed_or_pushed_by_this_task': False},
          'limitations': collection['limitations']}
(ROOT / 'validation-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'ok': report['ok'], 'failures': failures[:20], 'artifact_count': len(assets), 'artifact_bytes': total_bytes, 'references': len(reference_records), 'collection': report['collection_summary']}, ensure_ascii=False, indent=2))
assert not failures
