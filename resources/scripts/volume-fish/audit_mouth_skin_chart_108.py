#!/usr/bin/env python3
"""108 read-only mapped outer-skin XY chart feasibility. No CDT/refinement/asset writes."""
import argparse,json,hashlib,struct
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from scipy.spatial import cKDTree
from audit_mouth_refinement_108 import load_frozen_field

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cross(a,b):return float(a[0]*b[1]-a[1]*b[0])
def intersect(a,b,c,d):
 ab=b-a;cd=d-c;det=cross(ab,cd)
 if det==0:return False
 t=cross(c-a,cd)/det;u=cross(c-a,ab)/det
 return 0<t<1 and 0<u<1

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parent;script=Path(__file__).with_name('probe_mouth_monotone_108.py');frozen=json.loads((b/'cpu-y-uv-monotone/monotone-frozen.validation.json').read_text());assert sha(script)==next(v for k,v in frozen['dependencies_sha256'].items() if k.endswith('/probe_mouth_monotone_108.py'));ns=load_frozen_field(script,b/'source-mouth-alignment.validation.json');v=ns['st'][0];f=np.array(ns['data'][0]['indices']).reshape(-1,3);q=ns['canvas'](v);mapped,_,_=ns['evaluate'](q);dest=v.copy();on=mapped[:,1]!=q[:,1];dest[on,1]=(371-mapped[on,1])/2024;V=q[:,1]-(452.62-1.02*742/2024*(q[:,0]-1894.464));active=q[f,0].max(1)>=1988;cap=np.ptp(q[f,0],axis=1)==0;up=V[f].max(1)<0;low=V[f].min(1)>0;left=(v[f,2].min(1)>=0)&(v[f,2].max(1)>0);right=(v[f,2].max(1)<=0)&(v[f,2].min(1)<0);geokeys=sorted(set(tuple(p) for p in v));lookup={p:i for i,p in enumerate(geokeys)};g=np.array([lookup[tuple(p)] for p in v]);gv=np.array(geokeys);gq=ns['canvas'](gv);gm=ns['evaluate'](gq)[0];gd=gv.copy();gg=gm[:,1]!=gq[:,1];gd[gg,1]=(371-gm[gg,1])/2024;xy=gm;allct=Counter(tuple(sorted((int(x),int(y)))) for tri in g[f] for x,y in zip(tri,np.roll(tri,-1)));skinoral={e for e,c in allct.items() if c==1};res=[]
 for label,branch,side in [('left-upper',up,left),('right-upper',up,right),('left-lower',low,left),('right-lower',low,right)]:
  ids=np.flatnonzero(active&~cap&branch&side);tri=g[f[ids]];points=np.unique(tri);ct=Counter(tuple(sorted((int(x),int(y)))) for t in tri for x,y in zip(t,np.roll(t,-1)));edges={e for e,c in ct.items() if c==1};adj=defaultdict(set)
  for x,y in edges:adj[x].add(y);adj[y].add(x)
  invalid={int(k):len(nei) for k,nei in adj.items() if len(nei)!=2};loops=[];seen=set()
  if not invalid:
   for start in sorted(adj):
    if start in seen:continue
    loop=[start];prev=None;current=start
    while True:
     choices=sorted(adj[current]-({prev} if prev is not None else set()));nxt=choices[0]
     if nxt==start:break
     if nxt in loop:invalid[current]=-1;break
     prev,current=current,nxt;loop.append(current)
    loops.append(loop);seen.update(loop)
  groups=defaultdict(list)
  for k in points:groups[tuple(xy[k])].append(int(k))
  conflicts=[{'XY':list(key),'geometric_ids':val,'Z':gd[val,2].tolist()} for key,val in groups.items() if len(set(gd[val,2]))>1];tree=cKDTree(xy[points]);near=[]
  for aa,bb in tree.query_pairs(1e-7):
   x,y=int(points[aa]),int(points[bb])
   if gd[x,2]!=gd[y,2]:near.append({'ids':[x,y],'XY_distance_pixels':float(np.linalg.norm(xy[x]-xy[y])),'Z_difference_rest':float(abs(gd[x,2]-gd[y,2]))})
  crossings=[];boundary=sorted(edges)
  for i,(x,y) in enumerate(boundary):
   for u,z in boundary[i+1:]:
    if len({x,y,u,z})<4:continue
    if intersect(xy[x],xy[y],xy[u],xy[z]):crossings.append([[x,y],[u,z]])
  # Edge-through-point diagnostic does not merge or move coordinates.
  edgepoints=[]
  for x,y in boundary:
   aa=xy[x];dd=xy[y]-aa;len2=float(dd@dd)
   if len2==0:edgepoints.append({'edge':[x,y],'kind':'zero_XY_length'});continue
   for z in points:
    if z==x or z==y:continue
    t=float((xy[z]-aa)@dd/len2)
    if 0<t<1 and abs(cross(dd,xy[z]-aa))/np.sqrt(len2)<1e-9:edgepoints.append({'edge':[x,y],'point':int(z),'t':t})
  def inside(p,loop):
   poly=xy[loop];hit=False
   for aa,bb in zip(poly,np.roll(poly,-1,axis=0)):
    if (aa[1]>p[1])!=(bb[1]>p[1]) and p[0]<(bb[0]-aa[0])*(p[1]-aa[1])/(bb[1]-aa[1])+aa[0]:hit=not hit
   return hit
  outer=[]
  for loop in loops:outer.append((abs(sum(cross(xy[x],xy[y]) for x,y in zip(loop,loop[1:]+loop[:1]))/2),loop))
  largest=max(outer,default=(0,[]))[1];boundarypoints=set(adj);outside=[int(k) for k in points if k not in boundarypoints and not inside(xy[k],largest)] if largest else [];areas=np.array([cross(xy[t[1]]-xy[t[0]],xy[t[2]]-xy[t[0]]) for t in tri]);components=len(loops);simple=len(loops)==1 and not invalid and not crossings and not edgepoints and not conflicts and not outside
  res.append({'sheet':label,'triangles':len(ids),'vertices':len(points),'edges':len(ct),'boundary_edges':len(edges),'boundary_degrees_invalid':invalid,'loops':[{'vertices':len(loop),'ids':list(map(int,loop))} for loop in loops],'boundary_strict_crossings':crossings,'constraint_through_points':edgepoints,'same_XY_different_Z_conflicts':conflicts,'near_XY_different_Z_diagnostic_not_merged':{'count':len(near),'examples':near[:16]},'interior_points_outside_largest_boundary':outside,'Euler_V_E_F':len(points)-len(ct)+len(tri),'expected_faces_single_simple_domain':2*len(points)-len(edges)-2,'current_negative_XY_areas':int((areas<0).sum()),'current_positive_XY_areas':int((areas>0).sum()),'current_zero_XY_areas':int((areas==0).sum()),'skin_oral_parent_boundary_count':len(edges&skinoral),'kept_patch_interface_boundary_count':len(edges-skinoral),'simple_single_value_chart_not_yet_CDT':simple,'stage1_X_range':[float(gq[points,0].min()),float(gq[points,0].max())],'triangle_ids':ids.tolist()})
 # Exact source attribute provenance: normal differences are not silently welded.
 glb=Path(json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text())['raw_glb']);raw=glb.read_bytes();ln=struct.unpack_from('<I',raw,12)[0];gl=json.loads(raw[20:20+ln]);binary=raw[28+ln:];types={5126:'<f4',5123:'<u2',5121:'u1'};nums={'VEC2':2,'VEC3':3,'VEC4':4}
 def acc(ix):
  ac=gl['accessors'][ix];bv=gl['bufferViews'][ac['bufferView']];dt=np.dtype(types[ac['componentType']]);co=nums[ac['type']];return np.ndarray((ac['count'],co),dt,buffer=binary,offset=bv.get('byteOffset',0)+ac.get('byteOffset',0),strides=(bv.get('byteStride',co*dt.itemsize),dt.itemsize)).copy()
 attrs={k:acc(ix) for k,ix in next(m for m in gl['meshes'] if m.get('name')=='Closed_body')['primitives'][0]['attributes'].items()};rawgroups=defaultdict(list)
 for i,p0 in enumerate(attrs['POSITION']):rawgroups[tuple(p0.astype(float))].append(i)
 for sheet in res:
  points=np.unique(f[sheet['triangle_ids']]);conflicts=Counter();normalgroups=0;maxgroups=0
  for i in points:
   rid=rawgroups[tuple(ns['old'][0][i].astype(np.float32).astype(float))];maxgroups=max(maxgroups,len(rid))
   for att in ['JOINTS_0','WEIGHTS_0','TEXCOORD_0']:
    conflicts[att]+=any(not np.array_equal(attrs[att][rid[0]],attrs[att][j]) for j in rid[1:])
   normalgroups+=any(not np.array_equal(attrs['NORMAL'][rid[0]],attrs['NORMAL'][j]) for j in rid[1:])
  uvused=defaultdict(set)
  for actual in points:uvused[int(g[actual])].add(tuple(ns['data'][0]['source_uv'][actual]))
  chartuvconflicts=[{'geometric_id':k,'original_XYZ':gv[k].tolist(),'used_chart_UVs':sorted(vals)} for k,vals in uvused.items() if len(vals)>1]
  rawuvseams=[]
  for k in sorted(set(map(int,g[points]))):
   actual=next(int(i) for i in points if int(g[i])==k);rid=rawgroups[tuple(ns['old'][0][actual].astype(np.float32).astype(float))];values=sorted(set(tuple(map(float,attrs['TEXCOORD_0'][j])) for j in rid))
   if len(values)>1:rawuvseams.append({'geometric_id':k,'stage1_XYZ':gv[k].tolist(),'on_chart_boundary':k in set(z for edge,ct0 in Counter(tuple(sorted((int(g[a]),int(g[c])))) for face in f[sheet['triangle_ids']] for a,c in zip(face,np.roll(face,-1))).items() if ct0==1 for z in edge),'raw_UVs':values,'used_chart_UVs':sorted(uvused[k]),'note':'exact-position UV split must retain explicit corner provenance; never select arbitrary raw group UV'})
  sheet['chart_internal_UV_conflicts']=chartuvconflicts;sheet['raw_UV_seams']=rawuvseams
  sheet['raw_attribute_compatibility']={'J_W_UV_same_exact_POSITION_conflicts':dict(conflicts),'geometric_positions_with_distinct_raw_normal_groups':normalgroups,'max_raw_position_group_size':maxgroups,'normal_policy':'Distinct normal groups not merged; any CDT future would require explicit new-face normal policy approval.'}
 sideok=left|right;crossids=np.flatnonzero(active&~cap&~sideok);crossdata=[]
 for i in crossids:
  crossdata.append({'triangle':int(i),'branch':'upper' if up[i] else 'lower' if low[i] else 'straddle','stage1_X_range':[float(q[f[i],0].min()),float(q[f[i],0].max())],'Z_values_rest':v[f[i],2].tolist(),'native_XY':mapped[f[i]].tolist()})
 capids=np.flatnonzero(active&cap);capdata=[]
 for branch,mask in [('upper',up),('lower',low),('straddle',~(up|low))]:
  ii=np.flatnonzero(active&cap&mask)
  if len(ii):
   pp=np.unique(f[ii]);delta=mapped[pp,1]-q[pp,1];capdata.append({'branch':branch,'triangles':len(ii),'unique_X':sorted(set(q[pp,0].tolist())),'stage1_Y_range':[float(q[pp,1].min()),float(q[pp,1].max())],'mapped_Y_range':[float(mapped[pp,1].min()),float(mapped[pp,1].max())],'role':'Kept exact existing YZ cap topology; fixed F2 at constant X, no XY CDT.'})
 failure=json.loads((b/'cpu-y-uv-monotone/monotone-completion.validation.json').read_text());failed=set(k for pair in failure['canonical_actual_base_crossing']['pairs'] for k in pair if k<len(f));assigned=up|low;sideok=left|right;report={'status':'readonly_skin_destination_XY_chart','accepted':False,'CDT_executed':False,'refinement_executed':False,'assets_written':False,'selection':'skin triangle iff any Stage1 original-domain vertex X>=1988; exact-allXconstant caps excluded','active_skin_triangles':int(active.sum()),'excluded_exact_allXconstant_caps':int((active&cap).sum()),'branch_straddle_or_zero_active_noncap':int((active&~cap&~assigned).sum()),'z_crossing_or_all_centerline_active_noncap':int((active&~cap&~sideok).sum()),'z_all_centerline_active_noncap':int((active&~cap&(v[f,2].min(1)==0)&(v[f,2].max(1)==0)).sum()),'straddle_ids':np.flatnonzero(active&~cap&(~assigned|~sideok)).tolist(),'failed_skin_triangle_ids':sorted(failed),'all_failed_skin_triangles_covered_by_four_or_cap':all(any(k in s['triangle_ids'] for s in res) or cap[k] for k in failed),'sheets':res,'kept_cross_Z_faces':crossdata,'excluded_cap_groups':capdata,'original397_parent_edges':len(skinoral),'all_original_skin_geometry_edges_incidence1or2':all(c in [1,2] for c in allct.values()),'normal_or_UV_new_assets_generated':False,'dependencies_sha256':{str(p):sha(p) for p in [a.input,script,b/'cpu-y-uv-monotone/monotone-frozen.validation.json',Path(__file__)]},'limits':['Boundary simple/single-value tests do not prove valid CDT or final normals/UV/LOD/material.','Exact coordinates retained; 1e-7 pixel proximity only reported, never merged/snapped.','Existing inner diagonals may overlap in destination; this is a reconnect proposal, old interior signs are diagnostics not automatic veto.']};a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'active':report['active_skin_triangles'],'caps':report['excluded_exact_allXconstant_caps'],'straddles':report['branch_straddle_or_zero_active_noncap'],'center_or_crossz':report['z_crossing_or_all_centerline_active_noncap'],'sheets':[{k:s[k] for k in ['sheet','triangles','vertices','boundary_edges','Euler_V_E_F','current_zero_XY_areas','simple_single_value_chart_not_yet_CDT']}|{'loops':len(s['loops']),'crossings':len(s['boundary_strict_crossings']),'through_points':len(s['constraint_through_points']),'XY_Z_conflicts':len(s['same_XY_different_Z_conflicts'])} for s in res]},indent=2))
if __name__=='__main__':main()
