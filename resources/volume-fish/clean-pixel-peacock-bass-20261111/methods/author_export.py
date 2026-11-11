"""Author packed replacement PNGs and export the existing ordinary source alone."""
import argparse
from pathlib import Path
import hashlib
import json
import sys
import bpy
import numpy as np
W=Path(__file__).resolve().parent
ROOT=next(parent for parent in W.parents if (parent/'cli/gamefactory.py').is_file())
sys.path[:0]=[str(ROOT/'resources/scripts/volume-fish/portable'),str(ROOT/'resources/scripts/volume-fish')]
from glb_io import arrays,read_glb,sha
from patch_existing_fin_meshes import write
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature
from source_snapshot import rig_action_snapshot

SOURCE_IMAGE_BY_INDEX=['Anal native source cutout','Caudal native source cutout','Complete anterior mouth color chart.001','Dorsal_soft native source cutout','Dorsal_spiny native source cutout','Pectoral native source cutout','Pelvic native source cutout']
JOINT_ATTRIBUTES=[f'_FOUNDRY_JOINT{i}_GLTF' for i in range(4)]
WEIGHT_ATTRIBUTES=[f'_FOUNDRY_WEIGHT{i}_GLTF' for i in range(4)]

def digest(values):
    return hashlib.sha256(values.tobytes()).hexdigest()

def snapshot():
    state={}
    for ob in bpy.data.objects:
        if ob.type!='MESH':
            continue
        mesh=ob.data
        geom=geometry_signature(ob)
        normal=normal_attribute_signature(ob)
        assert geom==mesh.get('foundry_normal_geometry_sha256') and normal==mesh.get('foundry_exact_normal_sha256'),ob.name
        uv=[]
        for layer in mesh.uv_layers:
            data=np.empty(2*len(layer.uv),dtype=np.float32)
            layer.uv.foreach_get('vector',data)
            uv.append((layer.name,digest(data)))
        skin=[]
        for name in JOINT_ATTRIBUTES+WEIGHT_ATTRIBUTES:
            layer=mesh.attributes[name]
            data=np.empty(len(layer.data),dtype=np.float32)
            layer.data.foreach_get('value',data)
            skin.append(digest(data))
        state[ob.name]=(geom,normal,uv,skin,[m.name for m in mesh.materials])
    return state,rig_action_snapshot()

def write_array(doc,blob,idx,data):
    blob.extend(bytes((-len(blob))%4))
    payload=data.tobytes()
    doc['accessors'][idx]['bufferView']=len(doc['bufferViews'])
    doc['accessors'][idx].pop('byteOffset',None)
    doc['bufferViews'].append({'buffer':0,'byteOffset':len(blob),'byteLength':len(payload),'target':34962})
    blob.extend(payload)

def compact(doc,blob):
    attrs=[]
    for mesh in doc['meshes']:
        for prim in mesh['primitives']:
            attrs.extend((prim['attributes'],key) for key in prim['attributes'])
            attrs.append((prim,'indices'))
    attrs.extend((s,'inverseBindMatrices') for s in doc['skins'])
    for anim in doc['animations']:
        attrs.extend((s,k) for s in anim['samplers'] for k in ('input','output'))
    indices=sorted({r[k] for r,k in attrs})
    index_map={old:new for new,old in enumerate(indices)}
    doc['accessors']=[doc['accessors'][old] for old in indices]
    for r,k in attrs:
        r[k]=index_map[r[k]]
    refs=doc['accessors']+doc['images']
    views=sorted({r['bufferView'] for r in refs})
    view_map={old:new for new,old in enumerate(views)}
    doc['bufferViews']=[doc['bufferViews'][old] for old in views]
    for r in refs:
        r['bufferView']=view_map[r['bufferView']]
    packed=bytearray()
    for view in doc['bufferViews']:
        start=view.get('byteOffset',0)
        end=start+view['byteLength']
        packed.extend(bytes((-len(packed))%4))
        view['byteOffset']=len(packed)
        packed.extend(blob[start:end])
    return packed

