"""Pack the texture-only bake into a source copy and cold export from it."""
import argparse
import json
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'cli/gamefactory.py').exists())
WORK = ROOT / 'work'
SCRIPTS = ROOT/'resources/scripts/volume-fish'
sys.path[:0] = [str(SCRIPTS),str(SCRIPTS/'portable'),
                str(ROOT/'resources/volume-fish/clean-pixel-peacock-bass-20261111/methods')]
from author_export import (EXACT_NORMAL_ATTRIBUTE, JOINT_ATTRIBUTES, WEIGHT_ATTRIBUTES,
                           arrays, compact, read_glb, sha, snapshot, write, write_array)
from export_ordinary_source_owned import export_source
from restore_fin_source_normals import geometry_signature, normal_attribute_signature
from source_snapshot import rig_action_snapshot

CONTRACT = 'foundry_clean_pixel_source_export_contract'


def material_textures(material):
    pbr = material.get('pbrMetallicRoughness',{})
    return {path:record for path,record in (
        ('base',pbr.get('baseColorTexture')),('emission',material.get('emissiveTexture'))
    ) if record is not None}


def prepare_contract(doc):
    for original in doc['materials']:
        material = bpy.data.materials[original['name']]
        pbr = original.get('pbrMetallicRoughness',{})
        fields = {k:v for k,v in original.items() if k not in ('pbrMetallicRoughness','emissiveTexture')}
        samplers = {}
        for role,tex in material_textures(original).items():
            samplers[role] = doc['samplers'][doc['textures'][tex['index']]['sampler']]
        material[CONTRACT] = json.dumps({'fields':fields,'pbr':{k:v for k,v in pbr.items() if k!='baseColorTexture'},
                                         'samplers':samplers},sort_keys=True)


def native_export(output):
    before = snapshot()
    stock = output.with_name('native-stock.glb')
    assert not stock.exists()
    try:
        bpy.ops.export_scene.gltf(filepath=str(stock),export_format='GLB',export_animations=True,
                                  export_yup=True,export_skins=True,export_attributes=True)
        doc,binary = read_glb(stock)
        blob = bytearray(binary)
        for mesh in doc['meshes']:
            for primitive in mesh['primitives']:
                attrs = primitive['attributes']
                attrs['NORMAL'] = attrs.pop(EXACT_NORMAL_ATTRIBUTE)
                for key,names in [('JOINTS_0',JOINT_ATTRIBUTES),('WEIGHTS_0',WEIGHT_ATTRIBUTES)]:
                    target = attrs[key]
                    old = arrays(doc,binary,target)
                    source = np.concatenate([arrays(doc,binary,attrs.pop(n)) for n in names],axis=1)
                    if key=='JOINTS_0':
                        assert np.array_equal(source,np.rint(source))
                    write_array(doc,blob,target,source.astype(old.dtype))
        sampler_indices = {}
        samplers = []
        for i,mat in enumerate(doc['materials']):
            contract = json.loads(bpy.data.materials[mat['name']][CONTRACT])
            textures = material_textures(mat)
            assert textures.keys()==contract['samplers'].keys(), (mat['name'],textures.keys(),contract['samplers'].keys())
            restored = contract['fields'] | {'pbrMetallicRoughness':contract['pbr']}
            for role,texture in textures.items():
                sampler = contract['samplers'][role]
                if sampler not in samplers:
                    samplers.append(sampler)
                index = texture['index']
                sid = samplers.index(sampler)
                assert sampler_indices.setdefault(index,sid)==sid
                if role=='base':
                    restored['pbrMetallicRoughness']['baseColorTexture'] = texture
                else:
                    restored['emissiveTexture'] = texture
            doc['materials'][i] = restored
        for i,tex in enumerate(doc['textures']):
            tex['sampler'] = sampler_indices[i]
        doc['samplers'] = samplers
        assert snapshot()==before
        write(output,doc,compact(doc,blob))
    finally:
        if stock.is_file():
            stock.unlink()


def source_state():
    meshes = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        uv = {layer.name:np.array([list(loop.uv) for loop in layer.data],np.float32).tobytes()
              for layer in mesh.uv_layers}
        weights = [[(g.group,g.weight) for g in vertex.groups] for vertex in mesh.vertices]
        meshes[obj.name] = (geometry_signature(obj),normal_attribute_signature(obj),uv,weights,
                            [m.name for m in mesh.materials])
    return meshes,rig_action_snapshot()


def apply_images(doc, patches):
    for key,patch in patches.items():
        idx = int(key)
        p = Path(patch['path'])
        assert p.is_relative_to(WORK) and sha(p)==patch['sha256']
        materials = [bpy.data.materials[m['name']] for m in doc['materials']
                     if idx in {doc['textures'][t['index']]['source'] for t in material_textures(m).values()}]
        assert materials
        owners = [n for m in materials for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
        images = {n.image for n in owners}
        assert len(images)==1 and owners,(idx,[m.name for m in materials])
        old = images.pop()
        replacement = bpy.data.images.load(str(p),check_existing=False)
        assert tuple(old.size)==tuple(replacement.size)
        replacement.alpha_mode = old.alpha_mode
        replacement.colorspace_settings.name = old.colorspace_settings.name
        replacement.pack()
        for node in owners:
            node.image = replacement
        name = old.name
        if not old.users:
            bpy.data.images.remove(old)
            replacement.name = name
        else:
            replacement.name = name+' · clean pixel'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--species',choices=['zander','mahi_mahi','african_catfish'],required=True)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--base',type=Path)
    parser.add_argument('--body',type=Path)
    parser.add_argument('--fins',type=Path)
    parser.add_argument('--save-source',type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    for p in (args.output,args.report,args.save_source):
        if p:
            assert p.resolve().is_relative_to(WORK) and not p.exists()
    source_hash = sha(args.source)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    before = source_state()
    if args.save_source:
        body = json.loads((args.body/'bake.validation.json').read_bytes())
        fins = json.loads((args.fins/'bake.validation.json').read_bytes())
        assert body['ok'] and fins['ok'] and fins['body_frozen'] and body['body_rgba']==fins['body_rgba']
        assert body['input_model_sha256']==sha(args.base)
        doc,_ = read_glb(args.base)
        if args.species!='zander':
            prepare_contract(doc)
        apply_images(doc,body['changed_images'] | fins['changed_images'])
        assert source_state()==before
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(args.save_source.resolve()))
    if args.species=='zander':
        export_source(args.output)
    else:
        native_export(args.output)
    assert source_state()==before and sha(args.source)==source_hash
    args.report.write_text(json.dumps({'ok':True,'species':args.species,'source_sha256':sha(args.save_source or args.source),
                                       'model_sha256':sha(args.output),'fresh_process':not bool(args.save_source),
                                       'reference_glb_read_during_export':False,'source_geometry_uv_skin_rig_retained':True,
                                       'exporter_sha256':sha(__file__)},indent=2)+'\n')


if __name__=='__main__':
    main()
