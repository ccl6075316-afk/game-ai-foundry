"""Blocking full-fin/body collision and root-contact gate on actual game skinning."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['plan','game','godot','blender','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--species',required=True);p.add_argument('--exporter',type=Path);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    scripts=Path(__file__).resolve().parent;plan=json.loads(a.plan.read_text(encoding='utf8'));spec=next(x for x in plan['items'] if x['species']==a.species)
    exporter=a.exporter.resolve() if a.exporter else scripts/'export_runtime_fin_roots.gd'
    try:
        limits=spec['membrane_clearance'];assert 'root_collar_mm' in limits and 'penetration_tolerance_mm' in limits,'Freeze full-membrane limits before candidates'
        assert sha(spec['model'])==spec['model_sha256'],'Stale model plan'
        folder=a.output/a.species;folder.mkdir(exist_ok=True);export=folder/'export.validation.json'
        if export.exists():export.unlink()
        cmd=[str(a.godot),'--headless','--path',str(a.game.resolve()),'--quit-after','120','--script',str(exporter),'--',str(a.plan.resolve()),str(a.output),'full-fin',a.species,'--membranes']
        run=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=240);(a.output/'export.log').write_text(run.stdout+run.stderr,encoding='utf8');assert run.returncode==0 and 'ERROR:' not in run.stdout+run.stderr and export.exists(),'Full membrane export failed'
        exp=json.loads(export.read_text(encoding='utf8'));assert exp.get('fin_membrane_revision')==1 and len(exp['samples'])==490,'Incomplete full-fin pose coverage'
        checks=[]
        for checker,label,extra in [('check_runtime_fin_attachment.py','roots',['--tolerance-cm','.10','--max-penetration-cm','.60']),('check_fin_membrane_collision.py','membranes',['--root-collar-mm',str(limits['root_collar_mm']),'--penetration-tolerance-mm',str(limits['penetration_tolerance_mm'])])]:
            target=folder/(label+'.validation.json')
            if target.exists():target.unlink()
            run=subprocess.run([str(a.blender),'-b','--python',str(scripts/checker),'--','--export',str(export),'--output',str(target),*extra],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=240)
            (folder/(label+'.log')).write_text(run.stdout+run.stderr,encoding='utf8');assert target.exists(),'Missing '+label+' report'
            data=json.loads(target.read_text(encoding='utf8'));checks.append({'check':label,'ok':run.returncode==0 and data['ok'],'report':str(target),'sha256':sha(target)})
            assert data['model_sha256']==sha(spec['model']) and data['controller_sha256']==sha(a.game/spec.get('controller_script','res://scripts/aquarium/FoundryFishMotion.gd').removeprefix('res://')) and data['motion_config_sha256']==sha(a.game/'assets/models/fish/motion/motion.json'),'Runtime changed during validation'
            assert data['checker_sha256']==sha(scripts/checker),'Checker changed during validation'
        result={'ok':all(x['ok'] for x in checks),'species':a.species,'poses':490,'checks':checks,'plan_sha256':sha(a.plan),'model_sha256':sha(spec['model']),'exporter_sha256':sha(exporter),'limit':'Discrete time and whole-surface samples; only frozen root seam collar excepted; not continuous collision proof.'}
    except Exception as e:result={'ok':False,'error':str(e)}
    (a.output/'completion.validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(result));return 0 if result['ok'] else 1
if __name__=='__main__':sys.exit(main())
