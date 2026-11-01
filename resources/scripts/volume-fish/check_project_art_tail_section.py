"""Compare the actual whole-tail root with the frozen pre-authoring body cap."""
import argparse,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb,arrays,sha

def mesh(path,name):
    doc,blob=read_glb(path);node=next(n for n in doc['nodes']if n.get('name')==name);tri=[]
    for part in doc['meshes'][node['mesh']]['primitives']:
        v=arrays(doc,blob,part['attributes']['POSITION']).astype(float)[:,[0,2,1]];v[:,1]*=-1;tri.extend(v[arrays(doc,blob,part['indices']).reshape(-1,3)])
    return np.array(tri)

def half_width(triangles,x,z):
    segments=[]
    for tri in triangles:
        hits=[]
        for a,b in zip(tri,np.roll(tri,-1,axis=0)):
            if abs(a[0]-x)<1e-7:hits.append(a)
            if (a[0]-x)*(b[0]-x)<0:hits.append(a+(b-a)*(x-a[0])/(b[0]-a[0]))
        if len(hits)>=2:segments.append(hits[:2])
    widths=[]
    for a,b in segments:
        if abs(a[2]-z)<1e-7:widths.append(abs(a[1]))
        if (a[2]-z)*(b[2]-z)<0:widths.append(abs(a[1]+(b[1]-a[1])*(z-a[2])/(b[2]-a[2])))
    return max(widths,default=0)

def check(c):
    for key in ['body_reference','model','negative_model']:assert sha(c[key])==c[key+'_sha256']
    body=mesh(c['body_reference'],c['body']);rear=float(body[:,:,0].min());cap=body[np.abs(body[:,:,0]-rear)<1e-7];zs=sorted(set(cap[:,2]));results=[]
    for model in [c['model'],c['negative_model']]:
        tail=mesh(model,c['tail']);rows=[]
        for z in zs[1:-1]:
            expected=half_width(body,rear,z);actual=half_width(tail,rear-c['posterior_offset_m'],z);rows.append(dict(z_native=float(z),body_half_width_native=expected,tail_half_width_native=actual,width_error_mm=abs(expected-actual)*2000))
        error=float(max(r['width_error_mm']for r in rows));results.append(dict(ok=bool(rows) and error<=c['tolerance_mm'],sections=rows,maximum_width_error_mm=error,tolerance_mm=c['tolerance_mm'],plane_x_native=rear-c['posterior_offset_m'],model_sha256=sha(model)))
    return dict(ok=results[0]['ok'] and not results[1]['ok'],kind='actual_whole_tail_to_pre_author_body_section',current=results[0],rejected_original=results[1],body_reference_sha256=sha(c['body_reference']),checker_sha256=sha(__file__),scope='Full widths at every interior latitude of the actual finite pre-author body cap, just posterior to its plane. Previous thin-root candidate is an actual negative. Engineering continuity gate, not measured fish thickness.',formal_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();assert not a.output.exists();r=check(json.loads(a.config.read_text()));a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=r['ok'],current_error_mm=r['current']['maximum_width_error_mm'],negative_error_mm=r['rejected_original']['maximum_width_error_mm'])));raise SystemExit(0 if r['ok']else 1)
