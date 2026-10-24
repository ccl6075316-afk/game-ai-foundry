"""Install only the frozen, validated authorized mouth delta into an existing game."""
import argparse,hashlib,json,os,shutil
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['plan','validation','game','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();game=a.game.resolve();plan=json.loads(a.plan.read_text());validation=json.loads(a.validation.read_text())
    assert validation['ok'] and validation['mouth_delta_ready'] and validation['install_plan_sha256']==sha(a.plan),'No current complete delta validation'
    names=set(plan['config']['profiles']);assert len(names)==14 and not names.intersection(plan['excluded']) and not any(n.endswith('hammerhead') for n in names)
    assert sha(plan['helper'])==plan['helper_sha256'];writes=[];backup=a.output.parent/'installation139-backup';backup.mkdir(parents=True,exist_ok=True)
    def target(relative):
        path=(game/relative).resolve();assert path.is_relative_to(game);return path
    def preserve(path):
        if path.exists():
            dest=backup/path.relative_to(game);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    for item in plan['items']:
        s=item['species'];assert s in names and sha(game/f'assets/models/fish/{s}.glb')==item['profile']['source_model_sha256']
        for source,relative in item['copies'].items():
            assert relative.startswith(f'assets/models/fish/motion/mouth139/{s}/') and relative.endswith('.res')
            kind=next(v for v in [item['profile'].get('body'),item['profile'].get('lips'),*item['profile'].get('fins',{}).values()] if v and v['path']=='res://'+relative)
            assert sha(source)==kind['sha256'];dest=target(relative);preserve(dest);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);assert sha(dest)==kind['sha256'];writes.append({'path':relative,'sha256':sha(dest)})
    helper=target('scripts/aquarium/MouthRepair139.gd');preserve(helper);shutil.copy2(plan['helper'],helper);writes.append({'path':helper.relative_to(game).as_posix(),'sha256':sha(helper)})
    config=target('assets/models/fish/motion/mouth-repair139.json');preserve(config);config.write_text(json.dumps(plan['config'],indent=2));writes.append({'path':config.relative_to(game).as_posix(),'sha256':sha(config)})
    hook=target('scripts/aquarium/FishSurfaceOwnership.gd');preserve(hook)
    line='    changed.mouth_repair139 = preload("res://scripts/aquarium/MouthRepair139.gd").new().apply(model,species)'
    for attempt in range(3):
        before=sha(hook);code=hook.read_text(encoding='utf8')
        if line in code:break
        anchor='    changed.hammer_surface136 = preload("res://scripts/aquarium/HammerSurface136.gd").new().apply(model,species)'
        assert code.count(anchor)==1,'Unknown current ownership integration point'
        updated=code.replace(anchor,anchor+'\n'+line)
        if sha(hook)!=before:continue
        temporary=hook.with_suffix('.139.tmp');temporary.write_text(updated,encoding='utf8');os.replace(temporary,hook);break
    assert line in hook.read_text(encoding='utf8');writes.append({'path':hook.relative_to(game).as_posix(),'sha256':sha(hook)})
    result={'ok':True,'runtime_verified':False,'species':sorted(names),'install_plan_sha256':sha(a.plan),'validation_sha256':sha(a.validation),'game':str(game),'writes':writes,'backup':str(backup),'excluded':plan['excluded'],'scope':'Authorized frozen resources copied and one ownership hook added. Original GLBs and unrelated/hammerhead assets are not written. Fresh actual-game cold verification required before declaring delivery.'}
    a.output.write_text(json.dumps(result,indent=2));print(json.dumps({'ok':True,'fish':len(names),'writes':len(writes),'runtime_verified':False}))
if __name__=='__main__':main()
