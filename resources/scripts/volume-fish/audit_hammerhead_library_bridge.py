"""Check a broad axial bridge retraction without borrowing a library mesh.

Finite side sections include every old/new vertex station and interval midpoint.
This is a sampled envelope guard, not a proof of animated continuous clearance.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from portable.glb_io import read_glb, arrays

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def parts(d): return {n['name']: d['meshes'][n['mesh']]['primitives'] for n in d['nodes'] if 'mesh' in n}
def envelope(tri, x):
    b=np.roll(tri,-1,axis=1); k=(tri[:,:,0]-x)*(b[:,:,0]-x)<0
    points=tri[k]+((x-tri[:,:,0][k])/(b[:,:,0][k]-tri[:,:,0][k]))[:,None]*(b[k]-tri[k])
    points=np.concatenate([points,tri[abs(tri[:,:,0]-x)<1e-8]])
    return np.array([points[:,1].min(),points[:,1].max()])

def main():
    p=argparse.ArgumentParser()
    for k in ['model','baseline','config','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();c=json.loads(a.config.read_text());od,ob=read_glb(a.baseline);nd,nb=read_glb(a.model)
    old,new=parts(od),parts(nd);assert old.keys()==new.keys()
    assert od['materials']==nd['materials'] and od['samplers']==nd['samplers']
    changed=[]; normals=[];ot=[];nt=[]
    for name in old:
        assert len(old[name])==len(new[name])
        for u,v in zip(old[name],new[name]):
            assert u['attributes'].keys()==v['attributes'].keys()
            ix=arrays(od,ob,u['indices']);assert np.array_equal(ix,arrays(nd,nb,v['indices']))
            material=od['materials'][u['material']]['name'];protected=material=='Actual finite oral lining' or material.startswith('Own original side eye pixels')
            for key in u['attributes']:
                x,y=arrays(od,ob,u['attributes'][key]),arrays(nd,nb,v['attributes'][key]);assert x.shape==y.shape and np.isfinite(y).all()
                if name!='Reference_head_body' or key not in ['POSITION','NORMAL']: assert np.array_equal(x,y),(name,key)
                if name=='Reference_head_body' and key=='POSITION':
                    assert np.array_equal(x[:,1:],y[:,1:]); ot.append(x[ix.reshape(-1,3)]);nt.append(y[ix.reshape(-1,3)])
                    for xx,yy in zip(x[np.any(x!=y,axis=1)],y[np.any(x!=y,axis=1)]):
                        f=abs(float(xx[2]))/(c['head_span_m']/2)
                        assert xx[0]>=c['bridge']['axial_guard_m'][0] and c['bridge']['span_rise'][0]-1e-6<f<c['bridge']['span_fall'][1]+1e-6
                        assert 0<yy[0]-xx[0]<=c['bridge']['maximum_forward_shift_m']+1e-7
                        changed.append(dict(old=xx.tolist(),new=yy.tolist(),half_span_fraction=f))
                if protected:
                    if key!='NORMAL':assert np.array_equal(x,y),(material,key)
                    else:
                        q=x/np.linalg.norm(x,axis=1)[:,None];r=y/np.linalg.norm(y,axis=1)[:,None]
                        angle=2*np.arcsin(np.minimum(1,np.linalg.norm(q-r,axis=1)/2))
                        normals.append(dict(material=material,maximum_direction_difference_degrees=float(angle.max()*180/np.pi)))
    assert changed and min(x['half_span_fraction'] for x in changed)<.4 and max(x['half_span_fraction'] for x in changed)>.75
    ot,nt=np.concatenate(ot),np.concatenate(nt)
    xs=np.unique(np.r_[ot[:,:,0].ravel(),nt[:,:,0].ravel(),np.linspace(.70,1.032,1501)]);xs=xs[(xs>=.70)&(xs<=1.032)]
    xs=np.unique(np.r_[xs,(xs[:-1]+xs[1:])/2]);errors=[float(abs(envelope(ot,x)-envelope(nt,x)).max())for x in xs]
    maximum=max(errors);side=dict(ok=maximum<=2e-6,kind='finite_side_envelope_preservation',model_sha256=sha(a.model),baseline_sha256=sha(a.baseline),maximum_error_m=maximum,tolerance_m=2e-6,sections=len(xs),scope='Finite triangle sections; actual same-camera GPU masks separately checked. Axial coordinates change, up/transverse coordinates remain exact.')
    (a.output.parent/'side-sections.validation.json').write_text(json.dumps(side,indent=2)+'\n');assert side['ok'],side
    result=dict(ok=True,kind='whole_oblique_bridge_scope_guard',model_sha256=sha(a.model),baseline_sha256=sha(a.baseline),config_sha256=sha(a.config),checker_sha256=sha(__file__),body_transverse_vertical_positions_exact=True,all_fin_arrays_and_topology_exact=True,mouth_eye_positions_UV_skin_exact=True,materials_and_samplers_exact=True,changed_exported_points=len(changed),maximum_retraction_m=max(x['new'][0]-x['old'][0]for x in changed),changed_half_span_range=[min(x['half_span_fraction']for x in changed),max(x['half_span_fraction']for x in changed)],protected_normal_assignment_roundtrip=normals,side_sections=side,changes=changed,scope='Whole diagonal bridge shortened axially into crossbar; no lateral neck pinch. Source front, eyes and mouth retained. User review pending.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='changes'}))
if __name__=='__main__':main()
