"""Resolve prefab objects across the verified cnformal1 dependency closure."""
from pathlib import Path
from collections import Counter, defaultdict
import gc
import hashlib
import json
import sys
import time

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / 'cli/gamefactory.py').is_file())
ROOT = REPO / 'resources/fish-database'
WORK = REPO / 'work/fish-database-complete-20261102'
sys.path.insert(0, str(WORK / 'deps'))
import UnityPy

SID = 'fishing-master-cdn-cnformal1-20261102'
DEST = ROOT / 'artifacts' / SID
EVIDENCE = ROOT / 'evidence' / SID
progress_path = ROOT / 'progress.json'
progress = json.loads(progress_path.read_text())
assert not progress['failures'] and len(progress['resources']) == progress['planned_resource_count']
objects = {}
bundles = []
containers = {}
errors = []

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def save_progress(stage, **kwargs):
    progress['stage'] = stage
    progress.update(kwargs)
    write(progress_path, progress)

def oid(asset_file, path_id):
    return asset_file.name + ':' + str(path_id)

def ptr(value, asset_file):
    if value is None:
        return None
    fid = value.get('m_FileID', 0) if isinstance(value, dict) else value.m_FileID
    pid = value.get('m_PathID', 0) if isinstance(value, dict) else value.m_PathID
    if not pid:
        return None
    filename = asset_file.name if not fid else asset_file.externals[fid - 1].path.replace('\\', '/').split('/')[-1]
    return filename + ':' + str(pid)

def load_bundle(path):
    data = path.read_bytes()
    skip = 32 if data[32:40] == b'UnityFS\0' else 0
    return UnityPy.load(data[skip:]), skip

start = time.monotonic()
for i, resource in enumerate(progress['resources']):
    env, skip = load_bundle(ROOT / resource['path'])
    types = Counter()
    record = {'resource_path': resource['resource_path'], 'artifact_path': resource['path'],
              'sha256': resource['sha256'], 'unityfs_prefix_skipped': skip, 'containers': {}, 'read_errors': []}
    # Read container pointers directly. env.container eagerly resolves preload
    # dependencies via a filesystem scan; cross-file resolution is done below.
    for asset_file in env.assets:
        for asset_obj in asset_file.objects.values():
            if asset_obj.type.name != 'AssetBundle':
                continue
            bundle_data = asset_obj.read_typetree()
            for name, info in bundle_data.get('m_Container', []):
                key = ptr(info['asset'], asset_file)
                record['containers'][name.lower()] = key
                containers[(resource['resource_path'], name.lower())] = key
    for obj in env.objects:
        kind, f = obj.type.name, obj.assets_file
        types[kind] += 1
        key = oid(f, obj.path_id)
        node = {'type': kind, 'bundle': resource['resource_path'], 'path_id': obj.path_id, 'file': f.name}
        try:
            if kind in ('GameObject', 'Transform', 'RectTransform', 'SkinnedMeshRenderer', 'MeshRenderer', 'MeshFilter', 'Material', 'Animator', 'Texture2D'):
                data = obj.read_typetree()
                node['name'] = data.get('m_Name')
                if kind == 'GameObject':
                    node.update(components=[ptr(x['component'], f) for x in data['m_Component']], active=data.get('m_IsActive'))
                elif kind in ('Transform', 'RectTransform'):
                    node.update(game_object=ptr(data['m_GameObject'], f), children=[ptr(x, f) for x in data.get('m_Children', [])],
                                parent=ptr(data.get('m_Father'), f), position=data.get('m_LocalPosition'), rotation=data.get('m_LocalRotation'), scale=data.get('m_LocalScale'))
                elif kind in ('SkinnedMeshRenderer', 'MeshRenderer'):
                    node.update(game_object=ptr(data['m_GameObject'], f), mesh=ptr(data.get('m_Mesh'), f),
                                materials=[ptr(x, f) for x in data.get('m_Materials', [])],
                                bones=[ptr(x, f) for x in data.get('m_Bones', [])], root_bone=ptr(data.get('m_RootBone'), f), enabled=data.get('m_Enabled'))
                elif kind == 'MeshFilter':
                    node.update(game_object=ptr(data['m_GameObject'], f), mesh=ptr(data.get('m_Mesh'), f))
                elif kind == 'Material':
                    properties = data.get('m_SavedProperties', {})
                    node.update(shader=ptr(data.get('m_Shader'), f),
                                textures={name: ptr(value.get('m_Texture'), f) for name, value in properties.get('m_TexEnvs', [])})
                elif kind == 'Animator':
                    node.update(controller=ptr(data.get('m_Controller'), f), avatar=ptr(data.get('m_Avatar'), f))
                elif kind == 'Texture2D':
                    node.update(width=data.get('m_Width'), height=data.get('m_Height'), texture_format=data.get('m_TextureFormat'))
            elif kind in ('Mesh', 'Avatar', 'AnimatorController', 'AnimationClip'):
                node['name'] = obj.peek_name()
            objects[key] = node
        except Exception as exc:
            error = {'object': key, 'type': kind, 'error': f'{type(exc).__name__}: {exc}'}
            record['read_errors'].append(error)
            errors.append(error)
    record['object_counts'] = dict(types)
    bundles.append(record)
    del env
    if (i + 1) % 20 == 0 or i + 1 == len(progress['resources']):
        gc.collect()
        save_progress('object-index', parsed_resource_count=i + 1, parse_error_count=len(errors))
        print(json.dumps({'indexed': i + 1, 'objects': len(objects), 'errors': len(errors), 'seconds': round(time.monotonic() - start)}), flush=True)

