"""Run existing blocking gates per presentation candidate; keep independent failures visible."""
import argparse, concurrent.futures, hashlib, json, subprocess, sys, threading
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ['plan','game','godot','blender','output','friendly_poses']:ap.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=2);a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    scripts=Path(__file__).resolve().parent;plan=json.loads(a.plan.read_text());species=[e['species'] for e in plan['items']]
    def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    bound={p:sha(a.game/p) for p in ['scripts/aquarium/FoundryFishMotion.gd','assets/models/fish/motion/motion.json','assets/models/fish/motion/presentation.json','scripts/aquarium/FriendlyFishPresentation.gd']}
    results={};lock=threading.Lock()
    def persist():
        report={'schema_version':1,'command':'volume.friendly-batch-validation','ok':len(results)==len(species) and all(x['ok'] for x in results.values()),'status':'done' if len(results)==len(species) else 'running','next_action':'human_review' if len(results)==len(species) else 'poll','species':species,'completed':len(results),'records':results,'runtime_hashes':bound,'scope':'Independent standard177 roots, standard490 full fin surfaces and33 authored behavior poses; visual preference and body coverage recorded separately. Failing fish remains unaccepted.'}
        (out/'batch.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    persist()
    def run(k):
        folder=out/k;folder.mkdir(exist_ok=True);record={'species':k,'checks':{}}
        commands=[('roots',[sys.executable,str(scripts/'validate_fin_completion.py'),'--plan',str(a.plan),'--game',str(a.game),'--godot',str(a.godot),'--blender',str(a.blender),'--species',k,'--output',str(folder/'roots')],folder/'roots/completion.validation.json'),('full_fin',[sys.executable,str(scripts/'validate_fin_membrane_clearance.py'),'--plan',str(a.plan),'--game',str(a.game),'--godot',str(a.godot),'--blender',str(a.blender),'--species',k,'--output',str(folder/'full-fin')],folder/'full-fin/completion.validation.json'),('friendly_fin',[str(a.blender),'-b','--python',str(scripts/'check_fin_membrane_collision.py'),'--','--export',str(a.friendly_poses.resolve()/k/'export.validation.json'),'--output',str(folder/'friendly-membranes.validation.json'),'--root-collar-mm','.5','--penetration-tolerance-mm','.02'],folder/'friendly-membranes.validation.json')]
        for name,cmd,report in commands:
            assert all(sha(a.game/p)==v for p,v in bound.items()),'Runtime changed during batch'
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=900)
            (folder/(name+'.log')).write_text(result.stdout+result.stderr)
            data=json.loads(report.read_text()) if report.exists() else {'ok':False,'error':'Missing fresh report'}
            record['checks'][name]={'ok':result.returncode==0 and data.get('ok',False),'returncode':result.returncode,'report':str(report),'sha256':sha(report) if report.exists() else None,'error':data.get('error')}
            print('FRIENDLY_GATE',k,name,record['checks'][name]['ok'],flush=True)
            if data.get('error'):break
        record['ok']=len(record['checks'])==3 and all(c['ok'] for c in record['checks'].values())
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(a.jobs,2))) as pool:
        futures={pool.submit(run,k):k for k in species}
        for future in concurrent.futures.as_completed(futures):
            k=futures[future]
            try:result=future.result()
            except Exception as e:result={'species':k,'ok':False,'error':str(e)}
            with lock:results[k]=result;persist()
    return 0 if all(x['ok'] for x in results.values()) else 1
if __name__=='__main__':raise SystemExit(main())
