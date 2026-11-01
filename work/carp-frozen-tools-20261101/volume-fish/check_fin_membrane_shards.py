"""Run the unchanged full-membrane checker in bounded parallel pose shards.

The final receipt requires the complete 490-pose export, every unique shard,
identical frozen tolerances and runtime/model/checker hashes. Shards alone are
never delivery evidence. This only schedules checks; it does not alter samples.
"""
import argparse,concurrent.futures,hashlib,json,subprocess,sys
from pathlib import Path
from runtime_pose_coverage import validate_runtime_pose_coverage

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--export',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--blender',type=Path,required=True)
 p.add_argument('--workers',type=int,default=6);p.add_argument('--root-collar-mm',type=float,required=True);p.add_argument('--penetration-tolerance-mm',type=float,required=True)
 a=p.parse_args();e=read(a.export);validate_runtime_pose_coverage(e)
 assert len(e['samples'])==490 and e.get('fin_membrane_revision')==1 and not e.get('diagnostic_only')
 assert len({s['posed_mesh_json'] for s in e['samples']})==490
 assert sha(e['model'])==e['model_sha256']
 a.output.mkdir(parents=True,exist_ok=True);checker=Path(__file__).with_name('check_fin_membrane_collision.py');checker_hash=sha(checker)
 count=min(max(a.workers,1),12);parts=[]
 for k in range(count):
  part={**e,'samples':e['samples'][k::count],'shard_only':True,'parent_export_sha256':sha(a.export)}
  path=a.output/f'shard-{k:02}.export.json';write(path,part);parts.append(path)
 def run(path):
  target=path.with_name(path.name.replace('.export','.membranes'));log=path.with_suffix('.log')
  with log.open('w',encoding='utf8') as f:
   result=subprocess.run([str(a.blender),'-b','--python',str(checker),'--','--export',str(path),'--output',str(target),'--root-collar-mm',str(a.root_collar_mm),'--penetration-tolerance-mm',str(a.penetration_tolerance_mm)],stdout=f,stderr=subprocess.STDOUT)
  assert target.exists(),str(log);d=read(target);assert len(d['samples'])==len(read(path)['samples'])
  for key in ['model_sha256','controller_sha256','motion_config_sha256']:assert d[key]==e[key]
  assert d['checker_sha256']==checker_hash and d['root_collar_mm']==a.root_collar_mm and d['penetration_tolerance_mm']==a.penetration_tolerance_mm
  assert result.returncode==(0 if d['ok'] else 1),str(log)
  print('MEMBRANE_SHARD',path.stem,d['ok'],flush=True)
  return target,d
 with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:results=list(pool.map(run,parts))
 samples=[None]*490
 for k,(_,d) in enumerate(results):
  for index,row in zip(range(k,490,count),d['samples']):
   source=e['samples'][index];assert row['action']==source['action'] and row['seconds']==source['seconds'];samples[index]=row
 assert all(samples);summary={}
 for row in samples:
  assert set(row['fins'])==set(e['expected_fins'])
  for name,fin in row['fins'].items():
   item=summary.setdefault(name,{'failed_poses':0,'worst_penetration_mm':0.,'worst_pose':None})
   if fin['inside_samples']:item['failed_poses']+=1
   if fin['min_signed_distance_mm']<item['worst_penetration_mm']:item.update(worst_penetration_mm=fin['min_signed_distance_mm'],worst_pose={'action':row['action'],'seconds':row['seconds'],'point_m':fin['worst_point_m']})
 assert sha(checker)==checker_hash and sha(e['model'])==e['model_sha256']
 report={**results[0][1],'ok':all(d['ok'] for _,d in results),'poses':490,'samples':samples,'summary':summary,'export_report':str(a.export.resolve()),'export_report_sha256':sha(a.export),'shard_scheduler_sha256':sha(__file__),'shards':[{'path':str(path.resolve()),'sha256':sha(path)} for path,_ in results]}
 write(a.output/'membranes.validation.json',report);print(json.dumps({'ok':report['ok'],'summary':summary}));return 0 if report['ok'] else 1
if __name__=='__main__':sys.exit(main())
