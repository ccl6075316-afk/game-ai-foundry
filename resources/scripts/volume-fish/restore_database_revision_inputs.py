"""Restore only hash-bound installed-fish inputs from the verified historical pool."""
import gzip, importlib.util, json, tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'projects/fishing-2d/plans/reviews/local-cleanup-20261102/history-curation'
spec=importlib.util.spec_from_file_location('curated_restore',HERE/'restore_curated.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
OUT=ROOT/'output/five-fish-database-20261103/restored'
idx=json.load(gzip.open(HERE/'curation-index.json.gz','rt',encoding='utf8'))
installed=json.loads((OUT/'installation.validation.json').read_text(encoding='utf8'))
requests={}
def request(digest,target):
    row=mod.retained_record(idx,digest)
    if target.exists():assert mod.sha(target)==digest;return
    assert target.resolve().is_relative_to(OUT.resolve())
    requests[digest]=(target,row)
for record in installed['records']:
    species=record['species']
    request(record['editable_source']['sha256'],OUT/species/'baseline.blend')
    for key in ['SOP','actual_installed_entry']:
        request(record[key]['sha256'],OUT/species/(key+'.validation.json'))
    aliases=[record['delivery'],record['SOP']['path'].replace('sop.validation.json','spec-sop-review.json')]
    for alias in aliases:
        alias=alias.replace('\\','/').split('game-ai-foundry/')[-1]
        found=[(h,v) for h,v in idx['objects'].items() if alias in v['aliases']]
        if found:request(found[0][0],OUT/species/Path(alias).name)
    # Exact frozen production spec and gate plans from the same installed revision.
    prefix=record['editable_source']['path'].replace('\\','/').split('game-ai-foundry/')[-1].split('/source-run/')[0]+'/'
    for tail in ['fin.plan.json','delivery-config.json','plans/parts-manifest.json']:
        alias=prefix+tail
        matches=[(h,v) for h,v in idx['objects'].items() if alias in v['aliases'] and v['keep']]
        if matches:request(matches[0][0],OUT/species/'frozen'/tail)
    for h,v in idx['objects'].items():
        if not v['keep']:continue
        matches=[a for a in v['aliases'] if a.startswith(prefix) and any(a.endswith(s) for s in ['spec.json','spec-sop-review.json','production-review.json','fin-gate.plan.json','authored-roots.plan.json','delivery/manifest.json','delivery-r3/manifest.json'])]
        if matches:request(h,OUT/species/'frozen'/matches[0][len(prefix):])
pending={}
for digest,name in {
    '72771ac207e9ee6fe5d67342988aeacfec7a33c450af5fd5bdab8398f8e0542b':'volume-baseline.blend',
    '1bc84db45a56c8b2718bddd883f030d960c21c2dbccbbb6d6bdee4de8cfa3d7e':'volume-baseline.validation.json',
    'c39f1ccd694f754e27434ce4ce4bcccf13cfe2a92c6424de4e7532bd1666fe2f':'volume-baseline.config.json',
    '05e12de48e2506b0b3977050624acfb728414e4a0722be83eb9f7b01329b0ab2':'material-author-original.glb',
    '084f724437d26b53018374e38088b221281567adee48610534423ed1a1fab525':'body-source-original.png',
}.items():request(digest,OUT/'rainbow_trout'/name)
for record in installed['records']:
    species=record['species']
    if species=='rainbow_trout':continue
    prefix=record['editable_source']['path'].replace('\\','/').split('game-ai-foundry/')[-1].split('/source-run/')[0]+'/'
    for tail,name in [('volume-source/fish.blend','volume-baseline.blend'),('volume.config.json','volume-baseline.config.json'),('volume.validation.json','volume-baseline.validation.json')]:
        matches=[(h,v) for h,v in idx['objects'].items() if prefix+tail in v['aliases'] and v['keep']]
        if matches:request(matches[0][0],OUT/species/name)
    original=json.loads((OUT/species/'frozen/spec-sop-review.json').read_text(encoding='utf8'))
    author=original['candidate_files']['material_author_model'];h=author['sha256']
    if h in idx['objects']:request(h,OUT/species/'material-author-original.glb')
for h,(target,row) in requests.items():
    if row.get('provider'):
        print(json.dumps(mod.copy_payload(ROOT,HERE/'curation-index.json.gz',h,target)),flush=True)
    else:pending[h]=(target,row)
if pending:
    with mod.pool_stream(HERE,idx['pool']) as stream,tarfile.open(fileobj=stream,mode='r|xz') as archive:
        for item in archive:
            h=item.name.removeprefix('objects/')
            if h not in pending:continue
            target,row=pending.pop(h);assert item.isfile();target.parent.mkdir(parents=True,exist_ok=True)
            with archive.extractfile(item) as source,target.open('xb') as dest:
                for block in iter(lambda:source.read(mod.CHUNK),b''):dest.write(block)
            assert target.stat().st_size==row['bytes'] and mod.sha(target)==h
            print(json.dumps({'ok':True,'restored':str(target),'sha256':h,'bytes':row['bytes']}),flush=True)
            if not pending:break
assert not pending, list(pending)
print(json.dumps({'ok':True,'requested_payloads':len(requests),'output':str(OUT)}))
