"""User-authorized coil overlap: keep R5 mesh; bake 9% additional R_IV bend."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Quaternion
R=Path(__file__).resolve().parent; O=R/'motion-r7'; O.mkdir(exist_ok=True)
source=R/'motion-r5/octopus-actions.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');coll=bpy.data.collections['GRAY_REVIEW']
for tr in rig.animation_data.nla_tracks:tr.mute=True
old=bpy.data.actions['TightRoll'];rig.animation_data.action=old;rig.animation_data.action_slot=old.slots[0]
names=[f'R_IV_{j:02d}' for j in range(1,64)];samples=[]
for frame in range(1,302):
 bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();row=[]
 for name in names:
  q=rig.pose.bones[name].rotation_quaternion.copy()
  if q.w<0:q.negate()
  row.append(Quaternion(q.axis,q.angle*1.09) if q.angle>1e-7 else Quaternion())
 samples.append(row)
new=old.copy();old.name='TightRoll_Baseline';new.name='TightRoll'
rig.animation_data.action=new;rig.animation_data.action_slot=new.slots[0]
for frame,row in enumerate(samples,1):
 bpy.context.scene.frame_set(frame)
 for name,q in zip(names,row):
  b=rig.pose.bones[name];b.rotation_mode='QUATERNION';b.rotation_quaternion=q;b.keyframe_insert('rotation_quaternion',frame=frame,group=name)
for tr in rig.animation_data.nla_tracks:
 for st in tr.strips:
  if st.action==old:st.action=new;st.action_slot=new.slots[0]
rig.animation_data.action=None;bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for ob in coll.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'octopus-actions.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(O/'octopus-actions.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_merge_animation='NLA_TRACK',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((R/'motion-r5/build.validation.json').read_text());d.update(kind='user_authorized_tighter_roll',source_sha256=sha(O/'octopus-actions.blend'),model_sha256=sha(O/'octopus-actions.glb'),baseline_source_sha256=sha(source),changed_clip='TightRoll',changed_arm='R_IV',factor=1.09,modified_bones=names,contact_policy='Minor overlap inside coil allowed by user; assess visible intersections, exposed cup penetration and transition continuity; no zero-intersection gate.',morphs=0)
(O/'build.validation.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print('BUILT',d['model_sha256'])
