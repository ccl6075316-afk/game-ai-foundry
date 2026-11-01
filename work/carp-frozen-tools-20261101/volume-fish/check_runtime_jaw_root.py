"""Read-only root contact from actual Godot CPU-skinned jaw-root samples."""
import argparse,hashlib,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=argparse.ArgumentParser();p.add_argument('--export',required=True);p.add_argument('--output',required=True);p.add_argument('--tolerance-cm',type=float,default=.12)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
export=json.loads(Path(a.export).read_text(encoding='utf-8'))
if sha(export['model'])!=export['model_sha256']:raise ValueError('Runtime model hash changed')
rows=[];failures=[]
for sample in export['samples']:
    if sha(sample['posed_mesh_json'])!=sample['sha256']:raise ValueError('Runtime jaw sample hash changed')
    data=json.loads(Path(sample['posed_mesh_json']).read_text(encoding='utf-8'));verts=[Vector(v) for v in data['body_vertices_m']];faces=data['body_triangles']
    volume=sum(verts[i].dot(verts[j].cross(verts[k])) for i,j,k in faces)/6
    if volume<0:faces=[[k,j,i] for i,j,k in faces]
    tree=BVHTree.FromPolygons(verts,faces,all_triangles=True);distances=[]
    for coords in data.get('jaw_root_points_m',[]):
        v=Vector(coords);near,normal,_,d=tree.find_nearest(v);distances.append(d*100*(1 if (v-near).dot(normal)>=0 else -1))
    if not distances:raise ValueError('Missing actual jaw-root skin points')
    ok=max(distances)<=a.tolerance_cm and min(distances)<=0
    rows.append({'action':sample['action'],'seconds':sample['seconds'],'points':len(distances),'minimum_signed_cm':min(distances),'maximum_signed_cm':max(distances),'ok':ok})
    if not ok:failures.append('Jaw root lost contact: '+sample['action']+' '+str(sample['seconds']))
if len(rows)!=32 or {x['action'] for x in rows}!={'Swim','Turn','Ascend','Dive'}:failures.append('Incomplete four-action32-sample evidence')
report={'ok':not failures,'scope':'Posterior jaw root native x+.5<=.909, actual Godot CPU skin; embedded assembly allowed, gap<=tolerance. Not lip occlusion or joint rotation validation.','model_sha256':export['model_sha256'],'export_sha256':sha(a.export),'tolerance_cm':a.tolerance_cm,'sample_count':len(rows),'maximum_gap_cm':max(x['maximum_signed_cm'] for x in rows),'deepest_embedding_cm':min(x['minimum_signed_cm'] for x in rows),'samples':rows,'failures':failures}
Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='samples'}))
if failures:sys.exit(1)
