"""Execute reviewed per-file SHA plans after canonical and release SOP success."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[3];G=R/'projects/fishing-2d';D=G/'plans/reviews/six-fish-release-20261104'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for s in ['carp','bluegill']:
 q=D/s;assert read(q/'sop.validation.json')['ok']and read(q/'canonical-load.validation.json')['ok']and read(q/'canonical-pixels.validation.json')['ok']and read(q/'source-cold-export.validation.json')['ok']
 for row in read(q/'retention-manifest.json')['files']:
  p=Path(row['new']);assert p.is_file()and sha(p)==row['sha256'],('Retained byte changed',p)
 plan=read(q/'cleanup-plan.json');roots=[Path(x).resolve()for x in plan['target_roots']]
 assert all(p.is_relative_to(G/'experiments')and p!=G/'experiments'for p in roots)
 assert {str(p.resolve())for root in roots for p in root.rglob('*')if p.is_file()}=={r['path']for r in plan['files']},'Input inventory changed; re-audit before delete'
 for row in plan['files']:
  p=Path(row['path']);assert any(p.resolve().is_relative_to(root)for root in roots)and not p.is_symlink()and p.stat().st_size==row['bytes']and sha(p)==row['sha256'],p
 # Numerical conclusions and unique inputs are already byte-exact in release.
 write(q/'cleanup.validation.json',{'ok':True,'species':s,'deleted_files':len(plan['files']),'deleted_bytes':plan['total_bytes'],'exact_SHA_plan':{'path':str(q/'cleanup-plan.json'),'sha256':sha(q/'cleanup-plan.json')},'scope':'Only exact accepted-species experiment trees. Canonical GLB, packed source, source artwork/actual atlas/necessary donors, original anatomical negative fixtures, complete numeric and compact SOP/operator evidence retained. Other species and shared roots untouched.','new_archive_created':False})
 for row in plan['files']:Path(row['path']).unlink()
 for root in roots:
  for p in sorted([p for p in root.rglob('*')if p.is_dir()],key=lambda p:len(p.parts),reverse=True):p.rmdir()
  root.rmdir()
 print(json.dumps({'species':s,'deleted_bytes':plan['total_bytes'],'deleted_files':len(plan['files'])}),flush=True)
