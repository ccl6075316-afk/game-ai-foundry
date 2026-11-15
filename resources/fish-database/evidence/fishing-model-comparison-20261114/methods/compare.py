import io
import json
import math
import struct
import zipfile
from pathlib import Path

import numpy as np
import UnityPy
from PIL import Image, ImageDraw, ImageFont

from audit import APK_PATHS, DB, OUT, ROOT, mesh_data, mesh_pointer

DB_BUNDLES = DB / 'artifacts/fishing-master-cdn-cnformal1-20261102'
DATA = json.loads((OUT / 'audit.json').read_text(encoding='utf-8'))


def mapped(vertices, axis):
    return np.asarray(vertices)[:, np.abs(axis) - 1] * np.sign(axis)


def from_unity(mesh, materials, axis, dependencies=None):
    points, faces, uv = mesh_data(mesh)
    out = []
    for triangles, ptr in zip(faces, materials, strict=True):
        mat = ptr.read()
        entries = dict(mat.m_SavedProperties.m_TexEnvs)
        tex = (entries.get('_BaseMap') or entries['_MainTex']).m_Texture
        if tex.file_id and dependencies:
            tex_asset = dependencies[tex.path_id].read()
        else:
            tex_asset = tex.read()
        image = np.asarray(tex_asset.image.convert('RGBA'))
        coordinates = np.asarray(uv, dtype=np.float64)
        coordinates[:, 1] = 1 - coordinates[:, 1]
        out.append((mapped(points, axis), np.asarray(triangles), coordinates, image, None, True))
    return out


def competitor(source, prefab, axis):
    row = next(r for r in DATA[source]['records'] if r['prefab'] == prefab)
    with zipfile.ZipFile(APK_PATHS[source]) as apk:
        env = UnityPy.load(apk.read(row['package_entry']))
        submeshes = []
        for record in row['meshes']:
            obj = next(o for o in env.objects if o.path_id == record['renderer_id'])
            renderer = obj.read()
            submeshes.extend(from_unity(mesh_pointer(obj, renderer).read(), renderer.m_Materials, axis))
    return row['triangles'], submeshes


def load_local_bundle(name):
    raw = (DB_BUNDLES / name).read_bytes()
    return UnityPy.load(raw[32:] if raw[32:40] == b'UnityFS\0' else raw)


def database(name, axis):
    ref = DB / 'references' / f'fishing-master-cdn-cnformal1-20261102-{name}.json'
    facts = json.loads(ref.read_text(encoding='utf-8'))['verified_facts']
    env = load_local_bundle(Path(facts['preferred_bundle']).name)
    obj = next(o for o in env.objects if o.type.name in ('SkinnedMeshRenderer', 'MeshRenderer'))
    renderer = obj.read()
    desc = facts['mesh_objects'][0]
    depot = load_local_bundle(Path(desc['bundle']).name)
    mesh_id = int(desc['object_key'].split(':')[-1])
    mesh = next(o.read() for o in depot.objects if o.path_id == mesh_id and o.type.name == 'Mesh')
    dependencies = {}
    if name == 'atlanticsalmon':
        texture_depot = load_local_bundle('b_common_dependency_3.unity3d')
        dependencies = {o.path_id: o for o in texture_depot.objects if o.type.name == 'Texture2D'}
    return desc['triangles'], from_unity(mesh, renderer.m_Materials, axis, dependencies)


