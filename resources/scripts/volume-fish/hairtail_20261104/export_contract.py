"""Export ordinary multisurface source and verify its authored material contract."""
import bpy,json,struct,hashlib
from pathlib import Path
def export_current(path):
 path=Path(path);bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_animations=True)
 raw=path.read_bytes();n=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+n]);binary=raw[20+n:]
 contracts={m.name:json.loads(m['foundry_export_contract_json']) for m in bpy.data.materials if 'foundry_export_contract_json' in m}
 rows=[]
 sampler_changes=[]
 for material in doc.get('materials',[]):
  contract=contracts.get(material['name'])
  if not contract:continue
  assert material.get('alphaMode','OPAQUE')==contract['alphaMode'],'Ordinary source export did not honor MASK'
  assert material.get('alphaCutoff',.5)==contract['alphaCutoff']
  rows.append({'name':material['name'],'actual_alphaMode':material.get('alphaMode'),'actual_cutoff_including_spec_default':material.get('alphaCutoff',.5),'contract':contract})
  def texture_refs(value):
   refs=[]
   if isinstance(value,dict):
    for key,child in value.items():
     if key.endswith('Texture') and isinstance(child,dict) and 'index'in child:refs.append(child['index'])
     else:refs+=texture_refs(child)
   return refs
  for ti in texture_refs(material):
   sampler=doc['samplers'][doc['textures'][ti]['sampler']];before=sampler.copy()
   for key in ['magFilter','minFilter','wrapS','wrapT']:sampler[key]=contract[key]
   if before!=sampler:sampler_changes.append({'sampler':doc['textures'][ti]['sampler'],'before':before,'after':sampler.copy()})
 encoded=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode();encoded+=b' '*(-len(encoded)%4)
 output=struct.pack('<4sII',b'glTF',2,20+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+binary
 path.write_bytes(output)
 report={'ok':True,'kind':'source_owned_multimaterial_export_contract','source_contracts':rows,'binary_chunks_sha256':hashlib.sha256(binary).hexdigest(),'alpha_is_native_source_node_export':True,'sampler_metadata_changes':sampler_changes,'complete_BIN_unchanged':output[20+len(encoded):]==binary,'model_sha256':hashlib.sha256(output).hexdigest(),'scope':'MASK derives directly from source GREATER_THAN(.5), never patched. Only source-declared no-mip nearest/clamp sampler metadata is applied after ordinary Blender export (which emits minFilter9984). BIN arrays/PNG and original emission/PBR remain unchanged.'}
 (path.parent/'mask-export.validation.json').write_text(json.dumps(report,indent=2));return report
