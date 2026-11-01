"""Blender structural/deviation/contact diagnostics for whole-fish low budgets."""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assert root.is_relative_to(Path('E:/game-ai-foundry/projects/fishing-2d/plans/reviews').resolve())
records=[]
for budget in [1000,3000,6000]:
    path=root/('low-'+str(budget)+'.json');data=json.loads(path.read_text());parts=[];body=next(n for n in data['nodes'] if n['name']=='Closed_body');v=[];t=[];offset=0
    for p in body['surfaces']:
        vv=np.array(p['positions']);tt=np.array(p['indices']).reshape(-1,3);v.extend(vv);t.extend(tt+offset);offset+=len(vv)
    bv=np.array(v);bt=np.array(t);closed=True;error=''
    try:inside=build(bv,bt)
    except AssertionError as exc:closed=False;error=str(exc)
    tree=BVHTree.FromPolygons(bv.tolist(),bt.tolist(),all_triangles=True)
    for node in data['nodes']:
        for p in node['surfaces']:
            v=np.array(p['positions']);tri=np.array(p['indices']).reshape(-1,3);a=v[tri]
            areas=np.linalg.norm(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]),axis=1)*.5
            weights=np.array(p['weights'])
            row={'node':node['name'],'surface':p['surface'],'triangles':len(tri),'vertices':len(v),'finite':bool(np.isfinite(v).all()),'zero_area_triangles':int((areas<=1e-17).sum()),'weight_sum_error_max':float(abs(weights.sum(1)-1).max()),'source_projection_distance_native_max':p['source_projection_distance_native_max']}
            if node['name']=='Source_lips139' and closed:
                probes=np.concatenate([v,a.mean(1),(a[:,0]+a[:,1])*.5,(a[:,1]+a[:,2])*.5,(a[:,2]+a[:,0])*.5]);dist=[]
                for point in probes:
                    _,_,_,distance=tree.find_nearest(Vector(point));dist.append(-distance if inside(point) else distance)
                dist=np.array(dist);row['lip_static_contact']={'samples':len(dist),'signed_min_max':[float(dist.min()),float(dist.max())],'below_minus_3e_5':int((dist<-.00003).sum()),'threshold_pass':bool(dist.min()>=-.00003)}
            parts.append(row)
    record={'budget':budget,'actual_triangles':data['actual_triangles'],'body_closed':closed,'closure_error':error,'parts':parts,'candidate_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    records.append(record);print('WHOLE_CHECK',budget,data['actual_triangles'],'closed',closed,'lip_failures',sum(p.get('lip_static_contact',{}).get('below_minus_3e_5',0) for p in parts),flush=True)
(root/'structure.validation.json').write_text(json.dumps({'accepted':False,'production_changed':False,'scope':'Static structure and actual-body sampled lip contact only; no final body/fin/GPU/action gate claimed.','records':records},indent=2)+'\n',encoding='utf8')
