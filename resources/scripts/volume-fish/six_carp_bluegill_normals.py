"""Repair coarse finite-body normal hemisphere after nonlinear width deformation."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
base=ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104/carp';old=base/'width-r3';out=base/'width-r4';out.mkdir();d,b=read_glb(old/'fish.glb');p=d['meshes'][0]['primitives'][0];v=arrays(d,b,p['attributes']['POSITION']);n=arrays(d,b,p['attributes']['NORMAL']).astype(float);idx=arrays(d,b,p['indices']).reshape(-1);tris=np.concatenate([idx[q['index_start']:q['index_start']+q['index_count']]for q in d['extras']['geometry_parts']if q['role']in ['body_skin','mouth']]).reshape(-1,3);fn=np.cross(v[tris[:,1]]-v[tris[:,0]],v[tris[:,2]]-v[tris[:,0]]);fn/=np.maximum(np.linalg.norm(fn,axis=1)[:,None],1e-30);before=int(((fn*n[tris].mean(1)).sum(1)<=0).sum())
for step in range(500):
 dots=(fn*n[tris].mean(1)).sum(1);bad=np.flatnonzero(dots<.002)
 if not len(bad):break
 for i in bad:
  ids=tris[i];n[ids]+=max(0,.0021-float(n[ids].mean(0)@fn[i]))*fn[i];n[ids]/=np.linalg.norm(n[ids],axis=1)[:,None]
assert np.all((fn*n[tris].mean(1)).sum(1)>0);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();plan={'kind':'single_fish_transverse_width_trial','stage':'finite_body_normal_hemisphere_r4','species':'carp','inputs':{k:{'path':str(p),'sha256':sha(p)}for k,p in [('model',old/'fish.glb'),('blend',old/'fish.blend')]},'scope':'Only coarse-body normal hemisphere correction; positions/XY/UV/material/topology/skin/rig/clips unchanged from r3. No appearance acceptance.','normal_repair':{'wrong_hemisphere_before':before,'wrong_hemisphere_after':0,'iterations':step,'minimum_mean_vertex_normal_dot_finite_face':float((fn*n[tris].mean(1)).sum(1).min())},'old_positions_gltf':v.tolist(),'new_positions_gltf':v.tolist(),'new_normals_gltf':n.astype('float32').tolist(),'formal_acceptance':False};(out/'deformation.plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8');print(plan['normal_repair'])
