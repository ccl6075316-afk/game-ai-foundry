"""Blender: author measured per-fin local failure-envelope displacements.

Moves only diagnosed non-root geometry and all UV aliases. Actual LBS gain
determines each shift. Original rig/animation/UV/indices/weights stay unchanged.
"""
import argparse,copy,hashlib,json,struct,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from patch_existing_fin_meshes import read,write
from repair_fin_clearance import values
from restore_fin_source_normals import apply_frozen_normals
from triangulate_export_mesh import triangulate_export_mesh
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--envelope',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--max-triangles',type=int,required=True);p.add_argument('--max-local-shift-mm',type=float,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
root=Path(__file__).resolve().parents[3];out=a.output.resolve();assert out.is_relative_to(root/'projects/fishing-2d/experiments')and not out.exists();out.mkdir()
plan=load(a.plan);assert len(plan['items'])==1;spec=plan['items'][0];envelope=load(a.envelope);assert envelope['ok'] and sha(a.plan)==envelope['plan_sha256']
src=Path(spec['model']);blend=src.with_suffix('.blend');assert sha(src)==spec['model_sha256']==envelope['model_sha256'];assert envelope['limits_unchanged']==spec['membrane_clearance']
doc,binary=read(src);original=bytes(binary);changes={}
def put(index,rows):
    accessor=copy.deepcopy(doc['accessors'][index]);binary.extend(b'\0'*(-len(binary)%4));offset=len(binary)
    for row in rows:binary.extend(struct.pack('<fff',*row))
    accessor.update(bufferView=len(doc['bufferViews']),byteOffset=0,count=len(rows),min=[min(q[k]for q in rows)for k in range(3)],max=[max(q[k]for q in rows)for k in range(3)])
    doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(binary)-offset});doc['accessors'].append(accessor);return len(doc['accessors'])-1
for name,row in envelope['records'].items():
    assert name in spec['fins'] and row['all_UV_aliases_included'] and row['minimum_effective_LBS_normal_gain']>.025
    ids=set(row['source_gltf_vertices']);assert not ids&set(row['frozen_root_aliases_excluded'])
    amount=row['proposed_shift_mm'];assert 0<amount<=a.max_local_shift_mm
    axis=Vector(row['axis_gltf']);assert abs(axis.length-1)<1e-6
    node=next(n for n in doc['nodes']if n.get('name')==name and'mesh'in n);pr=doc['meshes'][node['mesh']]['primitives'][0]
    before=[Vector(q)for q in values(doc,binary,pr['attributes']['POSITION'])];after=[q.copy()for q in before];delta=axis*(amount/1000/envelope['scale_m_per_native'])
    for i in ids:after[i]+=delta
    triangles=[v[0]for v in values(doc,binary,pr['indices'])];normals=[Vector()for _ in after]
    for k in range(0,len(triangles),3):
        x,y,z=triangles[k:k+3];normal=(after[y]-after[x]).cross(after[z]-after[x])
        for i in (x,y,z):normals[i]+=normal
    pr['attributes']['POSITION']=put(pr['attributes']['POSITION'],after)
    pr['attributes']['NORMAL']=put(pr['attributes']['NORMAL'],[q.normalized()if q.length>1e-12 else Vector((0,0,1))for q in normals])
    changes[name]={'source_ids':sorted(ids),'before':[before[i]for i in sorted(ids)],'delta':delta,'shift_mm':amount}
assert bytes(binary[:len(original)])==original
model=out/'fish.glb';write(model,doc,binary)
bpy.ops.wm.open_mainfile(filepath=str(blend));source_records=[]
for name,row in changes.items():
    ob=bpy.data.objects[name];triangulation=triangulate_export_mesh(ob);matched=set();moved=[];delta=row['delta']
    for vertex in ob.data.vertices:
        q=Vector((vertex.co.x,vertex.co.z,-vertex.co.y));aliases={i for i,p in enumerate(row['before'])if(q-p).length<2e-6}
        if aliases:
            vertex.co+=Vector((delta.x,-delta.z,delta.y));moved.append(vertex.index);matched.update(aliases)
    assert matched==set(range(len(row['before']))),'GLB/Blender envelope mapping incomplete'
    ob.data.update();source_records.append({'name':name,'source_gltf_ids':row['source_ids'],'blend_vertices':moved,'physical_shift_mm':row['shift_mm'],'exact_export_triangulation':triangulation})
apply_frozen_normals(model,list(changes));bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
count=sum(doc['accessors'][pr['indices']]['count']//3 for mesh in doc['meshes']for pr in mesh['primitives']);assert count<=a.max_triangles
spec.update(model=str(model),model_sha256=sha(model));spec.pop('diagnostic_pose_filter',None)
for fin in spec['fins'].values():fin.pop('diagnostic_outward_axis',None)
plan['scope']='Measured local non-root failure envelope; complete roots, morphology source XY, UVs, skin, rig, original clips and limits retained. Fresh actual full490 still required.'
(out/'fin-gate.plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8')
report={'ok':True,'kind':'local_measured_fin_envelope_authoring','source_model_sha256':sha(src),'model_sha256':sha(model),'blend_sha256':sha(out/'fish.blend'),'envelope_sha256':sha(a.envelope),'triangles':count,'records':source_records,'all_roots_UVs_weights_indices_rig_native_animation_preserved':True,'original_binary_prefix_sha256':hashlib.sha256(original).hexdigest(),'formal_acceptance':False,'remaining':'Fresh source packing/cold export, all final gates and actual visual review.'}
(out/'envelope-repair.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
