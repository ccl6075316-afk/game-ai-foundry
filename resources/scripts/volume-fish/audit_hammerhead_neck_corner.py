"""Finite top-view rear-edge turn; declared engineering span, not anatomy metric."""
import argparse,json,hashlib,math
from pathlib import Path
import numpy as np
from portable.glb_io import read_glb,arrays

def load_body(path):
 d,b=read_glb(path);vs=[];fs=[];off=0
 for n in d['nodes']:
  if n.get('name')!='Reference_head_body':continue
  for p in d['meshes'][n['mesh']]['primitives']:
   v=arrays(d,b,p['attributes']['POSITION']).astype(float);f=arrays(d,b,p['indices']).reshape(-1,3);vs.append(v);fs.append(f+off);off+=len(v)
 return np.concatenate(vs),np.concatenate(fs)
def cut_intervals(v,f,z):
 t=v[f];a=t;b=np.roll(t,-1,axis=1);k=(a[:,:,2]-z)*(b[:,:,2]-z)<0;rows=[]
 for i in np.flatnonzero((t[:,:,2].min(1)<=z+1e-9)&(t[:,:,2].max(1)>=z-1e-9)):
  hits=[]
  for j in range(3):
   x,y=a[i,j],b[i,j]
   if abs(x[2]-z)<1e-9:hits.append(float(x[0]))
   if k[i,j]:hits.append(float(x[0]+(z-x[2])/(y[2]-x[2])*(y[0]-x[0])))
  if len(hits)>=2:rows.append([min(hits),max(hits)])
 merged=[]
 for a,b in sorted(rows):
  if merged and a<=merged[-1][1]+1e-7:merged[-1][1]=max(merged[-1][1],b)
  else:merged.append([a,b])
 return merged
def measure(path,half=.7196613358419568/2):
 v,f=load_body(path);result=[]
 for side in [-1,1]:
  rows=[]
  for fraction in np.linspace(.4,.65,26):
   y=side*half*fraction;ints=cut_intervals(v,f,-y);assert ints,(side,y);front=max(ints,key=lambda a:a[1]);assert front[1]>.75,(side,y,front);rows.append(dict(span_fraction=float(fraction),absolute_y_m=abs(y),rear_x_m=front[0],front_x_m=front[1],intervals=ints,isolated_head=len(ints)>1))
  slope,intercept=np.polyfit([r['absolute_y_m']for r in rows],[r['rear_x_m']for r in rows],1);angle=math.degrees(math.atan2(1,abs(slope)));result.append(dict(side=side,angle_degrees=angle,fit_dx_dy=float(slope),fit_intercept_m=float(intercept),within_user_approximate_range=bool(60<=angle<=70),rows=rows))
 return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--model',type=Path,required=True);a.add_argument('--baseline',type=Path);a.add_argument('--output',type=Path,required=True);q=a.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r=dict(kind='finite_top_view_inner_trailing_edge_turn',model_sha256=sha(q.model),candidate=measure(q.model),scope='Posterior cephalofoil edge segment across40–65% half-span, least-squares tangent versus longitudinal axis, original world rest coordinates. Engineering comparison to user approximate60–70deg; not a calibrated photograph or anatomical joint angle.',formal_acceptance=False)
 if q.baseline:r.update(baseline_sha256=sha(q.baseline),baseline=measure(q.baseline))
 q.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:[round(x['angle_degrees'],2)for x in v]for k,v in r.items()if k in ['candidate','baseline']}))
