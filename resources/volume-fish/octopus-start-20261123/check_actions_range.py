import bpy,math,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-r4'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(OUT/'octopus-actions.glb'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for tr in rig.animation_data.nla_tracks:tr.mute=True
labels=json.loads((ROOT/'motion-r3/rest/gray-build.validation.json').read_text())['arm_labels'];samples=[]
for name,dur in [('TightRoll',10),('ProbeTouch',16),('AlternatingTouch',16)]:
 a=next(a for a in bpy.data.actions if name==a.name);rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
 for f in range(round(dur*30)+1):
  bpy.context.scene.frame_set(f)
  for label in labels:
   bones=[rig.pose.bones[f'{label}_{j:02d}'] for j in range(64)];directions=[b.vector.normalized() for b in bones];arc=sum(b.length for b in bones);turn=sum(a.angle(b) for a,b in zip(directions,directions[1:]));rest=sum(b.bone.length for b in bones)
   samples.append({'clip':name,'frame':f,'arm':label,'chord_over_arc':(bones[-1].tail-bones[0].head).length/arc,'turns':turn/math.tau,'length_relative_error':abs(arc-rest)/rest,'max_head_gap':max((a.tail-b.head).length for a,b in zip(bones,bones[1:]))})
ranges=[]
for label in labels:
 ss=[s for s in samples if s['clip']=='AlternatingTouch' and s['arm']==label];ranges.append({'arm':label,'min_chord_over_arc':min(s['chord_over_arc'] for s in ss),'max_chord_over_arc':max(s['chord_over_arc'] for s in ss),'max_turns':max(s['turns'] for s in ss)})
single=[s for s in samples if s['clip']=='TightRoll' and s['arm']=='R_IV'];key=[s for s in single if s['frame'] in [0,30,60,75,90,120,135,150,180,240,300]]
checks={'both_contact_arms_straighten':all(r['max_chord_over_arc']>.999 for r in ranges if r['arm'] in ['R_IV','L_IV']),'single_coiled_then_straight_then_coiled':single[0]['turns']>1.1 and single[135]['chord_over_arc']>.999 and single[240]['turns']>1.1,'bone_chain_lengths_preserved':max(s['length_relative_error']for s in samples)<1e-4,'bone_chains_connected':max(s['max_head_gap']for s in samples)<1e-4}
report={'model_sha256':hashlib.sha256((OUT/'octopus-actions.glb').read_bytes()).hexdigest(),'method':'Cold imported native GLB skeleton evaluated at every frame; no authoring control metrics used','checks':checks,'ok':all(checks.values()),'evaluated_arm_poses':len(samples),'max_relative_length_error':max(s['length_relative_error']for s in samples),'max_head_gap':max(s['max_head_gap']for s in samples),'ranges':ranges,'single_arm_key_samples':key,'limits':['Skeleton arclength/chord/unsigned turning, not exact skin strain or biological articulation measurement']};(OUT/'range.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
