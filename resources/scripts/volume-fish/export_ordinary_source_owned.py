"""Ordinary fish export from source-owned exact normals and explicit texture sampling.

No accepted/reference GLB is read. Every texture-bearing source node must carry
its own nearest/no-mipmap sampler contract. Bone nodes sharing mesh names are
skipped; source normal guards still cover every exported mesh.
"""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from patch_existing_fin_meshes import read,write
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature
SAMPLER='foundry_native_sampler_contract_json'
WRAP={'EXTEND':33071,'REPEAT':10497,'MIRROR':33648}
def export_source(output):
 output=Path(output).resolve();assert not output.exists(),'Fresh ordinary source output required'
 guarded={}
 for ob in bpy.data.objects:
  if ob.type!='MESH':continue
  assert EXACT_NORMAL_ATTRIBUTE in ob.data.attributes,ob.name+' missing exact authored normal stream'
  assert geometry_signature(ob)==ob.data.get('foundry_normal_geometry_sha256'),ob.name+' source geometry guard changed'
  assert normal_attribute_signature(ob)==ob.data.get('foundry_exact_normal_sha256'),ob.name+' source normal guard changed'
  guarded[ob.name]=ob
 assert guarded
 bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',export_animations=True,export_yup=True,export_skins=True,export_attributes=True)
 doc,binary=read(output);bound=[]
 for node in doc['nodes']:
  if node.get('name')not in guarded or'mesh'not in node:continue
  for pr in doc['meshes'][node['mesh']]['primitives']:
   assert EXACT_NORMAL_ATTRIBUTE in pr['attributes'];pr['attributes']['NORMAL']=pr['attributes'].pop(EXACT_NORMAL_ATTRIBUTE)
  bound.append(node['name'])
 assert set(bound)==set(guarded)
 contracts={};source_contracts={}
 def texture_ids(value):
  result=[]
  if isinstance(value,dict):
   for key,item in value.items():
    if key.endswith('Texture')and isinstance(item,dict)and'index'in item:result.append(item['index'])
    else:result.extend(texture_ids(item))
  elif isinstance(value,list):
   for item in value:result.extend(texture_ids(item))
  return result
 for material in doc.get('materials',[]):
  source=bpy.data.materials.get(material.get('name',''));assert source is not None
  native=json.loads(source.get('foundry_export_contract_json','{}'))
  if'alphaMode'in native:material['alphaMode']=native['alphaMode']
  if material.get('alphaMode')=='MASK'and'alphaCutoff'in native:material['alphaCutoff']=native['alphaCutoff']
  material['doubleSided']=native.get('doubleSided',not source.use_backface_culling)
  nodes=[n for n in source.node_tree.nodes if n.type=='TEX_IMAGE'and n.image]if source.use_nodes else[];choices=[]
  for node in nodes:
   assert SAMPLER in node,source.name+'/'+node.name+' missing source sampler contract'
   contract=json.loads(node[SAMPLER]);assert node.interpolation=='Closest'and node.extension in WRAP
   assert contract==dict(magFilter=9728,minFilter=9728,wrapS=WRAP[node.extension],wrapT=WRAP[node.extension]),'Source node/sampler contract mismatch'
   choices.append((node.image.name,contract));source_contracts[source.name+'/'+node.name]=contract
  ids=texture_ids(material)
  for tid in ids:
   choices_for_texture=choices
   if len({json.dumps(c,sort_keys=True)for _,c in choices})>1:
    image_name=doc['images'][doc['textures'][tid]['source']].get('name','');choices_for_texture=[(name,c)for name,c in choices if name==image_name]
   assert choices_for_texture and len({json.dumps(c,sort_keys=True)for _,c in choices_for_texture})==1,'Ambiguous source sampling for '+source.name
   contract=choices_for_texture[0][1];assert tid not in contracts or contracts[tid]==contract,'Shared texture source contract conflict';contracts[tid]=contract
 assert set(contracts)==set(range(len(doc.get('textures',[])))),'Unbound exported texture sampling'
 samplers=[]
 for tid,texture in enumerate(doc.get('textures',[])):
  contract=contracts[tid]
  if contract not in samplers:samplers.append(contract)
  texture['sampler']=samplers.index(contract)
 doc['samplers']=samplers;write(output,doc,binary)
 return dict(ok=True,kind='ordinary_source_owned_export',model_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),source_normal_meshes=bound,source_sampler_contracts=source_contracts,samplers=samplers,source_owned=True,reference_glb_read=False,exporter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ['blend','output','report']:p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);assert not a.report.exists();before=hashlib.sha256(a.blend.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));r=export_source(a.output);assert before==hashlib.sha256(a.blend.read_bytes()).hexdigest();r['source_sha256']=before;a.report.write_text(json.dumps(r,indent=2));print(json.dumps({'ok':True,'model_sha256':r['model_sha256']}))
