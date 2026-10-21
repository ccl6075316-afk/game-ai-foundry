#!/usr/bin/env python3
"""Approved read-only finite attribution on stoppedattempt2 f32 points/oldCDT.
No field change, CDT invocation, model/UV/runtime or Phase3-pass write.
"""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from scipy.spatial import cKDTree
from validate_oral_cdt_108 import crossing,clip,polygon_area
from audit_mouth_skin_chart_108 import intersect,cross
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def graph(name,points,faces,axes,required,directed_expected):
 xy=points[:,axes];faces=np.asarray(faces,int);tt=xy[faces];areas=(tt[:,1,0]-tt[:,0,0])*(tt[:,2,1]-tt[:,0,1])-(tt[:,1,1]-tt[:,0,1])*(tt[:,2,0]-tt[:,0,0]);ct=Counter(tuple(sorted((int(i),int(j))))for f in faces for i,j in zip(f,np.roll(f,-1)));edges=sorted(ct);boundary=sorted(e for e,c in ct.items()if c==1);directed={(int(i),int(j))for f in faces for i,j in zip(f,np.roll(f,-1))if ct[tuple(sorted((int(i),int(j))))]==1};adj=defaultdict(set)
 for i,j in boundary:adj[i].add(j);adj[j].add(i)
 degree={int(i):len(j)for i,j in adj.items()if len(j)!=2};loops=[];seen=set()
 if not degree:
  for start in sorted(adj):
   if start in seen:continue
   loop=[start];prev=None;cur=start
   while True:
    choices=sorted(adj[cur]-({prev}if prev is not None else set()));nxt=choices[0]
    if nxt==start:break
    if nxt in loop:raise ValueError('non-simple graph walk')
    loop.append(nxt);prev,cur=cur,nxt
   seen.update(loop);loops.append(loop)
 zero=[list(e)for e in boundary if np.array_equal(xy[e[0]],xy[e[1]])];bc=[];collinear=[]
 for i,(u,v)in enumerate(boundary):
  for w,z in boundary[i+1:]:
   if len({u,v,w,z})<4:continue
   if intersect(xy[u],xy[v],xy[w],xy[z]):bc.append([[u,v],[w,z]])
   elif abs(cross(xy[v]-xy[u],xy[z]-xy[w]))<=1e-18 and abs(cross(xy[w]-xy[u],xy[v]-xy[u]))<=1e-18:
    axis=int(np.argmax(abs(xy[v]-xy[u])));over=min(max(xy[u,axis],xy[v,axis]),max(xy[w,axis],xy[z,axis]))-max(min(xy[u,axis],xy[v,axis]),min(xy[w,axis],xy[z,axis]))
    if over>0:collinear.append([[u,v],[w,z],float(over)])
 through=[];eb=[]
 for u,v in boundary:
  delta=xy[v]-xy[u];norm=float(delta@delta)
  if norm==0:continue
  for k in range(len(points)):
   if k in [u,v]:continue
   t=float((xy[k]-xy[u])@delta/norm);distance=abs(cross(delta,xy[k]-xy[u]))/np.sqrt(norm)
   if 0<t<1 and distance<1e-12:through.append([u,v,k,float(distance)])
 for u,v in edges:
  if (u,v)in boundary:continue
  for w,z in boundary:
   if len({u,v,w,z})<4:continue
   if intersect(xy[u],xy[v],xy[w],xy[z]):eb.append([[u,v],[w,z]])
 groups=defaultdict(list)
 for i,x in enumerate(xy):groups[tuple(x)].append(i)
 omitted=next(a for a in range(3)if a not in axes);conflicts=[dict(point_ids=ids,projected_xy=list(key),omitted_values=points[ids,omitted].tolist())for key,ids in groups.items()if len(set(points[ids,omitted]))>1];outside=[]
 if len(loops)==1:
  polygon=xy[loops[0]]
  for i in range(len(points)):
   if i in adj:continue
   hit=False
   for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
    if (a[1]>xy[i,1])!=(b[1]>xy[i,1])and xy[i,0]<(b[0]-a[0])*(xy[i,1]-a[1])/(b[1]-a[1])+a[0]:hit=not hit
   if not hit:outside.append(i)
 overlaps=[]
 for i in range(len(faces)):
  for j in range(i+1,len(faces)):
   area=polygon_area(clip(tt[i],tt[j]))
   if area>1e-16:overlaps.append(dict(faces=[i,j],positive_area=float(area)))
 minspacing=float(cKDTree(xy).query(xy,k=2)[0][:,1].min());simple=len(loops)==1 and not degree and not zero and not bc and not collinear;ready=simple and not through and not conflicts and not outside and minspacing>1e-9;wrong=np.flatnonzero(areas*required<=0)
 return dict(sheet=name,projection_axes=axes,points=len(points),faces=len(faces),required_uniform_sign=required,zero_projected_area_faces=np.flatnonzero(areas==0).tolist(),wrong_or_zero_signed_area_faces=wrong.tolist(),signed_area2=areas.tolist(),boundary_edges=len(boundary),directed_boundary_exact=directed=={tuple(e)for e in directed_expected},boundary_simple=simple,boundary_degree_errors=degree,boundary_loops=loops,boundary_zero_edges=zero,boundary_proper_crossings=bc,boundary_collinear_overlaps=collinear,constraint_through_points=through,internal_edge_boundary_crossings=eb,same_projection_different_omitted_coordinate=conflicts,interior_points_outside_boundary=outside,minimum_projected_distinct_spacing=minspacing,projected_positive_area_overlaps=overlaps,all_existing_points_boundary_legal_for_destination_CDT_proposal=ready,old_connectivity_projected_legal=not len(wrong)and not overlaps and not eb,thresholds=dict(constraint_distance_rest=1e-12,coplanar_overlap_area_rest2=1e-16,collinear_cross_rest2=1e-18,CDT_frozen_epsilon_rest=1e-9),scope='Finite read-only graph attribution, not newCDT or acceptance.')

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();root=Path(__file__).resolve().parents[3];b=root/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108';helper=Path(__file__).with_name('diagnostic_attempt2_ram_payload_108.py');run=subprocess.run([sys.executable,str(helper)],capture_output=True,text=True,check=True);payload=json.loads(run.stdout);assert not payload['accepted'];positions=[np.array(x['POSITION'])for x in payload['surfaces']];faces=[np.array(x['indices']).reshape(-1,3)for x in payload['surfaces']];ns=[];sapi=json.loads((b/'cpu-upper-skin-cdt/cdt-api-result.validation.json').read_text());scfg=json.loads(Path(sapi['input']).read_text());offset=len(faces[0])-209;patchmap={};skin_new_selected=np.zeros(len(positions[0]),bool)
 for sh,ret in zip(scfg['sheets'],sapi['sheets']):
  ids=np.array([p['raw_glb_vertex_ids'][0]for p in sh['points']]);p=positions[0][ids];local=np.array(ret['input_origin_faces']);stats=graph(sh['sheet'],p,local,[0,1],sh['required_uniform_directed_XY_area_sign'],sh['directed_boundary_edges']);stats['global_raw_face_range']=[offset,offset+len(local)];stats['original_actual_vertex_ids']=[p['actual_vertex_id']for p in sh['points']];patchmap[sh['sheet']]=(offset,ids,local,stats);ns.append(stats);offset+=len(local);skin_new_selected[ids]=True
 ocfg=json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text());oret=json.loads((b/'cpu-upper-cdt/cdt-api-result.validation.json').read_text());ids=np.array([p['raw_glb_vertex_ids'][0]for p in ocfg['points']]);points=positions[1][ids];local=np.array(oret['input_origin_faces']);# derive uniform directedoriginal XZ sign from frozenStage1points, not current normals
 oldpoints=np.array([p['stage1_xyz']for p in ocfg['points']]);oldtri=oldpoints[local][:,:,[0,2]];oldarea=(oldtri[:,1,0]-oldtri[:,0,0])*(oldtri[:,2,1]-oldtri[:,0,1])-(oldtri[:,1,1]-oldtri[:,0,1])*(oldtri[:,2,0]-oldtri[:,0,0]);ct=Counter(tuple(sorted((int(i),int(j))))for f in local for i,j in zip(f,np.roll(f,-1)));directed=[(int(i),int(j))for f in local for i,j in zip(f,np.roll(f,-1))if ct[tuple(sorted((int(i),int(j))))]==1];oralstats=graph('oral-upper97',points,local,[0,2],int(np.sign(oldarea[0])),directed);ns.append(oralstats)
 source=Path(payload['original_source']);g,bin0=read_glb(source);mi=next(n['mesh']for n in g['nodes']if n.get('name')=='Closed_body');raw=[{k:accessor(g,bin0,v)for k,v in p['attributes'].items()}for p in g['meshes'][mi]['primitives']];moved=[np.any(positions[i][:len(r['POSITION'])]!=r['POSITION'],axis=1)for i,r in enumerate(raw)];moved[0]|=skin_new_selected;moved[1]=np.r_[moved[1],np.ones(len(positions[1])-len(raw[1]['POSITION']),bool)];n=len(positions[0]);allf=np.r_[faces[0],faces[1]+n];allv=np.r_[*positions];selected=np.r_[*moved];cr=crossing(allv,allf,selected);tri=allv[allf];area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1);badshading=[]
 for surface in range(2):
  normal=np.array(payload['surfaces'][surface]['NORMAL']);tt=positions[surface][faces[surface]];fn=np.cross(tt[:,1]-tt[:,0],tt[:,2]-tt[:,0]);mag=np.linalg.norm(fn,axis=1);cos=(normal[faces[surface]]*fn[:,None,:]).sum(2)/mag[:,None];badfaces=np.flatnonzero((cos<=0).any(1))
  for i in badfaces:badshading.append(dict(surface=surface,raw_face=int(i),nonpositive_corners=np.flatnonzero(cos[i]<=0).tolist(),cos=cos[i].tolist(),centroid_source_native=[float((tt[i,:,0].mean()+.5)*2024),float(371-tt[i,:,1].mean()*2024)]))
 # Explicit source-bad diagonal relation and graph/global conflict face identity.
 rootcause=json.loads((b/'attempt2-cpu/rootcause-diagnostic.validation.json').read_text());sourcebad=rootcause['failed_knownlip2000_5_PL_contributor'];right=patchmap['right-upper'];originactual=[p['actual_vertex_id']for p in scfg['sheets'][1]['points']];edge=[originactual.index(i)for i in sourcebad['edge_vertex_ids']];edgefaces=[i for i,f in enumerate(right[2])if set(edge)<=set(f)];globalids=[right[0]+i for i in edgefaces];conflict_pairs=[pair for pair in cr['pairs']if set(pair)&set(globalids)];related_projection=[r for r in right[3]['projected_positive_area_overlaps']if set(r['faces'])&set(edgefaces)]
 proposal=[]
 for stats in ns[:2]:
  if not stats['old_connectivity_projected_legal']and stats['all_existing_points_boundary_legal_for_destination_CDT_proposal']:
   proposal.append(dict(sheet=stats['sheet'],proposal='One separately reviewed destinationXYCDT on same frozenattempt2f32points/currentboundary, singletonoriginreturn, nofield/UV/point/epsilonchange',not_executed=True,scope='Only connectivity attribution/proposal; needs independentauthorization. Mustfreshallactualcrossing/coplanar/interface/source1px andnormal/graychecks.'))
 a.output.mkdir(parents=True,exist_ok=True);out=dict(status='read_only_attempt2_connectivity_attribution_not_Phase3pass',accepted=False,assets_written=False,field_changed=False,CDT_invoked=False,original_attempt2_failed_unchanged=True,inputs=dict(field_sha256=payload['field_sha256'],parameters_sha256=payload['parameters_sha256'],failedCPU_sha256=payload['cpu_failure_report_sha256'],audit_sha256=sha(Path(__file__))),graphs=ns,global_full_actual_f32=dict(surface_triangle_counts=[len(f)for f in faces],all_lower_and_cap_and_crossZ_included=True,all209skin97oral_newfaces_selected=True,zero3D_faces=np.flatnonzero(area==0).tolist(),crossing=cr),source_bad_edge_relation=dict(original_definition=sourcebad,patch_point_ids=edge,patch_adjacent_faces=edgefaces,global_raw_faces=globalids,global_conflict_pairs_touching_edge_faces=conflict_pairs,projection_overlap_pairs_touching_edge_faces=related_projection),negative_corner_shading_suspects=dict(count=len(badshading),faces=badshading,not_topology_proof=True),minimal_next_step_proposals=proposal,limits=['Only read-only finite attribution, never changes stoppedCPUresult to pass.','Everyactualbaseface included in globalchecker; conservative changed+allnewtopology pairselection, includingcaps/lower/crossZ.','Negativecorner normals are shading suspects only, not winding/intersection proof.','No automatic newfield/newCDT/asset/UV/runtime authorization.'])
 (a.output/'connectivity-attribution.validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(graphs=[{k:s[k]for k in ['sheet','wrong_or_zero_signed_area_faces','boundary_simple','constraint_through_points','same_projection_different_omitted_coordinate','interior_points_outside_boundary','old_connectivity_projected_legal','all_existing_points_boundary_legal_for_destination_CDT_proposal']}for s in ns],globalcross=cr['proper_crossings'],globalcoplanar=cr['coplanar_positive_area_overlap_pairs'],globalzero=int((area==0).sum()),proposal=proposal)))
if __name__=='__main__':main()
