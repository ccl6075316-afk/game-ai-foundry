"""Run unchanged complete-root and membrane gates for frozen mouth candidates."""
import argparse, concurrent.futures, hashlib, json, subprocess, sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['root','game','godot','blender']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--species',nargs='+',required=True)
    p.add_argument('--jobs',type=int,default=2)
    a=p.parse_args();scripts=Path(__file__).resolve().parent
    def run(species):
        folder=a.root/species;checks=[]
        for script,out,extra in [('validate_fin_completion.py','fin-root177',[]),('validate_fin_membrane_clearance.py','full-fin490',['--checker-timeout','1800'])]:
            target=folder/out
            args=[sys.executable,'-X','utf8',str(scripts/script),'--plan',str(folder/'fin.plan.json'),'--game',str(a.game),'--godot',str(a.godot),'--blender',str(a.blender),'--species',species,'--output',str(target),'--exporter',str(scripts/'export_bound_mouth_fin_roots.gd'),*extra]
            log=folder/(out+'.batch.log')
            with log.open('w',encoding='utf8') as f:result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
            report=target/'completion.validation.json'
            data=json.loads(report.read_text()) if report.exists() else {'ok':False,'error':'Missing report'}
            checks.append({'report':str(report),'sha256':hashlib.sha256(report.read_bytes()).hexdigest() if report.exists() else None,'ok':result.returncode==0 and data['ok']})
            print('MOUTH_FIN',species,out,checks[-1]['ok'],flush=True)
            if not checks[-1]['ok']:break
        return {'species':species,'ok':all(c['ok'] for c in checks) and len(checks)==2,'checks':checks}
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as pool:rows=list(pool.map(run,a.species))
    output={'ok':all(r['ok'] for r in rows),'records':rows,'scope':'Frozen candidate body with original rig and complete species-specific basal selection. No visual acceptance.'}
    (a.root/'fin-batch139.validation.json').write_text(json.dumps(output,indent=2))
    return 0 if output['ok'] else 1
if __name__=='__main__':sys.exit(main())
