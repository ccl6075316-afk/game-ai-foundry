"""Source-owned ordinary export preserving actual normalized named skin weights.

Blender5's default glTF exporter discards influences <=.0001. This adapter uses
a temporary explicit source-vertex ID stream, then writes source weights and
joint indices into each actual primitive, removing the temporary attribute.
No target-model geometry, normal, skin or material data is read or copied.
"""
import bpy,sys,json,hashlib,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'resources/scripts/volume-fish/portable'),str(ROOT/'resources/scripts/volume-fish')]
from glb_io import read_glb,arrays
from patch_existing_fin_meshes import write
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
MARKER='_FND_SOURCE_VERTEX_ID'
def export(output,clip_name):
 source_weights={};ignored=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  m=ob.data;attribute=m.attributes.get(MARKER)or m.attributes.new(MARKER,'INT','POINT')
  for v in m.vertices:attribute.data[v.index].value=v.index
  groups={g.index:g.name for g in ob.vertex_groups};rows=[]
  for v in m.vertices:
   named={groups[g.group]:float(g.weight)for g in v.groups if g.group in groups and g.weight>1e-9};invalid=[g.group for g in v.groups if g.group not in groups and g.weight>1e-9]
   if invalid:ignored.append(dict(mesh=ob.name,vertex=v.index,ignored_deleted_group_indices=invalid))
   total=sum(named.values());assert total>0 and len(named)<=4,(ob.name,v.index,named);rows.append({k:w/total for k,w in named.items()})
  source_weights[ob.name]=rows
 bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False,export_attributes=True)
 d,blob=read_glb(output);blob=bytearray(blob);proof=[]
 def put(accessor_id,index,values):
  acc=d['accessors'][accessor_id];view=d['bufferViews'][acc['bufferView']];ctype=acc['componentType'];fmt={5121:'B',5123:'H',5125:'I',5126:'f'}[ctype];size=struct.calcsize('<4'+fmt);offset=view.get('byteOffset',0)+acc.get('byteOffset',0)+index*view.get('byteStride',size);struct.pack_into('<4'+fmt,blob,offset,*values)
 for node in d['nodes']:
  if 'mesh'not in node:continue
  name=node['name'];assert name in source_weights;names=[d['nodes'][j]['name']for j in d['skins'][node['skin']]['joints']];joint={name:i for i,name in enumerate(names)};seen=set();small=0
  for pr in d['meshes'][node['mesh']]['primitives']:
   assert MARKER in pr['attributes'];ids=arrays(d,blob,pr['attributes'][MARKER]).reshape(-1);oldw=arrays(d,blob,pr['attributes']['WEIGHTS_0']).copy();oldj=arrays(d,blob,pr['attributes']['JOINTS_0']).copy();changed=0
   for i,source_index in enumerate(ids):
    source_index=int(source_index);named=source_weights[name][source_index];ordered=sorted(named.items(),key=lambda r:(-r[1],r[0]));js=[joint[k]for k,w in ordered];ws=[w for k,w in ordered];small+=sum(0<w<=.0001 for w in ws);seen.add(source_index)
    js+= [0]*(4-len(js));ws+=[0.]*(4-len(ws));put(pr['attributes']['JOINTS_0'],i,js);put(pr['attributes']['WEIGHTS_0'],i,ws)
    old_named={names[int(j)]:float(w)for j,w in zip(oldj[i],oldw[i])if w>1e-9}
    if set(old_named)!=set(named)or any(abs(old_named.get(k,0)-w)>1e-7 for k,w in named.items()):changed+=1
   pr['attributes'].pop(MARKER);proof.append(dict(mesh=name,source_vertices=len(source_weights[name]),export_rows=len(ids),rows_corrected_from_source=changed,preserved_sub_0001_influences=small))
  assert seen==set(range(len(source_weights[name]))),(name,'Unrepresented source vertex identity',len(seen),len(source_weights[name]))
 assert len(d.get('animations',[]))==1;d['animations'][0]['name']=clip_name
 for s in d.get('samplers',[]):s.update(magFilter=9728,minFilter=9728)
 # Emit actual glTF defaults explicitly for durable material-chart identity.
 # This reads no old model and changes no alpha/culling behavior.
 for material in d.get('materials',[]):material.setdefault('alphaMode','OPAQUE');material.setdefault('doubleSided',False)
 write(output,d,blob)
 return dict(ok=True,kind='source_owned_exact_ordinary_skin_export',source_vertex_identity_used=True,temporary_marker_removed=True,no_target_model_read=True,static_builders_disabled=True,rows=proof,ignored_deleted_group_entries=ignored,model_sha256=sha(output),exporter_sha256=sha(__file__),native_clip_name=clip_name,limit='Preserves source float weights; actual Godot GPU storage/UNORM16 conversion and all physical/visual checks remain separate.')
if __name__=='__main__':
 a=sys.argv[sys.argv.index('--')+1:];source=Path(a[0]).resolve();profile=Path(a[1]).resolve();output=Path(a[2]).resolve();report=Path(a[3]).resolve();assert not output.exists()and not report.exists();assert output.is_relative_to(ROOT/'projects/fishing-2d/experiments')and report.parent==output.parent;before=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source));result=export(output,json.loads(profile.read_text())['base_clip']);assert before==sha(source);result.update(source_blend=dict(path=str(source),sha256=before),motion_profile=dict(path=str(profile),sha256=sha(profile)),fresh_process=True);report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(ok=True,model_sha256=result['model_sha256'],corrected_rows=sum(r['rows_corrected_from_source']for r in result['rows']))))
