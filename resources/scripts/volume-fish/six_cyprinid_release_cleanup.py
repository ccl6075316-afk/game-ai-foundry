"""Plan or execute explicit SHA-checked retirement of this pair's old experiments."""
import argparse,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';sys.path.insert(0,str(ROOT/'cli'));from volume_sop import check
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();ref=lambda p:{'path':str(Path(p).resolve()),'sha256':sha(p)}
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main(s,execute):
 assert s in ['crucian','grass_carp'];R=G/f'plans/reviews/six-fish-release-20261104/{s}';plan=read(R/'cleanup-plan.json');roots=[Path(x).resolve()for x in plan['target_roots']]
 for root in roots:assert root.is_relative_to((G/'experiments').resolve())and root!=(G/'experiments').resolve()and not root.is_symlink()
 inventory=R/'cleanup-inventory.json'
 if not execute:
  assert not inventory.exists();files=[]
  for root in roots:
   for p in sorted(root.rglob('*')):
    if p.is_file():
     assert p.resolve().is_relative_to(root)and not p.is_symlink();files.append({'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)})
  write(inventory,{'kind':'exact_retirement_inventory','species':s,'state':'planned_not_deleted','roots':[str(p)for p in roots],'files':files,'planned_delete_bytes':sum(x['bytes']for x in files),'plan':ref(R/'cleanup-plan.json')});print(json.dumps({'species':s,'files':len(files),'planned_bytes':sum(x['bytes']for x in files)}));return
 assert read(R/'manifest.json')['status']=='done'and read(R/'manifest.json')['user_acceptance']and read(R/'canonical-load.validation.json')['ok'];assert check(R/'production-review.json')['ok'];assert read(R/'source-cold-export.validation.json')['output_sha256']==sha(G/f'game/assets/models/fish/{s}.glb')
 retention=read(R/'retention-manifest.json')
 for row in retention['files']:
  p=Path(row['new']);assert p.is_file()and sha(p)==row['sha256']and not any(p.resolve().is_relative_to(root)for root in roots),('Missing retained input',p)
 ledger=read(R/'production-review.json')
 for row in list(ledger['candidate_files'].values())+list(ledger['evidence'].values()):
  p=Path(row['path']).resolve();assert p.is_file()and sha(p)==row['sha256']and not any(p.is_relative_to(root)for root in roots),('Current dependency still in retirement scope',p)
 inv=read(inventory);assert inv['state']=='planned_not_deleted';expected={x['path']:x for x in inv['files']};actual={str(p.resolve()):p for root in roots for p in root.rglob('*')if p.is_file()};assert set(actual)==set(expected),'Retirement inventory changed; inspect and generate a new explicit plan instead of guessing'
 for name,p in actual.items():
  row=expected[name];assert p.stat().st_size==row['bytes']and sha(p)==row['sha256']and any(p.resolve().is_relative_to(root)for root in roots)
 receipt={'ok':True,'kind':'accepted_cyprinid_old_experiment_cleanup','species':s,'user_authorized':True,'inventory':ref(inventory),'retention':ref(R/'retention-manifest.json'),'deleted_files':len(expected),'deleted_bytes':sum(x['bytes']for x in expected.values()),'roots':[str(x)for x in roots],'scope':'Exact named fish-specific roots only. Current canonical assets/editable sources/complete numeric evidence/actual original donors and unique negatives retained by SHA map; sibling fish and shared library untouched. Historical paths are intentionally retired.'};write(R/'cleanup.validation.json',receipt)
 for name,p in actual.items():assert sha(p)==expected[name]['sha256'];p.unlink()
 for root in roots:
  for d in sorted([x for x in root.rglob('*')if x.is_dir()],key=lambda x:len(x.parts),reverse=True):assert d.resolve().is_relative_to(root);d.rmdir()
  root.rmdir()
 assert check(R/'production-review.json')['ok'],'Current SOP lost a real dependency after cleanup'
 # New source-only cold exports and four original/direct pixel pairs have exact
 # numeric receipts and compact representative montage; no duplicate GLB cache.
 scratch=ROOT/f'output/six-cyprinid-release-20261104/{s}';extra=[]
 for p in list(scratch.glob('*'))+list(R.glob('*-canonical.png'))+list(R.glob('*-approved.png')):
  if p.is_file():extra.append({'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)})
 write(R/'verification-cache-cleanup.json',{'ok':True,'files':extra,'deleted_bytes':sum(x['bytes']for x in extra),'scope':'Regenerable source-only export/staging/log/pixel pairs after exact numeric parity and compact canonical-actions montage retained. Current source/model/report dependencies untouched.'})
 for row in extra:
  p=Path(row['path']);assert sha(p)==row['sha256'];p.unlink()
 if scratch.exists()and not list(scratch.iterdir()):scratch.rmdir()
 assert check(R/'production-review.json')['ok'];retained=set(p for p in R.rglob('*')if p.is_file())|set(p for p in (G/f'assets/source/fish/{s}').rglob('*')if p.is_file())|{G/f'game/assets/models/fish/{s}.glb',ROOT/f'resources/volume-fish/{s.replace("_","-")}-final-20261104.json',ROOT/f'resources/volume-fish/database-revision-20261104/{s}.profile.json'};size=sum(p.stat().st_size for p in retained);write(R/'retained-size.json',{'species':s,'files':len(retained),'total_bytes':size,'scope':'Canonical GLB, current editable/material source directory, species final metadata/profile and compact retained release evidence/history; shared library/Git object store excluded.'});m=read(R/'manifest.json');m.update(cleanup=ref(R/'cleanup.validation.json'),retained_size=ref(R/'retained-size.json'));write(R/'manifest.json',m)
 with(R/'HANDOFF.md').open('a',encoding='utf8')as f:f.write(f'\n旧实验已按{len(expected)}个精确path/SHA删除 {receipt["deleted_bytes"]:,} bytes；另清验证缓存 {sum(x["bytes"]for x in extra):,} bytes。当前规范资产/源/compact证据保留约 {size:,} bytes，详细scope见retained-size.json。删除后当前SOP再次通过，当前依赖未落在旧实验树。\n')
 m['handoff']=ref(R/'HANDOFF.md');write(R/'manifest.json',m);print(json.dumps({'ok':True,'species':s,'deleted_bytes':receipt['deleted_bytes']+sum(x['bytes']for x in extra),'retained_bytes':size}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--species',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args();main(a.species,a.execute)
