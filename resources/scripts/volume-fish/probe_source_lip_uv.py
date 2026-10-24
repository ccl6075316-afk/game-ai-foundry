"""Blender: inspect actual body-source UV under each frozen lip cross-row."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads((root/'trial.plan.json').read_text())
body=json.loads(Path(plan['body_mesh']).read_text());lip=json.loads(Path(plan['lip_mesh']).read_text())
vertices=[];uv=[];refs=[];tri=[];offset=0
for p in body['parts']:
 if p['source_surface']!=0:continue # Oral tunnel UV is not an exterior skin donor.
 v=np.array(p['vertices']);vertices.append(v);uv.append(np.array(p['uv']));refs.append(np.array(p['reference_positions']));tri.append(np.array(p['triangles']).reshape(-1,3)[:,[0,2,1]]+offset);offset+=len(v)
v=np.concatenate(vertices);uv=np.concatenate(uv);refs=np.concatenate(refs);tri=np.concatenate(tri);bvh=BVHTree.FromPolygons(v.tolist(),tri.tolist(),all_triangles=True)
repaired=[0]
def project(p):
 point,normal,face,distance=bvh.find_nearest(Vector(p));a,b,c=v[tri[face]];v0=b-a;v1=c-a;v2=np.array(point)-a
 d00=v0@v0;d01=v0@v1;d11=v1@v1;den=d00*d11-d01*d01;vv=(d11*(v2@v0)-d01*(v2@v1))/den;ww=(d00*(v2@v1)-d01*(v2@v0))/den
 weights=np.array([1-vv-ww,vv,ww]);sample=uv[tri[face]].T@weights
 if plan.get('source_uv_repair'):
  cfg=plan['source_uv_repair'];reference=refs[tri[face]].T@weights;preferred=np.array([reference[0]+.5,.5-reference[1]*cfg['source_size'][0]/cfg['source_size'][1]])
  if abs(sample[0]-preferred[0])>cfg['maximum_native_u_deviation']:
   sample=preferred;repaired[0]+=1
 return sample.tolist(),distance
out={}
for part in lip['parts']:
 result=[project(p) for p in part['vertices']];out[part['name']]={'body_uv':[r[0] for r in result],'surface_distances':[r[1] for r in result]}
out['source_coordinate_repair']={'vertices':repaired[0],'policy':plan.get('source_uv_repair'),'scope':'Explicit correction of stretched front-cap UV into original source-reference XY, only for lip/adjacent-skin continuity. Not raw-UV equivalence.'}
(root/'body-lip-correspondence.json').write_text(json.dumps(out,separators=(',',':')))
print('Actual source UV correspondence ready',flush=True)