def glb_model(name):
    data = (ROOT / 'projects/fishing-2d/game/assets/models/fish' / (name + '.glb')).read_bytes()
    metadata_size = struct.unpack_from('<I', data, 12)[0]
    spec = json.loads(data[20:20 + metadata_size])
    binary = memoryview(data)[28 + metadata_size:]
    cache = {}

    def accessor(index, elements):
        item = spec['accessors'][index]
        view = spec['bufferViews'][item['bufferView']]
        size = {'5123': '<u2', '5125': '<u4', '5126': '<f4'}[str(item['componentType'])]
        dtype = np.dtype(size)
        stride = view.get('byteStride', dtype.itemsize * elements)
        offset = view.get('byteOffset', 0) + item.get('byteOffset', 0)
        return np.ndarray((item['count'], elements), dtype=dtype, buffer=binary,
                          offset=offset, strides=(stride, dtype.itemsize))

    submeshes = []
    for node in spec['nodes']:
        if 'mesh' not in node:
            continue
        assert not set(node).intersection({'translation', 'scale', 'rotation', 'matrix'})
        for prim in spec['meshes'][node['mesh']]['primitives']:
            mat = spec['materials'][prim['material']]
            tex = mat['pbrMetallicRoughness']['baseColorTexture']['index']
            image_id = spec['textures'][tex]['source']
            if image_id not in cache:
                view = spec['bufferViews'][spec['images'][image_id]['bufferView']]
                offset = view.get('byteOffset', 0)
                cache[image_id] = np.asarray(Image.open(io.BytesIO(binary[offset:offset + view['byteLength']])).convert('RGBA'))
            vertices = accessor(prim['attributes']['POSITION'], 3)
            indices = accessor(prim['indices'], 1).reshape(-1, 3)
            uv = accessor(prim['attributes']['TEXCOORD_0'], 2)
            cutoff = mat.get('alphaCutoff', .5) if mat.get('alphaMode') == 'MASK' else None
            submeshes.append((vertices, indices, uv, cache[image_id], cutoff, False))
    return sum(len(s[1]) for s in submeshes), submeshes


def render(model, size, view, wire=False):
    width, height = size
    canvas = np.full((height, width, 3), (231, 238, 242), dtype=np.uint8)
    depth = np.full((height, width), -np.inf)
    angle, elevation = map(math.radians, view)
    right = np.array([math.cos(angle), 0, -math.sin(angle)])
    toward = np.array([math.sin(angle) * math.cos(elevation), math.sin(elevation),
                       math.cos(angle) * math.cos(elevation)])
    up = np.cross(toward, right)
    direction = np.array([-0.35, 0.72, 0.6])
    projection = np.array([right, up, toward]).T
    all_points = np.concatenate([p for p, *_ in model])
    projected = all_points @ projection
    center = (projected.max(0) + projected.min(0)) / 2
    scale = width * .8 / np.ptp(all_points[:, 0])
    for vertices, indices, uv, texture, cutoff, repeat in model:
        points = (vertices @ projection - center) * np.array([scale, -scale, 1])
        points[:, :2] += [width / 2, height / 2]
        for tri in indices:
            a, b, c = points[tri]
            x0, y0 = np.maximum(0, np.floor(np.min([a, b, c], axis=0)[:2]).astype(int))
            x1, y1 = np.minimum([width, height], np.ceil(np.max([a, b, c], axis=0)[:2]).astype(int) + 1)
            if x0 >= x1 or y0 >= y1:
                continue
            local_y, local_x = np.ogrid[y0:y1, x0:x1]
            v, w = b - a, c - a
            den = v[0] * w[1] - w[0] * v[1]
            if abs(den) < 1e-7:
                continue
            beta = ((local_x + .5 - a[0]) * w[1] - (local_y + .5 - a[1]) * w[0]) / den
            gamma = (v[0] * (local_y + .5 - a[1]) - v[1] * (local_x + .5 - a[0])) / den
            alpha = 1 - beta - gamma
            z = alpha * a[2] + beta * b[2] + gamma * c[2]
            patch_depth = depth[y0:y1, x0:x1]
            visible = (alpha >= -1e-6) & (beta >= -1e-6) & (gamma >= -1e-6) & (z > patch_depth)
            if not visible.any():
                continue
            uv_tri = uv[tri]
            uv_pixels = (alpha[visible, None] * uv_tri[0] + beta[visible, None] * uv_tri[1]
                         + gamma[visible, None] * uv_tri[2])
            th, tw, _ = texture.shape
            uv_pixels = uv_pixels % 1 if repeat else np.clip(uv_pixels, 0, 1)
            source = np.minimum((uv_pixels * [tw, th]).astype(int), [tw - 1, th - 1])
            texels = texture[source[:, 1], source[:, 0]]
            if cutoff is not None:
                keep = texels[:, 3] >= 255 * cutoff
                visible[visible] = keep
                texels = texels[keep]
            patch_depth[visible] = z[visible]
            va, vb, vc = vertices[tri]
            normal = np.cross(vb - va, vc - va)
            normal_length = np.linalg.norm(normal)
            if normal_length <= 1e-12:
                continue
            normal = normal / normal_length
            if normal @ toward < 0:
                normal = -normal
            light = .73 + .27 * max(0, normal @ direction)
            if wire:
                edges = np.array([np.linalg.norm(w[:2] - v[:2]), np.linalg.norm(w[:2]), np.linalg.norm(v[:2])])
                bary = np.array([alpha[visible], beta[visible], gamma[visible]]).T
                edge = np.min(bary * abs(den) / np.maximum(edges, 1e-8), axis=1) < .7
                color = np.where(edge[:, None], np.array([27, 60, 71]), light * np.array([175, 196, 199]))
            else:
                color = texels[:, :3] * light
            canvas[y0:y1, x0:x1][visible] = color.astype(np.uint8)
    return Image.fromarray(canvas)


