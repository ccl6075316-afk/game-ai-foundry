"""Blender closed-body sign index at the077 declared1e-7 identity precision.

Distance queries must continue using the unmodified actual triangles. Only
sign classification canonicalizes coincident seam positions and face winding.
"""
from collections import defaultdict,deque
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
def build(vertices,triangles):
 v,inv=np.unique(np.round(vertices,7),axis=0,return_inverse=True);t=inv[np.asarray(triangles,int)];owners=defaultdict(list)
 for i,face in enumerate(t):
  for a,b in zip(face,np.roll(face,-1)):owners[tuple(sorted((int(a),int(b))))].append((i,bool(a<b)))
 assert owners and all(len(q)==2 for q in owners.values()),'Sign index requires the same077 closed topology'
 adjacent=defaultdict(list)
 for edges in owners.values():
  (a,da),(b,db)=edges;adjacent[a].append((b,da==db));adjacent[b].append((a,da==db))
 flip=np.full(len(t),-1,int);components=[]
 for start in range(len(t)):
  if flip[start]>=0:continue
  flip[start]=0;queue=deque([start]);component=[]
  while queue:
   a=queue.popleft();component.append(a)
   for b,same in adjacent[a]:
    expected=flip[a]^int(same)
    if flip[b]<0:flip[b]=expected;queue.append(b)
    else:assert flip[b]==expected,'Non-orientable sign index'
  components.append(component)
 t[flip==1]=t[flip==1][:,[0,2,1]]
 for ids in components:
  q=t[ids];volume=np.einsum('ij,ij->i',v[q[:,0]],np.cross(v[q[:,1]],v[q[:,2]])).sum()/6
  if volume<0:t[ids]=t[ids][:,[0,2,1]]
 tree=BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True);ray=Vector((.231,.371,.899)).normalized()
 def inside(point):
  hit,normal,_,_=tree.ray_cast(Vector(point),ray)
  return hit is not None and normal.dot(ray)>0
 return inside
