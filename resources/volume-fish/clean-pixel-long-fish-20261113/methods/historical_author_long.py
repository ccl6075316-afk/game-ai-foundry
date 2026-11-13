"""Pack approved bake patches into a candidate Blender source and cold export."""
import argparse
import json
from pathlib import Path
import sys

import bpy

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
SCRIPTS = ROOT/'resources/scripts/volume-fish'
sys.path[:0] = [str(ROOT/'resources/volume-fish/clean-pixel-three-20261112/methods'),
                str(SCRIPTS/'hairtail_20261104')]
from author_three import native_export, prepare_contract, read_glb, sha, geometry_signature, rig_action_snapshot
from export_contract import export_current


def source_state():
    mesh_states = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        mesh_states[obj.name] = (
            geometry_signature(obj),
            tuple(tuple(normal.vector) for normal in mesh.corner_normals),
            tuple((layer.name, tuple(tuple(loop.uv) for loop in layer.data)) for layer in mesh.uv_layers),
            tuple(tuple((group.group, group.weight) for group in vertex.groups) for vertex in mesh.vertices),
            tuple(material.name for material in mesh.materials),
        )
    return mesh_states, rig_action_snapshot()


def patch_images(doc, patches):
    for image_id, patch in patches.items():
        path = Path(patch['path'])
        assert path.resolve().is_relative_to(WORK) and sha(path)==patch['sha256']
        materials = []
        for record in doc['materials']:
            texture = record.get('emissiveTexture') or record.get('pbrMetallicRoughness',{}).get('baseColorTexture')
            if texture and doc['textures'][texture['index']]['source']==int(image_id):
                materials.append(bpy.data.materials[record['name']])
        owners = [node for material in materials for node in material.node_tree.nodes
                  if node.type=='TEX_IMAGE' and node.image]
        images = {node.image for node in owners}
        assert len(images)==1 and owners,(image_id,[m.name for m in materials])
        old = images.pop()
        replacement = bpy.data.images.load(str(path),check_existing=False)
        assert tuple(replacement.size)==tuple(old.size)
        replacement.colorspace_settings.name = old.colorspace_settings.name
        replacement.alpha_mode = old.alpha_mode
        replacement.pack()
        # Source image nodes can share the native atlas across fins, eyes and
        # teeth. The baked patch has already protected each untouched domain.
        for material in bpy.data.materials:
            if material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type=='TEX_IMAGE' and node.image==old:
                        node.image = replacement
        name = old.name
        bpy.data.images.remove(old)
        replacement.name = name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('species',choices=['hairtail','silver_arowana'])
    parser.add_argument('stage',choices=['pack','cold','formal-cold'])
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    folder = WORK/args.species
    result = folder/'candidate'
    result.mkdir(exist_ok=True)
    official = ROOT/'projects/fishing-2d/assets/source/fish'/args.species/'fish.blend'
    candidate = result/'fish.blend'
    source = candidate if args.stage=='cold' else official
    output = result/('fish.glb' if args.stage=='pack' else args.stage+'.glb')
    assert not output.exists()
    source_sha = sha(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    before = source_state()
    if args.stage=='pack':
        body = json.loads((folder/'body/bake.validation.json').read_text())
        fins = json.loads((folder/'fins/bake.validation.json').read_text())
        assert body['ok'] and fins['ok'] and fins['input_model_sha256']==sha(folder/'body/fish.glb')
        base = ROOT/'projects/fishing-2d/game/assets/models/fish'/f'{args.species}.glb'
        assert body['input_model_sha256']==sha(base)
        doc,_ = read_glb(base)
        if args.species=='silver_arowana':
            prepare_contract(doc)
        patch_images(doc,body['changed_images']|fins['changed_images'])
        assert source_state()==before
        assert not candidate.exists()
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(candidate))
    if args.species=='hairtail':
        export_current(output)
    else:
        native_export(output)
    assert source_state()==before and sha(source)==source_sha
    receipt = {'ok':True,'species':args.species,'model_sha256':sha(output),
               'source_sha256':sha(candidate),'fresh_source_cold_export':args.stage!='pack',
               'source_geometry_uv_skin_rig_unchanged':True}
    (result/f'{args.stage}.validation.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    main()
