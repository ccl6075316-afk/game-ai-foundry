import collections
import hashlib
import json
import re
import statistics
import struct
import zipfile
from pathlib import Path

import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler

DB = Path(__file__).resolve().parents[3]
ROOT = DB.parents[1]
OUT = ROOT / 'work/fishing-benchmark-20261114'
APK_PATHS = {
    'hookem-xiaomi': DB / 'artifacts/hookem-fishing-xiaomi-4-3-20261114/hookem-xiaomi-4.3.apk',
    'qmdy2': DB / 'artifacts/national-fishing-2-2-6-7-20261114/national-fishing-2-2.6.7.apk',
}
SOURCES = {
    'hookem-xiaomi': {
        'title': '钓鱼达人', 'version': '4.3', 'version_code': 43,
        'package_id': 'com.zongyi.dydryx.mi',
        'product_page': 'https://game.xiaomi.com/game/62380179',
        'download_url': 'https://t1.g.mi.com/download/AppStore/00d13daaec6d44bc9883bd0d6b83a9be01ea17b1c/com.zongyi.dydryx.mi.apk',
        'recording_page': 'https://www.taptap.cn/app/131427',
    },
    'qmdy2': {
        'title': '全民钓鱼2', 'version': '2.6.7', 'version_code': 1027,
        'package_id': 'com.jfyd.fish',
        'product_page': 'https://www.taptap.cn/app/182581',
        'download_url': 'https://api.ddooo.com/down/224106',
        'channel_md5': 'aabe4cb73e614a4821c6ca37a9a996a6',
        'recording_page': 'https://www.taptap.cn/app/182581',
    },
}


def read_text(env, name):
    return next(obj.read().m_Script for obj in env.objects
                if obj.type.name == 'TextAsset' and obj.peek_name() == name)


def render_root(renderer, pattern):
    game_object = renderer.m_GameObject.read()
    transform = next(c.component.read() for c in game_object.m_Component
                     if c.component.deref().type.name == 'Transform')
    while transform:
        name = transform.m_GameObject.read().m_Name
        if pattern.fullmatch(name):
            return name.casefold()
        if not transform.m_Father:
            return None
        transform = transform.m_Father.read()
    return None


def mesh_data(mesh):
    handler = MeshHandler(mesh)
    handler.process()
    vertices = [list(v[:3]) for v in handler.m_Vertices]
    submeshes = [[list(t) for t in part] for part in handler.get_triangles()]
    uv = [list(pair[:2]) for pair in handler.m_UV0] if handler.m_UV0 is not None else []
    return vertices, submeshes, uv


def mesh_pointer(obj, renderer):
    if obj.type.name == 'SkinnedMeshRenderer':
        return renderer.m_Mesh
    game_object = renderer.m_GameObject.read()
    mesh_filter = next(c.component.read() for c in game_object.m_Component
                       if c.component.deref().type.name == 'MeshFilter')
    return mesh_filter.m_Mesh


def mesh_record(obj, renderer):
    pointer = mesh_pointer(obj, renderer)
    mesh = pointer.read()
    vertices, faces, _ = mesh_data(mesh)
    for part, submesh in zip(faces, mesh.m_SubMeshes, strict=True):
        if int(submesh.topology) == 0:
            assert len(part) * 3 == submesh.indexCount
        assert all(0 <= index < len(vertices) for face in part for index in face)
    digest = hashlib.sha256()
    for vertex in vertices:
        digest.update(struct.pack('<3f', *vertex))
    for part in faces:
        digest.update(struct.pack('<I', len(part)))
        for face in part:
            digest.update(struct.pack('<3I', *face))
    textures = []
    for material_pointer in renderer.m_Materials:
        material = material_pointer.read()
        for key, entry in material.m_SavedProperties.m_TexEnvs:
            if entry.m_Texture:
                texture = entry.m_Texture.read()
                textures.append([key, texture.m_Name, texture.m_Width, texture.m_Height])
    return {'name': mesh.m_Name, 'id': pointer.path_id,
            'geometry_sha256': digest.hexdigest(), 'vertices': len(vertices),
            'triangles': sum(map(len, faces)), 'surfaces': list(map(len, faces)),
            'bones': len(getattr(renderer, 'm_Bones', [])), 'textures': textures,
            'renderer': obj.type.name, 'renderer_id': obj.path_id}


