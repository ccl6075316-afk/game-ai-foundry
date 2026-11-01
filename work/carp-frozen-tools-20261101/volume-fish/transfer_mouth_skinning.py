"""Blender: bind a frozen mouth-study mesh through its source correspondences.

Writes candidate data and a validation report, never replaces a production GLB.
The plan freezes source, target geometry and mapping hashes. No species defaults.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf8'))


def bary(point, triangle):
    a, b, c = triangle
    u, v, w = b-a, c-a, point-a
    uu, uv, vv = u@u, u@v, v@v
    den = uu*vv-uv*uv
    assert den > 1e-25
    y = (vv*(w@u)-uv*(w@v))/den
    z = (uu*(w@v)-uv*(w@u))/den
    weights = np.maximum([1-y-z, y, z], 0)
    return weights/weights.sum()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    args = ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    plan = read(args.plan)
    for path, expected in plan['frozen_inputs'].items():
        assert sha(path) == expected, path
    raw = Path(plan['source_model']).read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    doc, binary = json.loads(raw[20:20+size]), raw[28+size:]

    def accessor(index):
        ac = doc['accessors'][index]
        view = doc['bufferViews'][ac['bufferView']]
        dtype = np.dtype('<'+{5126:'f4',5125:'u4',5123:'u2',5121:'u1'}[ac['componentType']])
        count = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[ac['type']]
        result = np.ndarray((ac['count'],count), dtype=dtype, buffer=binary,
                            offset=view.get('byteOffset',0)+ac.get('byteOffset',0),
                            strides=(view.get('byteStride',count*dtype.itemsize),dtype.itemsize)).copy()
        if ac.get('normalized'):
            result = result.astype(float)/np.iinfo(dtype).max
        return result

    node = next(n for n in doc['nodes'] if n.get('name') == plan['mesh'])
    assert 'skin' in node and not any(k in node for k in ['translation','rotation','scale','matrix'])
    positions, faces, joints, weights = [], [], [], []
    offset = 0
    for prim in doc['meshes'][node['mesh']]['primitives']:
        attrs = prim['attributes']
        p = accessor(attrs['POSITION'])
        positions.append(p)
        faces.append(accessor(prim['indices']).reshape(-1,3)+offset)
        joints.append(accessor(attrs['JOINTS_0']))
        weights.append(accessor(attrs['WEIGHTS_0']))
        offset += len(p)
    source = np.concatenate(positions).astype(float)
    triangles = np.concatenate(faces)
    joint = np.concatenate(joints)
    weight = np.concatenate(weights).astype(float)
    bvh = BVHTree.FromPolygons(source.tolist(), triangles.tolist(), all_triangles=True)
    body = read(plan['body'])
    diagnostics = []

    def merge_weights(ids,bw,js,ws):
        merged={}
        for vertex,factor in zip(ids,bw):
            for bone,influence in zip(js[vertex],ws[vertex]):
                merged[int(bone)]=merged.get(int(bone),0.)+float(factor*influence)
        ordered=sorted(merged.items(),key=lambda x:(-x[1],x[0]))
        discarded=sum(w for _,w in ordered[4:]);total=sum(w for _,w in ordered[:4])
        assert discarded<=plan['maximum_discarded_weight'] and total>0
        ordered=ordered[:4]+[(0,0.)]*max(0,4-len(ordered))
        return [j for j,w in ordered],[w/total for j,w in ordered],discarded

    def sample(bvh, verts, tris, js, ws, points):
        out_j, out_w, distances, discarded = [], [], [], []
        for point in points:
            hit, normal, face, distance = bvh.find_nearest(Vector(point))
            assert hit is not None
            ids = tris[face]
            bw = bary(np.asarray(hit), verts[ids])
            merged = {}
            for vertex, factor in zip(ids, bw):
                for bone, influence in zip(js[vertex], ws[vertex]):
                    merged[int(bone)] = merged.get(int(bone), 0.) + float(factor*influence)
            ordered = sorted(merged.items(), key=lambda x: (-x[1],x[0]))
            total = sum(w for _,w in ordered[:4])
            discarded.append(sum(w for _,w in ordered[4:]))
            ordered = ordered[:4] + [(0,0.)]*max(0,4-len(ordered))
            out_j.append([j for j,w in ordered])
            out_w.append([w/total for j,w in ordered])
            distances.append(distance)
        assert max(discarded) <= plan['maximum_discarded_weight']
        return out_j, out_w, {'maximum_projection_distance':max(distances), 'maximum_discarded_weight':max(discarded)}

    for part in body['parts']:
        if plan.get('reuse_body_binding',False):
            js=np.asarray(part['joints']);ws=np.asarray(part['weights'])
            assert js.shape==ws.shape==(len(part['vertices']),4)
            assert np.all(js>=0) and np.all(js<len(doc['skins'][node['skin']]['joints']))
            assert np.all(ws>=0) and np.max(abs(ws.sum(axis=1)-1))<1e-5
            diagnostics.append({'part':'body','surface':part['source_surface'],'binding_reused_from_frozen_body':True})
            continue
        if 'source_face_ids' in part:
            js=[];ws=[];discarded=[];errors=[]
            for face,bw,reference in zip(part['source_face_ids'],part['source_bary_weights'],part['reference_positions']):
                ids=triangles[face];bw=np.asarray(bw)
                assert np.all(bw>=0) and abs(bw.sum()-1)<1e-10
                errors.append(float(np.linalg.norm(source[ids].T@bw-reference)))
                j,w,lost=merge_weights(ids,bw,joint,weight);js.append(j);ws.append(w);discarded.append(lost)
            assert len(js)==len(part['vertices']) and max(errors)<1e-10
            part['joints'],part['weights']=js,ws
            diagnostics.append({'part':'body','surface':part['source_surface'],'direct_frozen_face_correspondence':True,'maximum_reference_reconstruction_error':max(errors),'maximum_discarded_weight':max(discarded)})
            continue
        js, ws, metric = sample(bvh, source, triangles, joint, weight, part['reference_positions'])
        assert metric['maximum_projection_distance'] <= plan['maximum_source_projection_distance'], metric
        part['joints'], part['weights'] = js, ws
        diagnostics.append({'part':'body','surface':part['source_surface'], **metric})

    verts, tris, js, ws = [], [], [], []
    offset = 0
    for part in body['parts']:
        verts.extend(part['vertices'])
        tris.extend((np.array(part['triangles']).reshape(-1,3)+offset).tolist())
        js.extend(part['joints']); ws.extend(part['weights'])
        offset += len(part['vertices'])
    verts, tris, js, ws = map(np.array, (verts,tris,js,ws))
    body_bvh = BVHTree.FromPolygons(verts.tolist(),tris.tolist(),all_triangles=True)
    lips = read(plan['lips']) if plan.get('lips') else {'parts':[]}
    for part in lips['parts']:
        j, w, metric = sample(body_bvh,verts,tris,js,ws,part['vertices'])
        assert metric['maximum_projection_distance'] <= plan['maximum_lip_projection_distance']
        part['joints'],part['weights'] = j,w
        diagnostics.append({'part':part['name'],**metric})
    dest = Path(plan['output']); dest.mkdir(parents=True,exist_ok=True)
    outputs = []
    for name, data in [('body.bound.json',body),('lips.bound.json',lips)]:
        path = dest/name
        path.write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
        outputs.append({'path':str(path),'sha256':sha(path)})
    report = {'schema_version':1,'ok':True,'command':'fish.transfer-mouth-skinning',
              'status':'done','next_action':'human_review','inputs':plan['frozen_inputs'],
              'outputs':outputs,'summary':{'species':plan['species'],'metrics':diagnostics,
              'skin_joint_node_order':doc['skins'][node['skin']]['joints'],
              'skin_joint_names':[doc['nodes'][i]['name'] for i in doc['skins'][node['skin']]['joints']],
              'geometry_uv_normals_unchanged':True,'production_installed':False,
              'scope':'Candidate weight transfer only; actual engine skin-bind order, fin/body/motion/LOD and visual gates still required.'},'failures':[]}
    (dest/'skinning.validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps({'ok':True,'metrics':diagnostics}),flush=True)


if __name__ == '__main__':
    main()
