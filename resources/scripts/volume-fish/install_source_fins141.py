"""Install a frozen, checked single-species source-fin revision without replacing other work."""
import argparse,hashlib,json,shutil
from pathlib import Path

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf8')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--game',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);a=p.parse_args();r=a.root.resolve();g=a.game.resolve();snap=a.snapshot.resolve();stage=read(r/'stage141.validation.json');candidate=Path(stage['candidate']);assert stage['species']==['nile_tilapia'];s='nile_tilapia'
 reports=[candidate/'build.validation.json',candidate/'source-build.validation.json',candidate/'resources/resources.validation.json',candidate/'runtime-binding.validation.json',candidate/'root177/completion.validation.json',candidate/'membrane490/completion.validation.json',r/'runtime-v10/runtime.validation.json',r/'runtime-v10/body-integrity/completion.validation.json',r/'controls-v10.validation.json',r/'delivery-v10/video.validation.json',r/'visual-review141.validation.json']
 for report in reports:assert read(report)['ok'],str(report)
 plan=read(candidate/'fin.plan.json')['items'][0]
 for path,h in plan['mouth_candidate']['frozen_inputs'].items():assert sha(path)==h,('Stale gate input',path)
 for name in ['scripts/aquarium/FishSurfaceOwnership.gd','assets/models/fish/motion/mouth-repair139.json']:
  assert sha(g/name)==sha(r/'baseline-files'/name),('Live changed; reconcile first',name)
 scope=read(r/'scope.validation.json')
 for row in scope['records']:assert sha(g/f"assets/models/fish/{row['species']}.glb")==row['source_model_sha256']
 # Patch the currently checked ownership file, keeping every other branch intact.
 hook='    changed.fin_source141 = preload("res://scripts/aquarium/FinSource141.gd").new().apply(model,species)\n';old=(g/'scripts/aquarium/FishSurfaceOwnership.gd').read_text();needle='    changed.mouth_repair139 =';assert old.count(needle)==1 and hook not in old;new=old.replace(needle,hook+needle);assert new==(snap/'scripts/aquarium/FishSurfaceOwnership.gd').read_text()
 cfg=read(g/'assets/models/fish/motion/mouth-repair139.json');newcfg=read(snap/'assets/models/fish/motion/mouth-repair139.json')
 for name,profile in cfg['profiles'].items():
  if name!=s:assert profile==newcfg['profiles'][name]
 oldn=dict(cfg['profiles'][s]);newn=dict(newcfg['profiles'][s]);oldn.pop('body');newn.pop('body');assert oldn==newn
 files=list(stage['copies'].values())+['scripts/aquarium/FinSource141.gd','assets/models/fish/motion/fin-source141.json','assets/models/fish/motion/mouth-repair139.json','scripts/aquarium/FishSurfaceOwnership.gd'];baseline={};copied={}
 for rel in files:
  source=snap/rel;dest=g/rel;assert source.is_file()
  if dest.exists():
   backup=r/'preinstall-files'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup);baseline[rel]=sha(dest)
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);assert sha(dest)==sha(source);copied[rel]=sha(dest)
 write(r/'installation141.validation.json',{'ok':True,'runtime_verified':False,'species':[s],'candidate':str(candidate),'files':copied,'before_sha256':baseline,'gates':{str(x):sha(x) for x in reports},'source_glbs_unchanged':True,'other_mouth_profiles_unchanged':True,'scope':'Checked single-fish installation. Fresh live cold-runtime and array checks still required. User accepted source pectoral cut boundary only, not whole-fish visual acceptance.'});print(json.dumps({'ok':True,'files':len(copied),'runtime_verified':False}));return 0
if __name__=='__main__':raise SystemExit(main())
