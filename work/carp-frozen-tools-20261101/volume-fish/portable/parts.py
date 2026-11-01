"""Portable validation-only partitions of an explicit one-surface skinned fish.

No anatomy is inferred from a name. The spec identifies each source surface and
which surfaces are opaque body donors; neither this manifest nor a successful
import substitutes for anatomical, physical, GPU or visual acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from glb_io import read_glb, arrays as accessor

BODY_ROLES = {'body', 'body_skin', 'mouth', 'oral_cavity'}
ROOT = Path(__file__).resolve().parents[4]
OUTPUT_ROOT = ROOT / 'work/fish-portable-tools'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(condition, message):
    if not condition: raise ValueError(message)
def read(path): return json.loads(Path(path).read_text(encoding='utf8'))
def fresh_output(path):
    path = Path(path).resolve()
    from fish_asset_spec import artifact_output
    return artifact_output(path)

def inventory(spec):
    rows = spec.get('parts')
    require(isinstance(rows, list) and bool(rows), 'Explicit nonempty parts inventory required')
    result = {}
    for row in rows:
        require(isinstance(row, dict), 'Part must be an object')
        require(all(isinstance(row.get(k), str) and row[k] for k in ('name', 'role', 'source_node')), 'Part needs name, role and source_node')
        require(type(row.get('source_surface')) is int and row['source_surface'] >= 0, 'Invalid source_surface')
        require('opaque_uv' not in row or type(row['opaque_uv']) is bool, 'opaque_uv must be boolean')
        require(row['role'] not in BODY_ROLES or row.get('opaque_uv', True), 'Body-role surfaces cannot disable opaque UV checks')
        key = (row['source_node'], row['source_surface'])
        require(key not in result, 'Duplicate source surface inventory: ' + str(key))
        result[key] = {**row, 'logical_name': row.get('logical_name', row['name']), 'opaque_uv': row.get('opaque_uv', row['role'] in BODY_ROLES)}
        require(isinstance(result[key]['logical_name'], str) and bool(result[key]['logical_name']), 'logical_name must be nonempty')
    logical_opacity = {}
    for row in result.values():
        name = row['logical_name']
        require(name not in logical_opacity or logical_opacity[name] == row['opaque_uv'], 'Logical group mixes body and nonbody opacity ownership')
        logical_opacity[name] = row['opaque_uv']
    require(any(row['opaque_uv'] for row in result.values()), 'At least one explicit opaque body surface required')
    return result

def packed_arrays(model, spec):
    doc, blob = read_glb(Path(model))
    declared = inventory(spec)
    raw = doc.get('extras', {}).get('geometry_parts')
    require(isinstance(raw, list) and len(raw) == len(declared), 'Missing or extra explicit packed part partitions')
    nodes = [node for node in doc.get('nodes', []) if 'mesh' in node]
    require(len(nodes) == 1 and 'skin' in nodes[0], 'Exactly one skinned mesh node required')
    node = nodes[0]
    require(not any(k in node for k in ('matrix', 'translation', 'rotation', 'scale')), 'Packed mesh transform must be baked identity')
    primitives = doc['meshes'][node['mesh']]['primitives']
    require(len(primitives) == 1 and primitives[0].get('mode', 4) == 4, 'Exactly one triangle surface required')
    primitive = primitives[0]; attrs = primitive['attributes']
    semantics = ('POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0')
    require(set(semantics) <= attrs.keys(), 'Required packed vertex attributes missing')
    values = {name: accessor(doc, blob, attrs[name]) for name in semantics}
    require(not any(doc['accessors'][attrs[k]].get('normalized', False) for k in ('POSITION','NORMAL','TEXCOORD_0','WEIGHTS_0')), 'Normalized attributes unsupported; supply explicit float source arrays')
    for key, lanes in [('POSITION',3),('NORMAL',3),('TEXCOORD_0',2),('JOINTS_0',4),('WEIGHTS_0',4)]:
        require(values[key].ndim == 2 and values[key].shape[1] == lanes, 'Invalid attribute dimensions: '+key)
    count = len(values['POSITION']); indices = accessor(doc, blob, primitive['indices']).reshape(-1).astype(np.int64)
    require(count > 0 and all(len(v) == count and np.isfinite(v).all() for v in values.values()), 'Invalid vertex arrays')
    require(len(indices) > 0 and len(indices) % 3 == 0 and indices.min() >= 0 and indices.max() < count, 'Invalid triangle indices')
    require(np.all(np.abs(values['WEIGHTS_0'].sum(axis=1) - 1) < 1e-5) and np.all(values['WEIGHTS_0'] >= 0), 'Invalid skin weights')
    joints = doc['skins'][node['skin']]['joints']; joint_names = [doc['nodes'][j]['name'] for j in joints]
    require(len(set(joint_names)) == len(joint_names), 'Unique joint names required')
    require(np.all(values['JOINTS_0'] >= 0) and np.all(values['JOINTS_0'] < len(joints)), 'Joint index outside skin')
    vertex_coverage = np.zeros(count, dtype=np.int32); index_coverage = np.zeros(len(indices), dtype=np.int32)
    parts = []; seen = set(); part_ids = set()
    for ordinal, part in enumerate(raw):
        key = (part.get('source_node'), part.get('source_surface', part.get('surface', 0)))
        require(key in declared and key not in seen, 'Missing/duplicate/unlisted source partition: ' + str(key)); seen.add(key)
        row = declared[key]
        require(part.get('role') == row['role'] and part.get('name') == row['name'], 'Packed part name/role differs from explicit spec')
        vr = part.get('vertex_range', [part.get('vertex_start'), (part.get('vertex_start') or 0) + (part.get('vertex_count') or 0)])
        ir = part.get('index_range', [part.get('index_start'), (part.get('index_start') or 0) + (part.get('index_count') or 0)])
        require(isinstance(vr,list) and isinstance(ir,list) and len(vr)==len(ir)==2 and all(type(v) is int and v>=0 for v in [*vr,*ir]), 'Invalid part ranges')
        lo, hi = vr; start, end = ir
        require(lo < hi <= count and start < end <= len(indices) and start % 3 == end % 3 == 0, 'Invalid partition bounds')
        require(np.all((indices[start:end] >= lo) & (indices[start:end] < hi)), 'Part triangle escapes vertex ownership')
        vertex_coverage[lo:hi] += 1; index_coverage[start:end] += 1
        part_id = part.get('part_id', ordinal)
        require(type(part_id) is int and part_id >= 0 and part_id not in part_ids, 'Duplicate/invalid part_id'); part_ids.add(part_id)
        parts.append({'part_id':part_id,'name':row['logical_name'],'source_name':row['name'],'role':row['role'],'source_node':key[0],'source_surface':key[1],'opaque_uv':row['opaque_uv'],'vertex_range':vr,'index_range':ir,'triangles':(end-start)//3})
    require(np.all(vertex_coverage == 1) and np.all(index_coverage == 1), 'Partitions must cover every vertex and index exactly once')
    if '_FOUNDRY_PART_ID' in attrs:
        labels = accessor(doc, blob, attrs['_FOUNDRY_PART_ID']).reshape(-1)
        require(len(labels) == count, 'Part label array length mismatch')
        for part in parts:
            lo, hi = part['vertex_range']; require(np.all(labels[lo:hi] == part['part_id']), 'Frozen labels disagree with metadata')
    actual = {'mesh_count':1,'surface_count':1,'vertices':count,'triangles':len(indices)//3,'bones':len(joints),'clips':len(doc.get('animations',[])),'animation_channels':sum(len(a.get('channels',[])) for a in doc.get('animations',[]))}
    for key, value in spec.get('expected',{}).items():
        if key in actual: require(type(value) is int and value == actual[key], 'Expected '+key+' differs from candidate')
    return doc, blob, node, primitive, parts, values, indices, joint_names, actual

def body_opacity(doc, blob, primitive, parts, values, indices):
    material = doc['materials'][primitive['material']]; mode = material.get('alphaMode','OPAQUE')
    require(mode in ('OPAQUE','MASK') and (mode != 'MASK' or material.get('alphaCutoff',.5)==.5), 'Unsupported material alpha mode/cutoff')
    pbr = material.get('pbrMetallicRoughness',{})
    require(pbr.get('baseColorFactor',[1,1,1,1])[3] == 1, 'Body material factor alpha must equal one')
    require(set(material.get('extensions',{})) <= {'KHR_materials_specular'}, 'Unsupported material extension')
    texref = pbr['baseColorTexture']; require(texref.get('texCoord',0)==0 and not texref.get('extensions'), 'Unsupported body texture coordinate transform')
    texture = doc['textures'][texref['index']]; image = doc['images'][texture['source']]
    require('bufferView' in image and 'uri' not in image, 'Embedded body atlas required')
    view = doc['bufferViews'][image['bufferView']]; image_bytes = blob[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']]
    rgba = np.asarray(Image.open(io.BytesIO(image_bytes)).convert('RGBA')); height,width = rgba.shape[:2]
    sampler = doc['samplers'][texture['sampler']]
    require(sampler.get('magFilter')==9728 and sampler.get('minFilter')==9728, 'Nearest sampling without mipmaps required')
    checked=[]
    for part in parts:
        if not part['opaque_uv']: continue
        start,end = part['index_range']; uv = values['TEXCOORD_0'][np.unique(indices[start:end])]
        require(np.all(uv>=0) and np.all(uv<1), 'Body UV outside atlas; wrapping unverified')
        lo=np.floor(uv.min(axis=0)*[width,height]).astype(int); hi=np.floor(uv.max(axis=0)*[width,height]).astype(int)
        region=rgba[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        require(region.size>0 and np.all(region[:,:,3]==255), 'Body donor UV rectangle contains nonopaque texel')
        checked.append({'name':part['name'],'source_node':part['source_node'],'source_surface':part['source_surface'],'texel_rectangle_inclusive':[lo.tolist(),hi.tolist()],'texels_checked':int(region.shape[0]*region.shape[1]),'alpha_min':255,'alpha_max':255})
    require(bool(checked), 'At least one opaque body rectangle required')
    return {'ok':True,'material_alpha_mode':mode,'body_regions':checked,'image_embedded_sha256':hashlib.sha256(image_bytes).hexdigest(),'rgba_sha256':hashlib.sha256(rgba.tobytes()).hexdigest(),'size':[width,height],'scope':'Every texel in each declared body UV bounding rectangle is alpha255. This does not prove same-pose GPU coverage or anatomical integrity.'}

def freeze(model, spec, output=None):
    model=Path(model).resolve(); doc,blob,node,primitive,parts,values,indices,names,actual=packed_arrays(model,spec)
    result={'ok':True,'schema_version':1,'kind':'fish_portable_part_manifest','model':str(model),'model_sha256':sha(model),'mesh_node':node.get('name',''),'parts':parts,'attributes':{k:v.tolist() for k,v in values.items()},'indices':indices.tolist(),'joint_names':names,'vertex_count':actual['vertices'],'triangles':actual['triangles'],'expected':actual,'body_names':list(dict.fromkeys(p['name'] for p in parts if p['opaque_uv'])),'fin_names':list(dict.fromkeys(p['name'] for p in parts if p['role']=='fin')),'body_opacity':body_opacity(doc,blob,primitive,parts,values,indices),'checker_sha256':sha(__file__),'scope':'Canonical explicit source ownership only. Actual Godot arrays must independently consume every oriented triangle with multiplicity; no anatomical/physical/GPU/visual pass transferred.'}
    if output is not None:
        output=fresh_output(output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True); parser.add_argument('--spec',type=Path,required=True); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--json',action='store_true')
    args=parser.parse_args()
    try:
        from fish_asset_spec import load_spec, input_paths
        spec=load_spec(args.spec); input_paths(spec)
        result=freeze(args.model,spec,args.output)
        print(json.dumps({'ok':True,'command':'portable.parts','status':'done','next_action':'none','outputs':[str(args.output.resolve())],'summary':{'triangles':result['triangles'],'parts':len(result['parts']),'body_surfaces':len(result['body_opacity']['body_regions'])},'failures':[]})); return 0
    except (ValueError,AssertionError,KeyError,IndexError,TypeError,OSError) as error:
        print(json.dumps({'ok':False,'command':'portable.parts','status':'failed','next_action':'fix_input','outputs':[],'failures':[{'kind':'validation','code':'portable_parts_invalid','message':str(error)[:1200]}]})); return 1
if __name__=='__main__': raise SystemExit(main())
