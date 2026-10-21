#!/usr/bin/env python3
"""108 Phase3 CPU feasibility only. Never writes model/UV/runtime assets."""
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).parent))
from audit_mouth_source_alignment_108 import plane_points

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canvas(v):v=np.asarray(v);return np.c_[(v[:,0]+.5)*2024,371-v[:,1]*2024]
def smooth(t):t=np.clip(t,0,1);return t**3*(10-15*t+6*t*t)
def dsmooth(t):return np.where((t>0)&(t<1),30*t*t*(1-t)**2,0)
def gate(x,a,b):return smooth((x-a)/(b-a)),dsmooth((x-a)/(b-a))/(b-a)
def masks(q,lo,hi):
 X,Y=q.T;n=len(q);one=np.ones(n);zero=np.zeros(n)
 def combine(a,b):return (1-(1-a[0])*(1-b[0]),a[1]*(1-b[0])[:,None]+b[1]*(1-a[0])[:,None])
 def prod(a,b):return (a[0]*b[0],a[1]*b[0][:,None]+b[1]*a[0][:,None])
 def g(axis,a,b):v,d=gate(q[:,axis],a,b);z=np.zeros((n,2));z[:,axis]=d;return v,z
 front=g(0,hi[0]+2,1940);lipfront=g(0,1988,1995)
 # Existing roof/floor only supplies distances, no normalized section chart.
 floor=457.174-0.3739328063*(X-1894.464);roof=floor-9.108
 topv,topd=gate(roof-Y,0,8);top=(topv,np.c_[-.3739328063*topd,-topd]);chv,chd=gate(Y-floor,0,8);chin=(chv,np.c_[.3739328063*chd,chd]);chin=prod(g(0,1860,1880),chin)
 mx=combine(lipfront,prod(front,top));my=combine(combine(lipfront,prod(front,top)),chin)
 # Exact zero over conservative enlarged eye bbox and zero derivative at boundaries.
 inside_x=prod(g(0,lo[0]-8,lo[0]),(1-g(0,hi[0],hi[0]+8)[0],-g(0,hi[0],hi[0]+8)[1]))
 inside_y=prod(g(1,lo[1]-8,lo[1]),(1-g(1,hi[1],hi[1]+8)[0],-g(1,hi[1],hi[1]+8)[1]))
 hole=prod(inside_x,inside_y);outside=(1-hole[0],-hole[1]);return prod(mx,outside),prod(my,outside)
def kernel(q,c,R):
 delta=q[:,None,:]-c[None,:,:];r=np.linalg.norm(delta,axis=2)/R;h=np.maximum(1-r,0);return h**4*(4*r+1),-20*h[:,:,None]**3*delta/(R*R)
def triangle_metrics(old,new,indices):
 ids=np.array(indices).reshape(-1,3);a=old[ids];b=new[ids];an=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);bn=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0]);aa=np.linalg.norm(an,axis=1);ba=np.linalg.norm(bn,axis=1);valid=aa>1e-14;ratio=ba/np.maximum(aa,1e-30);dot=(an*bn).sum(1);bad=valid&(dot<=0)
 return {'triangles':len(ids),'original_degenerate':int((~valid).sum()),'new_degenerate_from_valid':int((valid&(ba<=1e-14)).sum()),'opposite_normal_from_original':int(bad.sum()),'minimum_area_ratio_on_original_valid':float(ratio[valid].min()),'opposite_triangle_ids':np.flatnonzero(bad)[:24].tolist()}
