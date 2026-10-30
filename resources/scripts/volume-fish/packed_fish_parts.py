"""Freeze logical parts of a one-surface fish for validation, never runtime reconstruction."""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb, accessor


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized_parts(doc, body, fins):
    raw = doc.get('extras', {}).get('geometry_parts')
    assert isinstance(raw, list) and len(raw) == 9, 'Explicit nine packed part partitions required'
    nodes = [n for n in doc['nodes'] if 'mesh' in n]
    assert len(nodes) == 1 and 'skin' in nodes[0], 'Packed candidate must have one skinned mesh node'
    node = nodes[0]
    primitives = doc['meshes'][node['mesh']]['primitives']
    assert len(primitives) == 1 and primitives[0].get('mode', 4) == 4, 'One triangle surface required'
    parts = []
    for index, part in enumerate(raw):
        vr = part.get('vertex_range', [part.get('vertex_start'), (part.get('vertex_start') or 0) + (part.get('vertex_count') or 0)])
        ir = part.get('index_range', [part.get('index_start'), (part.get('index_start') or 0) + (part.get('index_count') or 0)])
        role = part.get('role', '')
        name = body if role in ('body_skin', 'mouth', 'body', 'oral_cavity') else part['name']
        surface = int(part.get('source_surface', part.get('surface', 0)))
        assert all(isinstance(v, int) and v >= 0 for v in [*vr, *ir]) and vr[1] > vr[0] and ir[1] > ir[0] and ir[0] % 3 == ir[1] % 3 == 0
        assert name == body or name in fins, 'Unlisted logical part: ' + name
        parts.append({'part_id': part.get('part_id', index), 'name': name, 'source_surface': surface, 'role': role or ('body_skin' if name == body and surface == 0 else 'mouth' if name == body else 'fin'), 'vertex_range': vr, 'index_range': ir})
    assert [p['source_surface'] for p in parts if p['name'] == body] == [0, 1], 'Complete skin and oral body partitions required'
    assert {p['name'] for p in parts} == {body, *fins} and len({*fins}) == 7
    return node, primitives[0], parts


def packed_arrays(model, body, fins):
    doc, blob = read_glb(Path(model))
    node, primitive, parts = normalized_parts(doc, body, fins)
    attrs = primitive['attributes']
    assert {'POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0'} <= attrs.keys()
    arrays = {name: accessor(doc, blob, attrs[name]) for name in ('POSITION', 'NORMAL', 'TEXCOORD_0', 'JOINTS_0', 'WEIGHTS_0')}
    indices = accessor(doc, blob, primitive['indices']).reshape(-1).astype(np.int64)
    count = len(arrays['POSITION'])
    assert all(len(v) == count and np.isfinite(v).all() for v in arrays.values())
    assert count > 0 and len(indices) > 0 and indices.min() >= 0 and indices.max() < count
    assert len(indices) % 3 == 0 and np.all(np.abs(arrays['WEIGHTS_0'].sum(axis=1) - 1) < 1e-5)
    vertex_coverage = np.zeros(count, dtype=np.int32)
    index_coverage = np.zeros(len(indices), dtype=np.int32)
    for part in parts:
        lo, hi = part['vertex_range']; start, end = part['index_range']
        assert hi <= count and end <= len(indices)
        vertex_coverage[lo:hi] += 1; index_coverage[start:end] += 1
        assert np.all((indices[start:end] >= lo) & (indices[start:end] < hi)), 'Part index escapes vertex ownership'
        part['triangles'] = (end - start) // 3
    assert np.all(vertex_coverage == 1) and np.all(index_coverage == 1), 'Part partitions must cover every vertex/index exactly once'
    if '_FOUNDRY_PART_ID' in attrs:
        labels = accessor(doc, blob, attrs['_FOUNDRY_PART_ID']).reshape(-1)
        for part in parts:
            lo, hi = part['vertex_range']
            assert np.all(labels[lo:hi] == part['part_id']), 'Frozen source part attribute disagrees with metadata'
    return doc, blob, node, primitive, parts, arrays, indices


