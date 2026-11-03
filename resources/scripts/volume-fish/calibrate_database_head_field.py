"""Calibrate a finite interpolation error against the unchanged external target."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays
from audit_transverse_width import section
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main(a):
    root=a.directory.resolve();candidate=root/'material-r1';model=candidate/'fish.glb';blend=candidate/'fish.blend';initial=json.loads((root/'width-r1/deformation.plan.json').read_text());assert initial['species']=='rainbow_trout','This finite-error regression uses rainbow-specific planes, never apply it to another fish';head=json.loads((root/'gates-r1/head-direct-reference.plan.json').read_text());item=head['items'][0];wanted=next(w for u,w in item['target_half_width_envelope'] if abs(u-.94)<1e-8)
    d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);normal=arrays(d,b,pr['attributes']['NORMAL']);idx=arrays(d,b,pr['indices']).reshape(-1);body=np.concatenate([idx[p['index_start']:p['index_start']+p['index_count']] for p in d['extras']['geometry_parts'] if p['role']in ['body_skin','mouth']]);lo,hi=float(v[:,0].min()),float(v[:,0].max());knots=[lo,.38,.44,.47,hi]
    def positions(gain):
        f=PchipInterpolator(knots,[1,1,gain,1,1]);new=v.copy();new[:,2]*=f(v[:,0]);return new,f
    def error(gain):return np.ptp(section(positions(gain)[0],body,.44)[:,2])/2-wanted
    gain=float(brentq(error,.8,1.2,xtol=1e-12));new,f=positions(gain);g=f(v[:,0]);dg=f.derivative()(v[:,0]);nn=normal.astype(float).copy();nn[:,0]-=v[:,2]*dg/g*normal[:,2];nn[:,2]/=g;nn/=np.linalg.norm(nn,axis=1)[:,None]
    tri=body.reshape(-1,3);fn=np.cross(new[tri[:,1]]-new[tri[:,0]],new[tri[:,2]]-new[tri[:,0]]);fn/=np.maximum(np.linalg.norm(fn,axis=1)[:,None],1e-30);assert np.all((fn*nn[tri].mean(1)).sum(1)>0)
    plan={**initial,'stage':'finite-head-calibration-r2','inputs':{**initial['inputs'],'model':{'path':str(model),'sha256':sha(model)},'blend':{'path':str(blend),'sha256':sha(blend)},'frozen_head_target':{'path':str(root/'gates-r1/head-direct-reference.plan.json'),'sha256':sha(root/'gates-r1/head-direct-reference.plan.json')}},'old_positions_gltf':v.tolist(),'new_positions_gltf':new.tolist(),'new_normals_gltf':nn.astype('float32').tolist(),'finite_reference_calibration':{'native_x_knots':knots,'gain':gain,'target_halfwidth_at_u094':wanted,'actual_before':float(np.ptp(section(v,body,.44)[:,2])/2),'actual_after':float(np.ptp(section(new,body,.44)[:,2])/2),'target_unchanged':True,'tolerance_unchanged':item['envelope_halfwidth_tolerance_native'],'scope':'Finite low-poly interpolation correction within x=.38...47; x<=.38 and x>=.47 exactly retained. No reference alteration, extra mesh or budget increase.'}}
    out=root/'width-r2';assert not out.exists();out.mkdir();(out/'deformation.plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'ok':True,'gain':gain,'target_halfwidth':wanted,'output':str(out)}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True,type=Path);main(p.parse_args())
