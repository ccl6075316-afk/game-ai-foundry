"""Insert noncrossing finite anatomical edges into a planar triangulation.

Remove only the strip of triangles actually crossed by each segment, then ear
clip the two boundary chains. Existing vertices and earlier constraints remain.
Coordinates are float64 barycentric coordinates of an original finite face.
"""
from collections import Counter,defaultdict
import numpy as np
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def bary(p,face,xy):
 a,b,c=[xy[i]for i in face];v,w=np.linalg.solve(np.column_stack((b-a,c-a)),p-a);return np.array([1-v-w,v,w])
def earclip(poly,xy):
 poly=list(poly);out=[]
 area=sum(cross(xy[a],xy[b])for a,b in zip(poly,poly[1:]+poly[:1]))
 if area<0:poly.reverse()
 while len(poly)>3:
  for k in range(len(poly)):
   a,b,c=poly[k-1],poly[k],poly[(k+1)%len(poly)]
   if cross(xy[b]-xy[a],xy[c]-xy[b])<1e-13:continue
   if any(bary(xy[i],(a,b,c),xy).min()>=-1e-10 for i in poly if i not in [a,b,c]):continue
   out.append((a,b,c));poly.pop(k);break
  else:raise ValueError('Non-simple finite constraint cavity')
 if abs(cross(xy[poly[1]]-xy[poly[0]],xy[poly[2]]-xy[poly[0]]))>1e-13:out.append(tuple(poly))
 else:raise ValueError('Degenerate finite constraint cavity')
 return out
def insert_segment(tris,A,B,xy):
 if any(A in f and B in f for f in tris):return tris
 removed=[]
 for k,f in enumerate(tris):
  a=bary(xy[A],f,xy);b=bary(xy[B],f,xy);d=b-a;lo,hi=0.,1.
  for v,g in zip(a,d):
   if abs(g)<1e-14:
    if v<-1e-10:lo,hi=1.,0.;break
   elif g>0:lo=max(lo,-v/g)
   else:hi=min(hi,-v/g)
  if hi-lo>1e-9 and (a+(lo+hi)/2*d).min()>1e-10:removed.append(k)
 assert removed,('Constraint traverses no finite faces',A,B)
 edges=Counter(tuple(sorted((a,b)))for k in removed for f in [tris[k]]for a,b in zip(f,(*f[1:],f[0])))
 adj=defaultdict(list)
 for (a,b),n in edges.items():
  if n==1:adj[a].append(b);adj[b].append(a)
 assert A in adj and B in adj and all(len(v)==2 for v in adj.values()),('Non-simple constraint corridor',A,B)
 paths=[]
 for first in adj[A]:
  path=[A,first]
  while path[-1]!=B:
   nxt=next(i for i in adj[path[-1]]if i!=path[-2]);assert nxt not in path;path.append(nxt)
  paths.append(path)
 replacement=[]
 for path in paths:
  if len(path)>2:replacement.extend(earclip(path,xy))
 return [f for k,f in enumerate(tris)if k not in removed]+replacement
def constrain(tris,segments,xy):
 xy=np.array(xy,dtype=float);frozen=[]
 for a,b in segments:
  d=xy[b]-xy[a];norm=np.dot(d,d);assert norm>1e-20
  chain=[]
  for i,p in enumerate(xy):
   t=np.dot(p-xy[a],d)/norm
   if -1e-9<=t<=1+1e-9 and abs(cross(p-xy[a],d))<1e-10:chain.append((t,i))
  chain.sort();assert chain[0][1]==a and chain[-1][1]==b
  for (_,A),(_,B)in zip(chain,chain[1:]):
   tris=insert_segment(tris,A,B,xy);frozen.append((A,B))
   assert all(any(u in f and v in f for f in tris)for u,v in frozen),'Earlier finite constraint lost'
 return tris
