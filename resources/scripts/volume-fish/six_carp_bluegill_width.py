"""Source-owned conservative body-width proposal; preserve both extreme ends."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays
from audit_transverse_width import section
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=sys.argv[1];base=ROOT/f'projects/fishing-2d/experiments/six-fish-database-20261104/{s}';r=json.loads((base/'reference-comparison.validation.json').read_text());model=ROOT/r['installed']['path'];blend=Path(r['editable_source']['path']);d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);n=arrays(d,b,pr['attributes']['NORMAL']).astype(float);idx=arrays(d,b,pr['indices']).reshape(-1);body=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']]for p in d['extras']['geometry_parts']if p['role']in ['body_skin','mouth']]);lo,hi=v[body,0].min(),v[body,0].max();L=hi-lo;rr=r['sections']['reference'];target=PchipInterpolator([x['s']for x in rr],[x['width_over_body_axis']for x in rr]);ts=np.array([0,.005,.015,.03,.05,.08,.12,.18,.24,.3,.36,.42,.48,.55,.62,.7,.76,.82,.88,.94,.98,1]);gg=[];stations=[]
for t in ts:
 if t<.015 or t>.98:gain=1.;old=desired=None
 else:
  old=float(np.ptp(section(v,body,hi-t*L)[:,2]));desired=float(target(t)*L);w=min(1.,(t-.005)/.025)*min(1.,(.98-t)/.16);w=max(0,w);w=w*w*(3-2*w);gain=1+(desired/old-1)*w
 gg.append(gain);stations.append({'s_body':float(t),'baseline_width':old,'reference_width':desired,'gain':gain})
field=PchipInterpolator(ts,gg);t=np.clip((hi-v[:,0])/L,0,1);gain=field(t);dgdx=-field.derivative()(t)/L;new=v.copy();new[:,2]*=gain;n[:,0]-=v[:,2]*dgdx/gain*n[:,2];n[:,2]/=gain;n/=np.linalg.norm(n,axis=1)[:,None]
out=base/'width-r1';out.mkdir();inputs={'model':model,'blend':blend,'comparison':base/'reference-comparison.validation.json','reference':ROOT/r['reference']['path']};plan={'kind':'single_fish_transverse_width_trial','stage':'database-width-r1','species':s,'inputs':{k:{'path':str(p),'sha256':sha(p)}for k,p in inputs.items()},'scope':'Body-nose/peduncle normalized local named game-art reference. Original XY, complete mouth extreme front, terminal peduncle, exact topology/UV/material/skin/rig/clips preserved. All affected gates invalidate.','normalization':r['reference']['normalization'],'reference_stations':stations,'gain_stations':np.c_[ts,gg].tolist(),'gain_range':[float(gain.min()),float(gain.max())],'old_positions_gltf':v.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':n.astype('float32').tolist(),'formal_acceptance':False};(out/'deformation.plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'output':str(out),'gains':plan['gain_range']}))
