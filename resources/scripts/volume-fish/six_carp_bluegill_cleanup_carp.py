import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; base=(ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104/carp').resolve();assert base.is_relative_to(ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();protected=set()
def scan(v):
 if isinstance(v,dict):
  for x in v.values():scan(x)
 elif isinstance(v,list):
  for x in v:scan(x)
 elif isinstance(v,str):
  p=Path(v)
  if p.is_absolute()and p.exists():protected.add(p.resolve())
for name in ['production-review.json','root-contact-sheets.validation.json','current-evidence.validation.json']:
 scan(json.loads((base/name).read_text(encoding='utf8')))
keepframes={0,30,48,72,96,100,144,150,192,200,240,287};keepdense={0,1,9,48,72,128,256,384,489};targets=[]
for p in base.rglob('*'):
 if not p.is_file()or p.resolve()in protected:continue
 if p.parent.name=='frames'and p.suffix.lower()=='.jpg'and p.stem.startswith('frame-')and int(p.stem[6:])not in keepframes:targets.append(p)
 if p.stem.startswith('sample-')and p.suffix=='.json'and p.parent.name=='carp'and int(p.stem[7:])not in keepdense:targets.append(p)
before=sum(p.stat().st_size for p in base.rglob('*')if p.is_file()); rows=[{'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(set(targets))]
for r in rows:
 p=Path(r['path']);assert p.resolve().is_relative_to(base)and sha(p)==r['sha256'];p.unlink()
after=sum(p.stat().st_size for p in base.rglob('*')if p.is_file());receipt={'ok':True,'scope':'Exact transient dense posed meshes and redundant action JPG frames only. Full numerical root/membrane reports, 54 SOP evidence and all production/source/cold inputs retained. Movie and selected action frames replace dense frame series for review; these are discrete evidence, not continuous proof.','before_bytes':before,'deleted_bytes':sum(r['bytes']for r in rows),'retained_bytes_before_receipt':after,'deleted_files':rows,'kept_dense_pose_indices':sorted(keepdense),'kept_action_frame_indices':sorted(keepframes),'retained_numeric_reports':['delivery-r4/fin490/carp/roots.validation.json','delivery-r4/fin490/carp/membranes.validation.json'],'protected_explicit_evidence_count':len(protected)};(base/'cleanup.validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:receipt[k]for k in ['before_bytes','deleted_bytes','retained_bytes_before_receipt']},ensure_ascii=False))
