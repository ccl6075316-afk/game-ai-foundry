"""Actual finite side envelope and leading-edge/eye relative-motion proof.

These engineering indicators do not establish photographic or user acceptance.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from portable.glb_io import read_glb,arrays
from measure_hammerhead_head_field import load_candidate
from audit_hammerhead_head_gill import projected_bounds

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def body(path):
    d,b=read_glb(path);node=next(n for n in d['nodes']if n.get('name')=='Reference_head_body');ps=d['meshes'][node['mesh']]['primitives']
    vertices=np.concatenate([arrays(d,b,p['attributes']['POSITION'])for p in ps]);eyes=np.concatenate([arrays(d,b,p['attributes']['POSITION'])for p in ps if d['materials'][p['material']]['name'].startswith('Own original side eye pixels')])
    return vertices,eyes
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model',type=Path,required=True);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();L=2.4914281368255615;nose=1.032794117647059
    ov,oe=body(a.baseline);nv,ne=body(a.model);assert ov.shape==nv.shape and oe.shape==ne.shape
    xy=bool(np.array_equal(ov[:,[0,2]],nv[:,[0,2]]));rear=(nose-ov[:,0])/L>=.300001;rear_error=float(abs(nv[rear]-ov[rear]).max());front=ov[:,0]>ov[:,0].max()-1e-6;front_delta=float(np.mean(nv[front,1]-ov[front,1]));eye_delta=float(np.mean(ne[:,1]-oe[:,1]));eye_rigid_error=float(np.ptp(ne[:,1]-oe[:,1]));rows=[]
    v,f=load_candidate(a.model,L,nose);old,oldf=load_candidate(a.baseline,L,nose)
    for p in np.linspace(0,.30,301):
        current=projected_bounds(v,f,float(p));previous=projected_bounds(old,oldf,float(p));rows.append(dict(p=float(p),current_z_m=[z*L for z in current]if current else None,baseline_z_m=[z*L for z in previous]if previous else None))
    slopes={}
    for key in ['current_z_m','baseline_z_m']:
        slopes[key]={name:float(np.polyfit([r['p']for r in rows if lo<=r['p']<=hi],[r[key][1]for r in rows if lo<=r['p']<=hi],1)[0])for name,lo,hi in [('anterior',.04,.10),('neck',.14,.20)]}
    result=dict(ok=bool(xy and rear_error<1e-6 and eye_rigid_error<1e-6 and front_delta<eye_delta-.010),kind='actual_photo_forebody_nonrigid_shape_proof',model_sha256=sha(a.model),baseline_sha256=sha(a.baseline),checker_sha256=sha(__file__),body_axial_transverse_positions_exact=xy,posterior_body_maximum_error_m=rear_error,leading_edge_delta_z_m=front_delta,eye_delta_z_m=eye_delta,leading_edge_delta_relative_eye_m=front_delta-eye_delta,eye_rigid_translation_error_m=eye_rigid_error,upper_finite_slope_m_per_p=slopes,rows=rows,scope='Leading edge must move down relative to eye, rejecting equal rigid head translation;10mm is a declared engineering discrimination margin, not a biological threshold. Side-projected finite body only, no fin triangles. Continuous authored envelope/actual multi-view photo comparison still require review.',formal_acceptance=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['rows','scope']}));return 0 if result['ok']else 1
if __name__=='__main__':raise SystemExit(main())
