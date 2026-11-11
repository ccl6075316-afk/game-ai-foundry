"""Thin the explicitly reopened caudal free rim in the current editable source."""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'resources/scripts/volume-fish/portable'), str(ROOT/'resources/scripts/volume-fish')]
from glb_io import read_glb, arrays

def packed_arrays(path, spec):
    doc, blob = read_glb(path)
    node = next(n for n in doc['nodes'] if 'mesh' in n)
    primitive = doc['meshes'][node['mesh']]['primitives'][0]
    attrs = {key: arrays(doc, blob, primitive['attributes'][key])
             for key in ('POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0')}
    indices = arrays(doc, blob, primitive['indices']).reshape(-1).astype(int)
    parts = []
    for row in doc['extras']['geometry_parts']:
        parts.append(dict(name=row['logical_name'],
            vertex_range=[row['vertex_start'], row['vertex_start']+row['vertex_count']],
            index_range=[row['index_start'], row['index_start']+row['index_count']]))
    return doc, blob, node, primitive, parts, attrs, indices, None, {'triangles': len(indices)//3}
from export_packed_fish_source import SOURCE_VERTEX, EXACT_NORMAL_ATTRIBUTE, geometry_signature, normal_attribute_signature, float_uv_signature, part_signature, material_signature
from export_source import export_source
from source_snapshot import rig_action_snapshot

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
work = a.work.resolve()
state = json.loads((work/'manifest.json').read_text())
old = work/'source-r1'
out = work/'tail-r3'
assert not out.exists() and work.parent == ROOT/'work'
plan = json.loads((old/'review.plan.json').read_text())
doc, blob, node, primitive, parts, attrs, indices, names, expected = packed_arrays(old/'fish.glb', json.loads((work/'parts-spec.json').read_text()))
part = next(row for row in parts if row['name'] == 'Caudal_mesh')
tail_ids = np.arange(*part['vertex_range'])
triangles = indices[slice(*part['index_range'])].reshape(-1,3)
positions = attrs['POSITION'].copy()
normals = attrs['NORMAL'].copy()
before = positions.copy()
domain = json.loads((ROOT/state['root_domain']['path']).read_text())['current_export_domains']['Caudal_mesh']
root_ids = np.array(domain['ids'])
start = float(before[root_ids,0].min()) - .003
end = -.398 if state['species'] == 'red_seabream' else -.4195
edge_mm = .45
scale = plan['model_scale']*1000
groups = {}
for i in tail_ids:
    key = tuple(np.round(before[i,:2],6))
    groups.setdefault(key, []).append(int(i))
stations = []
for ids in groups.values():
    xyz = before[ids]
    low, high = float(xyz[:,2].min()), float(xyz[:,2].max())
    width = high-low
    if width < 1e-9:
        continue
    x = float(xyz[0,0])
    t = np.clip((start-x)/(start-end),0,1)
    amount = t*t*(3-2*t)
    target = width*(1-amount) + min(width,edge_mm/scale)*amount
    center = (low+high)/2
    if amount > 0:
        positions[ids,2] = center+(xyz[:,2]-center)*target/width
    stations.append(dict(x=x,y=float(xyz[0,1]),before_mm=width*scale,after_mm=target*scale))
field = json.loads((work/'tail-field.json').read_text())
assert field['baseline_sha256'] == sha(old/'fish.glb')
for i, factor in zip(field['ids'], field['factors']):
    if factor < 1-1e-7:
        positions[i,2] = before[i,2]*factor
assert np.array_equal(positions[root_ids],before[root_ids])
# Recompute only affected tail normals, retaining original hard-edge groups.
changed = np.any(positions!=before,axis=1)
normal_groups = {}
for i in tail_ids:
    key = (*np.round(before[i],6), *np.round(normals[i],5))
    normal_groups.setdefault(key,[]).append(int(i))
sums = np.zeros_like(positions,dtype=float)
for tri in triangles:
    q = positions[tri].astype(float)
    cross = np.cross(q[1]-q[0],q[2]-q[0])
    for i in tri:
        sums[i] += cross
for ids in normal_groups.values():
    if not np.any(changed[ids]):
        continue
    vector = sums[ids].sum(axis=0)
    assert np.linalg.norm(vector)>1e-12
    normals[ids] = vector/np.linalg.norm(vector)
bpy.ops.wm.open_mainfile(filepath=str(old/'fish.blend'))
ob = next(o for o in bpy.data.objects if o.type=='MESH')
mesh = ob.data
assert geometry_signature(ob)==mesh['foundry_normal_geometry_sha256']
assert normal_attribute_signature(ob)==mesh['foundry_exact_normal_sha256']
frozen = [float_uv_signature(mesh),part_signature(mesh),material_signature(mesh.materials[0]),rig_action_snapshot()]
source_ids = [int(round(v.value)) for v in mesh.attributes[SOURCE_VERTEX].data]
for vertex, source_id in zip(mesh.vertices,source_ids):
    original = before[source_id]
    assert np.max(np.abs(np.array(vertex.co)-original[[0,2,1]]*[1,-1,1]))<1e-7
    if changed[source_id]:
        q = positions[source_id]
        vertex.co = (float(q[0]),float(-q[2]),float(q[1]))
custom = []
for loop in mesh.loops:
    source_id = source_ids[loop.vertex_index]
    current = mesh.attributes[EXACT_NORMAL_ATTRIBUTE].data[loop.index]
    assert np.max(np.abs(np.array(current.vector)-attrs['NORMAL'][source_id]))<1e-7
    current.vector = normals[source_id].tolist()
    n = normals[source_id]
    custom.append((float(n[0]),float(-n[2]),float(n[1])))
mesh.normals_split_custom_set(custom)
mesh.update()
assert frozen == [float_uv_signature(mesh),part_signature(mesh),material_signature(mesh.materials[0]),rig_action_snapshot()]
mesh['foundry_normal_geometry_sha256'] = geometry_signature(ob)
mesh['foundry_exact_normal_sha256'] = normal_attribute_signature(ob)
out.mkdir()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
export = export_source(out/'fish.glb')
nd,nb,nn,np_,nparts,nattrs,ni,_,ne = packed_arrays(out/'fish.glb',json.loads((work/'parts-spec.json').read_text()))
assert np.array_equal(ni,indices)
assert np.array_equal(nattrs['POSITION'],positions)
assert np.array_equal(nattrs['NORMAL'],normals)
for key in ('TEXCOORD_0','JOINTS_0','WEIGHTS_0'):
    assert np.array_equal(nattrs[key],attrs[key])
for key in ('nodes','skins','animations','materials','textures','samplers'):
    assert nd.get(key)==doc.get(key),key
def image_bytes(d,b):
    v=d['bufferViews'][d['images'][0]['bufferView']]
    start=v.get('byteOffset',0)
    return b[start:start+v['byteLength']]
assert image_bytes(nd,nb)==image_bytes(doc,blob)
old_tri = before[triangles].astype(float)
new_tri = positions[triangles].astype(float)
old_area=np.linalg.norm(np.cross(old_tri[:,1]-old_tri[:,0],old_tri[:,2]-old_tri[:,0]),axis=1)
new_area=np.linalg.norm(np.cross(new_tri[:,1]-new_tri[:,0],new_tri[:,2]-new_tri[:,0]),axis=1)
assert np.all(new_area[old_area>1e-12]>1e-12)
result = dict(ok=True,species=state['species'],model_sha256=sha(out/'fish.glb'),source_sha256=sha(out/'fish.blend'),
 baseline_model_sha256=sha(old/'fish.glb'),baseline_source_sha256=sha(old/'fish.blend'),
 changed_vertices=int(changed.sum()),root_vertices_exact=len(root_ids),frozen_noncaudal_geometry=True,
 source_uv_skin_rig_material_pixels_exact=True,side_silhouette_xy_exact=True,triangles=expected['triangles'],
 parameters=dict(start_x=start,thin_rim_x=end,edge_cap_mm=edge_mm,transition='cubic smoothstep on axial distance'),
 thickness_stations=stations,export=export,
 scope='User-authorized central caudal rim repair. 0.45 mm is an artistic finite-edge target, not a species tissue measurement. Full current gates and visual review follow.')
(out/'tail-authoring.validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('ok','species','model_sha256','changed_vertices','root_vertices_exact')}))
