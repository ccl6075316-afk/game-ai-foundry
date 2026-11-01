"""Blender local diagnostics; this is explicitly not a whole-fish acceptance gate."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build
repo=Path(__file__).resolve().parents[3]
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
assert root==(repo/'projects/fishing-2d/plans/reviews/fish-volume-budget-v3').resolve()
config=json.loads((repo/'resources/volume-fish/volume-budget-study-v3.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def geometry(node):
    vertices=[];triangles=[];offset=0
    for p in node['surfaces']:
        v=np.array(p['positions']);t=np.array(p['indices']).reshape(-1,3)
        vertices.extend(v);triangles.extend(t+offset);offset+=len(v)
    return np.array(vertices),np.array(triangles)
records=[]
for species,settings in config['species'].items():
    folder=root/species;source=json.loads((folder/'source.validation.json').read_text());structure=json.loads((folder/'structure.validation.json').read_text());items=[]
    for budget in settings['whole_fish_triangle_budgets']:
        path=folder/f'low-{budget}.json';data=json.loads(path.read_text());nodes={n['name']:n for n in data['nodes']}
        assert data['source_sha256']==sha(folder/'source.validation.json')
        parts=[]
        for node in data['nodes']:
            for p in node['surfaces']:
                vertices=np.array(p['positions']);normals=np.array(p['normals']);weights=np.array(p['weights']);triangles=np.array(p['indices']).reshape(-1,3)
                assert np.isfinite(vertices).all() and np.isfinite(normals).all() and np.isfinite(weights).all()
                assert (weights>=0).all() and abs(weights.sum(1)-1).max()<1e-12
                assert triangles.min()>=0 and triangles.max()<len(vertices)
                part={'node':node['name'],'surface':p['surface'],'triangles':p['triangles'],'vertices':len(vertices),'finite':True,'weight_sum_error_max':float(abs(weights.sum(1)-1).max())}
                parts.append(part)
        body_v,body_t=geometry(nodes['Closed_body']);inside=build(body_v,body_t)
        tree=BVHTree.FromPolygons(body_v.tolist(),body_t.tolist(),all_triangles=True)
        lip=None
        if 'Source_lips139' in nodes:
            v,t=geometry(nodes['Source_lips139']);a=v[t]
            probes=np.concatenate([v,a.mean(1),(a[:,0]+a[:,1])*.5,(a[:,1]+a[:,2])*.5,(a[:,2]+a[:,0])*.5]);dist=[]
            for point in probes:
                _,_,_,distance=tree.find_nearest(Vector(point));dist.append(-distance if inside(point) else distance)
            dist=np.array(dist)
            lip={'samples':len(dist),'signed_min_native':float(dist.min()),'signed_max_native':float(dist.max()),'negative_samples':int((dist<0).sum()),'scope':'Vertices, all edge midpoints and face centres against the actual reduced closed body, rest pose only. No dynamic or continuous proof.'}
            if species=='zander':lip['samples_below_existing_zander_minus_3e_5']=int((dist<-.00003).sum())
        body_errors=[]
        for name in settings['body_nodes']:
            source_node=next(n for n in source['nodes'] if n['name']==name)
            cv,ct=geometry(nodes[name]);ctree=BVHTree.FromPolygons(cv.tolist(),ct.tolist(),all_triangles=True)
            sampled=[]
            for p in source_node['surfaces']:
                vv=np.fromfile(folder/p['attributes']['0'],dtype='<f4').reshape(-1,3)
                tt=np.fromfile(folder/p['attributes']['12'],dtype='<i4').reshape(-1,3)
                centers=vv[tt].mean(1);indices=np.linspace(0,len(centers)-1,min(4000,len(centers)),dtype=int)
                sampled.extend(centers[indices])
            distances=np.array([ctree.find_nearest(Vector(point))[3] for point in sampled])
            scale=source_node['world_axis_scales'][0]
            body_errors.append({'node':name,'source_face_centre_samples':len(sampled),'distance_m_p95':float(np.quantile(distances,.95)*scale),'distance_m_max':float(distances.max()*scale),'scope':'Deterministic sampled one-way closest-surface distance; not a Hausdorff or visual acceptance criterion.'})
        measured=next(c for c in structure['candidates'] if c['budget']==budget)
        body_volume_changes=[]
        for measurement,check in zip(structure['body_measurements'],measured['body_checks']):
            assert measurement['node']==check['node']
            body_volume_changes.append({'node':check['node'],'fractional_volume_change':check['native_volume']/measurement['native_volume']-1 if check['native_volume'] is not None and measurement['native_volume'] else None})
        items.append({'budget':budget,'recipe_sha256':sha(path),'parts':parts,'lip_contact_diagnostic':lip,'body_surface_distance':body_errors,'body_volume_changes':body_volume_changes})
        print('LOCAL_DIAGNOSTIC',species,budget,'lip_min',lip['signed_min_native'] if lip else 'not applicable',flush=True)
    records.append({'species':species,'candidates':items})
(root/'local-checks.validation.json').write_text(json.dumps({'schema_version':1,'records':records,'accepted':False,'production_ready':False,'scope':'Finite arrays, normalized native weights, sampled body deviation and rest-pose lip support. Full fin/body/GPU/action/finalization gates NOT run.','checker_sha256':sha(__file__)},indent=2)+'\n',encoding='utf8')
