import bpy,json,hashlib,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'motion-r6'
def snap():
 data={}
 for ob in bpy.data.collections['GRAY_REVIEW'].objects:
  if ob.type=='MESH':
   vv=ob.data.shape_keys.key_blocks['Basis'].data if ob.data.shape_keys else ob.data.vertices
   data[ob.name]={'vertices':[list(v.co)for v in vv],'faces':[list(p.vertices)for p in ob.data.polygons],'weights':[[(ob.vertex_groups[g.group].name,g.weight)for g in v.groups]for v in ob.data.vertices],'uv':[[list(v.uv)for v in l.data]for l in ob.data.uv_layers],'materials':[m.name for m in ob.data.materials]}
  elif ob.type=='ARMATURE':data[ob.name]={'bones':[(b.name,b.parent.name if b.parent else None,[list(row)for row in b.matrix_local])for b in ob.data.bones]}
 return data
bpy.ops.wm.open_mainfile(filepath=str(R/'motion-r5/octopus-actions.blend'));old=snap()
bpy.ops.wm.open_mainfile(filepath=str(O/'octopus-actions.blend'));new=snap();coll=bpy.data.collections['GRAY_REVIEW'];rig=next(o for o in coll.objects if o.type=='ARMATURE');changes=[];outside=[]
for ob in coll.objects:
 if ob.type!='MESH'or not ob.data.shape_keys:continue
 base=ob.data.shape_keys.key_blocks['Basis'];contact=ob.data.shape_keys.key_blocks['CoilContact_R_IV'];ids=[]
 for v in ob.data.vertices:
  if(contact.data[v.index].co-base.data[v.index].co).length>1e-7:
   ids.append(v.index)
   if sum(g.weight for g in v.groups if ob.vertex_groups[g.group].name.startswith('R_IV_'))<.99:outside.append((ob.name,v.index))
 changes.append({'object':ob.name,'changed_vertices':len(ids)})
checks={'R5_basis_topology_uv_weights_rest_bones_preserved':old==new,'correctives_only_right_IV':not outside and len(changes)==2,'budget':sum(len(p.vertices)-2 for ob in coll.objects if ob.type=='MESH'for p in ob.data.polygons)<=50000}
bpy.ops.object.select_all(action='DESELECT')
for ob in coll.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
cold=O/'octopus-actions.cold.glb'
bpy.ops.export_scene.gltf(filepath=str(cold),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_merge_animation='NLA_TRACK',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();checks['source_cold_export_identical']=sha(cold)==sha(O/'octopus-actions.glb');d={'ok':all(checks.values()),'checks':checks,'correctives':changes,'model_sha256':sha(O/'octopus-actions.glb'),'source_sha256':sha(O/'octopus-actions.blend'),'cold_sha256':sha(cold),'baseline_source_sha256':sha(R/'motion-r5/octopus-actions.blend')};(O/'source.validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
