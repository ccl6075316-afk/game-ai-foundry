"""Blender isolated reduction diagnostic. Same -3e-5 static contact threshold as140.

Not a final fish gate: no claim of continuous-time or complete posed validation.
"""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build

root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assert root.is_relative_to(Path('E:/game-ai-foundry/projects/fishing-2d/plans/reviews').resolve())
report=json.loads((root/'probe.validation.json').read_text())
def read_parts(name):
    vertices=[];faces=[];offset=0
    for row in report[name+'_geometry']:
        p=row['prefix']
        v=np.fromfile(root/(p+'-positions.bin'),dtype='<f4').reshape(-1,3)
        t=np.fromfile(root/(p+'-indices.bin'),dtype='<i4').reshape(-1,3)
        assert len(v)==row['vertices'] and len(t)==row['triangles']
        vertices.extend(v);faces.extend(t+offset);offset+=len(v)
    return np.array(vertices),np.array(faces)
bv,bt=read_parts('body')
tree=BVHTree.FromPolygons(bv.tolist(),bt.tolist(),all_triangles=True)
inside=build(bv,bt)
rows=[]
for name in ['baseline','lips-25','lips-10','lips-3']:
    v,t=read_parts(name);a=v[t]
    probes=np.concatenate([v,a.mean(1),(a[:,0]+a[:,1])*.5,(a[:,1]+a[:,2])*.5,(a[:,2]+a[:,0])*.5])
    distances=[]
    for p in probes:
        _,_,_,distance=tree.find_nearest(Vector(p))
        distances.append(-distance if inside(p) else distance)
    distances=np.array(distances)
    area=np.linalg.norm(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]),axis=1)*.5
    row={'name':name,'triangles':len(t),'vertices':len(v),'samples':len(probes),
         'signed_distance_native_min_max':[float(distances.min()),float(distances.max())],
         'samples_below_minus_3e_5':int((distances<-.00003).sum()),
         'minimum_triangle_area':float(area.min()),'contact_threshold_pass':bool(distances.min()>=-.00003)}
    rows.append(row);print('LIP_CONTACT_PROBE',json.dumps(row),flush=True)
result={'schema_version':1,'scope':'Actual rest-pose body and lip vertices, all edge midpoints and face centres. No dynamic or final asset acceptance.',
        'probe_sha256':hashlib.sha256((root/'probe.validation.json').read_bytes()).hexdigest(),
        'validator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'sign_helper_sha256':hashlib.sha256((Path(__file__).parent/'closed_body_index140.py').read_bytes()).hexdigest(),
        'threshold_native':-.00003,'records':rows}
(root/'contact.validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