def intersections(vertices,faces,changed):
 # Non-coplanar actual segment/triangle intersections. Coplanar cases are separately counted, not declared passed.
 tri=vertices[faces];lo=tri.min(1);hi=tri.max(1);cent=(lo+hi)/2;rad=np.linalg.norm(hi-lo,axis=1)/2;tree=cKDTree(cent);selected=np.flatnonzero(changed[faces].any(1));pairs=[]
 for i in selected:
  js=np.array(tree.query_ball_point(cent[i],rad[i]+rad.max()),dtype=int);js=js[js>i];js=js[np.all(lo[js]<=hi[i]+1e-10,axis=1)&np.all(hi[js]>=lo[i]-1e-10,axis=1)]
  if len(js):pairs.extend((int(i),int(j)) for j in js)
 if not pairs:return {'tested_pairs':0,'proper_intersections':0,'coplanar_candidates':0,'pairs':[]}
 pairs=np.array(pairs);A=tri[pairs[:,0]];B=tri[pairs[:,1]];shared=np.zeros(len(pairs),bool)
 for i in range(3):
  for j in range(3):shared|=(np.linalg.norm(A[:,i]-B[:,j],axis=1)<1e-7)
 pairs=pairs[~shared];A=A[~shared];B=B[~shared];hit=np.zeros(len(pairs),bool)
 for T,S in [(A,B),(B,A)]:
  e1=T[:,1]-T[:,0];e2=T[:,2]-T[:,0]
  for k in range(3):
   O=S[:,k];D=S[:,(k+1)%3]-O;H=np.cross(D,e2);det=(e1*H).sum(1);valid=abs(det)>1e-14;inv=np.zeros(len(det));inv[valid]=1/det[valid];s=O-T[:,0];u=(s*H).sum(1)*inv;Q=np.cross(s,e1);v=(D*Q).sum(1)*inv;t=(e2*Q).sum(1)*inv;hit|=valid&(u>1e-8)&(v>1e-8)&(u+v<1-1e-8)&(t>1e-8)&(t<1-1e-8)
 normal=np.cross(A[:,1]-A[:,0],A[:,2]-A[:,0]);normal2=np.cross(B[:,1]-B[:,0],B[:,2]-B[:,0]);parallel=np.linalg.norm(np.cross(normal,normal2),axis=1)<=1e-10*np.maximum(np.linalg.norm(normal,axis=1)*np.linalg.norm(normal2,axis=1),1e-30);plane=abs(((B[:,0]-A[:,0])*normal).sum(1))<=1e-10*np.maximum(np.linalg.norm(normal,axis=1),1e-30)
 return {'tested_pairs':len(pairs),'proper_intersections':int(hit.sum()),'coplanar_candidates_not_resolved':int((parallel&plane).sum()),'pairs':pairs[hit].tolist(),'limits':'shared-coordinate triangles excluded; proper crossing test only, coplanar overlap is not proved absent'}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=Path(__file__).resolve().parents[3];target=json.loads(a.input.read_text());folder=a.input.resolve().parent
 paths=[root/'projects/fishing-2d/experiments/blender-fish/eye-rollout-107/zander-mesh-rest.json',folder/'zander-oral-rest.json'];data=[json.loads(p.read_text()) for p in paths];verts=[np.array(d['rest_xyz']) for d in data];xy=[canvas(v) for v in verts];prot=json.loads((folder/'eye-protection-proposal.validation.json').read_text());frozen=[np.array(r['frozen_vertex_ids']) for r in prot['surfaces']];fxy=np.concatenate([x[ids] for x,ids in zip(xy,frozen)]);lo=fxy.min(0);hi=fxy.max(0);R=64.;controls=[]
 def add(role,p,targetxy,details=''):
  controls.append({'role':role,'old_rest_xyz':np.asarray(p).tolist(),'old_canvas_xy':canvas(np.array([p]))[0].tolist(),'target_canvas_xy':list(targetxy),'details':details})
 def section(sx,kind):
  points=plane_points(data[0],sx/2024-.5);q=canvas(points);return points[np.argmin(q[:,1]) if kind=='top' else np.argmax(q[:,1])]
 for sx,sy in [(1940.5,356),(1960.5,365),(1980.5,376),(1995.5,381)]:add('upper_outer',section(sx,'top'),(sx,sy),'source alpha top boundary')
 for sx,sy in [(1894.5,487),(1920.5,480),(1940.5,475),(1960.5,467),(1980.5,458),(1995.5,452)]:add('chin',section(sx,'bottom'),(sx,sy),'continuous source alpha lower cell boundary')
 source=json.loads((folder/'source-mouth-alignment.validation.json').read_text());interface=np.array([q for e in source['actual_interface'] for q in e['rest_xyz']]);iq=canvas(interface)
 def rim(x,upper):
  floor=457.174-.3739328063*(iq[:,0]-1894.464);select=iq[:,1]<floor-4.5 if upper else iq[:,1]>floor-4.5;ids=np.flatnonzero(select);j=ids[np.argmin(abs(iq[ids,0]-x))];return interface[j]
 add('upper_lip',rim(1995.6655,True),(2005.5,413),'definite front alpha upper-lip cell boundary; not same vertex as tip')
 add('lower_lip',rim(2005.6243,False),(2005.5,419),'definite front alpha lower-lip cell boundary')
 tip=source['actual_tips']['upper']['rest_xyz'][0];add('upper_tip',tip,(2019.5,401.5),'single endpoint takes representative cap center role only; no second406 target on this vertex. Actual projected cap coverage separately measured, not presumed impossible from vertex count.')
 cap_ids=np.array(source['actual_tips']['lower']['vertex_ids']);cap=verts[0][cap_ids];cy=canvas(cap)[:,1];cmin,cmax=cy.min(),cy.max()
 for role,j,ty in [('lower_cap_top',np.argmin(cy),425),('lower_cap_bottom',np.argmax(cy),436)]:add(role,cap[j],(2019.5,ty),'actual cap extreme; original Z unchanged')
 freeze={'status':'phase3_cpu_first_frozen_parameters','accepted':False,'model_written':False,'kernel':'WendlandC2','radius_native_pixels':R,'front_gate_source_x':[float(hi[0]+2),1940],'lip_front_gate_source_x':[1988,1995],'upper_distance_window_native_pixels':[0,8],'chin_distance_window_native_pixels':[0,8],'posterior_chin_source_x_window':[1860,1880],'eye_hole_bbox_native':[lo.tolist(),hi.tolist()],'eye_hole_outer_transition_native_pixels':8,'window':'quintic10t3-15t4+6t5','floor_distance_formula':'457.174-.3739328063*(X-1894.464); roof=floor-9.108. Only support distance, no division by section span.','controls':controls,'input_hashes':{str(p.relative_to(root)):sha(p) for p in paths},'source_target_sha256':sha(a.input),'protection_sha256':sha(folder/'eye-protection-proposal.validation.json'),'no_tuning':'first and only parameter solve; failure is evidence, not permission to vary radii/windows','probe_script_sha256':sha(Path(__file__))}
 a.output.mkdir(parents=True,exist_ok=True);fpath=a.output/'field-controls-frozen.validation.json';fpath.write_text(json.dumps(freeze,indent=2)+'\n')
 c=np.array([v['old_canvas_xy'] for v in controls]);want=np.array([v['target_canvas_xy'] for v in controls])-c;ms=masks(c,lo,hi);K,_=kernel(c,c,R);coeff=[];conditions=[];unsupported=[]
 for axis in range(2):
  M=ms[axis][0][:,None]*K;bad=(abs(ms[axis][0])<1e-14)&(abs(want[:,axis])>1e-10);unsupported.extend(np.flatnonzero(bad).tolist());condition=float(np.linalg.cond(M));rank=int(np.linalg.matrix_rank(M));conditions.append(condition)
  if bad.any() or rank<len(M) or not np.isfinite(condition) or condition>1e12:
   rejection={'status':'cpu_early_gate_rejected','accepted':False,'field_evaluated':False,'model_uv_runtime_written':False,'axis':axis,'rank':rank,'dimension':len(M),'condition_number':condition,'condition_limit':1e12,'unsupported_nonzero_target_control_ids':np.flatnonzero(bad).tolist(),'reason':'Reject unsupported, singular or illconditioned final-mask system before any coefficient solve; no least-squares fallback. Historical failed field snapshot remains separate.'};(a.output/'early-gate-rejection.validation.json').write_text(json.dumps(rejection,indent=2)+'\n');print(json.dumps(rejection,indent=2));return
  coeff.append(np.linalg.solve(M,want[:,axis]))
 coeff=np.array(coeff).T
 def evaluate(q,identity=False):
  k,dk=kernel(q,c,R);mm=masks(q,lo,hi);D=k@coeff;dd=np.einsum('ncd,ca->nad',dk,coeff);disp=np.zeros_like(q);J=np.tile(np.eye(2),(len(q),1,1))
  if identity:return disp,J
  for ax in range(2):disp[:,ax]=mm[ax][0]*D[:,ax];J[:,ax,:]+=mm[ax][1]*D[:,ax,None]+mm[ax][0][:,None]*dd[:,ax,:]
  return disp,J
 control_disp,_=evaluate(c);new=[];metrics=[];identitychecks=[];alljac=[];changed=[];protection=[]
 for i,(dat,v,q) in enumerate(zip(data,verts,xy)):
  disp,J=evaluate(q);out=v.copy();out[:,0]+=disp[:,0]/2024;out[:,1]-=disp[:,1]/2024;new.append(out);ch=np.linalg.norm(disp,axis=1)>1e-10;changed.append(ch);idet,ij=evaluate(q,True);identitychecks.append({'surface':i,'position_exact':bool(np.array_equal(v,v+np.c_[idet[:,0],idet[:,1],np.zeros(len(v))])),'uv_normal_not_touched':True,'jacobian_identity_exact':bool(np.array_equal(ij,np.tile(np.eye(2),(len(v),1,1))))});Jrest=J.copy();Jrest[:,0,1]*=-1;Jrest[:,1,0]*=-1;det=np.linalg.det(Jrest);alljac.extend(det.tolist());ids=frozen[i];protection.append({'surface':i,'protected_count':len(ids),'position_exact':bool(np.array_equal(out[ids],v[ids])),'max_field_displacement_px':float(np.linalg.norm(disp[ids],axis=1).max()),'max_jacobian_identity_error':float(abs(J[ids]-np.eye(2)).max()),'z_exact':bool(np.array_equal(out[:,2],v[:,2])),'posterior_x_before1860_position_exact':bool(np.array_equal(out[q[:,0]<=1860],v[q[:,0]<=1860]))})
  levels=[('base',dat['indices'])]+[(f'LOD{k}',ld['indices']) for k,ld in enumerate(dat['lods'])];metrics.append({'surface':i,'changed_vertices':int(ch.sum()),'minimum_jacobian_at_vertices':float(det.min()),'nonpositive_jacobians_at_vertices':int((det<=0).sum()),'levels':[dict(name=name,**triangle_metrics(v,out,indices)) for name,indices in levels]})
 # Jacobian at original base-triangle centroids adds interior probes; no claim of complete continuous proof.
 cent=np.concatenate([canvas(v[np.array(dat['indices']).reshape(-1,3)].mean(1)) for dat,v in zip(data,verts)]);_,cj=evaluate(cent);cdet=np.linalg.det(cj)
 # same function at shared rounded positions; actual array seam maximum retained separately.
 rimold=interface;rimnew=canvas(rimold)+evaluate(canvas(rimold))[0];common_error=[]
 for key in {tuple(np.round(v,7)) for v in interface}:
  actual=[]
  for vv,nn in zip(verts,new):
   ids=np.flatnonzero(np.all(np.round(vv,7)==key,axis=1));actual.extend(nn[ids])
  if len(actual)>1:common_error.append(float(np.linalg.norm(np.array(actual)-actual[0],axis=1).max()))
 uvneg=[]
 for surface,(q,vv,ch) in enumerate(zip(xy,new,changed)):
  dist=np.linalg.norm(canvas(vv)-q,axis=1);uvneg.append({'surface':surface,'applies':surface==0,'would_leave_source_projection_stale_vertices':int((dist>1/1024).sum()) if surface==0 else None,'max_additional_coordinate_mismatch_pixels':float(dist.max()) if surface==0 else None,'uv_written':False,'note':'skin sourceUV only; oral constant material has no source mapping and needs no sourceUV correction'})
 # Nonadjacent selfintersection on actual emitted geometry, including skin/inner crossing.
 vv=np.concatenate(new);faces=[];offset=0
 for dat,v in zip(data,new):faces.append(np.array(dat['indices']).reshape(-1,3)+offset);offset+=len(v)
 si=intersections(vv,np.concatenate(faces),np.concatenate(changed)); original_si=intersections(np.concatenate(verts),np.concatenate(faces),np.concatenate(changed)); old_pairs={tuple(x) for x in original_si['pairs']}; new_pairs={tuple(x) for x in si['pairs']}; si['baseline_proper_intersections_same_triangle_selection']=original_si['proper_intersections']; si['introduced_intersection_pair_count']=len(new_pairs-old_pairs); si['introduced_pair_examples']=[list(x) for x in sorted(new_pairs-old_pairs)[:24]]; si['original_pair_examples']=original_si['pairs'][:24];si['pairs']=si['pairs'][:24]
 # source-defined frontal gap on actual new skin triangle intersections.
 fake=dict(data[0]);fake['rest_xyz']=new[0].tolist();gap=[]
 for sx,up,down in [(2005.5,413,419),(2010.5,412,419),(2015.5,408,423),(2019.5,406,425)]:
  pts=plane_points(fake,sx/2024-.5);yy=canvas(pts)[:,1] if len(pts) else np.array([]);inside=yy[(yy>up+1e-4)&(yy<down-1e-4)];gap.append({'source_canvas_x':sx,'target_open_y':[up,down],'actual_triangle_plane_points_inside_target_gap':len(inside),'range_inside':([float(inside.min()),float(inside.max())] if len(inside) else None),'limits':'any surface intersection point in source transparent interval is a concrete gap mismatch; no points alone does not prove visibility/continuous gap'})
 # Verify analytic window+kernel product derivative independently, without modifying frozen parameters.
 eps=1e-3;sample=c.copy();_,Janalytic=evaluate(sample);Jn=np.zeros_like(Janalytic)
 for axis in range(2):
  step=np.zeros(2);step[axis]=eps;plus=evaluate(sample+step)[0]+sample+step;minus=evaluate(sample-step)[0]+sample-step;Jn[:,:,axis]=(plus-minus)/(2*eps)
 fd_error=abs(Jn-Janalytic).max()
 # Project actual emitted triangle union on one common source canvas; CPU raster diagnostic, not GPU visibility.
 roi=(1870,380,2024,500);zoom=4;boards=[];nativecap=[]
 for label,vertices in [('原版',verts),('首次场：失败，禁止安装',new)]:
  image=Image.new('RGB',((roi[2]-roi[0])*zoom,(roi[3]-roi[1])*zoom),(25,35,40));paint=ImageDraw.Draw(image);coverage=Image.new('1',image.size);cov=ImageDraw.Draw(coverage)
  for dat,vtx in zip(data,vertices):
   qq=canvas(vtx)
   for face in np.array(dat['indices']).reshape(-1,3):
    points=qq[face]
    if points[:,0].max()<roi[0] or points[:,0].min()>roi[2] or points[:,1].max()<roi[1] or points[:,1].min()>roi[3]:continue
    pp=[((x-roi[0])*zoom,(y-roi[1])*zoom) for x,y in points];cov.polygon(pp,fill=1);paint.line(pp+[pp[0]],fill=(70,170,200),width=1)
  cap=np.array(coverage)[(397-roi[1])*zoom:(406-roi[1])*zoom,(2019-roi[0])*zoom:(2020-roi[0])*zoom];nativecap.append({'label':label,'source_last_upper_cell_count':int(cap.size),'actual_projected_covered_subpixels':int(cap.sum()),'projection_sampling_per_pixel_axis':zoom,'limits':'allsurface projected union, not GPU visibility or biologicalcap target; finitecap claim based on this sampling only'})
  for ctl in controls:
   xx,yy=ctl['target_canvas_xy'];xx=(xx-roi[0])*zoom;yy=(yy-roi[1])*zoom;paint.ellipse((xx-3,yy-3,xx+3,yy+3),fill=(255,100,70))
  boards.append(image)
 board=Image.new('RGB',(boards[0].width*2,boards[0].height+32),(25,35,40));bd=ImageDraw.Draw(board)
 for k,im in enumerate(boards):board.paste(im,(k*im.width,32));bd.text((k*im.width+8,8),['Original actual triangles','First CPU field: FAILED / NOT INSTALLED'][k],fill='white')
 board.save(a.output/'cpu-projection-negative.png')
 # Execute the rejected cap-only shortening counterexample in memory.
 short=verts[0].copy();short[cap_ids,0]=float(tip[0]);short_chin=[]
 shortdata=dict(data[0]);shortdata['rest_xyz']=short.tolist()
 for sx in [1920.5,1940.5,1960.5]:
  oldpts=plane_points(data[0],sx/2024-.5);newpts=plane_points(shortdata,sx/2024-.5);short_chin.append({'source_canvas_x':sx,'old_chin_y':float(canvas(oldpts)[:,1].max()),'cap_shortened_chin_y':float(canvas(newpts)[:,1].max())})
 report={'schema_version':1,'status':'phase3_cpu_feasibility_only','accepted':False,'model_uv_runtime_written':False,'frozen_controls_sha256':sha(fpath),'unsupported_nonzero_target_control_ids':sorted(set(unsupported)),'system_condition_numbers_xy':conditions,'condition_note':'X full square matrix includes zero rows for analytically disabled zero-X-displacement controls; singular condition is reported, least-squares must still meet exact final-mask residuals. This is not a fullrank unique interpolation claim.','maximum_control_residual_pixels_xy':abs(control_disp-want).max(0).tolist(),'identity':identitychecks,'original_negative':{'upper_shortfall_pixels':2019-source['actual_tips']['upper']['max_canvas_x'],'lower_shortfall_pixels':2019-source['actual_tips']['lower']['max_canvas_x'],'chin_midsection_missing_pixels':[r['source_chin_below_mesh_px'] for r in source['stations'] if r['source_column'] in [1920,1940,1960]],'passes':False},'lower_tip_only_negative':{'upper_tip_shortfall_unchanged_pixels':2019-source['actual_tips']['upper']['max_canvas_x'],'changed_cap_vertex_count':len(cap_ids),'upper_actual_vertex_exact':bool(np.array_equal(short[source['actual_tips']['upper']['vertex_ids']],verts[0][source['actual_tips']['upper']['vertex_ids']])),'actual_chin_sections':short_chin,'chin_unchanged':all(x['old_chin_y']==x['cap_shortened_chin_y'] for x in short_chin),'passes':False,'reason':'shortening lower cannot restore upper tip or full chin envelope'},'protection':protection,'shared_397_edge_same_field':True,'posterior_actual_oral_rim':{'criterion':'actual397interface samples with sourceX<=1988 must remain unchanged','sample_count':int((iq[:,0]<=1988).sum()),'maximum_displacement_native_pixels':float(np.linalg.norm(evaluate(iq[iq[:,0]<=1988])[0],axis=1).max()),'exact_zero':bool(np.array_equal(evaluate(iq[iq[:,0]<=1988])[0],np.zeros_like(iq[iq[:,0]<=1988])))},'max_actual_co_position_seam_error_rest':max(common_error),'triangles_and_lod_sensitivity':metrics,'base_centroid_minimum_jacobian':float(cdet.min()),'base_centroid_minimum_location_source_canvas':cent[np.argmin(cdet)].tolist(),'base_centroid_nonpositive_jacobian_count':int((cdet<=0).sum()),'base_actual_self_intersection':si,'source_frontal_gap_negative':gap,'field_analytic_jacobian_finite_difference_max_error':float(fd_error),'uv_not_updated_negative':uvneg,'native_upper_cap_actual_projected_coverage':nativecap,'limits':['No model/UV/runtime written. No normals installed; exact eye/identity normals preserved by no-write contract.','Old generatedLOD indices only sensitivity, not new-importLOD preservation. All original levels retained.','Jacobian sampled vertices/centroids not full continuous proof. Coplanar self overlaps unresolved and cannot be declared pass.','Source cap representative endpoint is not source lip boundary. Finitecap coverage must be measured from actual projected triangles, not from max-X vertex count.']}
 ok=report['posterior_actual_oral_rim']['exact_zero'] and not unsupported and max(abs(control_disp-want).flat)<1e-6 and min(alljac)>0 and cdet.min()>0 and not si['proper_intersections'] and not si.get('coplanar_candidates_not_resolved',0) and all(x['position_exact'] for x in protection) and all(not lev['opposite_normal_from_original'] and not lev['new_degenerate_from_valid'] for m in metrics for lev in m['levels'])
 report['feasible_for_phase4']=bool(ok);report['next_action']='independent_phase3_review' if ok else 'report_infeasible_do_not_install';(a.output/'field-feasibility.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'feasible_for_phase4':report['feasible_for_phase4'],'control_residual_px':report['maximum_control_residual_pixels_xy'],'min_jacobian':report['base_centroid_minimum_jacobian'],'introduced_intersections':si['introduced_intersection_pair_count'],'next_action':report['next_action']},indent=2))
if __name__=='__main__':main()
