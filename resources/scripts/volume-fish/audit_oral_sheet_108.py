#!/usr/bin/env python3
"""Read-only108 active oral XZ patch audit. Does not invoke CDT or write mesh assets."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from scipy.spatial import cKDTree
from probe_mouth_slit_stage1_108 import field,canvas

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def components(adj):
 todo=set(adj);groups=[]
 while todo:
  queue=[todo.pop()];group=set(queue)
  while queue:
   for j in adj[queue.pop()]:
    if j not in group:group.add(j);todo.discard(j);queue.append(j)
  groups.append(group)
 return groups

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args();data=json.loads(args.input.read_text());v=np.array(data['rest_xyz']);f=np.array(data['indices']).reshape(-1,3);q=canvas(v);V=q[:,1]-(452.62-1.02*742/2024*(q[:,0]-1894.464));newq,_=field(q);new=v.copy();active=q[:,0]>1988;new[active,0]=newq[active,0]/2024-.5;new[active,1]=(371-newq[active,1])/2024
 # Exact geometric welding only: no tolerance-driven coordinate move/merge.
 points={};canonical=[];mapping=[]
 for i,p in enumerate(v):
  key=tuple(p)
  if key not in points:points[key]=len(canonical);canonical.append(i)
  mapping.append(points[key])
 mapping=np.array(mapping);canonical=np.array(canonical);wf=mapping[f];counts=Counter(tuple(sorted(e)) for face in wf for e in zip(face,np.roll(face,-1)));full_boundary={e for e,n in counts.items() if n==1};results=[]
 for label,side in [('upper',V[f].max(1)<0),('lower',V[f].min(1)>0)]:
  selected=side&(q[f,0].max(1)>1988);faceids=np.flatnonzero(selected);faces=wf[selected];used=np.unique(faces);ct=Counter(tuple(sorted(e)) for face in faces for e in zip(face,np.roll(face,-1)));boundary=[e for e,n in ct.items() if n==1];adj=defaultdict(set)
  for i,j in boundary:adj[i].add(j);adj[j].add(i)
  groups=components(adj);result={'sheet':label,'selected_triangle_ids':faceids.tolist(),'selected_triangles':len(faceids),'unique_exact_welded_vertices':len(used),'boundary_edges':len(boundary),'original_body_interface_edges':sum(e in full_boundary for e in boundary),'new_patch_to_kept_edges':sum(e not in full_boundary for e in boundary),'boundary_components':len(groups),'boundary_component_sizes':[len(g) for g in groups],'boundary_vertex_degree_histogram':dict(Counter(len(adj[i]) for i in adj)),'nonmanifold_edges':sum(n>2 for n in ct.values()),'boundary_edge_vertex_ids':[[int(canonical[i]),int(canonical[j])] for i,j in boundary],'patch_interface_canvas_max_x':max(q[canonical[list(e)],0].max() for e in boundary if e not in full_boundary),'geometries':[]}
  for name,coords in [('original',v),('stage1',new)]:
   cv=coords[canonical];p=cv[used][:,[0,2]];xzgroups=defaultdict(list)
   for i in used:xzgroups[tuple(cv[i,[0,2]])].append(i)
   multival=[{'welded_vertex_ids':g,'y_spread':float(np.ptp(cv[g,1]))} for g in xzgroups.values() if np.ptp(cv[g,1])>0]
   segments=cv[np.array(boundary)][:,:,[0,2]];proper=[];collinear=[]
   for i,(a,b) in enumerate(segments):
    D=b-a
    for j in range(i+1,len(segments)):
     if set(boundary[i])&set(boundary[j]):continue
     c,e=segments[j];E=e-c;den=cross(D,E)
     if abs(den)<=1e-18:
      if abs(cross(c-a,D))<=1e-18:
       ax=int(np.argmax(abs(D)));overlap=min(max(a[ax],b[ax]),max(c[ax],e[ax]))-max(min(a[ax],b[ax]),min(c[ax],e[ax]));
       if overlap>1e-12:collinear.append([i,j])
      continue
     t=cross(c-a,E)/den;u=cross(c-a,D)/den
     if 1e-8<t<1-1e-8 and 1e-8<u<1-1e-8:proper.append([i,j])
   # Simple loop for point inclusion; diagnostic only, no coordinate snapping.
   loop=[next(iter(adj))];previous=None
   while True:
    nxt=next(j for j in adj[loop[-1]] if j!=previous);previous=loop[-1]
    if nxt==loop[0]:break
    loop.append(nxt)
    if len(loop)>len(adj):raise ValueError('boundary failed simple loop traversal')
   poly=cv[loop][:,[0,2]];boundary_set=set(adj);outside=[];interior_on_boundary=[]
   for pointid in used:
    if pointid in boundary_set:continue
    point=cv[pointid,[0,2]];inside=False;on=False
    for aa,bb in zip(poly,np.roll(poly,-1,axis=0)):
     direction=bb-aa;t=float(np.dot(point-aa,direction)/np.dot(direction,direction));distance=abs(cross(direction,point-aa))
     if 0<t<1 and distance<=1e-18:on=True
     if (aa[1]>point[1])!=(bb[1]>point[1]) and point[0]<(bb[0]-aa[0])*(point[1]-aa[1])/(bb[1]-aa[1])+aa[0]:inside=not inside
    if on:interior_on_boundary.append(int(canonical[pointid]))
    elif not inside:outside.append(int(canonical[pointid]))
   lengths=np.linalg.norm(segments[:,1]-segments[:,0],axis=1);tree=cKDTree(p);nearest=tree.query(p,k=2)[0][:,1];result['geometries'].append({'interior_points_outside_boundary':len(outside),'outside_original_vertex_ids':outside,'interior_points_on_constraint_edge':len(interior_on_boundary),'on_edge_original_vertex_ids':interior_on_boundary,'geometry':name,'exact_xz_samepoint_multiple_y_count':len(multival),'same_xz_multiple_y_examples':multival[:8],'minimum_distinct_xz_vertex_distance':float(nearest.min()),'zero_length_boundary_edges':int((lengths==0).sum()),'minimum_boundary_xz_edge_length':float(lengths.min()),'boundary_proper_crossings':len(proper),'boundary_crossing_edge_ids':proper[:12],'boundary_collinear_overlap_pairs':len(collinear),'boundary_collinear_examples':collinear[:12]})
  results.append(result)
 # Cross-V bridge and all inactive faces remain part of kept mesh, never part of CDT input.
 bridge=(V[f].min(1)<=0)&(V[f].max(1)>=0);out={'status':'read_only_active_oral_sheet_proposal','accepted':False,'input':str(args.input),'input_sha256':sha(args.input),'audit_sha256':sha(Path(__file__)),'stage1_probe_sha256':sha(Path(__file__).with_name('probe_mouth_slit_stage1_108.py')),'selection':'one patch perV sign, tri iff any original vertexX>1988; exact original geometric weld only','cdt_invoked':False,'model_uv_runtime_written':False,'bridge_triangles':int(bridge.sum()),'bridge_max_canvas_x':float(q[f[bridge],0].max()),'active_bridge_triangles':int((bridge&(q[f,0].max(1)>1988)).sum()),'entire_oral_skin_interface_edges':len(full_boundary),'patches':results,'limits':['Finite overlap of old internal triangles is known failed connectivity to replace, not a prerequisite for CDT.','No CDT/new indices generated; newvertex requirement not measured against Blender output yet.','Projected pointcloud has no exact multi-Y keys; this does not prove a continuous targetY rule or skin weights at new points.','Existing build_fish CDT epsilon1e-7 must not be copied when distinct constrained input vertices are closer. Boundary coordinate and edge-origin checks must reject any merge or insertion onprotected interface.']};args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'patch_counts':[(x['sheet'],x['selected_triangles'],x['boundary_edges']) for x in results],'cdt_invoked':False},indent=2))
if __name__=='__main__':main()
