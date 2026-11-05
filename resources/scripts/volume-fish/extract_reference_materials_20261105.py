"""Recover original library material/alpha inputs for read-only model comparisons.

Uses the archived prefab's actual material order, never a guessed texture by name.
The original Unity shader is not reconstructed; outputs describe a diagnostic
diffuse/alpha interpretation and preserve all original material properties.
"""
import argparse
import hashlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB = ROOT / 'resources/fish-database'
SID = 'fishing-master-cdn-cnformal1-20261102'
EVIDENCE = DB / 'evidence' / SID


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(name):
    return [json.loads(s) for s in (EVIDENCE / name).read_text(encoding='utf8').splitlines() if s.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deps', required=True, type=Path)
    parser.add_argument('--mesh', action='append', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(ROOT / 'output')
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.deps.resolve()))
    import UnityPy

    bundles = {x['resource_path']: x for x in rows('bundle-inventory.jsonl')}
    meshes = rows('mesh-inventory.jsonl')
    prefabs = rows('prefab-inventory.jsonl')
    textures = {x['object_key'].lower(): x for x in rows('texture-inventory.jsonl')}
    cab_bundle = {}
    for bundle in bundles.values():
        for key in bundle.get('containers', {}).values():
            cab_bundle[key.split(':')[0].lower()] = bundle['resource_path']
    for item in meshes + list(textures.values()):
        cab_bundle[item['object_key'].split(':')[0].lower()] = item['bundle']

    @lru_cache(maxsize=6)
    def load_bundle(resource):
        record = bundles[resource]
        path = DB / record['artifact_path']
        assert sha(path) == record['sha256'], path
        raw = path.read_bytes()
        env = UnityPy.load(raw[record.get('unityfs_prefix_skipped', 0):])
        readers = {f'{o.assets_file.name}:{o.path_id}'.lower(): o for o in env.objects}
        return env, readers

    def object_for(key):
        resource = cab_bundle[key.split(':')[0].lower()]
        return load_bundle(resource)[1][key.lower()], resource

    def pointer_key(reader, ptr):
        file_id = int(ptr['m_FileID'])
        if file_id == 0:
            cab = reader.assets_file.name
        else:
            external = reader.assets_file.externals[file_id - 1]
            matches = re.findall(r'cab-[0-9a-f]{32}', external.path, re.I)
            assert matches, str(external.path)
            cab = matches[-1]
        return f'{cab}:{ptr["m_PathID"]}'

    results = []
    for mesh_path in args.mesh:
        mesh_path = mesh_path.resolve()
        assert mesh_path.is_relative_to(DB) and mesh_path.suffix == '.obj'
        digest = sha(mesh_path)
        mesh = next(x for x in meshes if x['sha256'] == digest)
        candidates = [p for p in prefabs if mesh['object_key'] in p['mesh_keys']]
        assert candidates, str(mesh_path)
        # This chooses only a material presentation for the identical archived
        # mesh. Historical adoption is independently recorded by the caller.
        candidates.sort(key=lambda p: (bool(re.search(r'_(rare|elite|monster|l\d+)', p['prefab_path'], re.I)), p['prefab_path']))
        prefab = candidates[0]
        renderer = next(x for x in prefab['renderers'] if x['mesh_key'] == mesh['object_key'])
        groups = []
        group = None
        for line in mesh_path.read_text(encoding='utf8').splitlines():
            if line.startswith('g '):
                group = line[2:].strip()
            elif line.startswith('f '):
                assert group is not None
                if group not in groups:
                    groups.append(group)
        folder = output / digest
        folder.mkdir(exist_ok=True)
        materials = []
        for index, material_key in enumerate(renderer['material_keys']):
            group = next(g for g in groups if g.endswith('_' + str(index)))
            reader, material_bundle = object_for(material_key)
            tree = reader.read_typetree()
            saved = tree['m_SavedProperties']
            floats = dict(saved.get('m_Floats', []))
            colors = dict(saved.get('m_Colors', []))
            texenvs = dict(saved.get('m_TexEnvs', []))
            env = next((texenvs[k] for k in ('_BaseMap', '_MainTex') if k in texenvs and texenvs[k]['m_Texture']['m_PathID']), None)
            tags = dict(tree.get('stringTagMap', []))
            alpha_mode = 'MASK' if floats.get('_AlphaClip', 0) > .5 or tags.get('RenderType') == 'TransparentCutout' else 'BLEND' if floats.get('_Surface', 0) > .5 or tags.get('RenderType') == 'Transparent' else 'OPAQUE'
            color = colors.get('_BaseColor', colors.get('_Color', dict(r=1, g=1, b=1, a=1)))
            row = {'group': group, 'name': tree['m_Name'], 'source_material_key': material_key,
                   'material_bundle': material_bundle, 'alpha_mode': alpha_mode,
                   'alpha_cutoff': floats.get('_Cutoff', .5),
                   'base_color': [color[k] for k in 'rgba'],
                   'double_sided': floats.get('_Cull', 2) == 0,
                   'uv_scale': [1., 1.], 'uv_offset': [0., 0.],
                   'interpolation': 'Closest', 'original_material_properties': tree}
            if env is not None:
                key = pointer_key(reader, env['m_Texture'])
                texture_reader, texture_bundle = object_for(key)
                image = texture_reader.read().image.convert('RGBA')
                pixel_sha = hashlib.sha256(image.tobytes()).hexdigest()
                original = textures.get(key.lower())
                if original:
                    assert pixel_sha == original['decoded_pixels_sha256'], key
                path = folder / (pixel_sha + '.png')
                if not path.exists():
                    image.save(path)
                row.update(texture_path=str(path), texture_sha256=sha(path),
                           decoded_pixels_sha256=pixel_sha, texture_key=key,
                           texture_bundle=texture_bundle,
                           uv_scale=[env['m_Scale'][k] for k in 'xy'],
                           uv_offset=[env['m_Offset'][k] for k in 'xy'])
            materials.append(row)
        assert set(groups) == {m['group'] for m in materials}, (groups, [m['group'] for m in materials])
        used = sorted({mesh['bundle'], prefab['bundle']} | {m['material_bundle'] for m in materials} | {m['texture_bundle'] for m in materials if 'texture_bundle' in m})
        report = {'ok': True, 'mesh': {'path': str(mesh_path), 'sha256': digest},
                  'mesh_object_key': mesh['object_key'], 'prefab': prefab['prefab_path'],
                  'prefab_material_selection': 'base presentation of the identical archived mesh; not a new assertion of historical adoption',
                  'unitypy_version': UnityPy.__version__, 'obj_materials': materials,
                  'source_bundles': [{'path': str(DB / bundles[k]['artifact_path']), 'sha256': bundles[k]['sha256']} for k in used],
                  'limits': 'Original RGBA/UV/material alpha properties, standardized diffuse renderer; original Unity custom shader, normal maps and render queue not reproduced.'}
        target = folder / 'materials.json'
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        assert sha(mesh_path) == digest
        results.append({'mesh': str(mesh_path), 'materials': str(target), 'groups': len(materials)})
    print(json.dumps({'ok': True, 'results': results}, ensure_ascii=False))


if __name__ == '__main__':
    main()
