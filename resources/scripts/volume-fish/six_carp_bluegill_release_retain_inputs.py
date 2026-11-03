import json,hashlib,shutil
from pathlib import Path
R=Path('E:/game-ai-foundry');G=R/'projects/fishing-2d';D=G/'plans/reviews/six-fish-release-20261104';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for s in ['carp','bluegill']:
 q=D/s;m=json.loads((q/'retention-manifest.json').read_text(encoding='utf8'));known={x['old']for x in m['files']};roots=([G/'experiments/carp-lowpoly-sop-20261031/native-fins-r5']if s=='carp'else[G/'experiments/three-fish-fin-detail-20261031/bluegill/masks-r2']);extra=([G/'experiments/six-fish-database-20261104/carp/volume-current.config.json',G/'experiments/carp-lowpoly-sop-20261031/packed-r5/packing.validation.json']if s=='carp'else[G/'experiments/three-fish-fin-detail-20261031/bluegill/tail-root-skin-r2/author/tail-donors.validation.json'])
 for root in roots:extra.extend(p for p in root.rglob('*')if p.is_file()and p.suffix.lower()in['.png','.json'])
 for p in extra:
  p=p.resolve()
  if str(p)in known:continue
  target=q/'history'/p.relative_to(G);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);assert sha(p)==sha(target);m['files'].append({'old':str(p),'new':str(target),'sha256':sha(target),'bytes':target.stat().st_size});known.add(str(p))
 (q/'retention-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(s,len(m['files']))
