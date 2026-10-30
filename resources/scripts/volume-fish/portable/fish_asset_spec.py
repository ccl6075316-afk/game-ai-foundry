"""Hash-bound portable fish asset recipe and read-only preflight.

Paths resolve against the repository root, never the current working directory.
This is a technical authoring contract, not visual or production acceptance.
"""
from __future__ import annotations
if not __debug__:
    raise RuntimeError('Optimized Python is unsupported: required validation assertions are disabled')

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class SpecError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise SpecError(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def resolve_ref(ref, root=ROOT):
    require(isinstance(ref, dict) and isinstance(ref.get('path'), str), 'Reference requires path and sha256')
    require(bool(re.fullmatch('[0-9a-f]{64}', str(ref.get('sha256', '')))), 'Reference requires lowercase sha256')
    root = Path(root).resolve()
    path = (root / ref['path']).resolve()
    require(path.is_relative_to(root), 'Reference escapes repository root: ' + ref['path'])
    require(path.is_file(), 'Missing reference: ' + str(path))
    require(sha(path) == ref['sha256'], 'Stale reference hash: ' + str(path))
    return path

def load_spec(path, root=ROOT):
    return load_spec_snapshot(path, root)[0]

def load_spec_snapshot(path, root=ROOT):
    raw = Path(path).read_bytes()
    spec = json.loads(raw)
    require(spec.get('kind') == 'fish_asset_finalization_spec' and spec.get('version') in (1, 2), 'Unsupported fish asset spec kind/version')
    require(isinstance(spec.get('inputs'), dict), 'inputs must be an object')
    for key in ('source_blend', 'reference_glb', 'atlas', 'packing_report'):
        require(key in spec['inputs'], 'Missing input ' + key)
    require(isinstance(spec.get('source_mesh_name'), str) and spec['source_mesh_name'], 'source_mesh_name required')
    require(isinstance(spec.get('expected'), dict), 'expected inventory object required')
    require(isinstance(spec.get('parts'), list) and spec['parts'], 'Explicit nonempty parts required')
    names = set(); keys = set()
    for part in spec['parts']:
        require(isinstance(part, dict), 'Part must be an object')
        for key in ('name', 'role', 'source_node'):
            require(isinstance(part.get(key), str) and part[key], 'Part requires ' + key)
        require(type(part.get('source_surface')) is int and part['source_surface'] >= 0, 'Part requires nonnegative source_surface')
        require(part['name'] not in names, 'Duplicate part name')
        key = (part['source_node'], part['source_surface'])
        require(key not in keys, 'Duplicate source node/surface declaration')
        names.add(part['name']); keys.add(key)
        if 'opaque_uv' in part:
            require(type(part['opaque_uv']) is bool, 'opaque_uv must be boolean')
            require(part['opaque_uv'] or part['role'] not in ('body','body_skin','mouth','oral_cavity'), 'Body/mouth opacity cannot be disabled')
    return spec, hashlib.sha256(raw).hexdigest()

def input_paths(spec, root=ROOT):
    return {key: resolve_ref(ref, root) for key, ref in spec['inputs'].items()}

def inspect_reference(path):
    from glb_io import read_glb, arrays, validate_skin_attributes
    import numpy as np
    doc, binary = read_glb(path)
    require(len(doc.get('meshes', [])) == 1, 'Only one packed mesh supported')
    mesh = doc['meshes'][0]
    require(len(mesh['primitives']) == 1, 'Only one packed surface supported')
    p = mesh['primitives'][0]
    require(type(p.get('material')) is int and p['material'] == 0, 'Packed primitive must bind material zero')
    require(p.get('mode', 4) == 4 and 'indices' in p, 'Indexed triangle primitive required')
    require(set(p['attributes']) == {'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}, 'Unsupported packed attributes')
    attrs = {k: arrays(doc, binary, a) for k, a in p['attributes'].items()}
    count = len(attrs['POSITION']); indices = arrays(doc, binary, p['indices']).reshape(-1)
    require(count > 0 and all(len(a) == count and np.isfinite(a).all() for a in attrs.values()), 'Invalid attribute rows')
    require(len(indices) > 0 and len(indices) % 3 == 0 and set(indices) == set(range(count)), 'Indices must cover every source vertex')
    nodes = [n for n in doc['nodes'] if 'mesh' in n]
    require(len(nodes) == 1 and nodes[0]['mesh'] == 0 and 'skin' in nodes[0], 'One skinned mesh owner required')
    require(len(doc.get('skins', [])) == 1 and nodes[0]['skin'] == 0, 'One skin required')
    joints = doc['skins'][0]['joints']
    node_names = [node.get('name') for node in doc['nodes']]
    require(all(node_names) and len(node_names) == len(set(node_names)), 'Named unique nodes required')
    clip_names = [clip.get('name') for clip in doc.get('animations',[])]
    require(all(clip_names) and len(clip_names) == len(set(clip_names)), 'Named unique clips required')
    names = [doc['nodes'][j].get('name') for j in joints]
    require(all(names) and len(names) == len(set(names)), 'Named unique joints required')
    validate_skin_attributes(doc, binary, p, len(joints))
    from glb_io import material_semantics
    material = material_semantics(doc)
    wanted = {'alphaMode':'MASK','alphaCutoff':.5,'doubleSided':False,'roughnessFactor':1,'metallicFactor':0,'specularFactor':0,'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071,'baseColorFactor':[1,1,1,1],'texture_texCoord':0,'emissiveFactor':[0,0,0]}
    require(material == wanted, 'Unsupported material; exact guarded MASK nearest-pixel contract required')
    return {'mesh_count':1, 'surface_count':1, 'vertices':count, 'triangles':len(indices)//3, 'bones':len(joints), 'clips':len(doc.get('animations', [])), 'animation_channels':sum(len(a['channels']) for a in doc.get('animations', [])), 'node_count':len(doc['nodes'])}

def declared_parts(spec, packing, inventory):
    require(any(c.get('sha256') == spec['inputs']['reference_glb']['sha256'] for c in packing.get('candidates', {}).values()), 'Packing report does not bind reference GLB')
    rows = packing.get('parts', [])
    declarations = {(p['source_node'], p['source_surface']): p for p in spec['parts']}
    require(len(rows) == len(declarations), 'Packing/declaration part count differs')
    verts = set(); indices = set(); result = []
    for pid, row in enumerate(rows, 1):
        key = (row['node'], row['surface'])
        require(key in declarations, 'Missing declared part ' + str(key))
        part = declarations.pop(key)
        start, end = row['new_vertex_range']; i0, i1 = row['new_index_range']
        require(all(type(x) is int for x in (start,end,i0,i1)) and 0 <= start < end <= inventory['vertices'] and 0 <= i0 < i1 <= inventory['triangles']*3 and i0%3 == i1%3 == 0, 'Invalid part ranges')
        vr = set(range(start,end)); ir = set(range(i0,i1))
        require(not verts.intersection(vr) and not indices.intersection(ir), 'Overlapping part ranges')
        verts.update(vr); indices.update(ir)
        result.append({'part_id':pid, 'name':part['name'], 'role':part['role'], 'logical_name':part.get('logical_name',part['name']), 'opaque_uv':part.get('opaque_uv',part['role'] in ('body','body_skin','mouth','oral_cavity')), 'source_node':row['node'], 'source_surface':row['surface'], 'source_vertex_start':start, 'vertex_count':end-start, 'index_start':i0, 'index_count':i1-i0, 'source_model_sha256':spec['inputs']['reference_glb']['sha256']})
    require(not declarations and verts == set(range(inventory['vertices'])) and indices == set(range(inventory['triangles']*3)), 'Parts must cover full vertex/index inventory')
    return result

def allowed_output(path, root=ROOT):
    path = Path(path).resolve(); root = Path(root).resolve()
    if any(path.is_relative_to(root/name) and path != root/name for name in ('work','output')):
        return True
    if path.is_relative_to(root/'projects'):
        parts = path.relative_to(root/'projects').parts
        return len(parts) >= 3 and parts[1] == 'experiments'
    return False

def artifact_output(path, inputs=(), root=ROOT):
    path = Path(path).resolve(); inputs = {Path(p).resolve() for p in inputs}
    require(allowed_output(path, root), 'Output outside work/output/projects/<project>/experiments')
    require(path not in inputs and not any(path in item.parents for item in inputs), 'Output aliases an input')
    require(not path.exists(), 'Fresh output required: ' + str(path))
    return path

def fresh_outputs(paths, inputs, root=ROOT):
    paths = [Path(p).resolve() for p in paths]
    require(len(set(paths)) == len(paths), 'Outputs alias each other')
    return [artifact_output(path, inputs, root) for path in paths]

def preflight(spec_path, root=ROOT):
    spec, spec_digest = load_spec_snapshot(spec_path, root); inputs = input_paths(spec, root)
    inventory = inspect_reference(inputs['reference_glb'])
    allowed = set(inventory) | {'source_mesh_objects'}
    for key, expected in spec['expected'].items():
        require(key in allowed and type(expected) is int and expected >= 0, 'Unknown/invalid expected count: ' + key)
        if key in inventory:
            require(inventory[key] == expected, f'Expected {key}={expected}, measured {inventory[key]}')
    packing = json.loads(inputs['packing_report'].read_text())
    require(packing.get('atlas', {}).get('sha256') == spec['inputs']['atlas']['sha256'], 'Packing report does not bind atlas')
    parts = declared_parts(spec, packing, inventory)
    from glb_io import read_glb, arrays
    doc, binary = read_glb(inputs['reference_glb'])
    primitive = doc['meshes'][0]['primitives'][0]
    indices = arrays(doc, binary, primitive['indices']).reshape(-1)
    for part in parts:
        lo = part['source_vertex_start']; hi = lo + part['vertex_count']
        chunk = indices[part['index_start']:part['index_start']+part['index_count']]
        require(bool(((chunk >= lo) & (chunk < hi)).all()), 'Triangle escapes declared logical part')
    image = doc['images'][0]; view = doc['bufferViews'][image['bufferView']]
    payload = binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
    require(hashlib.sha256(payload).hexdigest() == spec['inputs']['atlas']['sha256'], 'Atlas bytes differ from hash-bound reference image')
    require(sha(spec_path) == spec_digest, 'Spec changed during preflight')
    return {'schema_version':1,'ok':True,'command':'fish_asset_preflight','stage':'validate','status':'done','next_action':'none','inputs':{k:str(v) for k,v in inputs.items()},'outputs':[], 'summary':{'spec_sha256':spec_digest,'inventory':inventory,'parts':parts, 'source_mesh_objects':'checked in Blender build, not inferred from GLB'},'failures':[]}

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--spec',type=Path,required=True); p.add_argument('--json',action='store_true'); args = p.parse_args()
    try:
        result = preflight(args.spec)
    except (ValueError, AssertionError, KeyError, OSError) as error:
        result = {'schema_version':1,'ok':False,'command':'fish_asset_preflight','stage':'validate','status':'blocked','next_action':'fix_input','inputs':{'spec':str(args.spec)},'outputs':[],'summary':{},'failures':[{'kind':'validation','code':'fish_spec_invalid','message':str(error)}]}
    print(json.dumps(result,indent=2)); return 0 if result['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
