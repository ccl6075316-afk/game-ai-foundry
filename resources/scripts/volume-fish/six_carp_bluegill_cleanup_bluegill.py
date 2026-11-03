"""Exact current/historical dense-pose and frame cleanup after numeric receipts exist."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];base=(ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104/bluegill').resolve();assert base.is_relative_to(ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();protected=set()
def scan(v):
 if isinstance(v,dict):
  for x in v.values():scan(x)
 elif isinstance(v,list):
  for x in v:scan(x)
 elif isinstance(v,str):
  p=Path(v)
  if p.is_absolute()and p.exists():protected.add(p.resolve())
for name in ['production-review.json','current-evidence.validation.json','operator-final-r6/root-contact-sheets.validation.json','root-contact-sheets.validation.json']:
 if (base/name).exists():scan(json.loads((base/name).read_text(encoding='utf8')))
keepframes={0,30,48,72,96,100,144,170,192,216,250,287};genericposes={0,1,9,48,128,256,384,489};keep={};targets=[]
for folder in sorted(base.glob('delivery-r*/fin490/bluegill')):
 report=folder/'membranes.validation.json';indices=set(genericposes)
 if report.exists():
  d=json.loads(report.read_text(encoding='utf8'));scan(report)
  for row in d['summary'].values():
   worst=row.get('worst_pose')
   if worst:
    for i,s in enumerate(d['samples']):
     if s['action']==worst['action']and abs(s['seconds']-worst['seconds'])<1e-5:indices.add(i)
 keep[str(folder)]=sorted(indices)
for p in base.rglob('*'):
 if not p.is_file()or p.resolve()in protected:continue
 if p.parent.name=='frames'and p.suffix.lower()=='.jpg'and p.stem.startswith('frame-')and int(p.stem[6:])not in keepframes:targets.append(p)
 if p.stem.startswith('sample-')and p.suffix=='.json'and p.parent.name=='bluegill'and str(p.parent)in keep and int(p.stem[7:])not in keep[str(p.parent)]:targets.append(p)
before=sum(p.stat().st_size for p in base.rglob('*')if p.is_file());rows=[{'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(set(targets))]
for r in rows:
 p=Path(r['path']);assert p.resolve().is_relative_to(base)and sha(p)==r['sha256'];p.unlink()
after=sum(p.stat().st_size for p in base.rglob('*')if p.is_file());r={'ok':True,'scope':'Exact transient dense posed meshes and redundant JPG action frames only. Every full numerical conclusion, static image, current/frozen source chain, real current4probe/negative/source/lip data and required SOP evidence retained; selected static/worst pose JSON, representative action frames and24s video retained. No source/asset/unique original input deleted.','before_bytes':before,'deleted_bytes':sum(x['bytes']for x in rows),'retained_bytes_before_receipt':after,'deleted_files':rows,'kept_pose_indices_by_directory':keep,'kept_action_frame_indices':sorted(keepframes),'explicit_evidence_protected':len(protected)};(base/'cleanup.validation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({k:r[k]for k in ['before_bytes','deleted_bytes','retained_bytes_before_receipt']}))
