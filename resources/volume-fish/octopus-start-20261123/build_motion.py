"""Bake two editable trial animations on the unchanged R2 grey geometry."""
import bpy, bmesh, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-r1';OUT.mkdir(exist_ok=True)
build=json.loads((ROOT/'motion-r1/rest/gray-build.validation.json').read_text());paths=build['control_paths']
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'motion-r1/rest/octopus-gray.blend'))
scene=bpy.context.scene;coll=bpy.data.collections['GRAY_REVIEW'];meshes=list(coll.objects)
# Remove hidden construction geometry from the export selection only.
N=18

def curve(pts,t):
 u=t*(len(pts)-1);i=min(int(u),len(pts)-2);f=u-i
 a,b,c,d=[Vector(pts[k]) for k in [max(0,i-1),i,i+1,min(len(pts)-1,i+2)]]
 return .5*(2*b+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f)

def resample(pts):
 dense=[curve(pts,k/1000) for k in range(1001)];cum=[0.]
 for a,b in zip(dense,dense[1:]):cum.append(cum[-1]+(b-a).length)
 import bisect
 out=[]
 for j in range(N+1):
  target=cum[-1]*j/N;k=max(1,min(1000,bisect.bisect_left(cum,target)))
  out.append(dense[k-1].lerp(dense[k],(target-cum[k-1])/(cum[k]-cum[k-1])))
 return out
chains=[resample(p) for p in paths]
armdata=bpy.data.armatures.new('Octopus_trial_rig');rig=bpy.data.objects.new('Octopus_trial_rig',armdata);coll.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
root=armdata.edit_bones.new('Root');root.head=(0,0,.3);root.tail=(0,0,.6)
mantle=armdata.edit_bones.new('Mantle');mantle.head=build['mantle_eye_midpoint'];mantle.tail=Vector(mantle.head)+Vector(build['mantle_measurement_axis'])*.7;mantle.parent=root
for i,chain in enumerate(chains):
 parent=root
 for j in range(N):
  bone=armdata.edit_bones.new(f'{build["arm_labels"][i]}_{j:02d}');bone.head=chain[j];bone.tail=chain[j+1];bone.parent=parent;bone.use_connect=j>0;parent=bone
bpy.ops.object.mode_set(mode='OBJECT')
# Assign skin by nearest arm paths; the web blends the two closest chains.
def near_chain(p,chain):
 best=(1e9,0.,None)
 for j,(a,b) in enumerate(zip(chain,chain[1:])):
  v=b-a;vxy=Vector((v.x,v.y,0));delta=Vector((p.x-a.x,p.y-a.y,0))
  q=max(0.,min(1.,delta.dot(vxy)/vxy.length_squared));h=a+q*v;d=Vector((p.x-h.x,p.y-h.y,0)).length
  if d<best[0]:best=(d,j+q,h)
 return best

