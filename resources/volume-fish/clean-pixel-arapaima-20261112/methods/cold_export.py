"""Cold-export the accepted source-owned arapaima; no reconstruction chain."""
import argparse
import json
from pathlib import Path
import sys
import bpy
import numpy as np

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'cli/gamefactory.py').exists())
sys.path[:0] = [str(ROOT / 'resources/volume-fish/clean-pixel-three-20261112/methods'),
                str(ROOT / 'resources/volume-fish/clean-pixel-peacock-bass-20261111/methods')]
from author_three import CONTRACT, material_textures
from author_export import (arrays, read_glb, snapshot, write, compact, write_array,
                           EXACT_NORMAL_ATTRIBUTE, JOINT_ATTRIBUTES, WEIGHT_ATTRIBUTES)

def export(path):
 before=snapshot();stock=path.with_name('native-stock.glb')
 assert not stock.exists()
 try:
  bpy.ops.export_scene.gltf(filepath=str(stock),export_format='GLB',export_animations=True,export_yup=True,export_skins=True,export_attributes=True)
  d,b=read_glb(stock);blob=bytearray(b)
  armature=next(o for o in bpy.data.objects if o.type=='ARMATURE')
  order=json.loads(armature['foundry_exact_joint_names'])
  animation_names=json.loads(armature['foundry_export_animation_names'])
  assert len(animation_names)==len(d['animations'])
  for animation,name in zip(d['animations'],animation_names):animation['name']=name
  for node in d['nodes']:
   if 'mesh' not in node:continue
   names=[d['nodes'][i]['name'] for i in d['skins'][node['skin']]['joints']]
   remap=np.array([names.index(name) for name in order])
   for prim in d['meshes'][node['mesh']]['primitives']:
    a=prim['attributes'];a['NORMAL']=a.pop(EXACT_NORMAL_ATTRIBUTE)
    for key,attrs in [('JOINTS_0',JOINT_ATTRIBUTES),('WEIGHTS_0',WEIGHT_ATTRIBUTES)]:
     old=arrays(d,b,a[key]);src=np.concatenate([arrays(d,b,a.pop(n)) for n in attrs],axis=1)
     if key=='JOINTS_0':
      assert np.array_equal(src,np.rint(src));src=remap[src.astype(int)]
     write_array(d,blob,a[key],src.astype(old.dtype))
  samplers=[];sampler_indices={}
  for i,m in enumerate(d['materials']):
   contract=json.loads(bpy.data.materials[m['name']][CONTRACT]);textures=material_textures(m)
   assert textures.keys()==contract['samplers'].keys()
   restored=contract['fields']|{'pbrMetallicRoughness':contract['pbr']}
   for role,texture in textures.items():
    s=contract['samplers'][role]
    if s not in samplers:samplers.append(s)
    ti=texture['index'];sid=samplers.index(s);assert sampler_indices.setdefault(ti,sid)==sid
    if role=='base':restored['pbrMetallicRoughness']['baseColorTexture']=texture
    else:restored['emissiveTexture']=texture
   d['materials'][i]=restored
  for i,t in enumerate(d['textures']):t['sampler']=sampler_indices[i]
  d['samplers']=samplers
  assert snapshot()==before
  write(path,d,compact(d,blob))
 finally:
  if stock.exists():stock.unlink()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source, output = args.source.resolve(), args.output.resolve()
    assert source.is_file() and source.suffix == '.blend'
    assert not output.exists() and output.suffix == '.glb', 'Use a new verification output'
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    export(output)
