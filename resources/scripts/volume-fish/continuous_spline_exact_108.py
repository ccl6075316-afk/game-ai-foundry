#!/usr/bin/env python3
"""108 attempt3 ONLY: six fixed knots/four internal Ys exact bounded convex QP."""
from fractions import Fraction as F
from itertools import combinations
from math import comb
from pathlib import Path
import json
import numpy as np
from continuous_lip_exact_108 import Q,val,der,compose,add,scale,mul,nroots

def linear_solve(A,b):
 n=len(b);m=[list(row)+[x]for row,x in zip(A,b)]
 for i in range(n):
  pivot=next((j for j in range(i,n)if m[j][i]!=0),None)
  if pivot is None:return None
  m[i],m[pivot]=m[pivot],m[i];div=m[i][i];m[i]=[x/div for x in m[i]]
  for j in range(n):
   if j!=i:
    c=m[j][i]
    if c:m[j]=[v-c*w for v,w in zip(m[j],m[i])]
 return[row[-1]for row in m]
def spd_ldl(H):
 n=len(H);assert n==4 and all(H[i][j]==H[j][i]for i in range(n)for j in range(n));L=[[F(int(i==j))for j in range(n)]for i in range(n)];D=[]
 for i in range(n):
  p=H[i][i]-sum(L[i][k]**2*D[k]for k in range(i))
  if p<=0:raise ValueError('SPLINE_HESSIAN_NOT_STRICTLY_SPD_PIVOT_'+str(i)+':'+str(p))
  D.append(p)
  for j in range(i+1,n):L[j][i]=(H[j][i]-sum(L[j][k]*L[i][k]*D[k]for k in range(i)))/p
 assert all(H[i][j]==sum(L[i][k]*D[k]*L[j][k]for k in range(n))for i in range(n)for j in range(n))
 return D

def clamped(knots,ys,m0,m1):
 n=len(knots);assert n==6 and len(ys)==6;h=[b-a for a,b in zip(knots,knots[1:])];A=[[F(0)]*n for _ in range(n)];rhs=[F(0)]*n;A[0][0]=2*h[0];A[0][1]=h[0];rhs[0]=6*((ys[1]-ys[0])/h[0]-m0);A[-1][-2]=h[-1];A[-1][-1]=2*h[-1];rhs[-1]=6*(m1-(ys[-1]-ys[-2])/h[-1])
 for i in range(1,n-1):A[i][i-1]=h[i-1];A[i][i]=2*(h[i-1]+h[i]);A[i][i+1]=h[i];rhs[i]=6*((ys[i+1]-ys[i])/h[i]-(ys[i]-ys[i-1])/h[i-1])
 M=linear_solve(A,rhs);assert M is not None;polys=[];bezier=[]
 for i,w in enumerate(h):
  d=(ys[i+1]-ys[i])/w-w*(2*M[i]+M[i+1])/6;p=[ys[i],d,M[i]/2,(M[i+1]-M[i])/(6*w)];polys.append(p);dr=val(der(p),w);bezier.append([ys[i],ys[i]+w*d/3,ys[i+1]-w*dr/3,ys[i+1]])
 assert val(der(polys[0]),F(0))==m0 and val(der(polys[-1]),h[-1])==m1
 for i in range(4):
  assert val(polys[i],h[i])==polys[i+1][0]
  assert val(der(polys[i]),h[i])==polys[i+1][1]
  assert val(der(der(polys[i])),h[i])==2*polys[i+1][2]
 return dict(knots=knots,Y=ys,M=M,polys=polys,bezier=bezier)
def sample(s,X):
 i=max(j for j,v in enumerate(s['knots'][:-1])if X>=v);return val(s['polys'][i],X-s['knots'][i])
def bilinear(knots,a,b):
 return sum((y-x)/3*(a[i]*b[i]+(a[i]*b[i+1]+a[i+1]*b[i])/2+a[i+1]*b[i+1])for i,(x,y)in enumerate(zip(knots,knots[1:])))
def objective_terms(knots,base,variations):
 H=[[2*bilinear(knots,x['M'],y['M'])for y in variations]for x in variations];f=[2*bilinear(knots,base['M'],x['M'])for x in variations];constant=bilinear(knots,base['M'],base['M']);return H,f,constant

