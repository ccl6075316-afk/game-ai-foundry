"""Complete distal coiling to straight extension via a travelling bend front."""
import bpy,math,json,hashlib,bisect
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-r3';REST=OUT/'rest'
build=json.loads((REST/'gray-build.validation.json').read_text());paths=build['control_paths'];labels=build['arm_labels']
bpy.ops.wm.open_mainfile(filepath=str(REST/'octopus-gray.blend'))
scene=bpy.context.scene;scene.render.fps=30;coll=bpy.data.collections['GRAY_REVIEW'];meshes=[o for o in coll.objects if o.type=='MESH']
N=64
roots=[Vector(p[0]) for p in paths];directions=[(Vector(p[-1])-Vector(p[0])).normalized() for p in paths];lengths=[(Vector(p[-1])-Vector(p[0])).length for p in paths]
stations=[[lengths[i]*(1-(1-j/N)**1.6) for j in range(N+1)] for i in range(8)]
chains=[[roots[i]+directions[i]*s for s in stations[i]] for i in range(8)]
armdata=bpy.data.armatures.new('Octopus_roll_rig');rig=bpy.data.objects.new('Octopus_roll_rig',armdata);coll.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
r=armdata.edit_bones.new('Root');r.head=(0,0,.3);r.tail=(0,0,.6)
for i,ch in enumerate(chains):
 parent=r
 for j in range(N):
  b=armdata.edit_bones.new(f'{labels[i]}_{j:02d}');b.head=ch[j];b.tail=ch[j+1];b.parent=parent;b.use_connect=j>0;parent=b
bpy.ops.object.mode_set(mode='OBJECT')
# Use exact nearest positions on straight arm axes; dense geometry supplies
# deformation resolution, and proximal web attachment remains in the straight zone.
def smooth(x):x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def weights_for_arm(i,s):
 centers=[(a+b)*.5 for a,b in zip(stations[i],stations[i][1:])];k=bisect.bisect_right(centers,s)
 if k==0:return [(f'{labels[i]}_00',1.)]
 if k>=N:return [(f'{labels[i]}_{N-1:02d}',1.)]
 q=(s-centers[k-1])/(centers[k]-centers[k-1]);return [(f'{labels[i]}_{k-1:02d}',1-q),(f'{labels[i]}_{k:02d}',q)]
