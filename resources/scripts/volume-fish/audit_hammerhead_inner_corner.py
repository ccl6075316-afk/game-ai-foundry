"""Independent whole-array scope guard for an accepted-side/local-top repair."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from portable.glb_io import read_glb,arrays

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest();c=json.loads(a.config.read_text());roi=c['inner_corner'];od,ob=read_glb(a.baseline);nd,nb=read_glb(a.model);parts=lambda d:{n['name']:d['meshes'][n['mesh']]['primitives']for n in d['nodes']if'mesh'in n};old,new=parts(od),parts(nd);assert old.keys()==new.keys();assert od['materials']==nd['materials']and od['samplers']==nd['samplers'];changed=[];normals=[]
    for name in old:
        assert len(old[name])==len(new[name])
        for u,v in zip(old[name],new[name]):
            assert u['attributes'].keys()==v['attributes'].keys();assert np.array_equal(arrays(od,ob,u['indices']),arrays(nd,nb,v['indices']));material=od['materials'][u['material']]['name'];protected=material=='Actual finite oral lining'or material.startswith('Own original side eye pixels')
            for key in u['attributes']:
                x,y=arrays(od,ob,u['attributes'][key]),arrays(nd,nb,v['attributes'][key]);assert x.shape==y.shape and np.isfinite(y).all()
                if name!='Reference_head_body'or key not in ['POSITION','NORMAL']:assert np.array_equal(x,y),(name,key)
                if name=='Reference_head_body'and key=='POSITION':
                    assert np.array_equal(x[:,[0,1]],y[:,[0,1]])
                    for xx,yy in zip(x[np.any(x!=y,axis=1)],y[np.any(x!=y,axis=1)]):
                        assert roi['axial_rise_m'][0]<xx[0]<roi['axial_fall_m'][1]and roi['span_rise_m'][0]<abs(xx[2])<roi['span_fall_m'][1];assert 0<abs(xx[2])-abs(yy[2])<=roi['inward_m']+1e-7;changed.append(dict(old=xx.tolist(),new=yy.tolist()))
                if protected:
                    if key!='NORMAL':assert np.array_equal(x,y),(material,key)
                    else:
                        q=x/np.linalg.norm(x,axis=1)[:,None];r=y/np.linalg.norm(y,axis=1)[:,None];angle=2*np.arcsin(np.minimum(1,np.linalg.norm(q-r,axis=1)/2));normals.append(dict(material=material,maximum_component_difference=float(abs(x-y).max()),maximum_direction_difference_degrees=float(angle.max()*180/np.pi)))
    assert changed
    result=dict(ok=True,kind='whole_array_inner_corner_scope_guard',model_sha256=sha(a.model),baseline_sha256=sha(a.baseline),config_sha256=sha(a.config),checker_sha256=sha(__file__),projection_pose='REST',body_axial_vertical_positions_exact=True,all_rest_side_projected_triangles_exact=True,all_fin_arrays_and_topology_exact=True,mouth_eye_positions_UV_skin_exact=True,materials_and_samplers_exact=True,changes_restricted_to_declared_medial_rear_patch=True,changed_exported_points=len(changed),maximum_inward_m=max(abs(x['old'][2]-x['new'][2])for x in changed),protected_normal_assignment_roundtrip=normals,changes=changed,scope='Geometry scope proof only. Normal direction differences measured rather than claimed bit exact; current winding/opaque body gate, fin/motion tests and actual top/oblique review remain separate. User partial acceptance belongs to baseline only.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ['changes','scope']}))
if __name__=='__main__':main()