def font(size):
    return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', size)


def sheet(rows, filename, wiring):
    title = '鱼模型线框 · 斜侧视' if wiring else '鱼模型贴图 · 统一光照侧视'
    columns = ['钓鱼达人 4.3', '全民钓鱼2 2.6.7', '资料库 · 欢乐钓鱼大师', '我们 · 正式 GLB']
    cell_w, content_h, row_h = 385, 192, 239
    page = Image.new('RGB', (1580, 110 + len(rows) * row_h), (246, 248, 250))
    pen = ImageDraw.Draw(page)
    pen.text((18, 12), title, font=font(29), fill='#17323a')
    pen.text((18, 52), '按整鱼长度归一。截取模型静息几何和原始颜色贴图，统一相机与光照。', font=font(17), fill='#42616a')
    for i, header in enumerate(columns):
        pen.text((18 + i * 390, 83), header, font=font(19), fill='#1b5160')
    for row_index, row in enumerate(rows):
        for column, (name, model) in enumerate(row):
            x, y = 18 + column * 390, 114 + row_index * row_h
            if model is None:
                pen.rectangle((x, y, x + cell_w, y + content_h), fill='#e7eef2')
                pen.text((x + 114, y + 76), '该组无样本', font=font(20), fill='#52717a')
                continue
            count, geometry = model
            angle = (24, 12) if wiring else (0, 0)
            page.paste(render(geometry, (cell_w * 2, content_h * 2), angle, wiring)
                       .resize((cell_w, content_h), Image.Resampling.LANCZOS), (x, y))
            pen.text((x, y + content_h + 7), f'{name}  ·  {count:,} 三角面', font=font(18), fill='#17323a')
    page.save(OUT / filename, quality=94, subsampling=0)


if __name__ == '__main__':
    rows = [
        [('雨伞旗鱼', competitor('hookem-xiaomi', 'im_fish_30', [-2, 3, -1])),
         ('大西洋旗鱼（贴图名）', competitor('qmdy2', 'fish_01_01_13', [-1, 2, -3])),
         ('Sailfish', database('sailfish', [-2, 3, 1])),
         ('大西洋旗鱼', glb_model('atlantic_sailfish'))],
        [('', None),
         ('三道鳞（贴图名）', competitor('qmdy2', 'fish_01_02_08', [-2, 3, -1])),
         ('MirrorCarp', database('mirrorcarp', [-2, 3, 1])),
         ('鲤鱼', glb_model('carp'))],
        [('', None),
         ('红头鲫（贴图名）', competitor('qmdy2', 'fish_01_03_02', [-2, 3, -1])),
         ('CrucianCarp', database('cruciancarp', [-2, 3, 1])),
         ('鲫鱼', glb_model('crucian'))],
        [('三文鱼（游戏名）', competitor('hookem-xiaomi', 'im_fish_38', [-2, 3, -1])),
         ('', None),
         ('AtlanticSalmon', database('atlanticsalmon', [-2, 3, 1])),
         ('大西洋鲑', glb_model('atlantic_salmon'))],
    ]
    sheet(rows, 'textured.jpg', False)
    sheet(rows, 'wireframe.jpg', True)
