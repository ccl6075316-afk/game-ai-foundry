"""Exact SHA-listed retirement of this pair's obsolete experiment roots only."""
import json,hashlib,stat,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';RELEASE=G/'plans/reviews/six-fish-release-20261104';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def inventory(root):
 result=[]
 for p in root.rglob('*'):
  st=p.lstat();assert not(p.is_symlink()or getattr(st,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT),str(p)
  if p.is_file():result.append(p)
 return result
for S,oldname,date in [('red_seabream','red-seabream-lowpoly-sop-20261101','20261101'),('black_seabream','black-seabream-lowpoly-sop-20261102','20261102')]:
 O=RELEASE/S;A=G/'assets/source/fish'/S;roots=[G/'experiments'/oldname,G/'experiments/six-fish-database-20261104'/S]
 for r in roots:assert r.resolve()==r and r.is_relative_to(G/'experiments')and r.is_dir()
 for name in ['cleanup.validation.json','preflight-cleanup.validation.json']:
  if(O/name).exists():shutil.copy2(O/name,O/'history'/('prior-'+name))
 acceptance=roots[0]/('release-'+date)/'user-acceptance.json';shutil.copy2(acceptance,O/'history/original-user-acceptance.json')
 # Verify all current active ledger roles/evidence before retiring originals.
 ledger=json.loads((O/'production-review.json').read_text(encoding='utf8'))
 for table in ['candidate_files','evidence']:
  for e in ledger[table].values():
   p=Path(e['path']).resolve();assert p.is_file()and sha(p)==e['sha256'];assert not any(p.is_relative_to(r)for r in roots),(table,p)
 retained=inventory(O)+inventory(A)+[G/f'game/assets/models/fish/{S}.glb'];index={};keep=[]
 for p in retained:
  h=sha(p);index.setdefault(h,[]).append(str(p));keep.append({'path':str(p),'sha256':h,'bytes':p.stat().st_size})
 files=[p for r in roots for p in inventory(r)];rows=[]
 for p in files:
  h=sha(p);rows.append({'path':str(p.resolve()),'sha256':h,'bytes':p.stat().st_size,'retained_same_bytes_at':index.get(h,[]),'reason':'Retire original experimental location after compact current source/evidence publication'if h in index else'Retired noncurrent candidate, dense sampling/frame/cache/log, or superseded historical assembly; current unique inputs, selected negative and complete aggregate numeric results retained separately'})
 plan=O/'cleanup.plan.json';assert not plan.exists();write(plan,{'kind':'exact_pair_experiment_retirement_plan','species':S,'authorized_scope':'User explicitly authorized six-fish finished installation and deletion of associated old experiments/screenshots. Root delegated this exact pair.','roots':[str(r)for r in roots],'files':rows,'file_count':len(rows),'delete_bytes':sum(r['bytes']for r in rows),'retained_files':keep,'retained_bytes_before_receipt':sum(r['bytes']for r in keep),'limits':'No blanket archive created. Original paths in immutable historical reports are provenance only. Exact retained bytes map by SHA; migrated recheck recipes are separate from historical run plan SHA.'})
 # Re-verify exact hashes immediately before unlink; no path expansion or shell.
 deleted=0
 for row in rows:
  p=Path(row['path']);assert p.is_absolute()and any(p.is_relative_to(r)for r in roots);assert p.resolve()==p and p.is_file()and sha(p)==row['sha256']and p.stat().st_size==row['bytes'];p.unlink();deleted+=row['bytes']
 for r in roots:
  for p in sorted([p for p in r.rglob('*')if p.is_dir()],key=lambda p:len(p.parts),reverse=True):p.rmdir()
  r.rmdir();assert not r.exists()
 receipt={'ok':True,'kind':'exact_pair_experiment_retirement_receipt','species':S,'plan':str(plan),'plan_sha256':sha(plan),'deleted_files':len(rows),'deleted_bytes':deleted,'all_planned_files_deleted':True,'removed_roots':[str(r)for r in roots],'retained_current_files':len(keep),'retained_bytes_before_receipt':sum(r['bytes']for r in keep),'no_new_archive':True,'scope':'Only verified exact two own species experiment trees. Current canonical GLB/source/atlas/native inputs/necessary material donors, unique negative, numeric aggregates and representative views remain.'};write(O/'cleanup.validation.json',receipt)
 print(json.dumps({'species':S,'deleted_files':len(rows),'deleted_bytes':deleted,'retained_bytes':receipt['retained_bytes_before_receipt']}),flush=True)
