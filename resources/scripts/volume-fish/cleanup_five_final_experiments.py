"""Exact SHA-verified retirement of the accepted five fish's obsolete experiments."""
import argparse,gzip,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';R=G/'plans/reviews/five-fish-release-20261104';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text(encoding='utf8'))
NAMES=['rainbow_trout','brown_trout','atlantic_salmon','sea_bass','red_emperor'];EXPS=['five-fish-database-20261103','five-fish-head-evidence-20261101','five-fish-list-20261031','five-fish-side-top-video-20261101','five-fish-version-compare-20261101','five-fish-width-cutout-review-20261101']+[s.replace('_','-')+suffix for s in NAMES for suffix in ['-portable-trial-20261031','-static-merge']]
roots=[G/'experiments'/s for s in EXPS]+[G/'experiments/blender-fish/models'/s for s in NAMES]+[G/f'game/assets/models/fish/motion/final{i}' for i in [164,166,169,170,176]]+[ROOT/'output/five-fish-database-20261103']
singles=[G/f'game/scripts/aquarium/{name}.gd'for name in ['FinalizedRainbowTrout176','FinalizedBrownTrout166','FinalizedAtlanticSalmon164','FinalizedSeaBass170','FinalizedRedEmperor169']]+[G/f'game/scripts/aquarium/import/{name}.gd'for name in ['RainbowTrout176','BrownTroutNoBodyLod166','RedEmperorNoBodyLod169']]
singles+=[p.with_suffix(p.suffix+'.uid')for p in list(singles)]
def plan():
 assert read(R/'installation.validation.json')['ok'];retention=read(R/'retention-manifest.json')
 for r in retention['files']:assert Path(r['new']).is_file() and sha(Path(r['new']))==r['sha256']
 # Small original input PNGs and prior width overlays remain unique provenance.
 raw=ROOT/'output/five-fish-database-20261103'
 for p in list((raw/'restored').rglob('*.png'))+[raw/'body-preflight/body-comparison.png',raw/'restored/installation.validation.json']:
  if p.exists():
   dest=R/'history/original-inputs'/p.relative_to(raw);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);assert sha(dest)==sha(p);retention['files'].append({'old':str(p),'new':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size})
 (R/'retention-manifest.json').write_text(json.dumps(retention,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 tracked=set(subprocess.check_output(['git','ls-files','-z'],cwd=G).decode('utf8').split('\0'));files=set()
 for root in roots:
  assert root.resolve().is_relative_to(ROOT) and (root.is_relative_to(G/'experiments')or root.is_relative_to(G/'game/assets/models/fish/motion')or root==raw)
  if root.exists():
   assert not root.is_symlink();files.update(p for p in root.rglob('*')if p.is_file())
 files.update(p for p in singles if p.exists());records=[]
 for p in sorted(files):
  assert not p.is_symlink() and p.resolve().is_relative_to(ROOT);rel=p.relative_to(G).as_posix()if p.is_relative_to(G)else None;records.append({'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size,'tracked_in_game':rel in tracked if rel else False})
 # Remaining runtime source must not call removed legacy binders/import hooks.
 deleting={p.resolve()for p in files};retired=['FinalizedRainbowTrout176.gd','FinalizedBrownTrout166.gd','FinalizedAtlanticSalmon164.gd','FinalizedSeaBass170.gd','FinalizedRedEmperor169.gd','motion/final164/','motion/final166/','motion/final169/','motion/final170/','motion/final176/']
 foreign=[]
 for p in (G/'game').rglob('*'):
  if p.suffix not in ['.gd','.tscn','.import'] or p.resolve()in deleting:continue
  content=p.read_text(encoding='utf8',errors='replace')
  if any(t in content for t in retired):foreign.append(str(p))
 assert not foreign,foreign
 with gzip.open(R/'cleanup-files.json.gz','wt',encoding='utf8')as f:json.dump(records,f,ensure_ascii=False,separators=(',',':'))
 summary={'ok':True,'scope':'Only five accepted species: obsolete trials/static merges/batch previews, their old model subtrees, retired binders/import hooks and old per-species animation/LOD payloads, plus redundant restoration workspace. Current source/GLBs, complete numeric reports, unique source images/negative fixtures, representative visuals/videos and library raw inputs retained. No asset archive.','roots':[str(p.resolve())for p in roots],'single_files':[str(p.resolve())for p in singles],'files':len(records),'bytes':sum(r['bytes']for r in records),'tracked_game_files':sum(r['tracked_in_game']for r in records),'list_sha256':sha(R/'cleanup-files.json.gz'),'retention_sha256':sha(R/'retention-manifest.json'),'game_parent_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=G,text=True).strip(),'runtime_reference_audit_unresolved':foreign}
 (R/'cleanup-plan.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k not in ['roots','single_files','scope']}))
def execute():
 p=read(R/'cleanup-plan.json');assert p['ok'] and p['retention_sha256']==sha(R/'retention-manifest.json') and p['list_sha256']==sha(R/'cleanup-files.json.gz');retention=read(R/'retention-manifest.json')
 for r in retention['files']:assert sha(Path(r['new']))==r['sha256']
 with gzip.open(R/'cleanup-files.json.gz','rt',encoding='utf8')as f:rows=json.load(f)
 for row in rows:
  q=Path(row['path']);assert q.resolve().is_relative_to(ROOT) and not q.is_symlink() and q.stat().st_size==row['bytes'] and sha(q)==row['sha256']
 for row in rows:Path(row['path']).unlink()
 for root in roots:
  if not root.exists():continue
  for d in sorted([x for x in root.rglob('*')if x.is_dir()],key=lambda q:len(q.parts),reverse=True):assert d.resolve().is_relative_to(root.resolve()) and not d.is_symlink();d.rmdir()
  root.rmdir()
 report={'ok':True,'deleted_files':len(rows),'deleted_bytes':sum(r['bytes']for r in rows),'tracked_game_files_deleted':sum(r['tracked_in_game']for r in rows),'all_exact_targets_removed':all(not Path(r['path']).exists()for r in rows),'current_source_and_evidence_retained':True,'new_asset_archives':0};(R/'cleanup-execution.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args();execute()if a.execute else plan()
