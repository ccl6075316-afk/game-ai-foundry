"""Retain verification conclusions, then remove only exact regenerated scratch files."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';R=G/'plans/reviews/five-fish-release-20261104';read=lambda p:json.loads(p.read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
previous=read(R/'verification-cleanup.json')if(R/'verification-cleanup.json').exists()else None
viewer=ROOT/'output/five-final-viewer/20261104-011549-937207'
if viewer.exists():
 assert read(viewer/'viewer.validation.json')['ok']
 for old,new in [('viewer.validation.json','viewer-smoke.validation.json'),('list-overview.png','viewer-overview.png')]:shutil.copy2(viewer/old,R/new);assert sha(viewer/old)==sha(R/new)
else:assert read(R/'viewer-smoke.validation.json')['ok']
records=[];targets=set()
scratch=ROOT/'output/five-fish-release-20261104';targets.update(p for p in scratch.rglob('*')if p.is_file())
viewer_roots=[p for p in (ROOT/'output/five-final-viewer').iterdir()if p.is_dir()]
for d in viewer_roots:targets.update(p for p in d.rglob('*')if p.is_file())
for row in read(R/'manifest.json')['records']:
 s=row['species'];d=R/s;assert read(d/'sop.validation.json')['ok'];assert read(d/'canonical-pixels.validation.json')['ok']
 targets.update(d.glob('*-canonical.png'));targets.update(d.glob('*-approved.png'))
# Automatic editor-import byproducts for an unrelated unchanged fish/script:
# not production source, and no tracked file or five-fish entry uses them.
targets.update(p for p in [G/'game/assets/models/fish/black_seabream_atlas.png',G/'game/assets/models/fish/black_seabream_atlas.png.import',G/'game/scripts/aquarium/FinalizedNileTilapia.gd.uid']if p.exists())
for p in sorted(targets):
 assert p.resolve().is_relative_to(ROOT) and not p.is_symlink();records.append({'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)})
receipt={'ok':True,'scope':'Regenerated verification GLBs/logs/staging and pixel-pair PNGs after numeric equality receipts and five representative action montages retained; technical list smoke report/overview retained. Untracked unrelated editor byproducts removed. Accepted sources, current GLBs, engine-bound five atlas copies and all SOP evidence preserved.','files':records,'deleted_files':len(records),'deleted_bytes':sum(x['bytes']for x in records)}
if previous:
 receipt.update(files=previous['files']+records,deleted_files=previous['deleted_files']+len(records),deleted_bytes=previous['deleted_bytes']+sum(x['bytes']for x in records),rounds=previous.get('rounds',1)+1)
write(R/'verification-cleanup.json',receipt)
for row in records:
 p=Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];p.unlink()
for root in [scratch]+viewer_roots:
 assert root.resolve().is_relative_to(ROOT/'output')
 for d in sorted([p for p in root.rglob('*')if p.is_dir()],key=lambda p:len(p.parts),reverse=True):d.rmdir()
 root.rmdir()
names=[r['species']for r in read(R/'manifest.json')['records']];paths=set(p for p in R.rglob('*')if p.is_file())
for s in names:
 paths.update(p for p in (G/f'assets/source/fish/{s}').rglob('*')if p.is_file())
 paths.update([G/f'game/assets/models/fish/{s}.glb',G/f'game/assets/models/fish/{s}.glb.import',G/f'game/assets/models/fish/{s}_atlas.png',G/f'game/assets/models/fish/{s}_atlas.png.import',ROOT/f'resources/volume-fish/{s.replace("_","-")}-final-20261104.json',ROOT/f'resources/volume-fish/database-revision-20261103/{s}.profile.json'])
paths.add(ROOT/'resources/volume-fish/final-five-fish-20261104.json');write(R/'retained-size.json',{'kind':'five_fish_release_retained_size','scope':'Current five source directories, canonical GLBs/import settings and same-byte engine atlas copies, release evidence/history, species/final metadata. Measured before handoff prose; shared library and Git object stores excluded.','files':len(paths),'total_bytes':sum(p.stat().st_size for p in paths)})
print(json.dumps({k:receipt[k]for k in ['ok','deleted_files','deleted_bytes']}))
