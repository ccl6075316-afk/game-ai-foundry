"""Parallelize existing finite checks; preserve every original pose exactly once."""
from pathlib import Path
import json,hashlib,subprocess,concurrent.futures
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(blender,checker,export,target,extra,workers,timeout):
 export=Path(export);target=Path(target);source=json.loads(export.read_text());samples=source['samples'];assert samples and workers>=2
 workers=min(workers,len(samples));original_hash=sha(export);partdir=target.parent/'membrane-parts';partdir.mkdir(exist_ok=True);jobs=[]
 for i in range(workers):
  indices=list(range(i,len(samples),workers));part={**source,'samples':[samples[j]for j in indices],'partition_scope':{'source_export_sha256':original_hash,'global_sample_indices':indices,'total_samples':len(samples)}};path=partdir/(str(i)+'.export.json');path.write_text(json.dumps(part));jobs.append((indices,path,partdir/(str(i)+'.validation.json')))
 def check(job):
  indices,path,result=job
  if result.exists():result.unlink()
  r=subprocess.run([str(blender),'-b','--python',str(checker),'--','--export',str(path),'--output',str(result),*extra],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=timeout)
  (partdir/(path.stem+'.log')).write_text(r.stdout+r.stderr)
  assert result.exists(),'Missing partition result';d=json.loads(result.read_text());assert d['poses']==len(indices)and len(d['samples'])==len(indices)
  for key in ['model_sha256','controller_sha256','motion_config_sha256']:assert d[key]==source[key],'Partition input mismatch'
  assert d['checker_sha256']==sha(checker)
  return indices,path,result,d,r.returncode
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers)as pool:results=list(pool.map(check,jobs))
 assert sha(export)==original_hash,'Full export mutated during partitions'
 seen=set();ordered=[None]*len(samples);summary={};parts=[]
 for indices,path,result,d,code in results:
  assert not(seen&set(indices));seen.update(indices)
  for i,row in zip(indices,d['samples']):ordered[i]=row
  for name,r in d['summary'].items():
   q=summary.setdefault(name,{'failed_poses':0,'worst_penetration_mm':0.,'worst_pose':None});q['failed_poses']+=r['failed_poses']
   if r['worst_penetration_mm']<q['worst_penetration_mm']:q.update(worst_penetration_mm=r['worst_penetration_mm'],worst_pose=r['worst_pose'])
  parts.append({'indices':indices,'export':str(path),'export_sha256':sha(path),'report':str(result),'sha256':sha(result),'exit_code':code})
 assert seen==set(range(len(samples)))and all(r is not None for r in ordered),'Pose coverage lost'
 template=results[0][3];d={**template,'ok':all(r[3]['ok']and r[4]==0 for r in results),'poses':len(samples),'samples':ordered,'summary':summary,'partition_proof':{'source_export_sha256':original_hash,'workers':workers,'every_pose_exactly_once':True,'parts':parts,'runner_sha256':sha(Path(__file__))}};target.write_text(json.dumps(d,indent=2));return 0 if d['ok']else 1,json.dumps({'ok':d['ok'],'summary':summary,'workers':workers,'poses':len(samples)})
