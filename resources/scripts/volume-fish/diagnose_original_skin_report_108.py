#!/usr/bin/env python3
"""Read-only report after the one failed108CPU. Reuses unchanged field AST;
never rerunsCPU gate or emits assets/changes frozen report/parameters/CDT."""
import argparse,ast,json,types,hashlib
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True,help='failedCPU completion');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();report=json.loads(args.input.read_text());root=Path(__file__).resolve().parents[3];b=args.input.parent.parent;script=Path(__file__).with_name('probe_mouth_attempt2_108.py');require_hash=report['frozen_field_sha256'];assert sha(script)==require_hash;params=b/'phase2-attempt2-parameters.validation.json';assert sha(params)==report['input_sha256'];p=json.loads(params.read_text());tree=ast.parse(script.read_text());n={'__file__':str(script),'__name__':'attempt2_report_only','root':root,'b':b,'p':p,'report':{}}
 imports=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom))or isinstance(node,ast.FunctionDef)and node.name=='sha'];exec(compile(ast.Module(body=imports,type_ignores=[]),str(script),'exec'),n);mainast=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='main');req=next(x for x in mainast.body if isinstance(x,ast.FunctionDef)and x.name=='require');exec(compile(ast.Module(body=[req],type_ignores=[]),str(script),'exec'),n);trybody=next(x for x in mainast.body if isinstance(x,ast.Try)).body;prefix=[]
 for node in trybody:
  prefix.append(node)
  if isinstance(node,ast.FunctionDef)and node.name=='evaluate':break
 exec(compile(ast.Module(body=prefix,type_ignores=[]),str(script),'exec'),n)
 evaluate=n['evaluate'];canvas=n['canvas'];old=n['old'];st=n['st'];data=n['data'];dyrecords=[];dxrecords=[];eps=1e-4;maximum=0.;changed_data=[]
 for surface,q in enumerate(n['q']):
  mm,dy=evaluate(q);notcollapsed=~np.all(q==n['collapsed_xy'],axis=1);inside=(q[:,0]>n['chin_on']+eps)&(q[:,0]<n['end']-eps)&notcollapsed;probe=q[inside];dx=(evaluate(probe+[eps,0])[0][:,1]-evaluate(probe-[eps,0])[0][:,1])/(2*eps);dyrecords.append(dict(surface=surface,min_dYdY=float(dy[notcollapsed].min()),max_used_dYdY=float(dy[notcollapsed].max()),maximum_actual_vertex_id=int(np.flatnonzero(notcollapsed)[np.argmax(dy[notcollapsed])]),collapsed_excluded=int((~notcollapsed).sum())));dxrecords.append(dict(surface=surface,samples=len(dx),epsilon_native_pixels=eps,finite_dYdX_min=float(dx.min()),max=float(dx.max()),max_abs=float(abs(dx).max())));v=st[surface].copy();on=mm[:,1]!=q[:,1];v[on,1]=(371-mm[on,1])/2024;changed_data.append(v.astype(np.float32).astype(float))
 columns=[]
 for x in [1920.5,1921.,1922.1949]:
  X=np.array([x]);U,R,L,B,Ut,Rt,Lt,Bt,beta,Leff=n['values'](X);t=np.linspace(0,1,101);q=np.c_[np.full(len(t),x),L[0]+t*(B[0]-L[0])];m,d=evaluate(q);dx=(evaluate(q+[eps,0])[0][:,1]-evaluate(q-[eps,0])[0][:,1])/(2*eps);columns.append(dict(X=x,L=float(L[0]),B=float(B[0]),actual_anchor_equals_L=float(L[0]),span=float(B[0]-L[0]),Btarget=float(Bt[0]),deltaB=float(Bt[0]-B[0]),beta=float(beta[0]),theoretical_rear_peak_dYdY=float(1+1.875*(Bt[0]-B[0])/(B[0]-L[0])),sampled_min_dYdY=float(d.min()),sampled_max_dYdY=float(d.max()),finite_dYdX_min=float(dx.min()),finite_dYdX_max=float(dx.max()),finite_epsilon=eps))
 # Reconstruct the exact retained connectivity, no CDT or field mutation.
 skin=np.array(data[0]['indices']).reshape(-1,3);ff=skin;kept_count=len(skin);origin=[];v=n['q'][0][:,1]-(452.62-1.02*742/2024*(n['q'][0][:,0]-1894.464));uppermask=v[ff].max(1)<0;upper=ff[uppermask];upper_fullids=np.flatnonzero(uppermask)
 def plane_max(sx):
  best=None
  for local,face in enumerate(upper):
   q=canvas(changed_data[0][face]);
   if not(q[:,0].min()<=sx<=q[:,0].max()):continue
   for i,j in [(0,1),(1,2),(2,0)]:
    if q[i,0]==q[j,0]:continue
    t=(sx-q[i,0])/(q[j,0]-q[i,0])
    if 0<=t<=1:
     y=q[i,1]+t*(q[j,1]-q[i,1]);
     if best is None or y>best['Y']:best=dict(Y=float(y),combined_skin_face=int(upper_fullids[local]),skin_actual_vertex_ids=face.tolist(),edge_vertex_ids=[int(face[i]),int(face[j])],edge_parameter=float(t),actual_f32_canvas=q.tolist(),stage1_canvas=n['q'][0][face].tolist(),new_topology=bool(upper_fullids[local]>=kept_count),new_patch_origin=origin[int(upper_fullids[local])-kept_count]if upper_fullids[local]>=kept_count else None)
  return best
 hit=plane_max(2000.5);edgeids=hit['edge_vertex_ids'];stageedge=n['q'][0][edgeids];mappededge=canvas(changed_data[0][edgeids]);curvature=[]
 for name,t in [('Stage1_edge_midpoint',.5),('source_X2000_5',hit['edge_parameter'])]:
  stagep=(1-t)*stageedge[0]+t*stageedge[1];exact=evaluate(stagep[None])[0][0];linear=(1-t)*mappededge[0]+t*mappededge[1];curvature.append(dict(role=name,t=float(t),stage1_native_xy=stagep.tolist(),field_of_stage1_edge_point_native_xy=exact.tolist(),linear_final_f32_edge_native_xy=linear.tolist(),linear_minus_exact_field_Y=float(linear[1]-exact[1]),frozen_Rt_Y=float(n['rt'](stagep[0])),linear_minus_frozen_Rt_Y=float(linear[1]-n['rt'](stagep[0])),interpretation='Finite edge interpolation versus nonlinear frozen field; no new point/split is made.'))
 hit['edge_stage1_xyz']=n['st'][0][edgeids].tolist();hit['edge_original_xyz']=n['old'][0][edgeids].tolist();hit['edge_mapped_f32_xyz']=changed_data[0][edgeids].tolist();hit['curvature_attribution']=curvature;curve=[]
 for x in np.arange(1985.5,2019.5,.1):
  z=plane_max(float(x));curve.append([float(x),z['Y']])
 yy=np.array(curve);diff=np.diff(yy[:,1]);opposite=np.flatnonzero(diff>1e-6);rder=n['rt'].derivative()(yy[:,0]);out=dict(status='report_only_original_skin_CPU_failed_no_retune',original_completion_sha256=sha(args.input),field_script_sha256=sha(script),parameters_sha256=sha(params),used_derivative_vertex_statistics=dyrecords,finite_dYdX_vertex_statistics=dxrecords,rootcause_columns=columns,failed_knownlip2000_5_PL_contributor=hit,front_lip_curve=dict(samples=yy.tolist(),positive_forward_Y_steps_count=len(opposite),maximum_positive_step=float(diff.max()),positive_step_intervals=yy[opposite].tolist(),Rt_derivative_max=float(rder.max()),Rt_derivative_min=float(rder.min()),meaning='Rt is frozenmonotone; actualPL projectedlip may have additional reverseextrema from finite connectivity. epsilon1e-6 here only describes monotonic curve noise, not candidateacceptance.'),limits=['Diagnostic only: same failedfield, no changes to target/field/tolerance/topology and no second CPU acceptance run.','Finite dYdX sample difference is not analytic or fullJac proof; collapsed endpoint excluded.','Original-skin CPU failedsource1px gate remains failed. Separately authorized global readonly diagnostic is reported elsewhere, never a Phase3pass.'])
 args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['used_derivative_vertex_statistics','rootcause_columns','failed_knownlip2000_5_PL_contributor']}))
if __name__=='__main__':main()