write(WORK / 'object-index.json', objects)
with (EVIDENCE / 'bundle-inventory.jsonl').open('w') as stream:
    for item in bundles:
        stream.write(json.dumps(item, ensure_ascii=False) + '\n')

catalog = [json.loads(x) for x in (ROOT / 'catalogs/fishing-master-xiaomi-20260814/entries.jsonl').read_text().splitlines()]
prefabs = []
for entry in catalog:
    for bundle, prefab in zip(entry['bundle_paths'], entry['prefab_paths']):
        root = containers.get((bundle, prefab.lower()))
        item = {'base_id': entry['id'], 'base_name': entry['source_name'], 'prefab_path': prefab, 'bundle': bundle,
                'source_id': SID, 'root_object': root, 'hierarchy_errors': [], 'renderer_keys': [], 'animator_keys': [], 'transform_keys': []}
        if not root:
            item['hierarchy_errors'].append('Exact prefab container not found')
        queue, seen = [root] if root else [], set()
        while queue:
            key = queue.pop()
            if key in seen:
                continue
            seen.add(key)
            node = objects.get(key)
            if not node:
                item['hierarchy_errors'].append('Unresolved hierarchy object ' + str(key)); continue
            if node['type'] == 'GameObject':
                queue.extend(x for x in node['components'] if x)
            elif node['type'] in ('Transform', 'RectTransform'):
                item['transform_keys'].append(key)
                for child in node['children']:
                    tf = objects.get(child)
                    if tf:
                        queue.append(tf['game_object'])
                    else:
                        item['hierarchy_errors'].append('Unresolved child transform ' + str(child))
            elif node['type'] in ('SkinnedMeshRenderer', 'MeshRenderer'):
                item['renderer_keys'].append(key)
            elif node['type'] == 'Animator':
                item['animator_keys'].append(key)
        item['renderers'] = []
        for key in item['renderer_keys']:
            node = objects[key]
            mesh = node['mesh']
            if node['type'] == 'MeshRenderer':
                for component in objects.get(node['game_object'], {}).get('components', []):
                    candidate = objects.get(component, {})
                    if candidate.get('type') == 'MeshFilter':
                        mesh = candidate.get('mesh')
            item['renderers'].append({'object_key': key, 'type': node['type'], 'mesh_key': mesh,
                                      'material_keys': node['materials'], 'bone_keys': node['bones'], 'enabled': node.get('enabled')})
        prefabs.append(item)

mesh_keys = {renderer['mesh_key'] for item in prefabs for renderer in item['renderers'] if renderer['mesh_key']}
material_keys = {key for item in prefabs for renderer in item['renderers'] for key in renderer['material_keys'] if key}
texture_keys = {key for material in material_keys for key in objects.get(material, {}).get('textures', {}).values() if key}
save_progress('geometry-and-textures', indexed_object_count=len(objects), target_unique_mesh_count=len(mesh_keys), target_unique_texture_count=len(texture_keys))
requested = defaultdict(set)
for key in mesh_keys | texture_keys:
    if key in objects:
        requested[objects[key]['bundle']].add(key)
