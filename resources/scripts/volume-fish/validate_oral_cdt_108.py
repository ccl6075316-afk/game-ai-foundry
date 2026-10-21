#!/usr/bin/env python3
"""108 CPU-only CDT validation; canonical broadphase pairs include changed/static in either index order."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree
from probe_mouth_slit_stage1_108 import field,canvas

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cross2(a,b):return a[0]*b[1]-a[1]*b[0]
def polygon_area(p):
 p=np.array(p)
 return abs(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))/2 if len(p)>=3 else 0.
def clip(P,T):
 sign=np.sign(cross2(T[1]-T[0],T[2]-T[0]));poly=list(P)
 if not sign:return []
 for a,b in zip(T,np.roll(T,-1,axis=0)):
  out=[]
  if not poly:break
  for s,e in zip(poly,[*poly[1:],poly[0]]):
   ds=sign*cross2(b-a,s-a);de=sign*cross2(b-a,e-a);si=ds>=0;ei=de>=0
   if si!=ei:out.append(s+(e-s)*ds/(ds-de))
   if ei:out.append(e)
  poly=out
 return poly

def crossing(v,faces,changed):
 tri=v[faces];lo=tri.min(1);hi=tri.max(1);mid=(lo+hi)/2;rad=np.linalg.norm(hi-lo,axis=1)/2;tree=cKDTree(mid);selected=np.flatnonzero(changed[faces].any(1));pairset=set();old_missed=set()
 for i in selected:
  js=np.array(tree.query_ball_point(mid[i],rad[i]+rad.max()),int);js=js[js!=i];js=js[np.all(lo[js]<=hi[i]+1e-10,axis=1)&np.all(hi[js]>=lo[i]-1e-10,axis=1)]
  for j in js:
   pair=(min(int(i),int(j)),max(int(i),int(j)));pairset.add(pair)
   if j<i and j not in selected:old_missed.add(pair)
 if not pairset:return {'tested_pairs':0,'proper_crossings':0,'pairs':[],'coplanar_positive_area_overlap_pairs':0,'old_js_gt_i_would_miss_pairs':0}
 pairs=np.array(sorted(pairset));A=tri[pairs[:,0]];B=tri[pairs[:,1]];hit=np.zeros(len(pairs),bool)
 # Deliberately retain pairs sharing vertices: strict interior barycentrics exclude mere shared endpoints/edges.
 for T,S in [(A,B),(B,A)]:
  e1=T[:,1]-T[:,0];e2=T[:,2]-T[:,0]
  for k in range(3):
   O=S[:,k];D=S[:,(k+1)%3]-O;H=np.cross(D,e2);det=(e1*H).sum(1);valid=abs(det)>1e-14;inv=np.zeros(len(det));inv[valid]=1/det[valid];s=O-T[:,0];u=(s*H).sum(1)*inv;Q=np.cross(s,e1);w=(D*Q).sum(1)*inv;t=(e2*Q).sum(1)*inv;hit|=valid&(u>1e-8)&(w>1e-8)&(u+w<1-1e-8)&(t>1e-8)&(t<1-1e-8)
 n=np.cross(A[:,1]-A[:,0],A[:,2]-A[:,0]);nn=np.cross(B[:,1]-B[:,0],B[:,2]-B[:,0]);size=np.linalg.norm(n,axis=1);size2=np.linalg.norm(nn,axis=1);parallel=np.linalg.norm(np.cross(n,nn),axis=1)<=1e-10*np.maximum(size*size2,1e-30);plane=abs(((B[:,0]-A[:,0])*n).sum(1))<=1e-10*np.maximum(size,1e-30);copids=np.flatnonzero(parallel&plane&(size>1e-14)&(size2>1e-14));over=[]
 for k in copids:
  axes=[x for x in range(3) if x!=np.argmax(abs(n[k]))];area=polygon_area(clip(A[k][:,axes],B[k][:,axes]))
  if area>1e-16:over.append({'pair':pairs[k].tolist(),'projected_overlap_area':float(area)})
 return {'tested_pairs':len(pairs),'changed_triangles':len(selected),'proper_crossings':int(hit.sum()),'pairs':pairs[hit].tolist(),'coplanar_candidates':len(copids),'coplanar_positive_area_overlap_pairs':len(over),'coplanar_overlap_examples':over[:24],'old_js_gt_i_would_miss_pairs':len(old_missed),'shared_vertex_pairs_not_excluded':True,'limits':'All pairs with at least one changed vertex usecanonical unordered pair. Strict interior segment/triangle tests and projected coplanar positivearea threshold1e-16. Not continuous-time collision or exact-arithmetic proof.'}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();result=json.loads(a.input.read_text());frozenpath=Path(result['input']);cfg=json.loads(frozenpath.read_text());assert sha(frozenpath)==result['input_sha256'];assert cfg['epsilon']==1e-9 and result['origins_one_to_one'] and not result['unused_input_point_ids'];b=a.input.resolve().parents[1];data=[json.loads((b.parent/'eye-rollout-107/zander-mesh-rest.json').read_text()),json.loads((b/'zander-oral-rest.json').read_text())];old=[np.array(d['rest_xyz']) for d in data];mapped=[];changes=[]
 for v in old:
  q=canvas(v);mp,_=field(q);active=q[:,0]>1988;out=v.copy();out[active,0]=mp[active,0]/2024-.5;out[active,1]=(371-mp[active,1])/2024;mapped.append(out);changes.append(active)
 pointv=np.array([p['stage1_xyz'] for p in cfg['points']]);point_raw_ids=np.array([p['oral_actual_vertex_id'] for p in cfg['points']]);assert np.array_equal(pointv,mapped[1][point_raw_ids]);newlocal=np.array(result['input_origin_faces']);neworal=point_raw_ids[newlocal];oldoral=np.array(data[1]['indices']).reshape(-1,3);remove=np.array(cfg['old_oral_triangle_ids']);keep=np.ones(len(oldoral),bool);keep[remove]=False;oral=np.concatenate([oldoral[keep],neworal]);skin=np.array(data[0]['indices']).reshape(-1,3);n=len(old[0]);origfaces=np.concatenate([skin,oldoral+n]);newfaces=np.concatenate([skin,oral+n]);vertices=np.concatenate(mapped);changed=np.concatenate(changes);changed[n+point_raw_ids]=True # conservative topology-change selection: everynewupper97face selected, evenallpointsX<=1988
 # Euler, exact boundary and positive projected area with original3D origin coordinates, not CDT coordinates.
 counts=Counter(tuple(sorted(e)) for face in newlocal for e in zip(face,np.roll(face,-1)));boundary={e for e,x in counts.items() if x==1};directed_new={tuple(e) for face in newlocal for e in zip(face,np.roll(face,-1)) if tuple(sorted(e)) in boundary};point_lookup={tuple(p['original_xyz']):i for i,p in enumerate(cfg['points'])};oldlocal=np.array([[point_lookup[tuple(old[1][v])] for v in face] for face in oldoral[remove]]);oldcounts=Counter(tuple(sorted(e)) for face in oldlocal for e in zip(face,np.roll(face,-1)));directed_old={tuple(e) for face in oldlocal for e in zip(face,np.roll(face,-1)) if oldcounts[tuple(sorted(e))]==1};expected={tuple(sorted(e)) for e in cfg['edges']};xz=pointv[:,[0,2]];tri=xz[newlocal];areas=(tri[:,1,0]-tri[:,0,0])*(tri[:,2,1]-tri[:,0,1])-(tri[:,1,1]-tri[:,0,1])*(tri[:,2,0]-tri[:,0,0]);patchnormal=np.cross(pointv[newlocal[:,1]]-pointv[newlocal[:,0]],pointv[newlocal[:,2]]-pointv[newlocal[:,0]]);patcharea=sum(abs(areas))/2;boundaryarea=polygon_area(xz[cfg['loop']]);overlaps=[]
 for i in range(len(newlocal)):
  for j in range(i+1,len(newlocal)):
   area=polygon_area(clip(tri[i],tri[j]))
   if area>1e-16:overlaps.append([i,j,float(area)])
 # Entire397body interface geometry must remain exact and closed against skin.
 def geom_boundary(v,faces):
  keys=[tuple(p) for p in v];ct=Counter(tuple(sorted((keys[i],keys[j]))) for face in faces for i,j in zip(face,np.roll(face,-1)));return {e for e,x in ct.items() if x==1},sum(x>2 for x in ct.values())
 oldbound,_=geom_boundary(mapped[1],oldoral);newbound,nm=geom_boundary(mapped[1],oral);skinbound,_=geom_boundary(mapped[0],skin)
 regv=np.array([[0,0,0],[1,0,0],[0,1,0],[.2,.2,-1],[.2,.2,1],[.4,.2,0]],float);regression=crossing(regv,np.array([[0,1,2],[3,4,5]]),np.array([False]*3+[True]*3));originalcheck=crossing(np.concatenate(old),origfaces,changed);negative=crossing(vertices,origfaces,changed);positive=crossing(vertices,newfaces,changed);returndelta=max(np.linalg.norm(np.array(pos)-cfg['points'][orig[0]]['input_xz']) for pos,orig in zip(result['returned_xz_diagnostic_only'],result['output_orig_verts']));valid=boundary==expected and directed_new==directed_old and len(directed_new)==37 and len(newlocal)==97 and len(np.unique(newlocal))==68 and (areas<0).all() and abs(patcharea-boundaryarea)<1e-12 and not overlaps and oldbound==newbound and len(newbound)==397 and skinbound==newbound and not nm and not positive['proper_crossings'] and not positive['coplanar_positive_area_overlap_pairs'] and regression['proper_crossings']==1 and regression['old_js_gt_i_would_miss_pairs']==1
 out={'status':'cpu_upper_cdt_pending_independent_review','accepted':False,'base_cpu_gate_passed':bool(valid),'model_uv_runtime_written':False,'cdt_evaluations':1,'epsilon':cfg['epsilon'],'inputs':{str(p):sha(p) for p in [a.input,frozenpath,Path(__file__),Path(__file__).with_name('probe_mouth_slit_stage1_108.py')]},'points_origins_one_to_one':True,'new_geometric_points':0,'merged_geometry_points':0,'unused_points':result['unused_input_point_ids'],'returned_coordinate_max_delta_rest_not_used':float(returndelta),'kept_original_oral_indices_exact':bool(np.array_equal(oral[:keep.sum()],oldoral[keep])),'lower_indices_replaced':False,'lower_original_faces_all_kept':bool(np.all(keep[(canvas(old[1])[:,1]-(452.62-1.02*742/2024*(canvas(old[1])[:,0]-1894.464)))[oldoral].min(1)>0])),'skin_geometry_not_retriangulated':True,'changed_selection':'originalX>1988 plusall68upperoriginpoints, soall97newfacesselected includingallstaticpositiontopologychanges','all97newfaces_selected':bool(changed[n+neworal].any(1).all()),'point_stage1_positions_exact':True,'point_source_position_recovers_exact_raw_float32':all(p['actual_json_recovers_identical_raw_float32_position'] for p in cfg['points']),'point_JWUV_contract':'prepare CLI verified each exactfloat32 POSITION group J/W/UV equal and froze values+raworigins; no interpolated attributes generated','new_flat_face_normals_finite':bool(np.isfinite(patchnormal/np.linalg.norm(patchnormal,axis=1)[:,None]).all()),'static_lower_index_crossing_regression':regression,'euler':{'vertices':len(cfg['points']),'boundary':len(boundary),'faces':len(newlocal),'expected_faces':cfg['expected_faces_euler'],'all_points_used':len(np.unique(newlocal))==68},'xz_domain':{'boundary_exact':boundary==expected,'directed_boundary_exact':directed_new==directed_old,'directed_boundary_edge_count':len(directed_new),'old_directed_boundary':[[int(x) for x in e] for e in sorted(directed_old)],'new_directed_boundary':[[int(x) for x in e] for e in sorted(directed_new)],'all_upper_signed_area_negative':bool((areas<0).all()),'minimum_abs_area2':float(abs(areas).min()),'triangle_area_sum':float(patcharea),'polygon_area':float(boundaryarea),'area_difference':float(patcharea-boundaryarea),'positive_area_overlap_pairs':len(overlaps),'overlap_examples':overlaps[:12],'edge_multiplicity_gt2':sum(x>2 for x in counts.values()),'normal_min_area2':float(np.linalg.norm(patchnormal,axis=1).min())},'all397skin_interface':{'old_equals_new_exact':oldbound==newbound,'skin_equals_oral_exact':skinbound==newbound,'count':len(newbound),'nonmanifold_edges':nm},'new_broadphase_negative_controls':{'original':originalcheck,'stage1_old_connectivity':negative},'new_broadphase_positive_cdt':positive,'old_lod_status':'Original6/2LOD failures remain; noLOD rewritten. Positivegate is only base candidateCPU, actualnewimportLOD still required.','scope':'Onlyupper97faces are retriangulated inCPU; Stage1 remains fixed, lower connections kept, noStage2/chin/UV/model generation.'};a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'base_cpu_gate_passed':out['base_cpu_gate_passed'],'original_crossings':originalcheck['proper_crossings'],'stage1_old_crossings':negative['proper_crossings'],'cdt_crossings':positive['proper_crossings'],'cdt_coplanar_area_overlap':positive['coplanar_positive_area_overlap_pairs'],'boundary397':out['all397skin_interface'],'xz_domain':out['xz_domain']},indent=2))
if __name__=='__main__':main()
