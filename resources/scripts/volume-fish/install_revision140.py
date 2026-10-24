"""Install only validated140 resources; preserve all139 files and other chats."""
import argparse,json,hashlib,shutil,os
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--game',type=Path,required=True);p.add_argument('--validated-game',type=Path,required=True);a=p.parse_args();r=a.root;g=a.game.resolve();plan=json.loads((r/'install140.plan.json').read_text());validation=json.loads((r/'delivery140.validation.json').read_text());assert validation['ok'] and validation['revision_ready'] and validation['install_plan_sha256']==sha(r/'install140.plan.json');selected=set(plan['changed_species']);assert len(selected)==7 and not any(s.endswith('hammerhead') for s in selected)
 cfg=g/'assets/models/fish/motion/mouth-repair139.json';assert sha(cfg)==plan['baseline_config_sha256'],'Live mouth configuration changed; reconcile before installing';old=json.loads(cfg.read_text());backup=r/'installation140-backup';backup.mkdir(exist_ok=True);shutil.copy2(cfg,backup/'mouth-repair139.json');writes=[]
 for s in old['profiles']:
  if s not in selected:assert old['profiles'][s]==plan['config']['profiles'][s],'Unselected fish changed'
 for rel in ['scripts/aquarium/MouthRepair139.gd','scripts/aquarium/VolumeFishExhibit.gd','scripts/aquarium/FoundryFishMotion.gd','scripts/aquarium/review_candidates/red_seabream/FoundryFishMotion.gd','scripts/aquarium/review_candidates/black_seabream/FoundryFishMotion.gd','assets/models/fish/motion/motion.json']:assert sha(g/rel)==sha(a.validated_game/rel),'Live runtime changed: '+rel
 for item in plan['items']:
  s=item['species']
  if s not in selected:continue
  assert sha(g/f'assets/models/fish/{s}.glb')==item['profile']['source_model_sha256']
  for source,rel in item['copies'].items():
   assert rel.startswith(f'assets/models/fish/motion/mouth140/{s}/') and rel.endswith('.res');target=(g/rel).resolve();assert target.is_relative_to(g)
   if target.exists():assert sha(target)==sha(source),'Unexpected existing140 resource'
   else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
   assert sha(target)==sha(a.validated_game/rel)==sha(source);writes.append({'path':rel,'sha256':sha(target)})
 assert sha(cfg)==plan['baseline_config_sha256'];temp=cfg.with_suffix('.140.tmp');temp.write_text(json.dumps(plan['config'],indent=2));os.replace(temp,cfg);writes.append({'path':cfg.relative_to(g).as_posix(),'sha256':sha(cfg)})
 result={'ok':True,'runtime_verified':False,'species':sorted(selected),'install_plan_sha256':sha(r/'install140.plan.json'),'delivery_validation_sha256':sha(r/'delivery140.validation.json'),'writes':writes,'backup':str(backup),'whole_fish_acceptance':False,'scope':'Only seven frozen140 resource sets and mouth configuration written.139 resources, original GLBs, helper/hooks, unselected fish and hammerheads untouched. Fresh live cold verification still required.'};(r/'installation140.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps({'ok':True,'fish':len(selected),'writes':len(writes)}))
if __name__=='__main__':main()
