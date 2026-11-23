import bpy,json,hashlib,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'motion-r4';FLOOR=-.25;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(O/'octopus-actions.glb'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');skin=bpy.data.objects['Octopus_gray_skin'];cups=next(o for o in bpy.data.objects if o.name.startswith('Paired_sucker'))
for tr in rig.animation_data.nla_tracks:tr.mute=True
names={g.index:g.name for g in cups.vertex_groups};owned={label:[v.index for v in cups.data.vertices if sum(g.weight for g in v.groups if names[g.group].startswith(label+'_'))>.99]for label in ['R_IV','L_IV']}
reports=[];patch_reports=[]
for clip in ['ProbeTouch','AlternatingTouch']:
 a=bpy.data.actions[clip];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
 def coordinates(frame):
  bpy.context.scene.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get();values={}
  for o in [skin,cups]:
   ev=o.evaluated_get(deps);me=ev.to_mesh();values[o.name]=np.array([ev.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear()
  return values
 for f in range(0,481,3):
  vals=coordinates(f);reports.append({'clip':clip,'frame':f,'minimum_clearance':float(min(v[:,2].min()for v in vals.values())-FLOOR)})
 for label,first,last in [('R_IV',180,240)]+([('L_IV',420,480)]if clip=='AlternatingTouch'else[]):
  pts=coordinates(first)[cups.name];ids=[i for i in owned[label]if pts[i,2]<FLOOR+.003];assert ids,(clip,label);initial=pts[ids];samples=[]
  for f in range(first,last+1):
   current=coordinates(f)[cups.name];selected=current[ids];samples.append({'frame':f,'minimum_contact_clearance':float(current[owned[label],2].min()-FLOOR),'patch_lateral_drift':float(np.linalg.norm(selected[:,:2]-initial[:,:2],axis=1).max()),'patch_max_height_change':float(np.abs(selected[:,2]-initial[:,2]).max())})
  patch_reports.append({'clip':clip,'arm':label,'window_seconds':[first/30,last/30],'patch_vertices':len(ids),'max_lateral_drift':max(x['patch_lateral_drift']for x in samples),'max_height_change':max(x['patch_max_height_change']for x in samples),'samples':samples})
checks={'no_sampled_skin_or_cup_ground_penetration':min(s['minimum_clearance']for s in reports)>-1e-5,'contact_patch_present':all(p['patch_vertices']>=2 for p in patch_reports),'contact_within_0_003_ML':all(-1e-5<=s['minimum_contact_clearance']<=.003 for p in patch_reports for s in p['samples']),'contact_patch_does_not_slide':all(p['max_lateral_drift']<.001 and p['max_height_change']<.001 for p in patch_reports)}
d={'kind':'native_octopus_ground_contact','model_sha256':hashlib.sha256((O/'octopus-actions.glb').read_bytes()).hexdigest(),'floor_z':FLOOR,'checks':checks,'ok':all(checks.values()),'body_cup_samples':reports,'contact_patches':patch_reports,'limits':['Kinematic reach/contact, no suction force or body locomotion','Floor clearance includes authored 0.0008 ML margin','Global ground samples every3 frames; holds each frame; not continuous proof']};(O/'ground.validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'checks':checks,'min_clearance':min(s['minimum_clearance']for s in reports),'patches':[{k:v for k,v in p.items()if k!='samples'}for p in patch_reports]}))
