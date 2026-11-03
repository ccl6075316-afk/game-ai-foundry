import json,hashlib
from pathlib import Path
R=Path('E:/game-ai-foundry');G=R/'projects/fishing-2d';D=G/'plans/reviews/six-fish-release-20261104';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for s in ['carp','bluegill']:
 q=D/s;assert json.loads((q/'sop.validation.json').read_text(encoding='utf8'))['ok'];targets=list(q.glob('*-canonical.png'))+list(q.glob('*-approved.png'));scratch=R/f'output/six-fish-release-20261104/carp-bluegill/{s}';targets+=list(x for x in scratch.rglob('*')if x.is_file());rows=[]
 for p in sorted(set(targets)):
  assert p.resolve().is_relative_to(q)or p.resolve().is_relative_to(R/'output/six-fish-release-20261104/carp-bluegill');rows.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
 receipt={'ok':True,'species':s,'deleted_files':len(rows),'deleted_bytes':sum(x['bytes']for x in rows),'files':rows,'scope':'Redundant canonical/approved PNG pairs after zero-pixel-difference receipt and canonical-actions montage retained; duplicate source cold-export GLB and parts staging after exact-byte proof/report moved to release. Current canonical/source/atlas and all required SOP evidence untouched.'};(q/'verification-cleanup.validation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
 for row in rows:p=Path(row['path']);assert sha(p)==row['sha256'];p.unlink()
 if scratch.exists():
  for p in sorted([x for x in scratch.rglob('*')if x.is_dir()],key=lambda p:len(p.parts),reverse=True):p.rmdir()
  scratch.rmdir()
 print(s,receipt['deleted_bytes'])
