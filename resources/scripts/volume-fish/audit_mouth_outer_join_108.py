#!/usr/bin/env python3
"""108read-only requested outer join values; preserves firstYproposal, no newcandidate."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from probe_mouth_slit_stage1_108 import field,canvas,plane_points
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();b=a.input.resolve().parent;path=b.parent/'eye-rollout-107/zander-mesh-rest.json';d=json.loads(path.read_text());v=np.array(d['rest_xyz']);q=canvas(v);m,_=field(q);out=v.copy();on=q[:,0]>1988;out[on,0]=m[on,0]/2024-.5;out[on,1]=(371-m[on,1])/2024;dd=dict(d);dd['rest_xyz']=out.tolist();sourcepath=b.parent/'surface-mouth-audit-102/sources/zander/image-0.png';source=np.array(Image.open(sourcepath));rows=[]
for x in [1700,1740,1780,1800,1820,1840,1860,1870,1894,1922.194880008697,1930,1940,1960,1980]:
 pts=plane_points(dd,x/2024-.5);p=canvas(pts);sx=int(np.floor(x));ys=np.flatnonzero(source[:,sx,3]>=243);groups=[[int(g.min()),int(g.max())] for g in np.split(ys,np.where(np.diff(ys)>1)[0]+1)];main=max(groups,key=lambda g:max(0,min(g[1]+1,600)-max(g[0],300)));rows.append({'actual_plane_canvas_x':x,'source_native_column':sx,'source_pixelcenter_x':sx+.5,'source_all_opaque_runs_inclusive':groups,'source_selected_contiguous_main_run':main,'source_top_boundary_y':main[0],'source_bottom_cell_boundary_y':main[1]+1,'actual_skin_top_y':float(p[:,1].min()),'actual_skin_bottom_y':float(p[:,1].max()),'source_minus_skin_top':float(main[0]-p[:,1].min()),'source_minus_skin_bottom':float(main[1]+1-p[:,1].max())})
def value(x,top):return float(canvas(plane_points(dd,x/2024-.5))[:,1].min() if top else canvas(plane_points(dd,x/2024-.5))[:,1].max())
tangents=[]
for x,istop,targetx,targety in [(1922.194880008697,True,1960.5,365),(1780,False,1870.5,494)]:
 y=value(x,istop);m=(value(x+.01,istop)-value(x-.01,istop))/.02;s=(targety-y)/(targetx-x);tangents.append({'branch':'top' if istop else 'chin','old_anchor':[x,y],'candidate_source_anchor':[targetx,targety],'actual_left_tangent':m,'joining_secant':s,'left_slope_to_secant_ratio':m/s,'not_frozen_candidate':'Onlynumericalfeasibilitybasis, noPCHIP/Hermitecurveevaluated.'})
inputs=[a.input.resolve(),path,sourcepath,Path(__file__),Path(__file__).with_name('probe_mouth_slit_stage1_108.py')];r={'status':'read_only_outer_join_table','accepted':False,'stage1_parameters_unchanged':True,'proposal_v1_unchanged':True,'source_alpha_threshold':243,'coordinate_note':'ActualX=requestednativecanvas. Sourcecolumn=floor(X), itscenter separatelylisted. Noindependentregistration. Mainalpha run is notautomaticallyseparatedfromconnectedfin orapprovedbodytarget.','inputs_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'rows':rows,'monotone_join_readonly_basis':tangents};a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'rows':len(rows),'join_basis':tangents},indent=2))