def scan_apk(stem):
    records, problems = [], []
    hook = stem == 'hookem-xiaomi'
    with zipfile.ZipFile(APK_PATHS[stem]) as apk:
        if hook:
            config = UnityPy.load(apk.read(next(n for n in apk.namelist() if '/config_assets_' in n)))
            names = {row['langId']: row['simplified']
                     for row in json.loads(read_text(config, 'lang'), strict=False)}
            labels = {row['iconPath'].casefold(): names.get(row['name'], '')
                      for row in json.loads(read_text(config, 'fish'), strict=False)}
            pattern = re.compile(r'IM_fish_\d+', re.I)
            bundles = [n for n in apk.namelist() if re.search(r'/fish(?:_map\d+)?_assets_all_', n)]
        else:
            config = UnityPy.load(apk.read('assets/Others/data.unity3d'))
            data = json.loads(read_text(config, 'data'), strict=False)
            labels = {row['t14'].casefold(): row['t14'] for row in data['FishData']}
            pattern = re.compile(r'Fish_\w+|ie_1005_04', re.I)
            bundles = [n for n in apk.namelist() if re.search(r'^assets/Fishes/(?:new)?fish_[^/]+\.unity3d$', n, re.I)]
            bundles.append('assets/Fishes/ie_1005_04.unity3d')
            labels['ie_1005_04'] = 'shumeiyux_tex01_shumeiyu'

        for bundle in bundles:
            blob = apk.read(bundle)
            env = UnityPy.load(blob)
            groups = collections.defaultdict(list)
            for obj in env.objects:
                if obj.type.name not in ('SkinnedMeshRenderer', 'MeshRenderer'):
                    continue
                renderer = obj.read()
                root = render_root(renderer, pattern)
                if not root or not renderer.m_Enabled:
                    problems.append([bundle, obj.path_id, root, renderer.m_Enabled])
                    continue
                groups[root].append(mesh_record(obj, renderer))
            if not groups:
                problems.append([bundle, 'no fish renderer'])
            for root, meshes in groups.items():
                records.append({'prefab': root, 'label': labels.get(root, ''), 'package_entry': bundle,
                                'bundle_sha256': hashlib.sha256(blob).hexdigest(),
                                'triangles': sum(m['triangles'] for m in meshes), 'meshes': meshes})
    return records, problems, bundles


def describe_apk(name):
    file = APK_PATHS[name]
    with file.open('rb') as stream:
        sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
        stream.seek(0)
        md5 = hashlib.file_digest(stream, 'md5').hexdigest()
    with zipfile.ZipFile(file) as archive:
        assert archive.testzip() is None
        entries = len(archive.infolist())
    source = SOURCES[name]
    assert source.get('channel_md5', md5) == md5
    return {**source, 'size': file.stat().st_size, 'sha256': sha256, 'md5': md5, 'zip_entries_verified': entries}


def glb_records():
    records = []
    for item in sorted((ROOT / 'projects/fishing-2d/game/assets/models/fish').glob('*.glb')):
        with item.open('rb') as f:
            magic, version, _, length, section = struct.unpack('<5I', f.read(20))
            assert (magic, version, section) == (0x46546C67, 2, 0x4E4F534A), item
            manifest = json.loads(f.read(length))
        indices = []
        for node in manifest['nodes']:
            if 'mesh' in node:
                for primitive in manifest['meshes'][node['mesh']]['primitives']:
                    assert primitive.get('mode', 4) == 4, item
                    count = manifest['accessors'][primitive['indices']]['count']
                    assert count % 3 == 0
                    indices.append(count // 3)
        records.append({'name': item.stem, 'triangles': sum(indices), 'surfaces': indices,
                        'bones': len(manifest.get('skins', [{}])[0].get('joints', [])),
                        'sha256': hashlib.sha256(item.read_bytes()).hexdigest()})
    return records


def db_records():
    path = DB / 'artifacts/fishing-master-cdn-cnformal1-20261102/mesh-exports'
    result = []
    for obj in sorted(path.glob('*.obj')):
        with obj.open('rb') as content:
            faces = sum(len(line.split()) - 3 for line in content if line.startswith(b'f '))
        if faces <= 0:
            raise ValueError(f'Missing OBJ faces: {obj}')
        result.append({'file': obj.name, 'triangles': faces})
    return result


def summary(records):
    counts = sorted(row['triangles'] for row in records)
    q1, _, q3 = statistics.quantiles(counts, n=4, method='inclusive')
    return {'count': len(counts), 'minimum': min(counts), 'median': statistics.median(counts),
            'middle_50_percent': [q1, q3],
            'maximum': max(counts), 'under_1500': sum(c <= 1500 for c in counts),
            'under_2000': sum(c <= 2000 for c in counts), 'under_4000': sum(c <= 4000 for c in counts)}


if __name__ == '__main__':
    artifact = {'method': {
        'date': '2026-11-14',
        'unitypy_version': UnityPy.__version__,
        'competitor_unit': 'One fish prefab entry per APK bundle/root pair, including variants. '
                           'Use enabled MeshRenderer and SkinnedMeshRenderer submeshes. '
                           'Exclude the three key props, boot and pop can in the qmdy2 Fishes folder.',
        'geometry_signature': 'Ordered float32 vertex positions plus ordered triangle indices and '
                              'submesh lengths. Does not incorporate materials, UVs or rigging, '
                              'and does not match reordered or transformed equivalents.',
        'comparison_unit': 'Each installed Foundry GLB or each locally exported database OBJ. '
                           'The database contains per-mesh exports and variants, including partial geometries.',
        'visual_scope': 'Normalized-length static rest geometry and base color maps under one light. '
                        'Public videos are separate, with no confirmed version. No on-device play, runtime LOD '
                        'selection, frame rate, animation quality or custom shader reproduction measured.',
    }}
    for name in ('hookem-xiaomi', 'qmdy2'):
        rows, issues, bundles = scan_apk(name)
        unique = {tuple(sorted(m['geometry_sha256'] for m in row['meshes'])): row for row in rows}
        artifact[name] = {'source': describe_apk(name), 'records': rows, 'issues': issues, 'bundles_scanned': len(bundles),
                          'prefab_statistics': summary(rows), 'deduplicated_statistics': summary(list(unique.values()))}
    for name, rows in [('foundry', glb_records()), ('database', db_records())]:
        artifact[name] = {'records': rows, 'statistics': summary(rows)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'audit.json').write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding='utf-8')
    for name, data in artifact.items():
        print(name, {k: v for k, v in data.items() if k != 'records'})
