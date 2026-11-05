"""Actual current-body/tail cross-sections and an explicit constructed negative.

No historical rejected model is invented or retained. The negative scales the
same actual tail's transverse vertices to five percent in memory only.
"""
import argparse,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from check_project_art_tail_section import mesh,half_width
from portable.glb_io import sha
p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();body=mesh(a.model,'Reference_head_body');tail=mesh(a.model,'Caudal');rear=float(body[:,:,0].min());cap=body[np.abs(body[:,:,0]-rear)<1e-7];zs=sorted(set(cap[:,2]));assert len(zs)>3;results=[]
for negative in [False,True]:
 t=tail.copy()
 if negative:t[:,:,1]*=.05
 rows=[]
 for z in zs[1:-1]:
  expected=half_width(body,rear,z);actual=half_width(t,rear-.0001,z);rows.append(dict(z_native=float(z),body_half_width_native=expected,tail_half_width_native=actual,width_error_mm=abs(expected-actual)*2000))
 error=float(max(r['width_error_mm']for r in rows));results.append(dict(ok=bool(rows and error<=.5),sections=rows,maximum_width_error_mm=error,tolerance_mm=.5,plane_x_native=rear-.0001,model_sha256=sha(a.model),constructed_negative=negative))
r=dict(ok=results[0]['ok']and not results[1]['ok'],kind='actual_current_body_tail_section_with_constructed_thin_negative',current=results[0],rejected_original=results[1],model_sha256=sha(a.model),checker_sha256=sha(__file__),scope='Every interior latitude of the CURRENT finite body cap at0.1mm posterior. Same actual tail scaled transversely to5% is an in-memory negative, not a historical rejected asset or biological measurement.',formal_acceptance=False);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=r['ok'],current_mm=results[0]['maximum_width_error_mm'],constructed_negative_mm=results[1]['maximum_width_error_mm'])));raise SystemExit(0 if r['ok'] else 1)
