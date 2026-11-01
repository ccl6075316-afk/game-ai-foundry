"""Check current GLB against frozen top-source head sections and reject old shape.

This measures the cephalofoil front/rear outline after one isotropic head-width
registration. It is not biological acceptance, and excludes the hidden central
rear collar. Rendered clay, source artwork and textured views remain mandatory.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb,accessor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sections(path,stations):
    d,b=read_glb(path);n=next(n for n in d['nodes'] if n.get('name')=='Cephalofoil')
    v=np.concatenate([accessor(d,b,p['attributes']['POSITION']) for p in d['meshes'][n['mesh']]['primitives']])
    half=(stations[-1]-stations[0])/2
    ids=np.rint((v[:,2]+half)/(2*half)*96).astype(int)
    assert len(np.unique(ids))==97 and ids.min()==0 and ids.max()==96
    return np.array([[v[ids==i,0].min()+.5,v[ids==i,0].max()+.5] for i in range(97)]),float(np.ptp(v[:,2]))
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--fit-report',type=Path,required=True);ap.add_argument('--source-plan',type=Path,required=True);ap.add_argument('--models',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    fit=json.loads(a.fit_report.read_text(encoding='utf8'));plan=json.loads(a.source_plan.read_text(encoding='utf8'));rows=[]
    for r in fit['items']:
        source=next(x for x in plan['items'] if x['species']==r['species']);assert sha(source['top_source'])==r['source_sha256']==source['source_sha256']
        target=a.models/(r['species']+'.glb');assert sha(target)==r['model_sha256']
        s=np.array(r['sections']);expected=s[:,1:];z=s[:,0];half=r['head_width']/2
        current,width=sections(target,z);old,_=sections(Path(source['model']),z)
        mask=(np.abs(z)>=.4*half)&(np.abs(z)<=.98*half)
        new_error=np.abs(current[mask]-expected[mask])/width;old_error=np.abs(old[mask]-expected[mask])/width
        front_error=np.abs(current[:,1]-expected[:,1])/width
        ok=bool(new_error.max()<.02 and new_error.mean()<.008 and front_error.max()<.02 and abs(width-r['head_width'])<1e-6 and old_error.mean()>.008)
        rows.append(dict(species=r['species'],ok=ok,model_sha256=sha(target),source_sha256=r['source_sha256'],head_width_unchanged=abs(width-r['head_width'])<1e-6,old_mean_outline_error_in_head_width=float(old_error.mean()),new_mean_outline_error_in_head_width=float(new_error.mean()),new_max_outline_error_in_head_width=float(new_error.max()),all_front_max_error_in_head_width=float(front_error.max()),old_shape_negative_control_rejected=bool(old_error.mean()>.008)))
    result=dict(ok=all(x['ok'] for x in rows),status='done',next_action='human_review',items=rows,fit_report_sha256=sha(a.fit_report),source_plan_sha256=sha(a.source_plan),checker_sha256=sha(__file__),limits='Source projection conformance only. Rear curve outside40%-98% halfspan; full leading edge. Hidden central root height, thickness, source correctness and continuous motion are not established by this check.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
