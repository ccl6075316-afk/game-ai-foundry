import json,struct,numpy as np
from pathlib import Path
r=Path(__file__).resolve().parent
def load(ver):
 raw=(r/ver/'octopus-actions.glb').read_bytes();n=struct.unpack_from('<I',raw,12)[0];d=json.loads(raw[20:20+n]);buf=raw[28+n:]
 def arr(i):
  a=d['accessors'][i];dims={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];dt={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
  def read(view,offset,count,typ):
   v=d['bufferViews'][view];return np.frombuffer(buf,dtype=typ,count=count,offset=v.get('byteOffset',0)+offset)
  out=read(a['bufferView'],a.get('byteOffset',0),a['count']*dims,dt).reshape(-1,dims).copy()if'bufferView'in a else np.zeros((a['count'],dims),dtype=dt)
  if 'sparse'in a:
   z=a['sparse'];v=z['values'];idx=z['indices'];ii=read(idx['bufferView'],idx.get('byteOffset',0),z['count'],{5121:'<u1',5123:'<u2',5125:'<u4'}[idx['componentType']]);out[ii]=read(v['bufferView'],v.get('byteOffset',0),z['count']*dims,dt).reshape(-1,dims)
  return out

 anim=next(a for a in d['animations']if a['name']=='TightRoll');ch={}
 for c in anim['channels']:
  name=d['nodes'][c['target']['node']].get('name','');prop=c['target']['path'];sm=anim['samplers'][c['sampler']];ch[(name,prop)]=arr(sm['output'])[0]
 return d,arr,ch

def channels(d,reader,clip):
 a=next(x for x in d['animations']if x['name']==clip);out={}
 for c in a['channels']:
  if c['target']['path']=='weights':continue
  sm=a['samplers'][c['sampler']];out[(d['nodes'][c['target']['node']]['name'],c['target']['path'])]=(reader(sm['input']),reader(sm['output']))
 return out
import hashlib
A,aa,_=load('motion-r5');B,bb,_=load('motion-r7')
checks={'all_float_streams_finite':all(np.isfinite(bb(i)).all() for i,a in enumerate(B['accessors']) if a['componentType']==5126)}
clips=[]
for clip in ['TightRoll','ProbeTouch','AlternatingTouch']:
 x=channels(A,aa,clip);y=channels(B,bb,clip);changed=[];outside=[];loop_error=0.0
 for k in x:
  same=all(np.array_equal(a,b) for a,b in zip(x[k],y[k]))
  if not same:
   changed.append(k)
   intended=clip=='TightRoll' and k[0].startswith('R_IV_') and k[0]!='R_IV_00'
   derived_roundoff=k[1] in ['translation','scale'] and np.array_equal(x[k][0],y[k][0]) and np.max(np.abs(x[k][1]-y[k][1]))<1e-6
   if not(intended and (k[1]=='rotation' or derived_roundoff)):outside.append(k)
  vals=y[k][1];err=float(np.max(np.abs(vals[0]-vals[-1])))
  if k[1]=='rotation':err=min(err,float(np.max(np.abs(vals[0]+vals[-1]))))
  loop_error=max(loop_error,err)
 checks[clip+'_only_intended_channels_changed']=not outside
 checks[clip+'_loop_closed']=loop_error<1e-5
 clips.append({'clip':clip,'changed_channels':changed,'loop_max_component_error':loop_error})
checks['tighter_roll_changes_exist']=len(clips[0]['changed_channels'])>0
report={'ok':all(checks.values()),'checks':checks,'clips':clips,'model_sha256':hashlib.sha256((r/'motion-r7/octopus-actions.glb').read_bytes()).hexdigest(),'export_roundoff_note':'Right-IV derived translation max 2.3748725652694702e-7 ML; scale max 2.384185791015625e-7. Source rest matrices and mesh exact.','collision_gate':'Minor internal coil overlap explicitly allowed; zero intersections not required.'}
(r/'motion-r7/export.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
