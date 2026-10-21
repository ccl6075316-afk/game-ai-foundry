#!/usr/bin/env python3
"""Read-only local clearance/upper envelope supplement108; no protection or field changes."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from audit_mouth_refinement_108 import load_frozen_field

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();d=json.loads(a.input.read_text());b=a.input.resolve().parents[1];ns=load_frozen_field(Path(__file__).with_name('probe_mouth_monotone_108.py'),b/'source-mouth-alignment.validation.json');v=ns['old'][0];q=ns['canvas'](v);ff=np.array(ns['data'][0]['indices']).reshape(-1,3);S=452.62-1.02*742/2024*(q[:,0]-1894.464);V=q[:,1]-S;low=ff[V[ff].min(1)>0];up=ff[V[ff].max(1)<0]
 def bounds(tri,x):
  ed=np.r_[tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]];x0=ed[:,0,0];dx=ed[:,1,0]-x0;dy=ed[:,1,1]-ed[:,0,1];valid=dx!=0;t=np.zeros(len(dx));t[valid]=(x-x0[valid])/dx[valid];on=valid&(t>=0)&(t<=1);ys=ed[on,0,1]+t[on]*dy[on];flat=(~valid)&(x0==x)
  if flat.any():ys=np.r_[ys,ed[flat,:,1].ravel()]
  return [float(ys.min()),float(ys.max())] if len(ys) else None
 lower=q[low];upper=q[up];minimum={};allvals={};corner=min((p[0]+.5)*2024 for e in ns['alignment']['actual_interface'] for p in e['rest_xyz'])
 for name,ids in [('base246',d['levels'][0]['union_vertex_ids']),('base_LOD0_4_union304',d['pass_level_union']['direct_feature_vertex_ids'])]:
  vals=[]
  for i in ids:
   x,y=q[i];L,B=bounds(lower,x);vals.append({'actual_vertex_id':int(i),'XYZ':v[i].tolist(),'nativeXY':q[i].tolist(),'old_lower_branch_L':L,'old_chin_B':B,'gap_L_minus_Y':L-float(y),'prior_to_actual_mouth_corner':bool(x<corner),'levels':[r['level'] for r in d['levels'][:-1] if i in r['union_vertex_ids']]})
  vals.sort(key=lambda x:x['gap_L_minus_Y']);zero=[r for r in vals if r['gap_L_minus_Y']==0];positive=[r for r in vals if r['gap_L_minus_Y']>0];negative=[r for r in vals if r['gap_L_minus_Y']<0];minimum[name]={'minimum':vals[0],'zero_gap_points':zero,'minimum_positive':positive[0] if positive else None,'next_positive12':positive[:12],'negative_gap_points':negative};allvals[name]=vals
 forward=[]
 for r in allvals['base_LOD0_4_union304']:
  x,y=r['nativeXY']
  if x<=1920:continue
  U,R=bounds(upper,x);L,B=bounds(lower,x);branch='upper' if y-(452.62-1.02*742/2024*(x-1894.464))<0 else 'lower';mm,dy,uv=ns['evaluate'](np.array([[x,y]]),True);forward.append({**r,'branch':branch,'old_U':U,'old_R':R,'old_L':L,'old_B':B,'Y_minus_U':y-U,'R_minus_Y':R-y,'Y_minus_L':y-L,'B_minus_Y':B-y,'rejected_F2_mapped_nativeXY':mm[0].tolist(),'rejected_F2_dYdY':float(dy[0]),'rejected_F2_UV_weight':float(uv[0][0]),'scope':'existing rejected field diagnostic only; not reusing or changingit'})
 forward.sort(key=lambda r:r['nativeXY'][0]);st=ns['st'][0];sq=ns['canvas'](st);sv=sq[:,1]-(452.62-1.02*742/2024*(sq[:,0]-1894.464));stageup=ff[sv[ff].max(1)<0];stagetri=sq[stageup];tab=[]
 for x in [1988.,1990.,1995.,2000.,2005.,2010.,2015.]:
  U,R=bounds(stagetri,x);tab.append({'stage1_X':x,'actual_upper_U':U,'actual_upper_R':R,'span_R_minus_U':R-U,'field_positions_not_changed':True})
 out={'status':'read_only_clearance_anchor_feasibility_data','accepted':False,'newfield_executed':False,'actual_mouth_corner_min_X':corner,'minima':minimum,'all_vertex_clearances':allvals,'union_protected_X_gt1920':forward,'Stage1_actual_upper_U_R':tab,'important_semantics':['L is strictV lowerbranch plane envelope, not actualcutlip beforemouthcorner.','Zero-gap vertex is not removed: an eventual Dirichlet anchor withtargetL=oldLcouldpin it; this report only suppliesdata and doesnotauthorizefield.','Minimumpositivegap mustnot replaceglobalmin without explicitzeroanchor contract and interiorintervalchecks.','304directPOS/NORMAL/UVgroups are frombase+oldLOD0–4;580normalincidentPOSare separate potentialrecompute dependencies, not automaticnewprotection.','New actual importLOD and wholeeye fragment/normal support still requirefreshverification.'],'dependencies_sha256':{str(p):sha(p) for p in [a.input,Path(__file__),Path(__file__).with_name('probe_mouth_monotone_108.py'),b.parent/'eye-rollout-107/zander-mesh-rest.json']}};a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'minima':{k:{z:v[z] for z in ['minimum','zero_gap_points','minimum_positive']} for k,v in minimum.items()},'forward_count':len(forward),'forward':forward,'stage1':tab},indent=2))
if __name__=='__main__':main()