def exact_qp(H,f,constraints,report,progress_path=None):
 pivots=spd_ldl(H);n=len(H);assert n==4;assert len(constraints)<=25;eye=[[F(int(i==j))for i in range(n)]for j in range(n)];cols=[linear_solve(H,c)for c in eye];Hi=[[cols[j][i]for j in range(n)]for i in range(n)];u0=linear_solve(H,[-v for v in f]);tested=0;singular=0;negative=0;infeasible=0;maxsub=sum(comb(len(constraints),k)for k in range(5)if k<=len(constraints));report.update(H_rational=[[str(x)for x in row]for row in H],f_rational=[str(x)for x in f],SPD_LDL_positive_pivots_rational=[str(x)for x in pivots],constraints_count=len(constraints),maximum_active_subsets=maxsub,active_subset_bound=15276)
 def progress():
  report.update(subsets_tested=tested,singular_subsets=singular,negative_multiplier_subsets=negative,infeasible_stationary_subsets=infeasible)
  if progress_path:Path(progress_path).write_text(json.dumps(dict(status='single_QP_in_progress_no_asset',**report),indent=2)+'\n')
 for k in range(5):
  for ids in combinations(range(len(constraints)),k):
   tested+=1
   if tested%512==0:progress()
   if not k:u=u0;lam=[]
   else:
    A=[constraints[i]['a']for i in ids];b=[constraints[i]['b']for i in ids];HA=[[sum(Hi[i][j]*row[j]for j in range(n))for i in range(n)]for row in A];G=[[sum(x*y for x,y in zip(row,ha))for ha in HA]for row in A];rhs=[sum(a*x for a,x in zip(row,u0))-bb for row,bb in zip(A,b)];lam=linear_solve(G,rhs)
    if lam is None:singular+=1;continue
    if min(lam)<0:negative+=1;continue
    u=[u0[j]-sum(l*ha[j]for l,ha in zip(lam,HA))for j in range(n)]
   if not all(sum(a*x for a,x in zip(c['a'],u))<=c['b']for c in constraints):infeasible+=1
   else:
    assert all(sum(H[i][j]*u[j]for j in range(n))+f[i]+sum(l*constraints[j]['a'][i]for l,j in zip(lam,ids))==0 for i in range(n))
    assert all(sum(a*x for a,x in zip(constraints[i]['a'],u))==constraints[i]['b']for i in ids)
    progress();report.update(solved=True,u_rational=[str(x)for x in u],active_indices=list(ids),active_roles=[constraints[i]['roles']for i in ids],multipliers_rational=[str(x)for x in lam],exact_KKT_gradient_equalities_and_all_constraints=True,unique_global_minimum_by_SPD=True);return u
   if tested%512==0:progress()
 progress();report['exact_complete_enumeration_no_KKT']=True;return None

class Spline:
 def __init__(self,s):self.s=s;self.x=np.array([float(v)for v in s['knots']]);self.polys=s['polys']
 def __call__(self,x):
  a=np.asarray(x);ids=np.clip(np.searchsorted(self.x,a,side='right')-1,0,4);out=np.empty_like(a,dtype=float)
  for i in range(5):
   on=ids==i
   if on.any():out[on]=np.polynomial.polynomial.polyval(a[on]-self.x[i],[float(v)for v in self.polys[i]])
  return out
 def derivative(self):
  def apply(x):
   a=np.asarray(x);ids=np.clip(np.searchsorted(self.x,a,side='right')-1,0,4);out=np.empty_like(a,dtype=float)
   for i in range(5):
    on=ids==i
    if on.any():out[on]=np.polynomial.polynomial.polyval(a[on]-self.x[i],[float(v)for v in der(self.polys[i])])
   return out
  return apply
 def exact_piece(self,lo,hi):
  i=max(j for j,v in enumerate(self.s['knots'][:-1])if lo>=v);return compose(self.polys[i],[lo-self.s['knots'][i],hi-lo])

