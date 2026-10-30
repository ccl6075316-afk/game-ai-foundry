"""Blocking per-fish fin attachment gate for a configured Godot game.

Requires a frozen plan enumerating every anatomical fin's complete basal band.
The exporter independently rejects omitted fin meshes. Checks actual GLB skin,
static pose, four actions and transitions, not preservation or tank bounds.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def discard_passing_samples(export,directory):
 """Preflight the entire set before deleting any passing pose evidence."""
 manifest=json.loads(Path(export).read_text());directory=Path(directory).resolve();removed=[];seen=set()
 for sample in manifest['samples']:
  path=Path(sample['posed_mesh_json']).resolve()
  assert path.parent==directory and path.name.startswith('sample-') and path.suffix=='.json','Unexpected dense sample path'
  assert path not in seen,'Duplicate dense sample path';seen.add(path)
  assert sha(path)==sample['sha256'],'Dense sample changed before cleanup'
  removed.append({'path':str(path),'sha256':sample['sha256'],'bytes':path.stat().st_size})
 receipt=directory/'sample-cleanup.validation.json'
 result={'ok':False,'status':'prepared','scope':'Complete passing check precedes cleanup. Exact posed output hashes retained; regenerate from frozen plan/current runtime. Failed validation samples are never discarded by this option.','removed':removed}
 receipt.write_text(json.dumps(result,indent=2))
 for item in removed:Path(item['path']).unlink()
 result.update(ok=True,status='done');receipt.write_text(json.dumps(result,indent=2))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['plan','game','godot','blender','output']:p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--species',help='Validate one finished fish; default all plan entries')
 p.add_argument('--exporter',type=Path,help='Explicit frozen runtime exporter; defaults to the standard exporter')
 p.add_argument('--checker-timeout',type=float,default=180,help='Seconds per dense complete-root check; geometric limits unchanged.')
 p.add_argument('--discard-passing-samples',action='store_true',help='After a complete successful fish check, retain receipts and remove its regenerable dense pose JSON. Failed evidence is retained.')
 p.add_argument('--reuse-full490-completion',type=Path,help='Bind this root gate to an already passing CURRENT490 completion after exact model/runtime/checker/export hashes; does not claim a new177 run.')
 a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True);plan=json.loads(a.plan.read_text(encoding='utf8'));script=Path(__file__).parent;items=[r for r in plan['items'] if not a.species or r['species']==a.species];assert items,'No matching fish'
 exporter=a.exporter.resolve() if a.exporter else script/'export_runtime_fin_roots.gd'
 if a.reuse_full490_completion:
  try:
   assert len(items)==1,'Reuse requires one explicit species';r=items[0];source=json.loads(a.reuse_full490_completion.read_text());assert source['ok'] and source['poses']==490 and source['model_sha256']==sha(r['model'])==r['model_sha256']
   assert source['plan_sha256']==sha(a.plan) and source['exporter_sha256']==sha(exporter),'Different490 plan/exporter'
   for path,h in source.get('packed_validation_bindings',{}).items():assert sha(path)==h,'Stale packed490 dependency'
   proof=next(x for x in source['checks']if x['check']=='roots');assert proof['ok'] and sha(proof['report'])==proof['sha256'];value=json.loads(Path(proof['report']).read_text());assert value['ok'] and len(value['samples'])==490 and value['checker_sha256']==sha(script/'check_runtime_fin_attachment.py') and value['export_script_sha256']==sha(exporter)
   assert value['coverage_checker_sha256']==sha(script/'runtime_pose_coverage.py') and value['tolerance_cm']==.10 and value['max_penetration_cm']==.60,'Different coverage or root limits'
   assert value['export_report_sha256']==source['export_sha256']==sha(value['export_report']),'Stale490 posed export'
   for key,file in [('controller_sha256',r.get('controller_script','res://scripts/aquarium/FoundryFishMotion.gd').removeprefix('res://')),('exhibit_sha256','scripts/aquarium/VolumeFishExhibit.gd'),('motion_config_sha256','assets/models/fish/motion/motion.json')]:assert value[key]==sha(a.game/file),'Stale490 runtime'
   assert set(value['summary'])==set(r['fins']) and value['model_sha256']==r['model_sha256'];assert all(v['failed_contact_samples']==0 for v in value['summary'].values())
   result={'ok':True,'status':'done','next_action':'human_review','checks':[{'species':r['species'],'ok':True,'fins':len(r['fins']),'poses':490,'report':proof['report'],'report_sha256':proof['sha256']}],'plan_sha256':sha(a.plan),'reused_current_full490_completion':str(a.reuse_full490_completion),'reused_completion_sha256':sha(a.reuse_full490_completion),'scope':'Exact current490 root report includes177 coverage; no duplicate export or fabricated new177 run.'}
  except Exception as e:result={'ok':False,'status':'failed','next_action':'fix_input','error':str(e)}
  (a.output/'completion.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps({'ok':result['ok'],'reused_current490':True}));return 0 if result['ok']else 1
 cmd=[str(a.godot),'--headless','--quit-after','120','--path',str(a.game.resolve()),'--script',str(exporter),'--',str(a.plan.resolve()),str(a.output),'completion']
 if a.species:cmd.append(a.species)
 try:
  for r in items:assert sha(r['model'])==r['model_sha256'],'Stale model selection '+r['species']
  run=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=600);(a.output/'export.log').write_text(run.stdout+run.stderr,encoding='utf8');assert run.returncode==0 and 'SCRIPT ERROR' not in run.stderr and 'ERROR:' not in run.stderr,run.stdout+run.stderr
  reports=[]
  for r in items:
   d=a.output/r['species'];export=d/'export.validation.json';report=d/'contact.validation.json'
   run=subprocess.run([str(a.blender),'-b','--python',str(script/'check_runtime_fin_attachment.py'),'--','--export',str(export),'--output',str(report),'--tolerance-cm','.10','--max-penetration-cm','.60'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=a.checker_timeout);(d/'check.log').write_text(run.stdout+run.stderr,encoding='utf8');value=json.loads(report.read_text());assert value['model_sha256']==r['model_sha256'];assert value['export_script_sha256']==sha(exporter);assert value['checker_sha256']==sha(script/'check_runtime_fin_attachment.py')
   for key,file in [('controller_sha256',r.get('controller_script','res://scripts/aquarium/FoundryFishMotion.gd').removeprefix('res://')),('exhibit_sha256','scripts/aquarium/VolumeFishExhibit.gd'),('motion_config_sha256','assets/models/fish/motion/motion.json')]:assert value[key]==sha(a.game/file),'Runtime changed during validation'
   assert sha(r['model'])==r['model_sha256'],'Model changed during validation'
   if a.discard_passing_samples and run.returncode==0 and value['ok']:
    discard_passing_samples(export,d)
   reports.append({'species':r['species'],'ok':bool(run.returncode==0 and value['ok']),'model':r['model'],'model_sha256':r['model_sha256'],'fins':len(value['summary']),'poses':len(value['samples']),'report':str(report),'report_sha256':sha(report),'maximum_gap_cm':max(v['maximum_signed_distance_cm'] for v in value['summary'].values()),'deepest_embedding_cm':min(v['minimum_signed_distance_cm'] for v in value['summary'].values())});print('FIN_COMPLETION',r['species'],reports[-1]['ok'],flush=True)
  ok=all(r['ok'] for r in reports);result={'ok':ok,'status':'done' if ok else 'failed','next_action':'human_review' if ok else 'fix_input','scope':'Absolute fin contact at recorded static/action/transition samples; anatomical accuracy and visual review remain separate.','plan':str(a.plan.resolve()),'plan_sha256':sha(a.plan),'checks':reports}
 except Exception as e:
  result={'ok':False,'status':'failed','next_action':'fix_input','error':str(e)}
 (a.output/'completion.validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');return 0 if result['ok'] else 1
if __name__=='__main__':sys.exit(main())
