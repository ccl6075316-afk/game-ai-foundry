#!/usr/bin/env python3
"""One frozen108 attempt2 CPU: unified ordered Y chart. Never emits assets/CDT."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from audit_mouth_refinement_108 import load_frozen_field
from validate_oral_cdt_108 import crossing
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=Path(__file__).resolve().parents[3];p=json.loads(a.input.read_text());b=a.input.parent;a.output.mkdir(parents=True,exist_ok=True);report={'status':'attempt2_single_CPU_started','accepted':False,'assets_written':False,'CDT_invoked':False,'input_sha256':sha(a.input),'script_sha256':sha(Path(__file__)),'failures':[]}
 assert not(a.output/'completion.validation.json').exists(),'Refuse overwrite frozen attempt2 CPU'
 def require(ok,code,detail):
  if not ok:raise ValueError(code+': '+str(detail))
 try:
  for path,h in p['frozen_dependencies_sha256'].items():require(sha(root/path)==h,'STALE_DEPENDENCY',path)
  ns=load_frozen_field(Path(__file__).with_name('probe_mouth_monotone_108.py'),b/'source-mouth-alignment.validation.json');old=ns['old'];st=ns['st'];data=ns['data'];canvas=ns['canvas'];env=ns['env'];q=[canvas(v)for v in st]
  top=CubicHermiteSpline(np.array(p['top_curve']['knots'])[:,0],np.array(p['top_curve']['knots'])[:,1],p['top_curve']['slopes']);chin=CubicHermiteSpline(np.array(p['chin_curve']['knots'])[:,0],np.array(p['chin_curve']['knots'])[:,1],p['chin_curve']['slopes']);rt=CubicHermiteSpline(p['upper_R_target']['X'],p['upper_R_target']['Y'],p['upper_R_target']['derivatives']);lt=CubicHermiteSpline(p['lower_L_target']['X'],p['lower_L_target']['Y'],p['lower_L_target']['derivatives']);head=p['top_curve']['knots'][0][0];chin_on=p['chin_curve']['knots'][0][0];end=p['collapsed_tip']['X'];bs=p['lower_front_blend']['start'];be=p['lower_front_blend']['end'];rjoin=p['upper_R_target']['X'][0];ljoin=p['lower_L_target']['X'][0]
  tipids=np.array(ns['alignment']['actual_tips']['upper']['vertex_ids']);require(len(tipids)==1,'COLLAPSED_ROLE','single frozen upper tip required');collapsed_xy=q[0][tipids[0]].copy();report['collapsed_point_role']={'skin_actual_id':int(tipids[0]),'stage1_exact_canvas_xy':collapsed_xy.tolist(),'target_Y':401.5,'exception':'only this exact frozen XY identity, no coordinateepsilon/wholechart clamp'}
  def values(X):
   U,R,L,B=[c(X)for c in env];Ut=U.copy();Bt=B.copy();Rt=R.copy();Lt=L.copy();Ut[X>head]=top(X[X>head]);Bt[X>chin_on]=chin(X[X>chin_on]);Rt[X>rjoin]=rt(X[X>rjoin]);Lt[X>ljoin]=lt(X[X>ljoin]);z=np.clip((X-bs)/(be-bs),0,1);beta=z**3*(10-15*z+6*z*z);Leff=L+beta*(Lt-L);return U,R,L,B,Ut,Rt,Lt,Bt,beta,Leff
  def H(Y,aa,bb,AA,BB):
   span=bb-aa;require(np.all(span>0),'NONPOSITIVE_ACTIVE_INPUT_SPAN',float(span.min()));rho=(BB-AA)/span;require(np.all(rho>1/3),'NONMONOTONE_ACTIVE_HERMITE_RHO',float(rho.min()));t=(Y-aa)/span;h01=t*t*(3-2*t);h00=1-h01;out=Y+(AA-aa)*h00+(BB-bb)*h01;dy=1+6*t*(1-t)*(rho-1);return out,dy
  def evaluate(points):
   X,Y=np.asarray(points).T;out=np.asarray(points).copy();dy=np.ones(len(X));collapsed=np.all(np.asarray(points)==collapsed_xy,axis=1);active=(X>chin_on)&(~collapsed)
   out[collapsed,1]=401.5
   if not active.any():return out,dy
   idx=np.flatnonzero(active);x=X[idx];y=Y[idx];U,R,L,B,Ut,Rt,Lt,Bt,beta,Leff=values(x);ny=y.copy();dd=np.ones(len(x));above=y<=U;upper=(y>U)&(y<=R);gap=(y>R)&(y<L);lower=(y>=L)&(y<B);below=y>=B
   require(np.all((R<L)&(L<B)),'OLD_GAP_LOWER_ORDER','R<L<B');ny[above]=y[above]+(Ut[above]-U[above]);ny[below]=y[below]+(Bt[below]-B[below])
   # Frozen displacement Hermite makes identity analytical, not a mask repair.
   for m,aa,bb,AA,BB in [(upper,U,R,Ut,Rt),(gap,R,L,Rt,Leff)]:
    if m.any():ny[m],dd[m]=H(y[m],aa[m],bb[m],AA[m],BB[m])
   if lower.any():
    ii=np.flatnonzero(lower);v=y[ii];span=B[ii]-L[ii];require(np.all(span>0),'LOWER_SPAN',float(span.min()));t=(v-L[ii])/span;qq=t**3*(10-15*t+6*t*t);dq=30*t*t*(1-t)**2;rear=v.copy();rd=np.ones(len(ii));front=v.copy();fd=np.ones(len(ii));use_rear=beta[ii]<1;use_front=beta[ii]>0
    rear[use_rear]=v[use_rear]+(Bt[ii][use_rear]-B[ii][use_rear])*qq[use_rear];rd[use_rear]=1+(Bt[ii][use_rear]-B[ii][use_rear])/span[use_rear]*dq[use_rear]
    if use_front.any():front[use_front],fd[use_front]=H(v[use_front],L[ii][use_front],B[ii][use_front],Lt[ii][use_front],Bt[ii][use_front])
    require(np.all(rd[use_rear]>0),'REAR_NONPOSITIVE_DERIVATIVE',float(rd[use_rear].min())if use_rear.any()else None);ny[ii]=(1-beta[ii])*rear+beta[ii]*front;dd[ii]=(1-beta[ii])*rd+beta[ii]*fd
   require(np.all(dd>0),'NONPOSITIVE_USED_DERIVATIVE',float(dd.min()));out[idx,1]=ny;dy[idx]=dd;return out,dy
  # Cover actual used X ranges, not only the source knots. No interval-proof
  # claim: finite0.025nativepixel grid+all actualX/envelopebreaks/targetknots.
  xs=np.unique(np.r_[np.arange(chin_on,end,.025),*[z[z[:,0]>chin_on,0]for z in q],*[e.x[(e.x>chin_on)&(e.x<end)]for e in env],p['upper_R_target']['X'],p['lower_L_target']['X']]);xs=xs[(xs>chin_on)&(xs<end)&(xs!=collapsed_xy[0])];U,R,L,B,Ut,Rt,Lt,Bt,beta,Leff=values(xs);tests={}
  for label,oldspan,targetspan,mask in [('UR',R-U,Rt-Ut,np.ones(len(xs),bool)),('RL',L-R,Leff-Rt,np.ones(len(xs),bool)),('frontLB',B-L,Bt-Lt,beta>0)]:
   require(np.all(oldspan[mask]>0),'COVERAGE_INPUT_SPAN_'+label,float(oldspan[mask].min()));rho=targetspan[mask]/oldspan[mask];tests[label]={'min_old_span':float(oldspan[mask].min()),'min_target_span':float(targetspan[mask].min()),'min_rho':float(rho.min()),'samples':int(mask.sum())};require(np.all(rho>1/3),'COVERAGE_RHO_'+label,tests[label])
  rearused=beta<1;rear_min=1+1.875*np.minimum(Bt-B,0)/(B-L);require(np.all(rear_min[rearused]>0),'COVERAGE_REAR_DERIVATIVE',float(rear_min[rearused].min()));report['span_derivative_coverage']={'sampled_X_count':len(xs),'range':[float(xs.min()),float(xs.max())],'grid_native_pixels':.025,'actual_X_and_PCHIP_breaks_included':True,'charts':tests,'rear_min_used_dYdY':float(rear_min[rearused].min()),'limit':'Finite interval coverage, not analytic allX proof. Collapsedendpointexcluded onlyatX2019.5; nofullJacclaim.'}
  mapped=[];dyall=[]
  for v,qq in zip(st,q):
   mm,dy=evaluate(qq);vv=v.copy();on=mm[:,1]!=qq[:,1];vv[on,1]=(371-mm[on,1])/2024;mapped.append(vv.astype(np.float32).astype(float));dyall.extend(dy.tolist())
  # No field editback mask. Freeze exact original eye triangles/corners/lookup.
  eye=p['base_eye_contract'];vid=np.array(eye['vertex_ids'],int);ef=np.array(eye['triangle_indices'],int);require(len(vid)==246 and len(ef)==408,'EYE_SCOPE','246/408');require(np.array_equal(mapped[0][vid],np.asarray(old[0],np.float32)[vid]),'EYE_POS_CHANGED',vid.tolist());src=Path(json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text())['raw_glb']);gd,gb=read_glb(src);body=next(m for m in gd['meshes']if m.get('name')=='Closed_body')['primitives']
  for group in eye['raw_corner_groups']:
   for side in group['raw_sides']:
    pr=body[side['surface']];ids=np.array(side['raw_vertex_ids'],int)
    for k in ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']:require(np.array_equal(accessor(gd,gb,pr['attributes'][k])[ids],np.asarray(side[k],dtype=accessor(gd,gb,pr['attributes'][k]).dtype)),'EYE_FROZEN_RAW_CORNER_CHANGED',k)
  report['eye408tri246']={'POS_exact_without_mask':True,'original_NORMAL_UV_JW_corner_lookup_values_unchanged_CPU':True,'triangles':408,'vertices':246,'runtime_lookup_reimport':'notgenerated; noGPU/changedVERTEX_IDclaim'}
  # Existing fixed topology: no new CDT invocation or parameter search.
  skin=np.array(data[0]['indices']).reshape(-1,3);oral=np.array(data[1]['indices']).reshape(-1,3);sapi=json.loads((b/'cpu-upper-skin-cdt/cdt-api-result.validation.json').read_text());scfg=json.loads(Path(sapi['input']).read_text());keep=np.ones(len(skin),bool);newskin=[];skinpoints=[]
  for sh,rr in zip(scfg['sheets'],sapi['sheets']):
   ids=np.array([x['actual_vertex_id']for x in sh['points']]);keep[sh['old_skin_triangle_ids']]=False;newskin.append(ids[np.array(rr['input_origin_faces'])]);skinpoints.extend(ids.tolist())
  require(not set(np.array(eye['triangle_ids']).tolist())&set(np.flatnonzero(~keep).tolist()),'EYE_TRIANGLE_CONNECTION_CHANGED','CDTselection');skin=np.r_[skin[keep],*newskin];ocfg=json.loads((b/'cpu-upper-cdt/cdt-input-frozen.validation.json').read_text());oapi=json.loads((b/'cpu-upper-cdt/cdt-api-result.validation.json').read_text());ok=np.ones(len(oral),bool);ok[ocfg['old_oral_triangle_ids']]=False;opoints=np.array([x['oral_actual_vertex_id']for x in ocfg['points']]);oral=np.r_[oral[ok],opoints[np.array(oapi['input_origin_faces'])]];n=len(mapped[0]);faces=np.r_[skin,oral+n];vertices=np.r_[*mapped];changed=np.r_[np.any(mapped[0]!=np.asarray(old[0],np.float32),axis=1),np.any(mapped[1]!=np.asarray(old[1],np.float32),axis=1)];changed[np.array(skinpoints)]=True;changed[n+opoints]=True
  normal=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]]);report['zero_3D_area_faces']=int((np.linalg.norm(normal,axis=1)==0).sum());require(report['zero_3D_area_faces']==0,'ZERO_3D_AREA',report['zero_3D_area_faces'])
  def boundaries(v,ff):
   keys=[tuple(x)for x in v];ct=Counter(tuple(sorted((keys[i],keys[j])))for f in ff for i,j in zip(f,np.roll(f,-1)));direct={(keys[i],keys[j])for f in ff for i,j in zip(f,np.roll(f,-1))if ct[tuple(sorted((keys[i],keys[j]))) ]==1};return direct,ct
  sb,ss=boundaries(mapped[0],skin);ob,oo=boundaries(mapped[1],oral);closed=sb=={(z,x)for x,z in ob};_,allct=boundaries(vertices,faces);report['interface397']={'count':len(sb),'directed_opposite':closed,'all_geometric_edges_incident2':all(k==2 for k in allct.values())};require(closed and len(sb)==397 and report['interface397']['all_geometric_edges_incident2'],'CLOSURE397',report['interface397'])
  # Every original endpoint ID and semantic region disclosed; no640/704exact claim.
  rc=p['old_rim_contract_change'];ep=np.array(rc['original_endpoint_rest_xyz']);eq=canvas(ep);sm=ns['stage1'](eq)[0];fm,_=evaluate(sm);ev=ep.copy();on=eq[:,0]>1988;ev[on,0]=sm[on,0]/2024-.5;ev[on,1]=(371-sm[on,1])/2024;on2=fm[:,1]!=sm[:,1];ev[on2,1]=(371-fm[on2,1])/2024;written=canvas(ev.astype(np.float32));original=canvas(ep.astype(np.float32));dist=np.linalg.norm(written-original,axis=1);unknown=eq[:,0]<=rjoin;maxrear=float(dist[unknown].max());endpoint=[]
  for i,(before,after,dd)in enumerate(zip(original,written,dist)):
   label='posterior_unknown'if before[0]<=rjoin else 'engineering_or_dark_unknown'if before[0]>2010.5 or 1995.5<before[0]<2000.5 else'frozen_source_target_region'
   endpoint.append({'sample_id':i,'skin_actual_id':int(rc['all_endpoint_skin_actual_ids'][i]),'before_canvas':before.tolist(),'after_canvas':after.tolist(),'displacement_pixels':float(dd),'region':label})
  report['rear_endpoint_displacements']={'all_samples':endpoint,'unknown_X_le1985_5_max_pixels':maxrear,'strict_limit_pixels':rc['unknown_X_le1985_5_strict_max_displacement_native_pixels'],'sourceUV_JW_unchanged':True};require(maxrear<rc['unknown_X_le1985_5_strict_max_displacement_native_pixels'],'UNKNOWN_REAR_DISPLACEMENT',maxrear)
  # Actual finite PL lip envelopes at declared known source nodes; not merely
  # target-curve knot agreement.
  stageq=q[0];vv=stageq[:,1]-(452.62-1.02*742/2024*(stageq[:,0]-1894.464));upperfaces=skin[vv[skin].max(1)<0];lowerfaces=skin[vv[skin].min(1)>0]
  def actual_y(ff,sx,upper):
   tri=mapped[0][ff];edges=np.r_[tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]];qq=canvas(edges.reshape(-1,3)).reshape(-1,2,2);dx=qq[:,1,0]-qq[:,0,0];good=dx!=0;t=np.zeros(len(dx));t[good]=(sx-qq[good,0,0])/dx[good];sel=good&(t>=0)&(t<=1);ys=qq[sel,0,1]+t[sel]*(qq[sel,1,1]-qq[sel,0,1]);flat=(~good)&(qq[:,0,0]==sx)
   if flat.any():ys=np.r_[ys,qq[flat,:,1].ravel()]
   require(len(ys)>0,'NO_LIP_PLANE_HIT',sx);return float(ys.max()if upper else ys.min())
  known=[]
  for upper,xx,yy in [(True,[1990.5,1995.5,2000.5,2005.5,2010.5],[413,413,407,407,407]),(False,[2002.5,2005.5,2010.5,2015.5,2018.5],[418,419,419,423,425])]:
   for x,y in zip(xx,yy):val=actual_y(upperfaces if upper else lowerfaces,x,upper);known.append({'lip':'upper_gold'if upper else'lower_source_run','X':x,'source_Y':y,'actual_PL_Y':val,'error_pixels':abs(val-y)})
  report['source_known_lip_nodes']=known;maxerr=max(z['error_pixels']for z in known);require(maxerr<=p['semantic_lip_actual_canvas_tolerance_native_pixels'],'SOURCE_KNOWN_LIP_ERROR',maxerr)
  cr=crossing(vertices,faces,changed);report['actual_f32_global_crossing']=cr;require(not cr['proper_crossings']and not cr['coplanar_positive_area_overlap_pairs'],'FINITE_TRIANGLE_INTERSECTION',{'cross':cr['proper_crossings'],'overlap':cr['coplanar_positive_area_overlap_pairs']});report['all_new_topology_selected']={'skin209':bool(changed[skin[-209:]].any(1).all()),'oral97':bool(changed[oral[-97:]+n].any(1).all())};report['minimum_actual_vertex_dYdY']=min(dyall);report['cpu_gate_passed']=True;report['status']='attempt2_CPU_pass_pending_independent_review';report['next_action']='independent_review_no_asset_permission'
 except Exception as exc:
  report['cpu_gate_passed']=False;report['status']='attempt2_CPU_failed_stop';report['next_action']='fix_input_no_retune';report['failures'].append({'kind':'validation','code':type(exc).__name__,'message':str(exc)})
 (a.output/'completion.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k in ['status','cpu_gate_passed','failures','span_derivative_coverage','interface397','minimum_actual_vertex_dYdY','source_known_lip_nodes']}));raise SystemExit(0 if report['cpu_gate_passed']else 1)
if __name__=='__main__':main()
