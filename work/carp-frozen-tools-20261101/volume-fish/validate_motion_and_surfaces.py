"""Blocking runtime control/material checks. Fin contact and GPU visual review remain separate gates."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['game','godot','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    scripts=Path(__file__).resolve().parent;reports=[]
    try:
        for script,label in [('validate_motion_controls.gd','motion'),('validate_surface_ownership.gd','surfaces')]:
            target=a.output/(label+'.validation.json')
            # Delete only this wrapper's previous receipt; a failed rerun must
            # never inherit success from yesterday's unchanged output path.
            if target.exists():target.unlink()
            run=subprocess.run([str(a.godot),'--headless','--path',str(a.game.resolve()),'--quit-after','120','--script',str(scripts/script),'--',str(target)],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=90)
            (a.output/(label+'.log')).write_text(run.stdout+run.stderr,encoding='utf8')
            assert run.returncode==0 and 'ERROR:' not in run.stdout+run.stderr and target.exists(),'Runtime check failed: '+label
            data=json.loads(target.read_text(encoding='utf8'));assert data['ok'] and data['checks'],'Empty/failed runtime receipt'
            for entry in data['checks']:
                assert entry['ok'] and entry['model_sha256']==sha(a.game/'assets/models/fish'/(entry['species']+'.glb')),'Stale fish receipt'
            for relative,digest in data.get('files',{}).items():assert sha(a.game/relative)==digest,'Runtime changed during validation'
            if 'controller_sha256' in data:assert sha(a.game/'scripts/aquarium/FoundryFishMotion.gd')==data['controller_sha256']
            if 'motion_config_sha256' in data:assert sha(a.game/'assets/models/fish/motion/motion.json')==data['motion_config_sha256']
            reports.append({'check':label,'ok':True,'fish':len(data['checks']),'report':str(target),'sha256':sha(target),'checker_sha256':sha(scripts/script)})
        result={'ok':True,'checks':reports,'limit':'Control/material ownership contracts only; full fin-root contact, GPU shader compilation and hidden-fin/source visual review required separately.'}
    except Exception as e:result={'ok':False,'checks':reports,'error':str(e)}
    (a.output/'completion.validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False));return 0 if result['ok'] else 1
if __name__=='__main__':sys.exit(main())
