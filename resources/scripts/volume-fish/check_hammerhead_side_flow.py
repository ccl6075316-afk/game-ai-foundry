"""Measure an actual finite side envelope against its declared artistic curve."""
from pathlib import Path
import argparse,json,hashlib,math
import numpy as np
from check_project_art_tail_section import mesh
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def section(tri,x):
 values=[]
 for i,j in [(0,1),(1,2),(2,0)]:
  a,b=tri[:,i],tri[:,j];sel=(a[:,0]-x)*(b[:,0]-x)<0
  if sel.any():values.extend((a[sel]+(b[sel]-a[sel])*((x-a[sel,0])/(b[sel,0]-a[sel,0]))[:,None])[:,2])
 assert values,'Empty finite body section';return min(values),max(values)
def check(model,plan,tolerance=.0015):
 c=json.loads(plan.read_text());baseline=model.parent.parent/c['baseline']/'fish.glb';assert sha(baseline)==c['baseline_model_sha256'],'Stale previous finite envelope';tri=mesh(model,'Reference_head_body');a,b=c['interval'];t=np.linspace(a,b,311);s=(t-a)/(b-a)
 target=sum(math.comb(5,k)*(1-s)**(5-k)*s**k*v for k,v in enumerate(c['bernstein_coefficients']))
 actual=np.array([section(tri,c['nose']-x*c['L'])[1]/c['L']for x in t]);old=np.interp(t,c['samples_t'],c['original_top']);error=abs(actual-target);old_error=abs(old-target)
 def angles(z):return float(abs(np.diff(np.arctan(np.diff(z)/np.diff(t)))).max()*180/math.pi)
 result=dict(ok=bool(error.max()<=tolerance and error.max()<old_error.max()*.35),kind='actual_finite_upper_side_flow_correspondence',model_sha256=sha(model),plan_sha256=sha(plan),tolerance_over_display_length=tolerance,maximum_current_error_mm=float(error.max()*c['L']*1000),maximum_previous_error_mm=float(old_error.max()*c['L']*1000),maximum_sampled_current_turn_degrees=angles(actual),maximum_sampled_previous_turn_degrees=angles(old),samples=[dict(t=float(x),target_top_over_length=float(y),actual_top_over_length=float(z),previous_top_over_length=float(o),error_mm=float(e*c['L']*1000))for x,y,z,o,e in zip(t,target,actual,old,error)],checker_sha256=sha(Path(__file__)),negative_control=dict(path=str(baseline),sha256=sha(baseline),same_target_would_fail_tolerance=bool(old_error.max()>tolerance)),scope='Finite low-poly silhouette correspondence to an explicit artistic continuity target; old actual R26 is the negative comparison. No biological or continuous surface smoothness claim. Tolerance fixed before this measurement.')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=check(a.model,a.plan);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='samples'}));raise SystemExit(0 if r['ok']else 1)
