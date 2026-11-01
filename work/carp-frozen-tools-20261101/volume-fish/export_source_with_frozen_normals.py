"""Export guarded source float normals. Does not read normals from a reference GLB.
The source must carry authored FLOAT_VECTOR corner normals plus mesh/normal hashes.
Ordinary Blender INT16_2D viewport normals may differ; static exported NORMAL uses
only the exact float attribute exported by Blender alongside the same vertices.
"""
import bpy,copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from patch_existing_fin_meshes import read,write
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature

def export_guarded(output):
 output=Path(output);assert not output.exists(),'Refuse overwriting export';guarded={}
 for ob in bpy.data.objects:
  if ob.type!='MESH'or EXACT_NORMAL_ATTRIBUTE not in ob.data.attributes:continue
  assert geometry_signature(ob)==ob.data.get('foundry_normal_geometry_sha256'),ob.name+' edited mesh invalidates authored normals'
  assert normal_attribute_signature(ob)==ob.data.get('foundry_exact_normal_sha256'),ob.name+' edited authored normal stream'
  guarded[ob.name]={'geometry_sha256':geometry_signature(ob),'normal_sha256':normal_attribute_signature(ob)}
 assert guarded,'No authored source normal streams'
 bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',export_animations=True,export_yup=True,export_skins=True,export_attributes=True)
 d,b=read(output);original=copy.deepcopy(d);oldbinary=bytes(b);changed=[]
 for n in d['nodes']:
  if n.get('name')not in guarded:continue
  assert'mesh'in n
  for pr in d['meshes'][n['mesh']]['primitives']:
   assert EXACT_NORMAL_ATTRIBUTE in pr['attributes'];idx=pr['attributes'].pop(EXACT_NORMAL_ATTRIBUTE);acc=d['accessors'][idx];assert acc['type']=='VEC3'and acc['componentType']==5126 and acc['count']==d['accessors'][pr['attributes']['POSITION']]['count'];pr['attributes']['NORMAL']=idx
  changed.append(n['name'])
 assert set(changed)==set(guarded)
 # The generated geometry, UV, skin, image and animation streams stay untouched.
 check=copy.deepcopy(d)
 for n in check['nodes']:
  if n.get('name')in guarded:check['meshes'][n['mesh']]=original['meshes'][n['mesh']]
 assert check==original and bytes(b)==oldbinary
 write(output,d,b);return {'ok':True,'source_guards':guarded,'changed_only_NORMAL_bindings':changed,'native_export_binary_prefix_unchanged':True,'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}

def main():
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--blend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);before=hashlib.sha256(a.blend.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));r=export_guarded(a.output.resolve());assert hashlib.sha256(a.blend.read_bytes()).hexdigest()==before;r['blend_sha256']=before;a.report.write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':main()
