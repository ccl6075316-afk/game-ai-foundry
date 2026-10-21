#!/usr/bin/env python3
"""Runnable small synthetic fixtures, NOT production spline solve or asset generation."""
import argparse,json,hashlib,ast
from pathlib import Path
from fractions import Fraction as F
import numpy as np
from continuous_spline_exact_108 import clamped,objective_terms,spd_ldl,exact_qp,bilinear
from continuous_lip_exact_108 import nroots,positive,mul,add,der,compose,integral_product
from continuous_spline_checks_108 import source_band_check

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args();p=json.loads(args.input.read_text());rows=[]
 def check(name,a,b):rows.append(dict(name=name,actual=a,expected=b,passed=a==b));assert a==b,(name,a,b)
 for c in p['QP_cases']:
  H=[[F(c['H_diag'][i])if i==j else F(0)for j in range(4)]for i in range(4)];constraints=[dict(a=list(map(F,r['a'])),b=F(r['b']),roles=[str(i)])for i,r in enumerate(c['constraints'])];report={};fit=exact_qp(H,list(map(F,c['f'])),constraints,report);check(c['name'],None if fit is None else list(map(str,fit)),None if c['expected']is None else list(map(str,c['expected'])))
 for diag in p['non_SPD_diagonals']:
  H=[[F(diag[i])if i==j else F(0)for j in range(4)]for i in range(4)];rejected=False
  try:spd_ldl(H)
  except ValueError:rejected=True
  check('Reject nonSPD '+str(diag),rejected,True)
 for c in p['spline_cases']:
  knots=list(map(F,c['knots']));s=clamped(knots,list(map(F,c['Y'])),*map(F,c['slopes']));energy=bilinear(knots,s['M'],s['M']);integral=F(0)
  for i,poly in enumerate(s['polys']):h=knots[i+1]-knots[i];dd=compose(der(der(poly)),[F(0),h]);integral+=h*integral_product(dd,dd)
  check(c['name']+' exact energy identity',str(energy),str(integral))
  if c['expected_energy']is not None:check(c['name']+' known energy',str(energy),str(c['expected_energy']))
  variations=[]
  for i in range(4):ys=[F(0)]*6;ys[i+1]=F(1);variations.append(clamped(knots,ys,F(0),F(0)))
  H,f,constant=objective_terms(knots,s,variations);check(c['name']+' reduced Hessian strictlySPD',min(spd_ldl(H))>0,True)
 for c in p['root_polynomials_ascending']:check(c['name'],nroots(list(map(F,c['p']))),c['expected_count'])
 for c in p['strict_positive_polynomials']:
  square=mul([-F(c['square_center']),F(1)],[-F(c['square_center']),F(1)]);check(c['name'],positive(add(square,[F(c['offset'])]))[0],c['expected'])
 c=p['Bezier_conservative_counterexample'];B=list(map(F,c['B']));controls=[3*(y-x)for x,y in zip(B,B[1:])];half=(controls[0]+2*controls[1]+controls[2])/4;check('Conservative domain rejects actual monotone counterexample',all(x<=0 for x in controls),c['expected_Bezier_domain_accepted']);check('Counterexample derivative midpoint exact',str(half),str(F(c['derivative_at_half'])));t=F(c['derivative_critical_t']);peak=controls[0]*(1-t)**2+2*controls[1]*t*(1-t)+controls[2]*t*t;check('Actual monotone counterexample critical maximum exact',str(peak),str(F(c['derivative_at_critical'])))
 c=p['PL_fixture'];points=np.array([[float(F(x))for x in row]for row in c['points']]);faces=np.array(c['triangles']);canvas=lambda v:np.asarray(v)[...,:2];result=source_band_check(points,faces,points[:,:2],canvas);check('Exact fullPL positive fixture',result['passed'],c['expected_band_pass']);negative=points.copy();negative[c['negative_point_id'],1]=c['negative_Y'];result=source_band_check(negative,faces,points[:,:2],canvas);check('Exact fullPL negative fixture',result['passed'],c['expected_modified_band_pass'])
 root=Path(__file__).resolve().parents[3]
 def fn(path):return{n.name:ast.dump(n,include_attributes=False)for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,ast.FunctionDef)and n.name in ['H','evaluate','values']}
 check('Frozen H/evaluate/values AST exact',fn(root/'resources/scripts/volume-fish/probe_mouth_attempt2_108.py')==fn(root/'resources/scripts/volume-fish/probe_continuous_spline_108.py'),True)
 sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest();out=dict(status='synthetic_controls_only_NO_production_solve',production_solver_not_run=True,input_sha256=sha(args.input),executor_sha256=sha(Path(__file__)),command='python3 resources/scripts/volume-fish/test_continuous_spline_108.py --input '+str(args.input)+' --output '+str(args.output),controls=rows,passed=all(r['passed']for r in rows));args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(controls=len(rows),passed=out['passed'])))
if __name__=='__main__':main()
