import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'motion-r6';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'motion-r5/octopus-actions.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');skin=bpy.data.objects['Octopus_gray_skin']
for tr in rig.animation_data.nla_tracks:tr.mute=True
rig.animation_data.action=bpy.data.actions['TightRoll'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
build=json.loads((R/'motion-r3/rest/gray-build.validation.json').read_text());path=build['control_paths'][7];root=Vector(path[0]);L=(Vector(path[-1])-root).length;direction=(Vector(path[-1])-root).normalized();bones=[rig.pose.bones[f'R_IV_{j:02d}']for j in range(64)];ss=[(b.bone.head_local-root).dot(direction)for b in bones];aa=[0.]
for a,b in zip(bones,bones[1:]):aa.append(aa[-1]+a.vector.angle(b.vector))
ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();ids=[];coords=[];normals=[];fractions=[];angles=[]
for v in skin.data.vertices:
 w=sum(g.weight for g in v.groups if skin.vertex_groups[g.group].name.startswith('R_IV_'));s=(v.co-root).dot(direction)
 if w>.99 and s/L>.4:
  ids.append(v.index);coords.append(list(me.vertices[v.index].co));normals.append(list(me.vertices[v.index].normal));fractions.append(s/L);angles.append(float(np.interp(s,ss,aa)))
p=np.array(coords);nn=np.array(normals);a=np.array(angles);f=np.array(fractions);candidates=[]
for i in range(len(p)):
 diff=a-a[i];dist=np.linalg.norm(p-p[i],axis=1);mask=(diff>math.pi*1.5)&(diff<math.pi*2.5)&(dist>.0001)&(dist<.09)
 for j in np.where(mask)[0]:
  n=(p[j]-p[i])/dist[j]
  if nn[i]@n>.4 and nn[j]@n<-.4:
   candidates.append((float(dist[j]),i,int(j)))
candidates.sort();chosen=[]
for d,i,j in candidates:
 c=(p[i]+p[j])*.5
 if all(np.linalg.norm(c-q['center'])>.075 for q in chosen):
  chosen.append({'distance':d,'ids':[ids[i],ids[j]],'fractions':[f[i],f[j]],'center':c.tolist(),'normal':((p[j]-p[i])/d).tolist(),'points':[p[i].tolist(),p[j].tolist()]})
 if len(chosen)>=12:break
(O/'contact-probe.json').write_text(json.dumps({'candidates':len(candidates),'patches':chosen},indent=2)+'\n');print(json.dumps(chosen))
for prop in ['export_animation_mode','export_merge_animation','export_nla_strips','export_anim_single_armature','export_morph_animation']:
 p=bpy.ops.export_scene.gltf.get_rna_type().properties.get(prop)
 if p:print(prop,p.description,[(x.identifier,x.description)for x in p.enum_items]if p.type=='ENUM'else p.default)