def smooth(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
def bind_pair(i,s):
 # Bone centres, rather than bone heads, provide smooth adjacent weights.
 u=max(0,min(N-1,s-.5));a=int(u);b=min(N-1,a+1);q=u-a
 return [(f'{build["arm_labels"][i]}_{a:02d}',1-q),(f'{build["arm_labels"][i]}_{b:02d}',q)]
for ob in meshes:
 bpy.context.view_layer.objects.active=ob
 for vg in list(ob.vertex_groups):ob.vertex_groups.remove(vg)
 for bone in armdata.bones:ob.vertex_groups.new(name=bone.name)
 for vert in ob.data.vertices:
  p=ob.matrix_world@vert.co;weights={}
  if ob.name.startswith(('Eye','Open_siphon','Oral_')):weights={'Root':1.}
  else:
   near=sorted([(near_chain(p,ch),i) for i,ch in enumerate(chains)],key=lambda x:x[0][0]);(dist,s,h),i=near[0]
   is_cup=ob.name.startswith('Paired_sucker')
   # Body and eye shoulders are protected. Distal raised tips remain arm-owned.
   body_zone=(p.x*p.x+p.y*p.y)**.5<1.5 and p.z>.40
   if body_zone and not is_cup:
    axial=(p-Vector(build['mantle_eye_midpoint'])).dot(Vector(build['mantle_measurement_axis']))
    mw=smooth((axial-.12)/.35);weights={'Root':1-mw,'Mantle':mw}
   else:
    radial=(p.x*p.x+p.y*p.y)**.5;aw=smooth((radial-.22)/.36)
    choices=[(i,s,1.)]
    if not is_cup and radial<1.55:
     (d2,s2,h2),i2=near[1];w1=1/max(.015,dist)**4;w2=1/max(.015,d2)**4
     choices=[(i,s,w1/(w1+w2)),(i2,s2,w2/(w1+w2))]
    weights={'Root':1-aw}
    for ci,cs,cw in choices:
     for name,w in bind_pair(ci,cs):weights[name]=weights.get(name,0)+w*cw*aw
  weights={n:w for n,w in weights.items() if w>1e-7}
  # Keep at most four influences, as in glTF's ordinary skin representation.
  weights=dict(sorted(weights.items(),key=lambda x:-x[1])[:4]);total=sum(weights.values())
  for name,w in weights.items():ob.vertex_groups[name].add([vert.index],w/total,'REPLACE')
 mod=ob.modifiers.new('Trial skeletal deformation','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
 ob.parent=rig
# Bake global target orientations while retaining every bone's rest length.
rest={b.name:b.matrix_local.copy() for b in armdata.bones}
clips=[('ArmExplore',6.),('JetGlide',4.8)]
scene.render.fps=30
for name,duration in clips:
 rig.animation_data_clear();rig.animation_data_create();action=bpy.data.actions.new(name);rig.animation_data.action=action
 frames=round(duration*30)
 for frame in range(frames+1):
  t=frame/30;phase=t/duration*math.tau
  for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
  pb=rig.pose.bones['Mantle'];pb.scale=(1-.025*(.5+.5*math.cos(phase)) if name=='JetGlide' else 1,1,1-.025*(.5+.5*math.cos(phase)) if name=='JetGlide' else 1)
  desired={'Root':rest['Root']}
  for i,chain in enumerate(chains):
   radial=Vector((chain[2].x,chain[2].y,0)).normalized();fold_axis=radial.cross(Vector((0,0,-1))).normalized()
   head=chain[0].copy();offset=[0,1.8,3.6,.9,4.8,2.7,5.5,4.1][i]
   for j in range(N):
    u=(j+.5)/N;bone_name=f'{build["arm_labels"][i]}_{j:02d}';bone=armdata.bones[bone_name]
    if name=='ArmExplore':
     fold=.10+.08*math.sin(phase+offset)+.50*u*u*math.sin(phase-u*3+offset)
     sweep=.065*u*math.sin(phase-u*2+offset)
    else:
     pulse=.5+.5*math.cos(phase-.2)
     fold=.10+.22*pulse + .24*u*u*math.sin(phase-u*2.5+offset)
     sweep=.035*u*math.sin(phase-u*2+offset)
    q=Quaternion(Vector((0,0,1)),sweep)@Quaternion(fold_axis,fold)
    target=q.to_matrix().to_4x4()@rest[bone_name];target.translation=head
    parent=bone.parent.name
    rig.pose.bones[bone_name].matrix_basis=rest[bone_name].inverted()@rest[parent]@desired[parent].inverted()@target
    desired[bone_name]=target
    head=head+q@(chain[j+1]-chain[j])
  for pb in rig.pose.bones:
   pb.rotation_mode='QUATERNION';pb.keyframe_insert('rotation_quaternion',frame=frame+1,group=pb.name);pb.keyframe_insert('location',frame=frame+1,group=pb.name);pb.keyframe_insert('scale',frame=frame+1,group=pb.name)
  bpy.context.view_layer.update()
 # Actions export via one named NLA track each.
 track=rig.animation_data.nla_tracks.new();track.name=name;strip=track.strips.new(name,1,action);strip.action_frame_start=1;strip.action_frame_end=frames+1
 # Keep track list across animation_data_clear by storing actions until end.
rig.animation_data_clear();rig.animation_data_create()
for name,duration in clips:
 track=rig.animation_data.nla_tracks.new();track.name=name;strip=track.strips.new(name,1,bpy.data.actions[name]);strip.action_frame_end=round(duration*30)+1
scene.frame_start=1;scene.frame_end=181;scene.frame_set(1)
# Avoid overlapping NLA evaluation in the authoring view; active action is explicit.
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=bpy.data.actions['ArmExplore']
bpy.ops.object.select_all(action='DESELECT')
for ob in [*meshes,rig]:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'octopus-motion.blend'),compress=True)
# ACTIONS exports the authored actions even though preview NLA tracks are muted.
bpy.ops.export_scene.gltf(filepath=str(OUT/'octopus-motion.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
report={'kind':'octopus_motion_trial_build','source_baseline':str(ROOT/'motion-r1/rest/octopus-gray.blend'),'source_baseline_sha256':hashlib.sha256((ROOT/'motion-r1/rest/octopus-gray.blend').read_bytes()).hexdigest(),'bones':len(armdata.bones),'arm_segments':N,'clips':[{'name':n,'duration':d} for n,d in clips],'web_support':'Derived R2 control geometry: web half-thickness 0.028–0.053 ML, 4800 skin-triangle target; length constraints retained', 'triangles':sum(len(p.vertices)-2 for ob in meshes for p in ob.data.polygons),'model_sha256':hashlib.sha256((OUT/'octopus-motion.glb').read_bytes()).hexdigest(),'limitations':['Trial motion timing and angles are authored, not specimen measurements','Membrane locally thickened and subdivided for trial deformation; not final production topology','No suckered contact or crawling/feeding simulation','Root path is a separate normalized stage demonstration, not calibrated swimming velocity']}
(OUT/'build.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
