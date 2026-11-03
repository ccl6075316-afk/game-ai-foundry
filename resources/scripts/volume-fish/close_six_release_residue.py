"""Remove exact retired runtime/Nile leaves after preserving compact history.

Only declared paths within this checkout are eligible. Current release and
source directories are never deletion targets. Each file is hashed twice.
"""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';R=G/'plans/reviews/six-fish-release-20261104'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 receipt=R/'root-residue-cleanup.validation.json'
 if receipt.exists():print(receipt.read_text(encoding='utf8'));return
 targets=[G/'experiments'/s for s in ['nile-tilapia-static-merge','nile-width-trial-20261031']]
 targets += [G/'game/assets/models/fish/motion'/s for s in ['final165','final167','final168','final175']]
 names=['FinalizedGrassCarp175.gd','FinalizedCrucian168.gd','FinalizedCarp167.gd','FinalizedBluegill165.gd','import/CarpNoAuxLod167.gd','import/CrucianNoReplacementLod168.gd','import/GrassCarp175.gd']
 for n in names:
  p=G/'game/scripts/aquarium'/n;targets.extend([p,Path(str(p)+'.uid')])
 targets=[p.resolve() for p in targets if p.exists()]
 assert all(p.is_relative_to(G.resolve()) and p!=G.resolve() for p in targets)
 files=sorted({f for p in targets for f in ([p] if p.is_file() else p.rglob('*')) if f.is_file()})
 # The installed runtime may not reference any removed static script/payload.
 needles=[p.name for p in targets if p.suffix=='.gd']+['motion/'+x+'/' for x in ['final165','final167','final168','final175']]
 for p in (G/'game').rglob('*'):
  if not p.is_file() or p.suffix not in ['.gd','.tscn','.tres','.import','.json'] or '.godot' in p.parts or p.resolve() in files:continue
  text=p.read_text(encoding='utf8',errors='replace')
  assert not any(n in text for n in needles),f'Live reference in {p}'
 # Current Nile's review is independent of these historical trials.
 current=(G/'plans/reviews/nile-tilapia-release-20261103/production-review.json').read_text(encoding='utf8')
 assert all(n not in current for n in ['nile-tilapia-static-merge','nile-width-trial-20261031'])
 retained=[]
 for p in files:
  if p.suffix not in ['.json','.md','.py','.gd']:continue
  dest=R/'history/finished-residue'/p.relative_to(G)
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
  retained.append({'original':str(p),'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size})
 plan={'kind':'exact_retired_static_runtime_and_nile_experiments','targets':[str(p) for p in targets],'files':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}for p in files],'retained':retained,'current_nile_review_independent':True,'runtime_reference_check_passed':True}
 write(R/'root-residue-cleanup.plan.json',plan)
 for row in plan['files']:
  p=Path(row['path']);assert p.is_relative_to(G.resolve()) and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'];p.unlink()
 for p in targets:
  if p.is_dir():
   for d in sorted([x for x in p.rglob('*') if x.is_dir()],key=lambda q:len(q.parts),reverse=True):d.rmdir()
   p.rmdir()
 report={'ok':True,'deleted_files':len(files),'deleted_bytes':sum(x['bytes'] for x in plan['files']),'retained_history_bytes':sum(x['bytes'] for x in retained),'all_targets_absent':all(not p.exists() for p in targets),'plan_sha256':sha(R/'root-residue-cleanup.plan.json'),'scope':'Only six-release retired static payloads and two superseded Nile trials. Current sources, accepted models and mixed-species historical archives retained.'}
 write(receipt,report);print(json.dumps(report))
if __name__=='__main__':main()