def solve(oldR,report,progress_path=None):
 knots=list(map(Q,[1972,1985,1998,2000,2012,2019.5]));y0=Q(oldR(1972.));y5=F(803,2);m0=Q(oldR.derivative()(1972.));m5=Q(oldR.derivative()(2010.5));ys=[y0+(y5-y0)*(x-knots[0])/(knots[-1]-knots[0])for x in knots];base=clamped(knots,ys,m0,m5);variations=[]
 for j in range(4):dy=[F(0)]*6;dy[j+1]=F(1);variations.append(clamped(knots,dy,F(0),F(0)))
 H,f,constant=objective_terms(knots,base,variations);rows=[]
 for i in range(5):
  for j in range(3):rows.append(dict(a=[s['bezier'][i][j+1]-s['bezier'][i][j]for s in variations],b=base['bezier'][i][j]-base['bezier'][i][j+1],roles=[f'piece{i}_Bezier_difference{j}_nonpositive']))
 for lo,hi,low,high,role in [(1985,1998,F(815,2),F(825,2),'high_rear'),(2000,2010,F(805,2),F(813,2),'high_front'),(2010,2012,F(805,2),F(813,2),'medium_front')]:
  for X in [lo,hi]:
   bb=sample(base,F(X));aa=[sample(s,F(X))for s in variations];rows.extend([dict(a=aa,b=high-bb,roles=[f'{role}_X{X}_upper']),dict(a=[-v for v in aa],b=bb-low,roles=[f'{role}_X{X}_lower'])])
 # Preserve all raw roles; only exact positive-scaled duplicates removed.
 dedup={};constants=[]
 for row in rows:
  first=next((abs(x)for x in row['a']if x),None)
  if first is None:
   constants.append(dict(roles=row['roles'],bound_rational=str(row['b']),true=row['b']>=0))
   if row['b']<0:raise ValueError('SPLINE_FALSE_CONSTANT_CONSTRAINT')
   continue
  aa=[x/first for x in row['a']];bb=row['b']/first;key=tuple(aa+[bb])
  if key in dedup:dedup[key]['roles'].extend(row['roles'])
  else:dedup[key]=dict(a=aa,b=bb,roles=row['roles'])
 constraints=list(dedup.values());report.update(method='4DOF_fixedC2clamped_cubic_exact_SPD_bounded_active_set_QP',knots=[float(v)for v in knots],start_value=float(y0),end_value=401.5,start_derivative=float(m0),end_derivative=float(m5),objective='unique integral Rtsecond_squared, no cross or rendering objective',conservative_monotone_domain='all3Bezier derivative controls<=0 in each5pieces; stricter than general monotonicity',constant_constraints=constants,raw_constraint_roles_count=len(rows),constraints=[dict(a_rational=[str(x)for x in c['a']],b_rational=str(c['b']),roles=c['roles'])for c in constraints],objective_constant_rational=str(constant),reference='Exact rational meaning of frozen endpoint floats; runtime float64 separately checked.')
 u=exact_qp(H,f,constraints,report,progress_path)
 if u is None:raise ValueError('SPLINE_QP_INFEASIBLE_COMPLETE_ENUMERATION')
 finalY=[ys[0]]+[ys[i+1]+u[i]for i in range(4)]+[ys[-1]];s=clamped(knots,finalY,m0,m5)
 assert all(s['bezier'][i][j+1]<=s['bezier'][i][j]for i in range(5)for j in range(3));critical=[]
 for i,(a,b)in enumerate(zip(knots,knots[1:])):
  width=b-a;dp=der(s['polys'][i]);dd=der(dp);tests=[F(0),width]
  if len(dd)==2 and dd[1]!=0:
   root=-dd[0]/dd[1]
   if 0<root<width:tests.append(root)
  assert all(val(dp,x)<=0 for x in tests);critical.append(dict(piece=i,derivative_critical_offsets_rational=[str(x)for x in tests],derivative_values_rational=[str(val(dp,x))for x in tests],all_interior_real_derivative_roots='identically_zero'if all(v==0 for v in dp)else nroots(dp,F(0),width)))
 report['per_piece_all_real_derivative_critical_points']=critical;bandchecks=[]
 for lo,hi,low,high,role in [(1985,1998,F(815,2),F(825,2),'high_rear'),(2000,2010,F(805,2),F(813,2),'high_front'),(2010,2012,F(805,2),F(813,2),'medium_front')]:
  yy=[sample(s,F(x))for x in range(lo,hi+1)];assert all(low<=y<=high for y in yy);bandchecks.append(dict(role=role,X=[lo,hi],all_integer_cell_edges_rational=[str(y)for y in yy],all_interval_values_proven_by_monotonicity=True))
 report['reference_complete_cell_band']=bandchecks;objective=bilinear(knots,s['M'],s['M']);report.update(node_Y_rational=[str(v)for v in finalY],node_Y_float=[float(v)for v in finalY],piece_coefficients_native_rational=[[str(c)for c in p]for p in s['polys']],second_derivatives_rational=[str(v)for v in s['M']],Bezier_controls_rational=[[str(v)for v in row]for row in s['bezier']],all_Bezier_controls_certified_nonincreasing=True,C2_exact=True,endpoint_values_and_clamps_exact=True,objective_native=float(objective));return Spline(s)
