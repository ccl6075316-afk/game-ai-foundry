"""Resume a timed-out membrane gate on a hash-verified complete posed export.

Reuse a successful current root report only when it binds that exact export.
Rerun the membrane checker; never turn the old failed wrapper into success.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['plan','game','blender','export','roots','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--species',required=True);p.add_argument('--timeout',type=float,default=1800);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);scripts=Path(__file__).resolve().parent
    try:
        spec=next(r for r in json.loads(a.plan.read_text())['items'] if r['species']==a.species);export=json.loads(a.export.read_text());roots=json.loads(a.roots.read_text())
        assert roots['ok'] and roots['export_report_sha256']==sha(a.export) and roots['checker_sha256']==sha(scripts/'check_runtime_fin_attachment.py') and roots['coverage_checker_sha256']==sha(scripts/'runtime_pose_coverage.py')
        assert export['export_script_sha256']==sha(scripts/'export_bound_mouth_fin_roots.gd') and len(export['samples'])==490 and export['fin_membrane_revision']==1
        assert export['candidate_input_sha256']==spec['mouth_candidate']['frozen_inputs']
        frozen={**export['candidate_input_sha256'],str(a.export):sha(a.export),str(a.roots):sha(a.roots),spec['model']:spec['model_sha256']}
        for path,h in frozen.items():assert sha(path)==h,'Stale posed export input'
        controller=a.game/export['controller_source'].removeprefix('res://')
        assert export['controller_sha256']==sha(controller) and export['motion_config_sha256']==sha(a.game/'assets/models/fish/motion/motion.json') and export['exhibit_sha256']==sha(a.game/'scripts/aquarium/VolumeFishExhibit.gd')
        target=a.output/'membranes.validation.json';limits=spec['membrane_clearance']
        run=subprocess.run([str(a.blender),'-b','--python',str(scripts/'check_fin_membrane_collision.py'),'--','--export',str(a.export),'--output',str(target),'--root-collar-mm',str(limits['root_collar_mm']),'--penetration-tolerance-mm',str(limits['penetration_tolerance_mm'])],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=a.timeout)
        (a.output/'membranes.log').write_text(run.stdout+run.stderr)
        data=json.loads(target.read_text());assert run.returncode==0 and data['ok'] and data['poses']==490 and data['checker_sha256']==sha(scripts/'check_fin_membrane_collision.py')
        for path,h in frozen.items():assert sha(path)==h,'Input changed during resumed check'
        result={'ok':True,'species':a.species,'poses':490,'export_sha256':sha(a.export),'candidate_input_sha256':export['candidate_input_sha256'],'plan_sha256':sha(a.plan),'checks':[{'check':'roots','report':str(a.roots),'sha256':sha(a.roots),'ok':True},{'check':'membranes','report':str(target),'sha256':sha(target),'ok':True}],'scope':'Fresh membrane run on the exact complete posed export already passed by current root checker. Original timeout report retained. Discrete poses, not continuous proof.'}
    except Exception as e:result={'ok':False,'error':str(e)}
    (a.output/'completion.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return 0 if result['ok'] else 1
if __name__=='__main__':sys.exit(main())
