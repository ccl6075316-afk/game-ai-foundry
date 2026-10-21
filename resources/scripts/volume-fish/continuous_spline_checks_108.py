#!/usr/bin/env python3
"""108 attempt3 reference-polynomial span + emittedf32 PL band; no models saved."""
from fractions import Fraction as F
from collections import Counter
import numpy as np
from continuous_lip_exact_108 import Q,add,scale,mul,compose,hermite,positive,val,trim

def piece(curve,lo,hi):
 k=int(np.searchsorted(curve.x,(float(lo)+float(hi))/2,side='right')-1);k=min(max(0,k),len(curve.x)-2);a=Q(curve.x[k]);b=Q(curve.x[k+1]);w=b-a;y0=Q(curve(float(a)));y1=Q(curve(float(b)));m0=Q(curve.derivative()(float(a)));m1=Q(curve.derivative()(float(b)));p=hermite(y0,y1,m0,m1,w);return compose(p,[(lo-a)/w,(hi-lo)/w])
def certify_spans(ns,rt,report):
 # Exact rational Hermite reference of frozen knot values/derivatives. Runtime
 # remains scipy float64; numerical difference is explicitly measured below.
 U,R,L,B=ns['env'];top=ns['top'];chin=ns['chin'];lt=ns['lt'];head=Q(ns['head']);chin_on=Q(ns['chin_on']);join=F(1972);ljoin=Q(ns['ljoin']);bs=Q(ns['bs']);be=Q(ns['be']);end=F(4039,2);breaks=sorted({Q(x)for c in [U,R,L,B,top,chin,lt,rt]for x in c.x if float(chin_on)<=x<=float(end)}|{chin_on,head,join,ljoin,bs,be,end});records=[];methods=Counter();maxdiff=0.;lowest={};report.update(status='in_progress',reference='Exact rational cubicHermite using frozen float64 knot values and derivatives; newRt exact rational C2clampedcubic pieces. A reference function sign certificate, not a proof of every IEEE754 execution or endpointJacobian.',intervals=records)
 for i,(lo,hi)in enumerate(zip(breaks,breaks[1:])):
  if hi<=chin_on or lo>=end:continue
  old=[piece(c,lo,hi)for c in [U,R,L,B]];u,r,l,b=old;ut=piece(top,lo,hi)if lo>=head else u;bt=piece(chin,lo,hi)if lo>=chin_on else b;rr=rt.exact_piece(lo,hi)if lo>=join else r;ll=piece(lt,lo,hi)if lo>=ljoin else l
  if hi<=bs:beta=[F(0)]
  elif lo>=be:beta=[F(1)]
  else:
   z=[(lo-bs)/(be-bs),(hi-lo)/(be-bs)];z2=mul(z,z);z3=mul(z2,z);beta=mul(z3,add([F(10)],add(scale(z,-15),scale(z2,6))))
  leff=add(l,mul(beta,add(ll,scale(l,-1))));oldspans=[add(r,scale(u,-1)),add(l,scale(r,-1)),add(b,scale(l,-1))];targetupper=add(rr,scale(ut,-1));targetgap=add(leff,scale(rr,-1));checks={'old_UR':oldspans[0],'old_RL':oldspans[1],'old_LB':oldspans[2],'target_UR':targetupper,'target_RL':targetgap,'3targetUR_minus_oldUR':add(scale(targetupper,3),scale(oldspans[0],-1)),'3targetRL_minus_oldRL':add(scale(targetgap,3),scale(oldspans[1],-1))}
  if hi>bs:checks['target_frontLB']=add(bt,scale(ll,-1));checks['3target_frontLB_minus_oldLB']=add(scale(checks['target_frontLB'],3),scale(oldspans[2],-1))
  if lo<be:checks['rear_lower_derivative_numerator']=add(oldspans[2],scale(add(bt,scale(b,-1)),F(15,8)))
  entry=dict(index=i,X=[float(lo),float(hi)],checks={})
  for name,poly in checks.items():
   collapsed=hi==end and name in ['old_UR','target_UR','3targetUR_minus_oldUR'];ok,detail=positive(poly,allow_right_zero=collapsed);entry['checks'][name]=dict(passed=ok,**detail);methods[detail['method']]+=1
   if not ok:records.append(entry);report.update(status='failed_stop',failed_interval=entry,method_counts=dict(methods));raise ValueError('CONTINUOUS_TARGET_SPAN_OR_RHO_CERTIFICATE_FAILED:'+name)
  for t in [F(1,4),F(1,2),F(3,4)]:
   x=float(lo+(hi-lo)*t)
   for poly,c in zip(old,[U,R,L,B]):maxdiff=max(maxdiff,abs(float(val(poly,t))-float(c(x))))
  records.append(entry)
 report.update(status='reference_all_open_intervals_certified',method_counts=dict(methods),interval_count=len(records),maximum_reference_vs_frozen_PCHIP_float64_quarter_sample_native_px=maxdiff,collapsed_exception='Only X2019.5 collapsed upper role. No endpointJacobian/fullfloatingexecution claim; targetfront/gap/otherbranches are still checked.',real_root_statement='Positive Bernstein coefficients exclude ALL open-interval realroots; remaining signs use exact rational Sturm ALLrealroot count. Not grid-only.')