def body_opacity(doc, blob, primitive, parts, arrays, indices, body):
    material = doc['materials'][primitive['material']]
    assert material.get('alphaMode', 'OPAQUE') in ('OPAQUE', 'MASK')
    assert material.get('alphaMode') != 'MASK' or material.get('alphaCutoff', .5) == .5
    pbr = material['pbrMetallicRoughness']
    assert pbr.get('baseColorFactor', [1, 1, 1, 1])[3] == 1
    assert set(material.get('extensions', {})) <= {'KHR_materials_specular'}
    texture = doc['textures'][pbr['baseColorTexture']['index']]
    image = doc['images'][texture['source']]
    assert 'bufferView' in image and 'uri' not in image
    view = doc['bufferViews'][image['bufferView']]
    image_bytes = blob[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']]
    rgba = np.array(Image.open(io.BytesIO(image_bytes)).convert('RGBA'))
    sampler = doc['samplers'][texture['sampler']]
    assert sampler.get('magFilter') == 9728 and sampler.get('minFilter') == 9728, 'Native nearest sampler required'
    checked = []
    for part in parts:
        if part['name'] != body: continue
        start, end = part['index_range']
        used = np.unique(indices[start:end]); uv = arrays['TEXCOORD_0'][used]
        # Packed atlas tiles are internal; this conservative full rectangle includes every sampled body texel.
        assert np.all(uv >= 0) and np.all(uv < 1), 'Packed body UV must be inside atlas; no unverified wrapping'
        lo = np.floor(uv.min(axis=0) * [rgba.shape[1], rgba.shape[0]]).astype(int)
        hi = np.floor(uv.max(axis=0) * [rgba.shape[1], rgba.shape[0]]).astype(int)
        region = rgba[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        assert region.size and np.all(region[:, :, 3] == 255), 'Packed body donor has nonopaque sampled texels'
        checked.append({'source_surface': part['source_surface'], 'texel_rectangle_inclusive': [lo.tolist(), hi.tolist()], 'texels_checked': int(region.shape[0] * region.shape[1]), 'alpha_min': 255, 'alpha_max': 255})
    assert len(checked) == 2
    return {'ok': True, 'material_alpha_mode': material.get('alphaMode', 'OPAQUE'), 'body_regions': checked, 'image_embedded_sha256': hashlib.sha256(image_bytes).hexdigest(), 'rgba_sha256': hashlib.sha256(rgba.tobytes()).hexdigest(), 'size': [rgba.shape[1], rgba.shape[0]], 'scope': 'All texels in each body-part UV bounding rectangle are opaque. Other fin atlas regions may remain transparent; actual GPU coverage and transparent negative still required.'}


def freeze(model, body, fins, output):
    doc, blob, node, primitive, parts, arrays, indices = packed_arrays(model, body, fins)
    opacity = body_opacity(doc, blob, primitive, parts, arrays, indices, body)
    joints = doc['skins'][node['skin']]['joints']
    result = {'ok': True, 'schema_version': 1, 'kind': 'fish_packed_part_manifest', 'model': str(Path(model).resolve()), 'model_sha256': sha(model), 'body': body, 'fins': fins, 'mesh_node': node['name'], 'parts': parts, 'attributes': {k: v.tolist() for k, v in arrays.items()}, 'indices': indices.tolist(), 'joint_names': [doc['nodes'][j]['name'] for j in joints], 'vertex_count': len(arrays['POSITION']), 'triangles': len(indices) // 3, 'body_opacity': opacity, 'checker_sha256': sha(__file__), 'scope': 'Canonical packed source table, not imported-order proof. Godot validator must map actual imported vertices/skin and consume every oriented triangle exactly once.'}
    Path(output).write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
    return result


def logical_document(model, body, fins):
    """In-memory analysis view of exact source arrays; never written as a game model."""
    doc, blob, node, primitive, parts, arrays, indices = packed_arrays(model, body, fins)
    opacity = body_opacity(doc, blob, primitive, parts, arrays, indices, body)
    assert not any(k in node for k in ('matrix', 'translation', 'rotation', 'scale')), 'Packed analysis expects baked identity mesh transform'
    result = copy.deepcopy(doc)
    for existing in result['nodes']: existing.pop('mesh', None)
    result['meshes'] = []
    names = list(dict.fromkeys(part['name'] for part in parts))
    for name in names:
        mesh = {'name': name, 'primitives': []}
        for part in parts:
            if part['name'] != name: continue
            lo, hi = part['vertex_range']; start, end = part['index_range']
            new_primitive = copy.deepcopy(primitive)
            new_primitive['attributes'] = {}
            for semantic, values in {**arrays, '_indices': indices[start:end] - lo}.items():
                data = values if semantic == '_indices' else values[lo:hi]
                template = {'componentType': 5125, 'type': 'SCALAR'} if semantic == '_indices' else copy.deepcopy(doc['accessors'][primitive['attributes'][semantic]])
                raw = np.asarray(data, dtype='<u4').tobytes() if semantic == '_indices' else data.tobytes()
                blob += b'\0' * (-len(blob) % 4)
                offset = len(blob); blob += raw
                view_id = len(result['bufferViews']); result['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(raw)})
                template.update(bufferView=view_id, byteOffset=0, count=len(data))
                template.pop('sparse', None)
                accessor_id = len(result['accessors']); result['accessors'].append(template)
                if semantic == '_indices': new_primitive['indices'] = accessor_id
                else: new_primitive['attributes'][semantic] = accessor_id
            mesh['primitives'].append(new_primitive)
        mesh_id = len(result['meshes']); result['meshes'].append(mesh)
        result['nodes'].append({'name': name, 'mesh': mesh_id, 'skin': node['skin']})
    result['buffers'][0]['byteLength'] = len(blob)
    return result, blob, opacity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--body', required=True)
    parser.add_argument('--fins', nargs=7, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output = args.output.resolve()
    assert output.is_relative_to(root) and any(v in ('experiments', 'work', 'output') for v in output.relative_to(root).parts)
    assert output != args.model.resolve() and not output.exists(), 'Do not overwrite input or existing evidence'
    output.parent.mkdir(parents=True, exist_ok=True)
    result = freeze(args.model.resolve(), args.body, args.fins, output)
    print(json.dumps({'ok': True, 'output': str(output), 'triangles': result['triangles'], 'logical_parts': len(result['parts']), 'model_sha256': result['model_sha256']}))


if __name__ == '__main__':
    main()