mesh_info, texture_info = {}, {}
export_dir = DEST / 'mesh-exports'
export_dir.mkdir(exist_ok=True)
for i, (bundle, keys) in enumerate(sorted(requested.items())):
    env, _ = load_bundle(DEST / Path(bundle).name)
    for obj in env.objects:
        key = oid(obj.assets_file, obj.path_id)
        if key not in keys:
            continue
        try:
            value = obj.read()
            if key in mesh_keys:
                text = value.export()
                digest = hashlib.sha256(text.encode()).hexdigest()
                path = export_dir / (digest + '.obj')
                if not path.exists():
                    path.write_text(text)
                lines = text.splitlines()
                info = {'object_key': key, 'bundle': bundle, 'name': value.m_Name,
                        'vertices': sum(line.startswith('v ') for line in lines),
                        'triangles': sum(line.startswith('f ') for line in lines),
                        'uvs': sum(line.startswith('vt ') for line in lines),
                        'submeshes': len(value.m_SubMeshes), 'sha256': digest,
                        'export_path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
                        'coordinate_basis': 'mesh-local rest geometry; node and bone transforms not baked'}
                info['ok'] = info['vertices'] > 0 and info['triangles'] > 0
                mesh_info[key] = info
            elif key in texture_keys:
                image = value.image
                pixels = image.tobytes()
                texture_info[key] = {'object_key': key, 'bundle': bundle, 'name': value.m_Name, 'ok': True,
                                     'width': image.width, 'height': image.height, 'decoded_mode': image.mode,
                                     'decoded_pixels_sha256': hashlib.sha256(pixels).hexdigest()}
                image.close()
                del pixels
        except Exception as exc:
            error = {'object_key': key, 'bundle': bundle, 'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
            (mesh_info if key in mesh_keys else texture_info)[key] = error
    del env
    if (i + 1) % 20 == 0 or i + 1 == len(requested):
        gc.collect()
        save_progress('geometry-and-textures', checked_mesh_count=len(mesh_info), checked_texture_count=len(texture_info))
        print(json.dumps({'geometry_bundles': i + 1, 'total': len(requested), 'meshes': len(mesh_info), 'textures': len(texture_info)}), flush=True)

for item in prefabs:
    item['mesh_keys'] = sorted({x['mesh_key'] for x in item['renderers'] if x['mesh_key']})
    item['material_keys'] = sorted({key for x in item['renderers'] for key in x['material_keys'] if key})
    item['texture_keys'] = sorted({key for mat in item['material_keys'] for key in objects.get(mat, {}).get('textures', {}).values() if key})
    item['geometry_readable'] = bool(item['mesh_keys']) and all(mesh_info.get(key, {}).get('ok', False) for key in item['mesh_keys'])
    item['materials_resolved'] = bool(item['material_keys']) and all(objects.get(key, {}).get('type') == 'Material' for key in item['material_keys'])
    item['textures_decoded'] = bool(item['texture_keys']) and all(texture_info.get(key, {}).get('ok', False) for key in item['texture_keys'])
    bones = {key for x in item['renderers'] for key in x['bone_keys'] if key}
    item['bone_references_resolved'] = bool(bones) and all(objects.get(key, {}).get('type') in ('Transform', 'RectTransform') for key in bones)
    item['animator_references'] = [{field: objects[key].get(field) for field in ('controller', 'avatar')} for key in item['animator_keys']]
    item['animator_references_resolved'] = all(ref is None or ref in objects for animator in item['animator_references'] for ref in animator.values())
    item['model_acquired'] = not item['hierarchy_errors'] and item['geometry_readable'] and item['materials_resolved'] and item['textures_decoded']
    item['visual_anatomy_review'] = 'not_performed'
    item['scene_pose_baked'] = False
    item['mesh_exports'] = [mesh_info[key].get('export_path') for key in item['mesh_keys'] if mesh_info.get(key, {}).get('ok')]

for filename, items in [('prefab-inventory.jsonl', prefabs), ('mesh-inventory.jsonl', list(mesh_info.values())), ('texture-inventory.jsonl', list(texture_info.values()))]:
    with (EVIDENCE / filename).open('w') as stream:
        for item in items:
            stream.write(json.dumps(item, ensure_ascii=False) + '\n')
summary = {'prefabs': len(prefabs), 'models_acquired': sum(x['model_acquired'] for x in prefabs),
           'unique_mesh_objects': len(mesh_info), 'readable_mesh_objects': sum(x.get('ok', False) for x in mesh_info.values()),
           'unique_decoded_texture_objects': sum(x.get('ok', False) for x in texture_info.values()),
           'metadata_read_errors': errors,
           'unacquired_prefabs': [x for x in prefabs if not x['model_acquired']],
           'texture_errors': [x for x in texture_info.values() if not x.get('ok')],
           'mesh_errors': [x for x in mesh_info.values() if not x.get('ok')]}
write(WORK / 'inspection-summary.json', summary)
save_progress('catalog-update', inspection_summary={k: v for k, v in summary.items() if not isinstance(v, list)})
print(json.dumps({k: v for k, v in summary.items() if not isinstance(v, list)}), flush=True)
