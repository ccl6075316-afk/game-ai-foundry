#!/usr/bin/env python3
"""108 Stage1 CPU only: monotone slit-aligned branch X map. No asset writes."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from probe_mouth_field_108 import plane_points,triangle_metrics,intersections,canvas,gate
A=1988.;U=1999.8681190013892;L=2015.9039835929864;T=2019.5;K=-1.02*742/2024
DU=T-U;DL=T-L

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def field(q,identity=False):
 q=np.asarray(q);X,Y=q.T;J=np.tile(np.eye(2),(len(q),1,1));new=q.copy();active=X>A
 if identity:return new,J
 gU,dU=gate(X,A,U);gL,dL=gate(X,A,L);V=Y-(452.62+K*(X-1894.464));w,dw=gate(V,-4.554,4.554)
 fU=X+DU*gU;fL=X+DL*gL;Xp=(1-w)*fU+w*fL;Yp=V+452.62+K*(Xp-1894.464)
 pure=(1-w)*(1+DU*dU)+w*(1+DL*dL);xdy=dw*(fL-fU);xdx=pure-K*xdy
 new[active]=np.c_[Xp,Yp][active];J[:,0,0]=xdx;J[:,0,1]=xdy;J[:,1,0]=-K+K*xdx;J[:,1,1]=1+K*xdy;J[~active]=np.eye(2)
 return new,J

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();root=Path(__file__).resolve().parents[3];folder=a.input.resolve().parent;source=json.loads(a.input.read_text());paths=[folder.parent/'eye-rollout-107/zander-mesh-rest.json',folder/'zander-oral-rest.json'];data=[json.loads(x.read_text()) for x in paths];vertices=[np.array(x['rest_xyz']) for x in data];xy=[canvas(v) for v in vertices];protect=json.loads((folder/'eye-protection-proposal.validation.json').read_text());a.output.mkdir(parents=True,exist_ok=True)
 freeze={'status':'stage1_first_frozen_parameters','accepted':False,'asset_written':False,'input_hashes':{str(p.relative_to(root)):sha(p) for p in paths},'source_alignment_sha256':sha(a.input),'proposal_sha256':sha(folder/'phase2-stage1-monotone-proposal.md'),'protection_sha256':sha(folder/'eye-protection-proposal.validation.json'),'probe_sha256':sha(Path(__file__)),'diagnostic_helpers_sha256':sha(Path(__file__).with_name('probe_mouth_field_108.py')),'fixed_parameters':{'onset_x':A,'old_upper_tip_x':U,'old_lower_tip_x':L,'target_tip_x':T,'delta_upper':DU,'delta_lower':DL,'slit_slope':K,'slit_anchor':[1894.464,452.62],'v_weight_transition':[-4.554,4.554],'window':'quintic10t3-15t4+6t5','z':'unchanged'},'no_tuning':'One frozen Stage1; no RBF, no span divide, no repeated parameter search. No Stage2.'};fpath=a.output/'stage1-parameters-frozen.validation.json';fpath.write_text(json.dumps(freeze,indent=2)+'\n')
 new=[];normals=[];changed=[];checks=[];metrics=[];minjac=[]
 for idx,(d,v,q,prot) in enumerate(zip(data,vertices,xy,protect['surfaces'])):
  mapped,J=field(q);out=v.copy();active=q[:,0]>A;out[active,0]=(mapped[active,0]/2024)-.5;out[active,1]=(371-mapped[active,1])/2024;new.append(out);changed.append(active)
  Jrest=J.copy();Jrest[:,0,1]*=-1;Jrest[:,1,0]*=-1;J3=np.tile(np.eye(3),(len(v),1,1));J3[:,:2,:2]=Jrest;n=np.array(d['rest_normals']);nn=n.copy();nn[active]=np.einsum('nij,nj->ni',np.linalg.inv(J3[active]).transpose(0,2,1),n[active]);nn[active]/=np.linalg.norm(nn[active],axis=1)[:,None];normals.append(nn);ids=np.array(prot['frozen_vertex_ids']);im,ij=field(q,True);det=np.linalg.det(J);minjac.extend(det.tolist());checks.append({'surface':idx,'active_vertices':int(active.sum()),'identity_position_exact':bool(np.array_equal(im,q)),'identity_jacobian_exact':bool(np.array_equal(ij,np.tile(np.eye(2),(len(q),1,1)))),'protected_position_exact':bool(np.array_equal(v[ids],out[ids])),'protected_normal_exact':bool(np.array_equal(n[ids],nn[ids])),'protected_uv_not_modified':True,'protected_jacobian_exact':bool(np.array_equal(J[ids],np.tile(np.eye(2),(len(ids),1,1)))),'posterior_position_normal_exact':bool(np.array_equal(v[~active],out[~active]) and np.array_equal(n[~active],nn[~active])),'z_exact':bool(np.array_equal(v[:,2],out[:,2])),'source_uv_exact':True,'normals_finite':bool(np.isfinite(nn).all()),'normal_min_length':float(np.linalg.norm(nn,axis=1).min()),'minimum_vertex_jacobian':float(det.min())})
  levels=[('base',d['indices'])]+[(f'LOD{k}',level['indices']) for k,level in enumerate(d['lods'])];metrics.append({'surface':idx,'levels':[dict(name=name,**triangle_metrics(v,out,indices)) for name,indices in levels]})
 # Test explicit unchanged rear oral interface, and shared geometric endpoints.
 interface=np.array([p for edge in source['actual_interface'] for p in edge['rest_xyz']]);iq=canvas(interface);rmap,rjac=field(iq);rear=iq[:,0]<=A;shared=[]
 for key in {tuple(np.round(v,7)) for v in interface}:
  positions=[]
  for old,out in zip(vertices,new):positions.extend(out[np.all(np.round(old,7)==key,axis=1)])
  if len(positions)>1:shared.append(float(np.linalg.norm(np.array(positions)-positions[0],axis=1).max()))
 # Independent finite difference includes off-mesh bridge/interior probes too.
 test=np.concatenate(xy+[np.array([[1990,452.62+K*(1990-1894.464)+vv] for vv in [-4,0,4]])]);test=test[test[:,0]>A+.01];eps=1e-4;_,analytic=field(test);fd=np.zeros_like(analytic)
 for ax in range(2):
  step=np.zeros(2);step[ax]=eps;fd[:,:,ax]=(field(test+step)[0]-field(test-step)[0])/(2*eps)
 # Base face centroid differential and concrete triangle crossings compare same selection.
 cent=np.concatenate([canvas(v[np.array(d['indices']).reshape(-1,3)].mean(1)) for d,v in zip(data,vertices)]);_,cj=field(cent);detc=np.linalg.det(cj);faces=[];offset=0
 for d,v in zip(data,vertices):faces.append(np.array(d['indices']).reshape(-1,3)+offset);offset+=len(v)
 allf=np.concatenate(faces);si=intersections(np.concatenate(new),allf,np.concatenate(changed));oldsi=intersections(np.concatenate(vertices),allf,np.concatenate(changed));introduced={tuple(p) for p in si['pairs']}-{tuple(p) for p in oldsi['pairs']};si['original_proper_intersections_same_selection']=oldsi['proper_intersections'];si['introduced_pair_count']=len(introduced);si['pairs']=si['pairs'][:24]
 # Concrete tip/cap values and still-unfixed source gap/chin/UV differences.
 qnew=canvas(new[0]);tipdata={}
 for name in ['upper','lower']:
  ids=np.array(source['actual_tips'][name]['vertex_ids']);tipdata[name]={'actual_old_tip_vertex_ids':ids.tolist(),'new_cap_x_minmax':[float(qnew[ids,0].min()),float(qnew[ids,0].max())],'new_cap_y_minmax':[float(qnew[ids,1].min()),float(qnew[ids,1].max())],'tip_x_residual_from2019_5':float(abs(qnew[ids,0]-T).max()),'new_actual_rest_z_unchanged':bool(np.array_equal(new[0][ids,2],vertices[0][ids,2]))}
 fake=dict(data[0]);fake['rest_xyz']=new[0].tolist();gap=[]
 for sx,up,down in [(2005.5,413,419),(2010.5,412,419),(2015.5,408,423),(2019.5,406,425)]:
  pts=plane_points(fake,sx/2024-.5);yy=canvas(pts)[:,1] if len(pts) else np.array([]);inside=yy[(yy>up+1e-4)&(yy<down-1e-4)];gap.append({'source_x':sx,'target_source_open_y':[up,down],'actual_skin_plane_hits_inside_source_gap':len(inside),'hit_range':([float(inside.min()),float(inside.max())] if len(inside) else None),'not_acceptance':'Plane intersection only; actual rendering/material opening still pending.'})
 chin=[]
 for sx in [1894.5,1920.5,1940.5,1960.5,1980.5,1995.5]:
  oldp=plane_points(data[0],sx/2024-.5);newp=plane_points(fake,sx/2024-.5);chin.append({'source_x':sx,'old_chin_y':float(canvas(oldp)[:,1].max()),'stage1_chin_y':float(canvas(newp)[:,1].max()),'stage2_not_done':True})
 dist=np.linalg.norm(qnew-xy[0],axis=1);report={'status':'stage1_cpu_only_pending_independent_review','accepted':False,'model_uv_runtime_written':False,'parameters_sha256':sha(fpath),'checks':checks,'rear_actual_640_oral_endpoint_samples':{'count':int(rear.sum()),'position_exact':bool(np.array_equal(rmap[rear],iq[rear])),'jacobian_exact':bool(np.array_equal(rjac[rear],np.tile(np.eye(2),(rear.sum(),1,1))))},'397_shared_edges_max_co_position_error_rest':max(shared),'max_analytic_vs_finite_difference_jacobian_error':float(abs(fd-analytic).max()),'minimum_jacobian_vertices':min(minjac),'minimum_jacobian_base_centroids':float(detc.min()),'nonpositive_base_centroid_jacobians':int((detc<=0).sum()),'actual_base_and_old_lod_sensitivity':metrics,'actual_base_self_intersection':si,'actual_tips':tipdata,'source_gap_remaining_mismatch':gap,'chin_remaining_mismatch':chin,'uv_not_updated_negative':{'skin_vertices_new_source_coordinate_drift_gt1over1024px':int((dist>1/1024).sum()),'maximum_new_drift_pixels':float(dist.max()),'uv_written':False,'oral_no_source_uv_mapping':True},'lower_source_cap_not_fitted':{'target_y_half_open':[425,436],'actual_y':tipdata['lower']['new_cap_y_minmax'],'stage2_required':True},'limits':['Stage1 only, no chin/Y-envelope fitting or sourceUV update. No model/normal/UV/runtime asset emitted.','Original generated6/2LOD index arrays retained only for CPU sensitivity. Fresh importedLOD may differ and needs binding/review.','Continuous positiveJac does not replace actual finite triangles; crossing test excludes shared-coordinate neighbors and does not prove all coplanar contacts absent.','No grey GPU, fin/body or wholemouth acceptance.']}
 report['stage1_discrete_feasible']=bool(all(x['identity_position_exact'] and x['protected_position_exact'] and x['protected_normal_exact'] and x['posterior_position_normal_exact'] and x['z_exact'] for x in checks) and report['rear_actual_640_oral_endpoint_samples']['position_exact'] and report['397_shared_edges_max_co_position_error_rest']<1e-7 and min(minjac)>0 and detc.min()>0 and not introduced and all(not level['new_degenerate_from_valid'] and not level['opposite_normal_from_original'] for s in metrics for level in s['levels']))
 report['next_action']='independent_phase3b_review_stage1_only' if report['stage1_discrete_feasible'] else 'reject_stage1_no_install';(a.output/'stage1-feasibility.validation.json').write_text(json.dumps(report,indent=2)+'\n')
 # CPU wireframe comparison, same source canvas, no independent alignment.
 roi=(1870,380,2024,500);zoom=4;images=[]
 for vlist in [vertices,new]:
  image=Image.new('RGB',((roi[2]-roi[0])*zoom,(roi[3]-roi[1])*zoom),(25,35,40));draw=ImageDraw.Draw(image)
  for d,v in zip(data,vlist):
   qq=canvas(v)
   for face in np.array(d['indices']).reshape(-1,3):
    pts=qq[face]
    if pts[:,0].max()<roi[0] or pts[:,0].min()>roi[2] or pts[:,1].max()<roi[1] or pts[:,1].min()>roi[3]:continue
    pp=[((x-roi[0])*zoom,(y-roi[1])*zoom) for x,y in pts];draw.line(pp+[pp[0]],fill=(70,170,200),width=1)
  images.append(image)
 board=Image.new('RGB',(images[0].width*2,images[0].height+32),(25,35,40));d=ImageDraw.Draw(board)
 for k,im in enumerate(images):board.paste(im,(k*im.width,32));d.text((k*im.width+8,8),['Original actual triangles','Stage1 CPU only / NOT INSTALLED'][k],fill='white')
 board.save(a.output/'stage1-cpu-projection.png');print(json.dumps({k:report[k] for k in ['stage1_discrete_feasible','minimum_jacobian_vertices','minimum_jacobian_base_centroids','max_analytic_vs_finite_difference_jacobian_error','next_action']},indent=2))
if __name__=='__main__':main()
