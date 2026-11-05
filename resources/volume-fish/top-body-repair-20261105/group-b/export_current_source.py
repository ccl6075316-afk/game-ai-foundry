"""Fresh ordinary source export with exact owned normals and named source weights."""
from pathlib import Path
import bpy,json,sys,hashlib
ROOT=next(p for p in Path(__file__).resolve().parents if(p/'cli/gamefactory.py').exists());P=Path(__file__).parent;sys.path[:0]=[str(P),str(ROOT/'resources/scripts/volume-fish'),str(ROOT/'resources/scripts/volume-fish/portable')]
from source_exact_skin import export as exact_skin
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature
from patch_existing_fin_meshes import read,write
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();source,profile,dest=map(lambda q:Path(q).resolve(),sys.argv[sys.argv.index('--')+1:]);base=dest.parent;base.mkdir(parents=True,exist_ok=True);assert not dest.exists();before=SHA(source);bpy.ops.wm.open_mainfile(filepath=str(source));guards={}
contracts={}
for mat in bpy.data.materials:
 if 'foundry_export_contract_json'not in mat:continue
 contract=json.loads(mat['foundry_export_contract_json']);contracts[mat.name]=contract
 bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');links=list(bs.inputs['Alpha'].links);assert len(links)==1;gate=links[0].from_node
 assert gate.type=='MATH'and gate.operation=='GREATER_THAN'and not gate.inputs[1].is_linked and gate.inputs[1].default_value==contract['alphaCutoff'],(mat.name,'Source cutout threshold drift')
 assert (not mat.use_backface_culling)==contract['doubleSided'],(mat.name,'Source culling drift')
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 assert EXACT_NORMAL_ATTRIBUTE in ob.data.attributes;assert geometry_signature(ob)==ob.data['foundry_normal_geometry_sha256'];assert normal_attribute_signature(ob)==ob.data['foundry_exact_normal_sha256'];guards[ob.name]={'geometry':geometry_signature(ob),'normal':normal_attribute_signature(ob)}
skin=exact_skin(dest,json.loads(profile.read_text())['base_clip']);d,b=read(dest);owners=[]
for node in d['nodes']:
 if 'mesh'not in node:continue
 assert node['name']in guards
 for pr in d['meshes'][node['mesh']]['primitives']:
  acc=pr['attributes'].pop(EXACT_NORMAL_ATTRIBUTE);assert d['accessors'][acc]['count']==d['accessors'][pr['attributes']['POSITION']]['count'];pr['attributes']['NORMAL']=acc
 owners.append(node['name'])
material_semantics=[]
for material in d['materials']:
 owner=bpy.data.materials.get(material.get('name',''))
 if owner is None or'foundry_native_alpha_mode_explicit'not in owner:continue
 mode=owner['foundry_native_alpha_mode'];assert material.get('alphaMode','OPAQUE')==mode
 if owner['foundry_native_alpha_mode_explicit']:material['alphaMode']=mode
 else:assert mode=='OPAQUE';material.pop('alphaMode',None)
 double=not owner.use_backface_culling
 if owner['foundry_native_double_sided_explicit']:material['doubleSided']=double
 else:assert not double;material.pop('doubleSided',None)
 material_semantics.append({'material':owner.name,'alpha_mode':mode,'double_sided':double,'source_owned_explicit_defaults':True})
for name,contract in contracts.items():
 material=next(m for m in d['materials']if m.get('name')==name);assert material.get('alphaMode','OPAQUE')==contract['alphaMode']and material.get('alphaCutoff',.5)==contract['alphaCutoff']and material.get('doubleSided',False)==contract['doubleSided'],(name,'Cold cutout contract drift')
 for sampler in d.get('samplers',[]):assert sampler.get('magFilter')==9728 and sampler.get('minFilter')==9728,'Native nearest/no-mip contract drift'
assert set(owners)==set(guards)and len(owners)==len(guards);write(dest,d,b);assert SHA(source)==before;result={'ok':True,'kind':'fresh_exact_source_normal_and_skin_multimesh_export','source_sha256':before,'output_sha256':SHA(dest),'guarded_mesh_owners':guards,'normal_attribute':EXACT_NORMAL_ATTRIBUTE,'source_owned_skin_proof':skin,'mesh_bone_name_collisions_disambiguated':True,'native_material_semantics':material_semantics,'exporter_sha256':SHA(__file__),'skin_helper_sha256':SHA(P/'source_exact_skin.py'),'source_unchanged_on_disk':True,'actual_source_cutout_contracts_verified':contracts};(base/'cold-export.validation.json').write_text(json.dumps(result,indent=2)+'\n');print('EXACT_COLD',source.stem,SHA(dest),'tiny_weights',sum(r['preserved_sub_0001_influences']for r in skin['rows']))
