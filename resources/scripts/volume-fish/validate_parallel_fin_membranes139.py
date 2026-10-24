"""Partition a complete490-pose export across unchanged membrane-check kernels.

The complete input must pass coverage validation first. Every pose and fin is
retained, with identical tolerances; workers only divide time samples. The
aggregate fails on any missing partition, changed input or membrane collision.
"""
import argparse,concurrent.futures,copy,hashlib,json,subprocess,sys
from pathlib import Path
from runtime_pose_coverage import validate_runtime_pose_coverage
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['plan','game','blender','export','roots','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--species',required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--partitions',type=int,default=8);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);scripts=Path(__file__).resolve().parent;kernel=scripts/'check_fin_membrane_collision.py'
    try:
        spec=next(r for r in json.loads(a.plan.read_text())['items'] if r['species']==a.species);export=json.loads(a.export.read_text());roots=json.loads(a.roots.read_text());validate_runtime_pose_coverage(export)
        assert len(export['samples'])==490 and export['fin_membrane_revision']==1
        assert roots['ok'] and roots['export_report_sha256']==sha(a.export) and roots['checker_sha256']==sha(scripts/'check_runtime_fin_attachment.py') and roots['coverage_checker_sha256']==sha(scripts/'runtime_pose_coverage.py')
        assert export['candidate_input_sha256']==spec['mouth_candidate']['frozen_inputs']
        assert export['model_sha256']==sha(spec['model']) and export['controller_sha256']==sha(a.game/export['controller_source'].removeprefix('res://')) and export['exhibit_sha256']==sha(a.game/'scripts/aquarium/VolumeFishExhibit.gd') and export['motion_config_sha256']==sha(a.game/'assets/models/fish/motion/motion.json')
        frozen={**export['candidate_input_sha256'],str(a.export):sha(a.export),str(a.roots):sha(a.roots),str(kernel):sha(kernel)}
        for path,h in frozen.items():assert sha(path)==h
        limits=spec['membrane_clearance'];groups=[list(range(i,490,a.partitions)) for i in range(a.partitions)];assert all(groups) and sorted(i for g in groups for i in g)==list(range(490))
        def run(pair):
            part,indices=pair;folder=a.output/f'part-{part:02d}';folder.mkdir();sub=copy.deepcopy(export);sub['samples']=[export['samples'][i] for i in indices];source=folder/'export.json';source.write_text(json.dumps(sub));target=folder/'membranes.validation.json'
            with (folder/'check.log').open('w',encoding='utf8') as log:
                process=subprocess.run([str(a.blender),'-b','--python',str(kernel),'--','--export',str(source),'--output',str(target),'--root-collar-mm',str(limits['root_collar_mm']),'--penetration-tolerance-mm',str(limits['penetration_tolerance_mm'])],stdout=log,stderr=subprocess.STDOUT,timeout=2400)
            d=json.loads(target.read_text());assert process.returncode in [0,1] and d['poses']==len(indices) and d['checker_sha256']==sha(kernel)
            assert set(d['summary'])==set(export['expected_fins']) and d['root_collar_mm']==limits['root_collar_mm'] and d['penetration_tolerance_mm']==limits['penetration_tolerance_mm']
            assert d['model_sha256']==export['model_sha256'] and d['controller_sha256']==export['controller_sha256'] and d['motion_config_sha256']==export['motion_config_sha256']
            for i,row in zip(indices,d['samples']):assert row['action']==export['samples'][i]['action'] and row['seconds']==export['samples'][i]['seconds'] and set(row['fins'])==set(export['expected_fins'])
            print('FIN_PART139',part,'poses',len(indices),'ok',d['ok'],flush=True)
            return {'indices':indices,'report':str(target),'sha256':sha(target),'input_sha256':sha(source),'data':d}
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:parts=list(pool.map(run,enumerate(groups)))
        samples=[None]*490;summary={name:{'failed_poses':0,'worst_penetration_mm':0.,'worst_pose':None} for name in export['expected_fins']}
        for part in parts:
            for i,row in zip(part['indices'],part['data']['samples']):assert samples[i] is None;samples[i]=row
            for name,value in part['data']['summary'].items():
                summary[name]['failed_poses']+=value['failed_poses']
                if value['worst_penetration_mm']<summary[name]['worst_penetration_mm']:summary[name].update(worst_penetration_mm=value['worst_penetration_mm'],worst_pose=value['worst_pose'])
        assert all(row is not None for row in samples)
        for path,h in frozen.items():assert sha(path)==h,'Changed partition input'
        membrane={'ok':all(v['failed_poses']==0 for v in summary.values()),'poses':490,'summary':summary,'samples':samples,'model_sha256':export['model_sha256'],'controller_sha256':export['controller_sha256'],'motion_config_sha256':export['motion_config_sha256'],'root_collar_mm':limits['root_collar_mm'],'penetration_tolerance_mm':limits['penetration_tolerance_mm'],'export_report_sha256':sha(a.export),'candidate_input_sha256':export['candidate_input_sha256'],'checker_sha256':sha(__file__),'kernel_sha256':sha(kernel),'partitions':[{k:v for k,v in part.items() if k!='data'} for part in parts],'scope':'All490 original samples and all expected fins, using the unchanged full vertex/edge/face checker. Time samples partitioned only; no tolerance/selection changes. Discrete sampling, not continuous proof.'}
        target=a.output/'membranes.validation.json';target.write_text(json.dumps(membrane,indent=2));result={'ok':membrane['ok'],'species':a.species,'poses':490,'plan_sha256':sha(a.plan),'export_sha256':sha(a.export),'checks':[{'check':'roots','report':str(a.roots),'sha256':sha(a.roots),'ok':True},{'check':'membranes','report':str(target),'sha256':sha(target),'ok':membrane['ok']}]}
    except Exception as e:result={'ok':False,'error':str(e)}
    (a.output/'completion.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return 0 if result['ok'] else 1
if __name__=='__main__':sys.exit(main())
