"""Bind unchanged species gates across an unrelated species' config edit.

Requires exact actual arrays/rest bindings/RGBA, same model/animations/controllers,
same complete own profiles and referenced resources. Never reuses a changed or
failed species. Other species in a shared JSON container are outside this scope.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resource_refs(value):
 if isinstance(value,dict):
  if isinstance(value.get('path'),str)and value['path'].startswith('res://')and'sha256'in value:yield value
  for child in value.values():yield from resource_refs(child)
 elif isinstance(value,list):
  for child in value:yield from resource_refs(child)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--game',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=a.root;current=a.game;records=[]
 try:
  old_results=read(r/'fin-completion140-final.validation.json')['records'];assert len(old_results)==11
  for row in old_results:
   s=row['species']
   if s=='peacock_bass':continue
   assert row['ok'],'Failed species cannot reuse gates';build=next(q for q in read(r/'build-batch143.plan.json')['items']if q['species']==s);c=Path(read(build['plan'])['output']);fp=c/'fin.plan.json';spec=read(fp)['items'][0];old=Path(spec['model']).parents[3];assert row['plan_sha256']==sha(fp)
   for path,h in spec['mouth_candidate']['frozen_inputs'].items():assert sha(path)==h,('Changed original gate input',path)
   for gate in [row['root_report'],row['full_report']]:assert read(gate)['ok']and read(gate)['plan_sha256']==sha(fp)
   assert sha(current/f'assets/models/fish/{s}.glb')==sha(old/f'assets/models/fish/{s}.glb')==spec['model_sha256']
   profiles={};resources={}
   for name in ['fin-source141','mouth-repair139','motion','surface-ownership','body-opacity']:
    rel=f'assets/models/fish/motion/{name}.json';x=read(old/rel);y=read(current/rel);assert {k:v for k,v in x.items()if k!='profiles'}=={k:v for k,v in y.items()if k!='profiles'};xp=x['profiles'].get(s);yp=y['profiles'].get(s);assert xp==yp,('Own profile changed',s,name);profiles[name]=hashlib.sha256(json.dumps(yp,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for ref in resource_refs(yp):
     rel=ref['path'][6:];assert sha(current/rel)==sha(old/rel)==ref['sha256'];resources[rel]=ref['sha256']
   scripts={}
   for path in (old/'scripts/aquarium').rglob('*'):
    if path.suffix not in ['.gd','.gdshader','.gdshaderinc']:continue
    rel=path.relative_to(old);assert sha(path)==sha(current/rel),('Runtime code changed',rel);scripts[str(rel)]=sha(path)
   before=read(r/'runtime-geometry-final'/(s+'.mesh.json'));nowpath=a.runtime/(s+'.mesh.json');now=read(nowpath)
   for kind in ['body','fins']:
    assert len(before[kind])==len(now[kind])
    for x,y in zip(before[kind],now[kind]):
     assert x['name']==y['name']and x['skin_joint_names']==y['skin_joint_names']and len(x['parts'])==len(y['parts'])
     for u,v in zip(x['parts'],y['parts']):
      for key in ['vertices','rest_vertices','normals','uv','joints','weights','triangles']:assert np.array_equal(u[key],v[key]),('Actual stream changed',s,kind,x['name'],key)
      if kind=='fins':assert np.array_equal(np.asarray(Image.open(u['texture']['path']).convert('RGBA')),np.asarray(Image.open(v['texture']['path']).convert('RGBA'))),'Actual fin pixels changed'
   records.append({'species':s,'ok':True,'own_profile_hashes':profiles,'resources':resources,'runtime_code':scripts,'actual_runtime_sha256':sha(nowpath),'original_fin_plan_sha256':sha(fp),'root_report':row['root_report'],'root_sha256':sha(row['root_report']),'membrane_report':row['full_report'],'membrane_sha256':sha(row['full_report'])})
  assert len(records)==10
  result={'ok':True,'records':records,'game':str(current),'scope':'Only peacock changed. Ten other species retain exact own configuration, actual arrays/rest skin/nativeRGBA, source models/animations and runtime code. Their original complete signed-distance gates remain unmodified and all original frozen inputs still exist unchanged. Current177 root audit is separately required; this report is not a new collision computation or a changed-species waiver.'}
 except Exception as e:result={'ok':False,'records':records,'error':str(e)}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':result['ok'],'species':len(records),'error':result.get('error')}));return 0 if result['ok']else 1
if __name__=='__main__':raise SystemExit(main())
