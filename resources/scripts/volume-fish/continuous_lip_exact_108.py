#!/usr/bin/env python3
"""Frozen attempt2 continuous-lip exact rational solver/proof utilities. No I/O meshes."""
from fractions import Fraction as F
from math import comb
import itertools
import numpy as np

def Q(x):return x if isinstance(x,F)else F(float(x))
def trim(a):
 a=list(a)
 while len(a)>1 and a[-1]==0:a.pop()
 return a or [F(0)]
def add(a,b):return trim([(a[i]if i<len(a)else 0)+(b[i]if i<len(b)else 0)for i in range(max(len(a),len(b)))])
def scale(a,c):return trim([x*c for x in a])
def mul(a,b):
 c=[F(0)]*(len(a)+len(b)-1)
 for i,x in enumerate(a):
  for j,y in enumerate(b):c[i+j]+=x*y
 return trim(c)
def der(a):return trim([i*a[i]for i in range(1,len(a))])
def val(a,x):
 v=F(0)
 for c in reversed(a):v=v*x+c
 return v
def compose(a,b):
 out=[F(0)]
 for c in reversed(a):out=add(mul(out,b),[c])
 return out
def divide(a,b):
 a=trim(a);b=trim(b);assert b!=[0];out=[F(0)]*max(1,len(a)-len(b)+1)
 while len(a)>=len(b)and a!=[0]:
  k=len(a)-len(b);t=a[-1]/b[-1];out[k]+=t;a=add(a,[F(0)]*k+scale(b,-t))
 return trim(out),trim(a)
def sturm(p):
 p=trim(p)
 if len(p)<2:return[p]
 s=[p,der(p)]
 while s[-1]!=[0]:
  _,r=divide(s[-2],s[-1])
  if r==[0]:break
  r=scale(r,-1);r=scale(r,1/abs(r[-1]));s.append(r)
 return s
def variations(s,x):
 a=[val(p,x)for p in s];a=[1 if v>0 else -1 for v in a if v];return sum(i!=j for i,j in zip(a,a[1:]))
def remove_endpoint(p,x):
 while len(p)>1 and val(p,x)==0:p,r=divide(p,[-x,F(1)]);assert r==[0]
 return p
def nroots(p,a=F(0),b=F(1)):
 p=remove_endpoint(remove_endpoint(trim(p),a),b)
 if len(p)<2:return 0
 s=sturm(p);return variations(s,a)-variations(s,b)
def root_intervals(p,a=F(0),b=F(1),bits=200):
 p=remove_endpoint(remove_endpoint(trim(p),a),b)
 if len(p)<2:return[]
 roots=[];s=sturm(p);todo=[(a,b,variations(s,a)-variations(s,b))]
 while todo:
  lo,hi,count=todo.pop()
  if not count:continue
  if count==1 and hi-lo<=F(1,2**bits):roots.append((lo,hi));continue
  mid=(lo+hi)/2
  if val(p,mid)==0:
   # Preserve exact rational root; restart quotient so neither half has a root endpoint.
   quotient,remainder=divide(p,[-mid,F(1)]);assert remainder==[0]
   return sorted([(mid,mid)]+root_intervals(quotient,a,b,bits))
  left=variations(s,lo)-variations(s,mid);todo.extend([(lo,mid,left),(mid,hi,count-left)])
 return sorted(roots)
def interval_val(p,lo,hi):
 a=b=F(0)
 for c in reversed(p):
  v=[a*lo,a*hi,b*lo,b*hi];a=min(v)+c;b=max(v)+c
 return a,b
def positive(p,allow_left_zero=False,allow_right_zero=False):
 p=trim(p);left=val(p,F(0));right=val(p,F(1));mid=val(p,F(1,2));okends=(left>0 or allow_left_zero and left==0)and(right>0 or allow_right_zero and right==0)
 if not okends or mid<=0:return False,dict(method='exact_endpoint_or_midpoint_reject',left=float(left),right=float(right),mid=float(mid))
 degree=len(p)-1;bern=[sum(p[i]*F(comb(k,i),comb(degree,i))for i in range(k+1))for k in range(degree+1)]
 if all(v>=0 for v in bern):return True,dict(method='exact_Bernstein_positive_excludes_all_open_interval_real_roots',minimum_Bernstein=float(min(bern)))
 count=nroots(p);return count==0,dict(method='exact_Sturm_all_open_interval_real_roots',root_count=count,left=float(left),right=float(right))
def hermite(y0,y1,m0,m1,width):return[Q(y0),Q(m0)*width,3*(Q(y1)-Q(y0))-width*(2*Q(m0)+Q(m1)),2*(Q(y0)-Q(y1))+width*(Q(m0)+Q(m1))]
def integral_product(a,b):return sum(c/F(i+1)for i,c in enumerate(mul(a,b)))
def mat2solve(H,q):
 det=H[0][0]*H[1][1]-H[0][1]*H[1][0]
 if det==0:return None
 return[(q[0]*H[1][1]-H[0][1]*q[1])/det,(H[0][0]*q[1]-q[0]*H[1][0])/det]
