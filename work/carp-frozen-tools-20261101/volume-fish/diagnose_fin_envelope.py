"""Blender: collect every failing finite sample and measure actual LBS push gain.

Read-only diagnosis. Root ownership and collision limits are frozen by the plan.
Includes vertices, edge quarters and all four face probes, including UV aliases.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).parent))
from patch_existing_fin_meshes import read
from repair_fin_clearance import values
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--export',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--target-clearance-mm',type=float,default=.04);p.add_argument('--margin-mm',type=float,default=.02);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
plan=load(a.plan);assert len(plan['items'])==1;spec=plan['items'][0];export=load(a.export)
assert sha(spec['model'])==spec['model_sha256']==export['model_sha256']
scale=spec['scale_cm']/100;limits=spec['membrane_clearance'];collar=limits['root_collar_mm']/1000;tol=limits['penetration_tolerance_mm']/1000
targets={n for n,f in spec['fins'].items()if 'diagnostic_outward_axis'in f};assert targets
static=load(next(s['posed_mesh_json']for s in export['samples']if s['action']=='Static'))
rest_raw={n:static['membranes'][n]['rest_vertices_native']for n in targets}
rest={n:[Vector(q)for q in rest_raw[n]]for n in targets}
root_ids={};selected={n:set()for n in targets};failures=[]
for name in targets:
    roots=[Vector(q)for q in static['roots'][name]['points_m']]
    root_ids[name]={i for i,q in enumerate(static['membranes'][name]['vertices_m'])if any((Vector(q)-r).length<1e-8 for r in roots)}
for si,sample in enumerate(export['samples']):
    assert sha(sample['posed_mesh_json'])==sample['sha256'];d=load(sample['posed_mesh_json'])
    verts=[Vector(q)for q in d['body_vertices_m']];faces=d['body_triangles']
    if sum(verts[x].dot(verts[y].cross(verts[z]))for x,y,z in faces)<0:faces=[list(reversed(f))for f in faces]
    tree=BVHTree.FromPolygons(verts,faces,all_triangles=True);lower=[min(v[j]for v in verts)for j in range(3)];upper=[max(v[j]for v in verts)for j in range(3)];ray=Vector((.231,.371,.899)).normalized()
    for name in targets:
        m=d['membranes'][name];vs=[Vector(q)for q in m['vertices_m']];tr=m['triangles'];roots=[Vector(q)for q in d['roots'][name]['points_m']];kd=KDTree(len(roots))
        for i,q in enumerate(roots):kd.insert(q,i)
        kd.balance();ri={i for i,q in enumerate(vs)if kd.find(q)[2]<1e-8};rf=[tr[i:i+3]for i in range(0,len(tr),3)if all(j in ri for j in tr[i:i+3])];rt=BVHTree.FromPolygons(vs,rf,all_triangles=True)if rf else None
        assert rest_raw[name]==m['rest_vertices_native'],'Actual rest vertex order changed between poses'
        probes=[([i],[1.0],'vertex')for i in range(len(vs))];edges=set()
        for k in range(0,len(tr),3):
            ids=tr[k:k+3]
            probes.extend((ids,weights,'face')for weights in ((1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)))
            edges.update(tuple(sorted((x,y)))for x,y in zip(ids,ids[1:]+ids[:1]))
        probes.extend(([x,y],[1-f,f],'edge')for x,y in edges for f in (.25,.5,.75))
        for ids,weights,kind in probes:
            q=sum((vs[i]*w for i,w in zip(ids,weights)),Vector());near,normal,_,distance=tree.find_nearest(q)
            outside=any(q[j]<lower[j]-1e-8 or q[j]>upper[j]+1e-8 for j in range(3));hit,rn,_,_=tree.ray_cast(q,ray)
            sd=-distance if not outside and hit is not None and rn.dot(ray)>0 else distance
            rd=kd.find(q)[2]
            if rt:rd=min(rd,rt.find_nearest(q)[3])
            if rd<=collar and sd>=-collar:continue
            if sd>=-tol:continue
            free=set(ids)-root_ids[name]
            assert free,'Failure is entirely frozen root; source root construction must be repaired first'
            selected[name].update(free)
            failures.append({'sample_index':si,'action':sample['action'],'seconds':sample['seconds'],'fin':name,'kind':kind,'ids':ids,'weights':weights,'signed_mm':sd*1000,'body_normal':list(normal),'outward_gain':m['outward_gain_m_per_native_unit']})
doc,binary=read(spec['model']);records={}
for name,chosen in selected.items():
    if not chosen:continue
    source=next(n for n in doc['nodes']if n.get('name')==name and'mesh'in n);primitive=doc['meshes'][source['mesh']]['primitives'][0];pos=[Vector(q)for q in values(doc,binary,primitive['attributes']['POSITION'])]
    aliases={i:{j for j,q in enumerate(pos)if(q-rest[name][i]).length<2e-6}for i in chosen|root_ids[name]}
    assert all(aliases.values()),'Actual/source vertex mapping incomplete'
    root_aliases=set().union(*(aliases[i]for i in root_ids[name]));moving=set().union(*(aliases[i]for i in chosen));assert not moving&root_aliases,'Frozen root alias selected'
    gains=[];required=[];rows=[]
    for row in failures:
        if row['fin']!=name:continue
        displacement=sum((Vector(row['outward_gain'][i])*w for i,w in zip(row['ids'],row['weights'])if i in chosen),Vector())
        gain=Vector(row['body_normal']).dot(displacement)/scale
        assert gain>.025,(name,'No reliable positive outward LBS gain',gain,row['kind'])
        need=(a.target_clearance_mm-row['signed_mm'])/gain
        gains.append(gain);required.append(need)
        rows.append({k:v for k,v in row.items()if k!='outward_gain'})
    shift=max(required)+a.margin_mm
    records[name]={'source_gltf_vertices':sorted(moving),'actual_vertices':sorted(chosen),'all_UV_aliases_included':True,'frozen_root_aliases_excluded':sorted(root_aliases),'axis_gltf':spec['fins'][name]['diagnostic_outward_axis'],'minimum_effective_LBS_normal_gain':min(gains),'maximum_required_shift_mm':max(required),'proposed_shift_mm':shift,'failed_sample_count':len(rows),'failed_poses':len({(x['action'],x['seconds'])for x in rows}),'worst_penetration_mm':min(x['signed_mm']for x in rows),'failure_descriptors':rows}
result={'ok':True,'kind':'complete_finite_fin_failure_envelope','model':spec['model'],'model_sha256':spec['model_sha256'],'input_export':str(a.export.resolve()),'input_export_sha256':sha(a.export),'plan_sha256':sha(a.plan),'scale_m_per_native':scale,'limits_unchanged':limits,'target_exterior_mm':a.target_clearance_mm,'construction_margin_mm':a.margin_mm,'records':records,'scope':'Every finite descriptor in all declared failed poses, plus original complete roots/UV aliases. Proposed local rest displacement uses actual posed LBS basis; requires source authoring and full current490 revalidation. No pass granted.'}
assert records and not a.output.exists();a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'records':{n:{k:v for k,v in r.items()if k not in ('failure_descriptors','frozen_root_aliases_excluded','source_gltf_vertices','actual_vertices')}for n,r in records.items()}}))