def export(output):
    assert not output.exists()
    stock=output.with_name('.'+output.name+'.stock.glb')
    assert not stock.exists()
    try:
        before=snapshot()
        bpy.ops.export_scene.gltf(filepath=str(stock),export_format='GLB',export_animations=True,export_yup=True,export_skins=True,export_attributes=True)
        doc,original=read_glb(stock)
        blob=bytearray(original)
        for mesh in doc['meshes']:
            for prim in mesh['primitives']:
                attrs=prim['attributes']
                normal=attrs.pop(EXACT_NORMAL_ATTRIBUTE)
                attrs['NORMAL']=normal
                for base,names,dtype in [('JOINTS_0',JOINT_ATTRIBUTES,None),('WEIGHTS_0',WEIGHT_ATTRIBUTES,'<f4')]:
                    idx=attrs[base]
                    stock_slots=arrays(doc,original,idx)
                    cols=[arrays(doc,original,attrs.pop(name)) for name in names]
                    slots=np.concatenate(cols,axis=1)
                    if base=='JOINTS_0':
                        assert np.array_equal(slots,np.rint(slots))
                    write_array(doc,blob,idx,slots.astype(dtype or stock_slots.dtype))
        for sampler in doc['samplers']:
            assert sampler['magFilter']==9728 and sampler['wrapS']==sampler['wrapT']==33071
            sampler['minFilter']=9728
        assert snapshot()==before
        write(output,doc,compact(doc,blob))
        return {'ok':True,'source_only':True,'reference_GLB_read':False,'model_sha256':sha(output),'active_accessors':len(doc['accessors']),'source_meshes':list(before[0]),'source_exporter_sha256':sha(__file__)}
    finally:
        if stock.exists():
            stock.unlink()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('model',type=Path)
    parser.add_argument('report',type=Path)
    parser.add_argument('--bake',type=Path)
    parser.add_argument('--output-source',type=Path)
    a=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    output_root = (ROOT/'work').resolve()
    assert a.model.resolve().is_relative_to(output_root) and a.report.resolve().is_relative_to(output_root) and not a.report.exists()
    baseline=sha(a.source)
    bpy.ops.wm.open_mainfile(filepath=str(a.source.resolve()))
    before=snapshot()
    if a.bake:
        p=a.bake/'bake.validation.json'
        proof=json.loads(p.read_text())
        assert proof['ok']
        if proof.get('stage')=='fins':
            assert proof['body_before_fins_RGBA_sha256']==proof['body_after_fins_RGBA_sha256']
            edited_images=range(len(SOURCE_IMAGE_BY_INDEX))
        else:
            assert proof['kind']=='real_pose_peacock_aperture_material_reprojection' and proof['delta_image_only']==2
            assert set(proof['images'])=={'2'} and proof['unchanged_image_alpha']
            edited_images=[2]
        assert a.output_source and a.output_source.resolve().is_relative_to(W) and not a.output_source.exists()
        for i in edited_images:
            name=SOURCE_IMAGE_BY_INDEX[i]
            receipt=proof['images'][str(i)]
            path=Path(receipt['path'])
            assert path.resolve().is_relative_to(W) and sha(path)==receipt['sha256']
            source=bpy.data.images[name]
            owners=[node for m in bpy.data.materials if m.node_tree for node in m.node_tree.nodes if node.type=='TEX_IMAGE' and node.image==source]
            assert owners and all(node.interpolation=='Closest' and node.extension=='EXTEND' for node in owners)
            new=bpy.data.images.load(str(path),check_existing=False)
            assert tuple(source.size)==tuple(new.size)
            new.alpha_mode=source.alpha_mode
            new.colorspace_settings.name=source.colorspace_settings.name
            new.pack()
            for node in owners:
                node.image=new
            source.name=name+' baseline replaced'
            new.name=name
            if not source.users:
                bpy.data.images.remove(source)
        assert snapshot()==before
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(a.output_source.resolve()))
    result=export(a.model)
    assert sha(a.source)==baseline
    result.update(source_sha256=sha(a.output_source if a.bake else a.source),fresh_export=not bool(a.bake),geometry_uv_exact_normal_exact_skin_rig_unchanged=snapshot()==before)
    a.report.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
    main()