def source_band_check(mapped,skin,stageq,canvas):
 vv=stageq[:,1]-(452.62-1.02*742/2024*(stageq[:,0]-1894.464));ff=skin[vv[skin].max(1)<0];allids=set(tuple(sorted((int(i),int(j))))for f in ff for i,j in zip(f,np.roll(f,-1)));points=canvas(mapped);segments=[];vertical=[]
 for i,j in sorted(allids):
  p=[Q(v)for v in points[i]];q=[Q(v)for v in points[j]]
  if max(p[0],q[0])<1985 or min(p[0],q[0])>2012:continue
  if p[0]==q[0]:vertical.append((p[0],max(p[1],q[1]),[i,j]));continue
  slope=(q[1]-p[1])/(q[0]-p[0]);intercept=p[1]-slope*p[0];segments.append((min(p[0],q[0]),max(p[0],q[0]),slope,intercept,[i,j]))
 records=[]
 for lo,hi,low,high,role in [(1985,1998,407,413,'high_rear'),(2000,2010,402,407,'high_front'),(2010,2012,402,407,'medium_front')]:
  use=[s for s in segments if s[0]<=hi and s[1]>=lo];xs={F(v)for v in range(lo,hi+1)}
  for a,b,m,c,ids in use:xs.update([max(a,F(lo)),min(b,F(hi))])
  for i,s in enumerate(use):
   for t in use[i+1:]:
    if s[2]==t[2]:continue
    x=(t[3]-s[3])/(s[2]-t[2])
    if max(s[0],t[0],F(lo))<=x<=min(s[1],t[1],F(hi)):xs.add(x)
  xs.update(x for x,y,ids in vertical if lo<=x<=hi);samples=[];worst=None
  for x in sorted(xs):
   ys=[(m*x+c,ids)for a,b,m,c,ids in use if a<=x<=b]+[(y,ids)for xx,y,ids in vertical if xx==x]
   if not ys:raise ValueError('NO_ACTUAL_FINITE_PL_BAND_ENVELOPE:'+str(x))
   y,ids=max(ys,key=lambda k:k[0]);error=max(F(low)-y,y-F(high),F(0));row=dict(X=float(x),actual_PL_Y=float(y),raw_or_actual_edge_ids=ids,violation_native_px=float(error));samples.append(row)
   if worst is None or error>worst[0]:worst=(error,row)
  records.append(dict(role=role,X_closed_interval=[lo,hi],band_cell_Y=[low,high],envelope_extrema_test_count=len(samples),minimum_actual_PL_Y=min(s['actual_PL_Y']for s in samples),maximum_actual_PL_Y=max(s['actual_PL_Y']for s in samples),worst=worst[1],passed=worst[0]==0,samples=samples))
 return dict(method='Exact Fraction of actualfloat32-derived native XY; every clippededge endpoint/cellboundary/pairwise lineintersection/verticaledge checked, covering all finite PL envelope extrema on complete knowncell intervals.',total_segments=len(segments),records=records,passed=all(r['passed']for r in records))
