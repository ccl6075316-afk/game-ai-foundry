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

import hashlib
A,aa,_=load('motion-r5');B,bb,_=load('motion-r6');bad=[i for i,a in enumerate(B['accessors'])if a['componentType']==5126 and not np.isfinite(bb(i)).all()]
def channels(d,reader,clip):
 a=next(x for x in d['animations']if x['name']==clip);out={}
 for c in a['channels']:
  if c['target']['path']=='weights':continue
  sm=a['samplers'][c['sampler']];out[(d['nodes'][c['target']['node']]['name'],c['target']['path'])]=(reader(sm['input']),reader(sm['output']))
 return out
comparisons=[]
for clip in ['TightRoll','ProbeTouch','AlternatingTouch']:
 x=channels(A,aa,clip);y=channels(B,bb,clip);same=x.keys()==y.keys() and all(np.array_equal(a,b)for k in x for a,b in zip(x[k],y[k]));comparisons.append({'clip':clip,'native_bone_curves_exact':same,'weight_tracks':sum(c['target']['path']=='weights'for a in B['animations']if a['name']==clip for c in a['channels'])})
checks={'all_exported_float_accessors_finite':not bad,'native_bone_curves_exactly_preserved':all(x['native_bone_curves_exact']for x in comparisons),'two_native_morph_tracks_per_clip':all(x['weight_tracks']==2 for x in comparisons),'skin_Basis_position_stream_preserved':np.array_equal(aa(A['meshes'][4]['primitives'][0]['attributes']['POSITION']),bb(B['meshes'][4]['primitives'][0]['attributes']['POSITION']))}
report={'ok':all(checks.values()),'checks':checks,'clips':comparisons,'model_sha256':hashlib.sha256((r/'motion-r6/octopus-actions.glb').read_bytes()).hexdigest(),'nonfinite_accessors':bad}
(r/'motion-r6/export.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
