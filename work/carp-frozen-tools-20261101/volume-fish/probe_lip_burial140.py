import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
r=Path(sys.argv[sys.argv.index('--')+1]);s='grass_carp';d=json.loads((r/s/'geometry/body.bound.json').read_text());vs=[];ts=[];at=0
for p in d['parts']:vs.extend(p['vertices']);ts.extend((np.array(p['triangles']).reshape(-1,3)+at).tolist());at+=len(p['vertices'])
v=np.array(vs);t=np.array(ts);volume=np.einsum('ij,ij->i',v[t[:,0]],np.cross(v[t[:,1]],v[t[:,2]])).sum()/6
if volume<0:t=t[:,[0,2,1]]
tree=BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True);ray=Vector((.231,.371,.899)).normalized();p=json.loads((r/s/'lips/aligned-lips.mesh.json').read_text())['parts'][1];points=np.array(p['vertices']);faces=np.array(p['triangles']).reshape(-1,3);bad=[]
for face in faces:
 for bary in [[1/3]*3,[.5,.5,0],[0,.5,.5],[.5,0,.5]]:
  point=points[face].T@bary;hit,normal,_,dist=tree.find_nearest(Vector(point));rh,rn,_,_=tree.ray_cast(Vector(point),ray)
  if rh is not None and rn.dot(ray)>0 and dist>.00003:bad.append((dist,point,face,bary))
for dist,point,face,bary in sorted(bad,key=lambda q:-q[0])[:8]:
 count=0;pos=Vector(point)+ray*1e-7
 for _ in range(50):
  hit,_,_,dd=tree.ray_cast(pos,ray)
  if hit is None:break
  count+=1;pos=hit+ray*1e-7
 print('BAD',dist,'point',point.tolist(),'indices',face.tolist(),'row/cross',[(int((i-1)//17),int((i-1)%17)) for i in face],'bary',bary,'parity',count,'volume',volume)
print('badcount',len(bad),flush=True)