for ob in meshes:
 for vg in list(ob.vertex_groups):ob.vertex_groups.remove(vg)
 for bone in armdata.bones:ob.vertex_groups.new(name=bone.name)
 for v in ob.data.vertices:
  p=ob.matrix_world@v.co
  if ob.name.startswith(('Eye','Oral_','Open_siphon')) or ((p.x*p.x+p.y*p.y)**.5<1.5 and p.z>.43):weights={'Root':1.}
  else:
   candidates=[]
   for i in range(8):
    s=max(0,min(lengths[i],(p-roots[i]).dot(directions[i])));h=roots[i]+directions[i]*s;dist=Vector((p.x-h.x,p.y-h.y,0)).length;candidates.append((dist,i,s))
   candidates.sort();d,i,s=candidates[0];radial=(p.x*p.x+p.y*p.y)**.5;aw=smooth((radial-.22)/.36);choices=[(i,s,1.)]
   if not ob.name.startswith('Paired_sucker') and radial<1.6:
    d2,i2,s2=candidates[1];a=1/max(.01,d)**4;b=1/max(.01,d2)**4;choices=[(i,s,a/(a+b)),(i2,s2,b/(a+b))]
   weights={'Root':1-aw}
   for ci,cs,cw in choices:
    for name,w in weights_for_arm(ci,cs):weights[name]=weights.get(name,0)+cw*w*aw
  weights=dict(sorted(((n,w) for n,w in weights.items() if w>1e-8),key=lambda x:-x[1])[:4]);total=sum(weights.values())
  for name,w in weights.items():ob.vertex_groups[name].add([v.index],w/total,'REPLACE')
 mod=ob.modifiers.new('Bend propagation skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False;ob.parent=rig
rest={b.name:b.matrix_local.copy() for b in armdata.bones}
# This is a reach-range demonstration, not propulsion. Preserve arc length while
# curvature disappears behind a root-to-tip front, leaving a truly straight arm.
CURL_START=.35;WIDTH=.12;PACKING=1.10
# The radial pitch derives from the finite arm/cup envelope, not a fixed turn count.
def radius_profile(t):
 def ease(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
 return .137*(1-t)**1.32+.009+.026*ease((t-.55)/.25)*(1-ease((t-.94)/.06))
def curve_point(i,t):
 pts=paths[i];u=t*(len(pts)-1);j=min(int(u),len(pts)-2);f=u-j
 a,b,c,d=[Vector(pts[k]) for k in [max(0,j-1),j,j+1,min(len(pts)-1,j+2)]]
 return .5*(2*b+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f)
curvature_tables=[];spiral_diagnostics=[]
for i,L in enumerate(lengths):
 tt=np.linspace(0,1,1001);ss=np.array([(curve_point(i,float(t))-roots[i]).dot(directions[i]) for t in tt])
 def envelope(s):
  t=float(np.interp(s,ss,tt));return max(.83*radius_profile(t), .69*radius_profile(t)+.021*(1-t)+.003)+.002
 u=0.;theta=0.;radius=.025;coords=[];material=[];angles=[]
 while u<L*(1-CURL_START)+.005:
  coords.append([radius*math.cos(theta),radius*math.sin(theta)]);material.append(u);angles.append(theta)
  dr=PACKING*(2*envelope(L-u)+.006)/math.tau;dt=.003
  u+=math.sqrt(radius*radius+dr*dr)*dt;radius+=dr*dt;theta+=dt
 # Turning angle derivative of the actual densely sampled spiral.
 pts=np.asarray(coords);uu=np.asarray(material);v=np.gradient(pts,axis=0);phi=np.unwrap(np.arctan2(v[:,1],v[:,0]));k=np.gradient(phi,uu)
 positions=L-uu[::-1];curvature=k[::-1]
 curvature_tables.append((positions,curvature))
 spiral_diagnostics.append({'arm':labels[i],'spiral_polar_turns':theta/math.tau,'outer_radius':radius,'inner_radius':.025,'packing_factor':PACKING,'envelope':'max(0.83*radius,0.69*radius+cup rim height)+0.002 ML','gap_allowance_ML':.006})

def extension(clip,t,i):
 if clip=='SingleArmRoll':
  if i!=7:return .07+[.10,.02,.16,.04,.13,.06,.09,.0][i]
  if t<=1:return 0.
  if t<4:return smooth((t-1)/3)
  if t<=5:return 1.
  if t<8:return 1-smooth((t-5)/3)
  return 0.
 phase=(t/14+[.00,.44,.76,.19,.61,.88,.31,.54][i])%1.
 if phase<.08:return 0.
 if phase<.40:return smooth((phase-.08)/.32)
 if phase<.55:return 1.
 if phase<.91:return 1-smooth((phase-.55)/.36)
 return 0.

def pose_arm(i,e,plane):
 L=lengths[i];s0=CURL_START*L;front=s0-WIDTH+(L-s0+2*WIDTH)*e
 table_s,table_k=curvature_tables[i]
 side=directions[i].cross(Vector((0,0,1))).normalized();bend=Vector((0,0,-1))*math.cos(plane)+side*math.sin(plane);axis=directions[i].cross(bend).normalized()
 theta=0.;head=roots[i].copy();targets=[];total_turn=0
 for j,(s1,s2) in enumerate(zip(stations[i],stations[i][1:])):
  # Integrate curvature over material arclength, sub-stepping each bone.
  increment=0.
  for k in range(8):
   s=s1+(k+.5)*(s2-s1)/8
   curvature=0. if s<s0 else float(np.interp(s,table_s,table_k))*smooth((s-front)/WIDTH)*smooth((s-s0)/.10)
   increment+=curvature*(s2-s1)/8
  midtheta=theta+.5*increment;q=Quaternion(axis,midtheta);targets.append((head.copy(),q));head+=q@directions[i]*(s2-s1);theta+=increment
 return targets,head,theta
clips=[('SingleArmRoll',10.),('EightArmReach',14.)];metrics=[]
for clip,duration in clips:
 rig.animation_data_clear();rig.animation_data_create();action=bpy.data.actions.new(clip);rig.animation_data.action=action
 count=round(duration*30)
 for f in range(count+1):
  t=f/30;desired={'Root':rest['Root']};rig.pose.bones['Root'].matrix_basis=Matrix.Identity(4)
  for i in range(8):
   e=extension(clip,t,i);plane=[-.12,.08,-.18,.10,-.07,.16,-.10,.0][i]
   targets,tip,turn=pose_arm(i,e,plane)
   for j,(head,q) in enumerate(targets):
    name=f'{labels[i]}_{j:02d}';parent=armdata.bones[name].parent.name;target=q.to_matrix().to_4x4()@rest[name];target.translation=head
    pb=rig.pose.bones[name];pb.rotation_mode='QUATERNION';pb.matrix_basis=rest[name].inverted()@rest[parent]@desired[parent].inverted()@target;desired[name]=target
    pb.keyframe_insert('rotation_quaternion',frame=f+1,group=name);pb.keyframe_insert('location',frame=f+1,group=name)
   if f%15==0:metrics.append({'clip':clip,'time':t,'arm':labels[i],'extension':e,'turns':turn/math.tau,'root_to_tip_over_arm_arc':(tip-roots[i]).length/lengths[i]})
  bpy.context.view_layer.update()
rig.animation_data_clear();rig.animation_data_create()
for clip,duration in clips:
 tr=rig.animation_data.nla_tracks.new();tr.name=clip;st=tr.strips.new(clip,1,bpy.data.actions[clip]);st.action_frame_end=round(duration*30)+1;tr.mute=True
rig.animation_data.action=bpy.data.actions['SingleArmRoll'];scene.frame_start=1;scene.frame_end=421;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for ob in [*meshes,rig]:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'octopus-roll.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'octopus-roll.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
tri=sum(len(p.vertices)-2 for ob in meshes for p in ob.data.polygons);assert tri<=50000
report={'kind':'octopus_full_roll_trial','status':'candidate','triangles':tri,'bones':len(armdata.bones),'arm_segments':N,'suckers':512,'clips':[{'name':n,'duration':d} for n,d in clips],'source_sha256':hashlib.sha256((OUT/'octopus-roll.blend').read_bytes()).hexdigest(),'model_sha256':hashlib.sha256((OUT/'octopus-roll.glb').read_bytes()).hexdigest(),'mechanism':{'curl_start_fraction':CURL_START,'spiral_profiles':spiral_diagnostics,'bend_front_width_ML':WIDTH,'arc_length_scaling':False},'sampled_control_metrics':metrics,'limits':['A full-range reach demonstration; not a swimming or crawling cycle','Curl amount, duration and coordinated sequence are authored targets; cross-species research supports the mechanism, not exact GPO kinematics','512 simplified cups; not an anatomical count'],'budget_basis':'User explicitly allows <=50000 triangles'}
(OUT/'build.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sampled_control_metrics'}))
