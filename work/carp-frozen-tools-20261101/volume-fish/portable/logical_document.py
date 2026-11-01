"""Read-only analysis projection of independently verified portable partitions."""
import copy
import numpy as np
from parts import read, freeze, packed_arrays, require

def logical_document(model, body, fins, manifest_path):
    manifest = read(manifest_path)
    spec = {'parts': [{'name': p['source_name'], 'role': p['role'], 'source_node': p['source_node'], 'source_surface': p['source_surface'], 'logical_name': p['name'], 'opaque_uv': p['opaque_uv']} for p in manifest['parts']], 'expected': manifest['expected']}
    require(freeze(model, spec) == manifest, 'Stale or altered portable manifest')
    require(manifest['body_names'] == [body] and set(manifest['fin_names']) == set(fins), 'Explicit body/fin inventory differs')
    doc, blob, node, primitive, parts, arrays, indices, _, _ = packed_arrays(model, spec)
    require(not any(k in node for k in ('matrix', 'translation', 'rotation', 'scale')), 'Identity baked mesh required')
    result = copy.deepcopy(doc)
    for existing in result['nodes']: existing.pop('mesh', None)
    result['meshes'] = []
    for name in dict.fromkeys(p['name'] for p in parts):
        mesh = {'name': name, 'primitives': []}
        for part in parts:
            if part['name'] != name: continue
            lo, hi = part['vertex_range']; start, end = part['index_range']
            prim = copy.deepcopy(primitive); prim['attributes'] = {}
            for semantic, values in {**arrays, '_indices': indices[start:end] - lo}.items():
                data = values if semantic == '_indices' else values[lo:hi]
                template = {'componentType': 5125, 'type': 'SCALAR'} if semantic == '_indices' else copy.deepcopy(doc['accessors'][primitive['attributes'][semantic]])
                raw = np.asarray(data, dtype='<u4').tobytes() if semantic == '_indices' else data.tobytes()
                blob += b'\0' * (-len(blob) % 4); offset = len(blob); blob += raw
                view_id = len(result['bufferViews']); result['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(raw)})
                template.update(bufferView=view_id, byteOffset=0, count=len(data)); template.pop('sparse', None)
                aid = len(result['accessors']); result['accessors'].append(template)
                if semantic == '_indices': prim['indices'] = aid
                else: prim['attributes'][semantic] = aid
            mesh['primitives'].append(prim)
        mid = len(result['meshes']); result['meshes'].append(mesh)
        result['nodes'].append({'name': name, 'mesh': mid, 'skin': node['skin']})
    result['buffers'][0]['byteLength'] = len(blob)
    return result, blob, manifest['body_opacity']