def qp2(H,f,constraints):
 # min .5*x'Hx+f'x, row a*x<=b. Enumerate the exact convex active set.
 candidates=[];free=mat2solve(H,[-v for v in f]);assert free is not None;candidates.append((free,[]))
 for i,(a,b)in enumerate(constraints):
  ha=mat2solve(H,a);den=sum(v*w for v,w in zip(a,ha))
  if den==0:continue
  lam=(sum(v*w for v,w in zip(a,free))-b)/den
  if lam>=0:candidates.append(([x-lam*y for x,y in zip(free,ha)],[i]))
 for i,j in itertools.combinations(range(len(constraints)),2):
  a,b=constraints[i];c,d=constraints[j];x=mat2solve([a,c],[b,d])
  if x is None:continue
  grad=[sum(H[k][l]*x[l]for l in range(2))+f[k]for k in range(2)];lam=mat2solve([[a[0],c[0]],[a[1],c[1]]],[-v for v in grad])
  if lam is not None and min(lam)>=0:candidates.append((x,[i,j]))
 feasible=[(x,active)for x,active in candidates if all(sum(v*w for v,w in zip(a,x))<=b for a,b in constraints)]
 if not feasible:return None
 objective=lambda x:sum(x[k]*H[k][l]*x[l]/2 for k in range(2)for l in range(2))+sum(v*w for v,w in zip(f,x))
 return min(feasible,key=lambda item:(objective(item[0]),item[1]))
class Guideline:
 def __init__(self,coeff,a=1972.,b=2019.5):self.coeff=coeff;self.a=a;self.b=b
 def __call__(self,x):return np.polynomial.polynomial.polyval((np.asarray(x)-self.a)/(self.b-self.a),[float(c)for c in self.coeff])
 def derivative(self):
  return lambda x:np.polynomial.polynomial.polyval((np.asarray(x)-self.a)/(self.b-self.a),[float(c)/(self.b-self.a)for c in der(self.coeff)])
def solve(oldR,report):
 a=F(1972);b=F(4039,2);width=b-a;start=Q(oldR(float(a)));m0=Q(oldR.derivative()(float(a)));m1=Q(oldR.derivative()(2010.5));base=hermite(start,F(803,2),m0,m1,width);bases=[[F(0),F(0),F(1),F(-2),F(1)],[F(0),F(0),F(-1),F(4),F(-5),F(2)]];dd=[der(der(p))for p in bases];d0=der(der(base));H=[[2*integral_product(x,y)/width**3 for y in dd]for x in dd];f=[2*integral_product(d0,x)/width**3 for x in dd];constraints=[];roles=[]
 for lo,hi,lower,upper,role in [(1985,1998,F(815,2),F(825,2),'high_rear'),(2000,2010,F(805,2),F(813,2),'high_front'),(2010,2012,F(805,2),F(813,2),'medium_front')]:
  for X in [lo,hi]:
   t=(F(X)-a)/width;bb=val(base,t);row=[val(p,t)for p in bases];constraints.extend([(row,upper-bb),([-v for v in row],bb-lower)]);roles.extend([f'{role}_X{X}_upper',f'{role}_X{X}_lower'])
 report.update(method='exact_rational_2D_convex_QP_active_sets_then_exact_Sturm_derivative_critical_roots_200bit_isolation',join=1972.,end=2019.5,start_value=float(start),start_derivative=float(m0),end_value=401.5,end_derivative=float(m1),target='one_global_degree<=5_min_integral_Rsecond_squared',exchange_max=64,history=[])
 for iteration in range(64):
  fit=qp2(H,f,constraints)
  if fit is None:raise ValueError('CONTINUOUS_LIP_QP_INFEASIBLE')
  x,active=fit;poly=add(base,add(scale(bases[0],x[0]),scale(bases[1],x[1])));d=der(poly);roots=root_intervals(der(d));tests=[(F(0),F(0)),*roots,(F(1),F(1))];violations=[];cert=[];uncertain=False
  for lo,hi in tests:
   low,high=interval_val(d,lo,hi);mid=(lo+hi)/2;v=val(d,mid);cert.append(dict(t_interval_rational=[str(lo),str(hi)],derivative_native_interval=[float(low/width),float(high/width)]))
   if low>0:violations.append((v,mid))
   elif high>0:uncertain=True
  report['history'].append(dict(iteration=iteration,active_constraints=[roles[i]for i in active],A=str(x[0]),B=str(x[1]),critical_tests=cert,positive_critical_intervals=len(violations),sign_uncertain=uncertain))
  if uncertain:raise ValueError('CONTINUOUS_LIP_DERIVATIVE_SIGN_UNCERTAIN')
  if not violations:
   assert val(poly,F(0))==start and val(poly,F(1))==F(803,2)and val(d,F(0))/width==m0 and val(d,F(1))/width==m1
   report.update(solved=True,coefficients_t_rational=[str(v)for v in poly],coefficients_t_float64=[float(v)for v in poly],derivative_all_real_critical_points_certified_nonpositive=True,objective_native=float(integral_product(der(der(poly)),der(der(poly)))/width**3),degree=len(poly)-1)
   return Guideline(poly)
  _,t=max(violations);constraints.append(([val(der(p),t)for p in bases],-val(der(base),t)));roles.append('derivative_exchange_t='+str(t))
 raise ValueError('CONTINUOUS_LIP_64_EXCHANGE_LIMIT')
