import pathlib,json,hashlib,shutil
R=pathlib.Path('E:/game-ai-foundry');G=R/'projects/fishing-2d';D=G/'plans/reviews/six-fish-release-20261104';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ref=lambda p:{'path':str(p),'sha256':sha(p)}
for s in ['carp','bluegill']:
 q=D/s;src=R/f'output/six-fish-release-20261104/carp-bluegill/{s}/source-cold-export.validation.json';data=json.loads(src.read_text(encoding='utf8'));target=q/'source-cold-export.validation.json';shutil.copy2(src,target);assert sha(src)==sha(target);assert data['output_sha256']==sha(G/f'game/assets/models/fish/{s}.glb');m=json.loads((q/'retention-manifest.json').read_text(encoding='utf8'));m['files'].append({'old':str(src),'new':str(target),'sha256':sha(target),'bytes':target.stat().st_size});(q/'retention-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 if s=='bluegill':
  byold={x['old']:x['new']for x in m['files']};old=G/'experiments/six-fish-database-20261104/bluegill/fin-volume-r6/contract.validation.json';raw=json.loads(old.read_text(encoding='utf8'));relocations=[]
  for k in ['source_correspondence','root490','membrane490','rejected_original','raw_measurement']:
   before=raw[k];p=pathlib.Path(byold[before['path']]);assert sha(p)==before['sha256'];raw[k]=ref(p);relocations.append({'role':k,'historical':before,'retained':raw[k]})
  raw.update(release_relocation_only=True,original_byte_exact_contract=ref(pathlib.Path(byold[str(old)])),relocated_same_byte_receipts=relocations,scope='New release binding of identical measured static source/model and byte-exact historical numeric receipts. Only nested retained-file locations changed; no new measurement run or old-checker execution claimed. Original contract remains immutable and retention map preserves every original reference SHA.');(q/'fin-volume-release-binding.validation.json').write_text(json.dumps(raw,indent=2)+'\n',encoding='utf8')
 targets=[G/f'experiments/six-fish-database-20261104/{s}']
 targets+=([G/'experiments/carp-lowpoly-sop-20261031',G/'experiments/blender-fish/models/carp']if s=='carp'else[G/'experiments/bluegill-portable-trial-20261030',G/'experiments/three-fish-fin-detail-20261031/bluegill'])
 files=[]
 for p in targets:
  if p.exists():
   assert p.resolve().is_relative_to(G/'experiments');files.extend(x for x in p.rglob('*')if x.is_file())
 plan={'species':s,'status':'planned_not_deleted','target_roots':[str(p.resolve())for p in targets if p.exists()],'files':[{'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(files)],'scope':'Only this accepted species current-authoring and obsolete experiment trees. Current canonical/source/unique inputs/technical numerics/SOP evidence relocated into species release with exact mapping. Other fish trees and shared folders excluded. Execute only after source/canonical/SOP success.','total_bytes':sum(p.stat().st_size for p in files)};(q/'cleanup-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(s,len(files),plan['total_bytes'])
