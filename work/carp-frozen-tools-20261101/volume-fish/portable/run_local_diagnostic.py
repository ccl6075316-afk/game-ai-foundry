"""Four declared actual membrane poses; reject a static-only diagnostic.

Uses the existing envelope selector without changing the full490 exporter.
Samples Static, native phase12/25, range phase6/16 and independent phase24/64.
These are representative local checks, never a full delivery gate.
The complete root checker requires177/490 coverage and is not weakened here.
"""
import argparse,copy,json,subprocess,sys,math
from pathlib import Path
import numpy as np
from parts import read,sha,fresh_output
from glb_io import read_glb,arrays
HERE=Path(__file__).resolve().parent

def run(a):
    source=read(a.plan);assert len(source['items'])==1;plan=copy.deepcopy(source);item=plan['items'][0]
    assert item['species']==a.species and sha(item['model'])==item['model_sha256']
    profile=read(item['motion_profile']);assert sha(item['motion_profile'])==item['motion_profile_sha256']
    doc,blob=read_glb(item['model']);clips=[x for x in doc['animations']if x['name']==profile['base_clip']];assert len(clips)==1
    duration=max(float(arrays(doc,blob,s['input']).max())for s in clips[0]['samplers'])
    expected=[('Static',0.),('Native',duration*12/25),('Range:WideFast',profile['period_seconds']*6/16),('Clearance:Independent',profile['period_seconds']*24/64)]
    if a.extra_poses:
        extra=read(a.extra_poses);assert isinstance(extra,list) and 0<len(extra)<=32
        for row in extra:
            assert set(row)=={'action','seconds'} and isinstance(row['action'],str)
            t=float(row['seconds']);assert math.isfinite(t) and t>=0
            pair=(row['action'],t)
            if pair not in expected:expected.append(pair)
        item['frozen_inputs'][str(a.extra_poses.resolve())]=sha(a.extra_poses)
    item['diagnostic_pose_filter']=[{'action':label,'seconds':t}for label,t in expected if label!='Static']
    item['frozen_inputs'][str(Path(__file__).resolve())]=sha(__file__)
    out=fresh_output(a.output);assert not out.exists();out.mkdir(parents=True)
    plan_path=out/'diagnostic.plan.json';plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8')
    result={'ok':False,'kind':'portable_local_four_pose_diagnostic','diagnostic_only':True,'formal_acceptance':False,'model_sha256':item['model_sha256'],'plan_sha256':sha(plan_path),'expected_poses':expected,'checks':[],'root_gate':'Not run: complete root checker requires177/490 and its coverage guard is preserved.','scope':'Four baseline actual membrane poses plus any explicitly declared own failure regressions; not177/490 or continuous clearance. Every declared pose must actually export; image review remains required.'}
    def invoke(name,cmd,report):
        run=subprocess.run(cmd,capture_output=True,timeout=180);log=run.stdout.decode('utf8',errors='replace')+run.stderr.decode('utf8',errors='replace');(out/(name+'.log')).write_text(log,encoding='utf8')
        assert run.returncode==0 and not any(s in log for s in ['ERROR:','SCRIPT ERROR','Parse Error','Traceback','Assertion failed']),name+': '+log[-1200:]
        data=read(report);result['checks'].append({'name':name,'ok':data.get('ok')is True,'report':str(report),'sha256':sha(report)});return data
    try:
        export=out/a.species/'export.validation.json'
        data=invoke('export',[str(a.godot.resolve()),'--headless','--path',str(a.game.resolve()),'--script',str(HERE/'export_fin_poses.gd'),'--',str(plan_path),str(out),'envelope',a.species,'--membranes'],export)
        observed=[(row['action'],float(row['seconds']))for row in data['samples']]
        assert len(observed)==len(expected) and all(any(label==other and abs(t-seconds)<1e-5 for other,seconds in observed)for label,t in expected),'Diagnostic missed declared poses: '+str(observed)
        assert data['model_sha256']==item['model_sha256'];result['actual_poses']=observed
        invoke('membranes',[str(a.blender.resolve()),'--background','--python-exit-code','1','--python',str(HERE.parent/'check_fin_membrane_collision.py'),'--','--export',str(export),'--output',str(out/a.species/'membranes.validation.json'),'--root-collar-mm',str(item['membrane_clearance']['root_collar_mm']),'--penetration-tolerance-mm',str(item['membrane_clearance']['penetration_tolerance_mm'])],out/a.species/'membranes.validation.json')
        result['ok']=all(r['ok']for r in result['checks'])
    except Exception as error:result['error']=str(error)[:2000]
    result.update(status='done'if result['ok']else'failed',next_action='human_review'if result['ok']else'fix_input')
    (out/'completion.validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':result['ok'],'diagnostic_only':True,'poses':len(result.get('actual_poses',[])),'checks':result['checks'],'error':result.get('error')}));return 0 if result['ok']else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['plan','godot','game','blender','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--extra-poses',type=Path,help='Own previously failed exact scheduled poses; all must actually be exported')
    p.add_argument('--species',required=True);p.add_argument('--json',action='store_true');raise SystemExit(run(p.parse_args()))
