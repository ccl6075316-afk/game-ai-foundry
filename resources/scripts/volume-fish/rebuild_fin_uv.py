"""REJECTED TECHNICAL PROBE: constrained retriangulation is not the selected B image-outline method. See Nile handoff; retained for failure reproduction only."""
"""New finite UV-domain fin mesh, bounded source silhouette simplification."""
import math
from collections import Counter,defaultdict
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

def generate(uvs,triangles,image_size=(1961,972),target_vertices=150,
             boundary_tolerance_pixels=.5,max_boundary_edge_pixels=16.):
 points=[Vector((u*image_size[0],v*image_size[1])) for u,v in uvs]
 edge_counts=Counter(tuple(sorted((t[i],t[(i+1)%3]))) for t in triangles for i in range(3))
 adjacency=defaultdict(list)
 for (a,b),count in edge_counts.items():
  assert count in [1,2]
  if count==1:adjacency[a].append(b);adjacency[b].append(a)
 assert adjacency and all(len(v)==2 for v in adjacency.values())
 start=min(adjacency,key=lambda i:tuple(points[i]));loop=[start];previous=-1;current=start
 while True:
  nxt=next(i for i in adjacency[current] if i!=previous)
  if nxt==start:break
  assert nxt not in loop,'Multiple/inconsistent boundary loops'
  loop.append(nxt);previous,current=current,nxt
 assert len(loop)==len(adjacency),'Holes require a different constrained domain'
 boundary=[points[i] for i in loop]
 def point_segment(p,a,b):
  ab=b-a;t=max(0.,min(1.,(p-a).dot(ab)/max(ab.length_squared,1e-20)))
  return (p-a-ab*t).length
 clearance=.02
 def rdp(seq):
  if len(seq)<=2:return seq
  distances=[point_segment(p,seq[0],seq[-1]) for p in seq[1:-1]];distance=max(distances,default=0)
  if distance<=boundary_tolerance_pixels-clearance*2:return [seq[0],seq[-1]]
  at=1+distances.index(distance);return rdp(seq[:at+1])[:-1]+rdp(seq[at:])
 opposite=max(range(1,len(boundary)),key=lambda i:(boundary[i]-boundary[0]).length_squared)
 simplified=rdp(boundary[:opposite+1])[:-1]+rdp(boundary[opposite:]+[boundary[0]])[:-1]
 # A pixel-corner contact must become a finite neck before shelling. A tiny
 # outward clearance stays inside the frozen total contour-error budget.
 area_sign=1 if sum(p.x*simplified[(i+1)%len(simplified)].y-p.y*simplified[(i+1)%len(simplified)].x for i,p in enumerate(simplified))>0 else -1
 expanded=[]
 for i,p in enumerate(simplified):
  prev=simplified[i-1];nxt=simplified[(i+1)%len(simplified)]
  incoming=(p-prev).normalized();outgoing=(nxt-p).normalized()
  normal=Vector((incoming.y+outgoing.y,-incoming.x-outgoing.x))*area_sign
  expanded.append(p+normal.normalized()*clearance if normal.length>1e-12 else p)
 simplified=expanded
 dense=[]
 for i,a in enumerate(simplified):
  b=simplified[(i+1)%len(simplified)];steps=max(1,math.ceil((b-a).length/max_boundary_edge_pixels))
  dense.extend(a.lerp(b,k/steps) for k in range(steps))
 required=len(dense)
 if required>target_vertices:raise ValueError(f'Frozen silhouette/edge limit needs {required} boundary vertices; budget allows {target_vertices}')
 def inside(p):
  odd=False
  for i,a in enumerate(dense):
   b=dense[(i+1)%len(dense)]
   if (a.y>p.y)!=(b.y>p.y) and p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x:odd=not odd
  return odd
 xmin,xmax=min(p.x for p in dense),max(p.x for p in dense);ymin,ymax=min(p.y for p in dense),max(p.y for p in dense)
 remaining=target_vertices-required;interior=[]
 if remaining:
  area=abs(sum(p.x*dense[(i+1)%required].y-p.y*dense[(i+1)%required].x for i,p in enumerate(dense)))/2
  step=math.sqrt(area/max(remaining,1))*.65
  candidates=[];row=0;y=ymin+step*.5
  while y<ymax:
   x=xmin+step*(.5+.5*(row%2))
   while x<xmax:
    p=Vector((x,y))
    if inside(p) and min(point_segment(p,dense[i],dense[(i+1)%required]) for i in range(required))>step*.15:candidates.append(p)
    x+=step
   y+=step;row+=1
  # Stable spread through the entire domain rather than keeping one corner.
  if len(candidates)>remaining:interior=[candidates[min(len(candidates)-1,int((i+.5)*len(candidates)/remaining))] for i in range(remaining)]
  else:interior=candidates
 vertices=dense+interior;edges=[(i,(i+1)%required) for i in range(required)]
 out_v,out_e,out_f,_,_,_=delaunay_2d_cdt(vertices,edges,[list(range(required))],1,1e-6,True)
 assert out_f and all(len(t)==3 and len(set(t))==3 for t in out_f)
 for a,b,c in out_f:
  assert abs((out_v[b]-out_v[a]).cross(out_v[c]-out_v[a]))>1e-10
  assert inside((out_v[a]+out_v[b]+out_v[c])/3),'Exterior output triangle'
 output_counts=Counter(tuple(sorted((t[i],t[(i+1)%3]))) for t in out_f for i in range(3))
 assert all(v in [1,2] for v in output_counts.values())
 assert len(out_v)-len(output_counts)+len(out_f)==1,'Output is not a topological disk'
 error=max(min(point_segment(p,dense[i],dense[(i+1)%required]) for i in range(required)) for p in boundary)
 assert error<=boundary_tolerance_pixels+1e-5
 return [(p.x/image_size[0],p.y/image_size[1]) for p in out_v],[tuple(t) for t in out_f],{
  'source_boundary_vertices':len(boundary),'simplified_boundary_vertices':required,'new_mid_vertices':len(out_v),
  'new_mid_triangles':len(out_f),'source_boundary_error_max_pixels':error,'requested_mid_vertices':target_vertices}
