import json,hashlib
from pathlib import Path
q=Path('E:/game-ai-foundry/projects/fishing-2d/experiments/six-fish-database-20261104/bluegill');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:{'path':str(p),'sha256':sha(p)};protected=set()
def scan(v):
 if isinstance(v,dict):
  for x in v.values():scan(x)
 elif isinstance(v,list):
  for x in v:scan(x)
 elif isinstance(v,str):
  p=Path(v)
  if p.is_absolute():protected.add(p.resolve())
for p in [q/'production-review.json',q/'operator-final-r6/root-contact-sheets.validation.json']:
 scan(json.loads(p.read_text(encoding='utf8')))
targets=[]
for folder in ['delivery-r1','delivery-r2','delivery-r4','delivery-r5','local-view','local-view-r4']:
 for p in (q/folder).rglob('*'):
  if not p.is_file()or p.resolve()in protected:continue
  if p.suffix.lower()in ['.png','.jpg']and p.name not in ['head-bottom-texture.png','head-front-texture.png','head-left-clay.png']:targets.append(p)
for name in ['root-head-review.jpg','root-whole-skin-review.jpg','root-motion-review.jpg']:
 p=q/name
 if p.exists()and p.resolve()not in protected:targets.append(p)
rows=[{'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(set(targets))]
for r in rows:
 p=Path(r['path']);assert p.resolve().is_relative_to(q)and sha(p)==r['sha256'];p.unlink()
r={'ok':True,'scope':'Superseded duplicate preview/static captures only. Original per-round head-bottom/front texture and side clay negative examples retained, all full numerical reports retained, final54-evidence images/frames and every source frozen by them protected. Final source/fin composition inputs unaffected.','deleted_bytes':sum(x['bytes']for x in rows),'deleted_files':rows};(q/'duplicate-preview-cleanup.validation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(r['deleted_bytes'])
