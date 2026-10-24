"""Install the frozen severe-fin batch only after source, physical and GPU review."""
import argparse,json,hashlib,shutil
from pathlib import Path
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--game',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);a=p.parse_args();r=a.root.resolve();g=a.game.resolve();snap=a.snapshot.resolve();scope=read(r/'scope.validation.json');stage=read(r/'stage143.validation.json');batch=read(r/'build-batch143.plan.json')['items'];species={x['species']for x in batch};assert len(species)==11 and 'nile_tilapia'not in species and not species.intersection(scope['excluded_species'])
 reports=[r/x for x in ['build143.validation.json','static143.validation.json','runtime-binding-current.validation.json','body-material-current.validation.json','runtime-current/completion.validation.json','runtime-current/runtime.validation.json','runtime-current/body-integrity/completion.validation.json','body-source-current/completion.validation.json','fin-controls-current.validation.json','delivery-current/video.validation.json','body-colour-current.validation.json','visual-review143.validation.json','gates143.validation.json','unchanged-species-binding143.validation.json','current-root177.validation.json','binding-negative143.validation.json']]
 gates={x['species']:x for x in read(r/'gates143.validation.json')['records']};visual=read(r/'visual-review143.validation.json');visual_rows={x['species']:x for x in visual['records']}
 for path,h in visual['files'].items():assert sha(path)==h,('Stale reviewed visual',path)
 for row in batch:
  c=Path(read(row['plan'])['output']);plan=c/'fin.plan.json';d=read(plan)['items'][0]
  for path,h in d['mouth_candidate']['frozen_inputs'].items():assert sha(path)==h,('Stale frozen candidate',path)
  assert visual_rows[row['species']]['current_fin_plan_sha256']==sha(plan),'Visual review belongs to another candidate'
  for rel in ['source-build.validation.json','runtime-binding.validation.json']:
   path=c/rel;report=read(path);assert report['ok'],path
   if 'plan_sha256'in report:assert report['plan_sha256']==sha(plan if rel.startswith(('root177','membrane490'))else row['plan']),path
   reports.append(path)
  gate=gates[row['species']];assert gate['plan_sha256']==sha(plan)
  for key,hashkey in [('root_report','root_sha256'),('membrane_report','membrane_sha256')]:
   path=Path(gate[key]);assert read(path)['ok']and sha(path)==gate[hashkey];reports.append(path)
 for report in reports:assert read(report)['ok'],report
 assert read(r/'runtime-current/runtime.validation.json')['config_sha256']==sha(snap/'assets/models/fish/motion/mouth-repair139.json')
 controls=read(r/'fin-controls-current.validation.json');assert controls['config_sha256']==sha(snap/'assets/models/fish/motion/mouth-repair139.json')and controls['motion_config_sha256']==sha(snap/'assets/models/fish/motion/motion.json')
 capture=read(r/'delivery-current/capture.validation.json')
 for path,h in capture['runtime_dependencies'].items():assert sha(snap/path)==h,('Stale captured runtime',path)
 assert read(r/'delivery-current/video.validation.json')['capture_sha256']==sha(r/'delivery-current/capture.validation.json')
 for rel,h in scope['baseline_game_files'].items():assert sha(g/rel)==h,('Live changed; reconcile',rel)
 for row in scope['records']:
  assert sha(g/f"assets/models/fish/{row['species']}.glb")==row['source_model_sha256'];assert sha(row['source'])==row['source_sha256']
 cfg=read(g/'assets/models/fish/motion/fin-source141.json');new=stage['fin_config'];assert cfg['profiles']['nile_tilapia']==new['profiles']['nile_tilapia'];assert set(new['profiles'])==set(cfg['profiles'])|species
 mouth=read(g/'assets/models/fish/motion/mouth-repair139.json');newmouth=stage['mouth_config'];assert set(mouth['profiles'])==set(newmouth['profiles'])
 for s,profile in mouth['profiles'].items():
  if s not in species:assert profile==newmouth['profiles'][s]
  else:
   before=dict(profile);after=dict(newmouth['profiles'][s]);before.pop('body');after.pop('body')
   if s=='peacock_bass':
    original=before.pop('fins');retained=after.pop('fins');assert retained=={k:v for k,v in original.items()if k not in new['profiles'][s]['fins']}
   assert before==after,('Unreviewed mouth/profile change',s)
 files=list(stage['copies'].values())+['scripts/aquarium/FinSource141.gd','assets/models/fish/motion/fin-source141.json','assets/models/fish/motion/mouth-repair139.json'];assert len(files)==51
 baseline={};copied={}
 for rel in files:
  source=snap/rel;dest=g/rel;assert source.is_file()
  if dest.exists():
   backup=r/'preinstall-files'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup);baseline[rel]=sha(dest)
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);assert sha(dest)==sha(source);copied[rel]=sha(dest)
 result={'ok':True,'runtime_verified':False,'species':sorted(species),'files':copied,'before_sha256':baseline,'gates':{str(x):sha(x)for x in reports},'source_glbs_unchanged':True,'source_rgba_unchanged':True,'nile142_profile_and_all_other_mouth_profiles_unchanged':True,'whole_fish_acceptance':False,'scope':'33 source-fin replacements plus5 contact-only fin replacements (arapaima4,peacock soft-dorsal1) and10 RGB-only body attachment resources. Fresh live cold validation required; no new user visual acceptance inferred.'}
 (r/'installation143.validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'files':len(files),'runtime_verified':False}));return 0
if __name__=='__main__':raise SystemExit(main())
