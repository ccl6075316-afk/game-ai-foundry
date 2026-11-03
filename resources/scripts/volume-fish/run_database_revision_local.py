"""Run current-source static gates before the expensive posed delivery checks.

Uses each fish's historical independently traced mouth config/negative only after
matching their recorded hashes. Reports and logs remain beside the candidate.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def main(a):
 s=a.species;root=ROOT/f'projects/fishing-2d/experiments/five-fish-database-20261103/{s}';out=root/f'gates-r{a.revision}';modeldir=root/f'width-r{a.revision}';logs=root/f'local-logs-r{a.revision}';logs.mkdir(exist_ok=True)
 def run(name,args):
  print(json.dumps({'stage':name,'status':'running'}),flush=True)
  p=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);log=p.stdout.decode('utf8','replace');(logs/(name+'.log')).write_text(log,encoding='utf8')
  assert p.returncode==0 and not any(t in log for t in ['Traceback','SCRIPT ERROR','Error: Python']),name+':'+log[-1800:]
  print(json.dumps({'stage':name,'status':'done'}),flush=True)
 py=[sys.executable];bl=[a.blender,'--background','--python']
 if not (root/'width-r2/fish.glb').exists():run('bind',bl+[HERE/'bind_packed_atlas_revision.py','--','--blend',root/'width-r1/fish.blend','--atlas',root/'ventral-bake-r2/atlas.png','--bake-report',root/'ventral-bake-r2/material.validation.json','--output',root/'width-r2'])
 assert (modeldir/'fish.glb').exists()
 if not out.exists():run('prepare',py+[HERE/'prepare_database_revision_gates.py','--species',s,'--model',modeldir/'fish.glb','--atlas',root/'ventral-bake-r2/atlas.png','--comparison',ROOT/f'output/five-fish-database-20261103/body-preflight/{s}.validation.json','--output',out])
 cfg=read(ROOT/f'output/five-fish-database-20261103/restored/{s}/volume-baseline.config.json');cfg['profile']=str(out/'head-envelope.profile.json');(out/'volume.config.json').write_text(json.dumps(cfg,indent=2)+'\n')
 if not (out/'volume-source.blend').exists():run('project',bl+[HERE/'project_packed_volume_source.py','--','--template',ROOT/f'output/five-fish-database-20261103/restored/{s}/volume-baseline.blend','--baseline',ROOT/f'projects/fishing-2d/game/assets/models/fish/{s}.glb','--model',modeldir/'fish.glb','--output',out/'volume-source.blend'])
 if not (out/'volume.validation.json').exists():run('volume',bl+[HERE/'validate_authored_fin_volume.py','--','--blend',out/'volume-source.blend','--model',modeldir/'fish.glb','--rejected-blend',cfg['input_blend'],'--config',out/'volume.config.json','--output',out/'volume.validation.json'])
 assert read(out/'volume.validation.json')['ok'],'Static full-root/volume gate failed; inspect before posed tests'
 old=ROOT/f'projects/fishing-2d/experiments/{s.replace("_","-")}-portable-trial-20261031';configs={sha(p):p for p in old.glob('mouth-boundaries*.json')};matches=[]
 for p in old.rglob('opening*.validation.json'):
  r=read(p)
  if r.get('ok') and r.get('config_sha256') in configs:
   n=r['results']['rejected'];q=Path(n['source_blend'])
   if q.exists() and sha(q)==n['sha256']:matches.append((p,configs[r['config_sha256']],q))
 assert matches,'No hash-verified source mouth negative/config pair';p,c,n=matches[-1]
 if not (out/'mouth-opening.validation.json').exists():run('mouth',bl+[HERE/'validate_source_mouth_opening.py','--','--config',c,'--current',out/'volume-source.blend','--rejected',n,'--output',out/'mouth-opening.validation.json'])
 assert read(out/'mouth-opening.validation.json')['ok']
 if not (modeldir/'cold-export.validation.json').exists():run('cold',bl+[HERE/'export_packed_fish_source.py','--','--blend',modeldir/'fish.blend','--output',modeldir/'cold-fish.glb','--report',modeldir/'cold-export.validation.json'])
 print(json.dumps({'ok':True,'species':s,'next_action':'posed_delivery_then_visual_review'}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True);p.add_argument('--revision',type=int,default=2);p.add_argument('--blender',type=Path,required=True);main(p.parse_args())
