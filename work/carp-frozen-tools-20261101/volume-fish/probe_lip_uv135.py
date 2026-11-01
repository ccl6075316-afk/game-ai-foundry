"""Blender: inspect actual body-source UV under each frozen lip cross-row."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root=Path(sys.argv[sys.argv.index('--')+1]);plan=json.loads((root/'trial.plan.json').read_text())
body=json.loads(Path(plan['body_mesh']).read_text());lip=json.loads(Path(plan['lip_mesh']).read_text())
vertices=[];uv=[];tri=[];offset=0
for p in body['parts']:
 v=np.array(p['vertices']);vertices.append(v);uv.append(np.array(p['uv']));tri.append(np.array(p['triangles']).reshape(-1,3)[:,[0,2,1]]+offset);offset+=len(v)
v=np.concatenate(vertices);uv=np.concatenate(uv);tri=np.concatenate(tri);bvh=BVHTree.FromPolygons(v.tolist(),tri.tolist(),all_triangles=True)
def project(p):
 point,normal,face,distance=bvh.find_nearest(Vector(p));a,b,c=v[tri[face]];v0=b-a;v1=c-a;v2=np.array(point)-a
 d00=v0@v0;d01=v0@v1;d11=v1@v1;den=d00*d11-d01*d01;vv=(d11*(v2@v0)-d01*(v2@v1))/den;ww=(d00*(v2@v1)-d01*(v2@v0))/den
 return (uv[tri[face]].T@np.array([1-vv-ww,vv,ww])).tolist(),distance
out={}
for part in lip['parts']:
 result=[project(p) for p in part['vertices']];out[part['name']]={'body_uv':[r[0] for r in result],'surface_distances':[r[1] for r in result]}
(root/'body-lip-correspondence.json').write_text(json.dumps(out,separators=(',',':')))
print('Actual source UV correspondence ready',flush=True)
