import bpy,numpy as np,json,hashlib
from mathutils.kdtree import KDTree
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'motion-r6';desired=np.load(O/'contact-targets.npz')['skin'];bpy.ops.wm.open_mainfile(filepath=str(O/'octopus-actions.blend'));skin=bpy.data.objects['Octopus_gray_skin'];rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');basis=np.array([v.co for v in skin.data.shape_keys.key_blocks['Basis'].data]);lookup={tuple(np.round(v,5)):i for i,v in enumerate(basis)};kd=KDTree(len(basis))
for i,v in enumerate(basis):kd.insert(v,i)
kd.balance()
for t in rig.animation_data.nla_tracks:t.mute=True
rig.animation_data.action=bpy.data.actions['TightRoll'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
keys=skin.data.shape_keys
for t in keys.animation_data.nla_tracks:t.mute=True
keys.animation_data.action=None;keys.key_blocks['CoilContact_R_IV'].value=1;bpy.context.scene.frame_set(1);bpy.context.view_layer.update();ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();actual=np.array([v.co for v in me.vertices]);print('SOURCE_MAX',np.linalg.norm(actual-desired,axis=1).max());ev.to_mesh_clear()
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'octopus-actions.glb'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');skin=next(o for o in bpy.data.objects if o.type=='MESH'and o.data.name.startswith('Tight_coil_skin'))
for id in [rig,skin.data.shape_keys]:
 for t in id.animation_data.nla_tracks:
  t.mute=True
  if t.name=='TightRoll':a=t.strips[0].action;slot=t.strips[0].action_slot
 id.animation_data.action=a;id.animation_data.action_slot=slot
bpy.context.scene.frame_set(0);bpy.context.view_layer.update();ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();errors=[];miss=0
for v in skin.data.vertices:
 k=lookup.get(tuple(np.round(np.array(skin.data.shape_keys.key_blocks['Basis'].data[v.index].co),5)))
 if k is None:
  _,k,dist=kd.find(skin.data.shape_keys.key_blocks['Basis'].data[v.index].co)
  if dist>1e-4:miss+=1;continue
 diff=np.linalg.norm(np.array(me.vertices[v.index].co)-desired[k]);errors.append((float(diff),v.index,k,list(me.vertices[v.index].co),desired[k].tolist()))
errors.sort(reverse=True);print('COLD_ERROR',errors[:3],'MISS',miss)

report={'ok':miss==0 and errors[0][0]<1e-4,'model_sha256':hashlib.sha256((O/'octopus-actions.glb').read_bytes()).hexdigest(),'matched_vertices':len(errors),'misses':miss,'maximum_cold_to_intended_surface_error_ML':errors[0][0],'method':'Cold native bone plus morph evaluation; rest Basis nearest matching to saved intended source target'}
(O/'target.validation.json').write_text(json.dumps(report,indent=2)+'\n')
