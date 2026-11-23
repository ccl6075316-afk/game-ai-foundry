"""Tighter curls plus reference-informed reach, touch, tip probe and recovery."""
import bpy,math,json,hashlib,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motion-r5';REST=ROOT/'motion-r3/rest'
build=json.loads((REST/'gray-build.validation.json').read_text());paths=build['control_paths'];labels=build['arm_labels'];N=64
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'motion-r4/octopus-actions.blend'))
scene=bpy.context.scene;scene.render.fps=30;coll=bpy.data.collections['GRAY_REVIEW'];meshes=[o for o in coll.objects if o.type=='MESH'];rig=next(o for o in coll.objects if o.type=='ARMATURE');armdata=rig.data
exec(compile((ROOT/'thicken_octopus_arms.py').read_text(),str(ROOT/'thicken_octopus_arms.py'),'exec'))
modify_arms(ROOT,OUT)
rig.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
roots=[Vector(p[0])for p in paths];directions=[(Vector(p[-1])-Vector(p[0])).normalized()for p in paths];lengths=[(Vector(p[-1])-Vector(p[0])).length for p in paths]
stations=[[lengths[i]*(1-(1-j/N)**1.6)for j in range(N+1)]for i in range(8)];rest={b.name:b.matrix_local.copy()for b in armdata.bones}
def smooth(x):x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
CURL_START=.35;WIDTH=.12;PACKING=1.02
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
  t=float(np.interp(s,ss,tt));scale=1+.06*smooth((s/L-.35)/.30)+.39*smooth((s/L-.92)/.08);return max(.83*radius_profile(t)*scale, (.69*radius_profile(t))*scale+.021*(1-t)+.003)+.002
 u=0.;theta=0.;radius=.025;coords=[];material=[];angles=[]
 while u<L*(1-CURL_START)+.005:
  coords.append([radius*math.cos(theta),radius*math.sin(theta)]);material.append(u);angles.append(theta)
  dr=(1.06 if i==1 else 1.03 if i==7 else PACKING)*(2*envelope(L-u)+.006)/math.tau;dt=.003
  u+=math.sqrt(radius*radius+dr*dr)*dt;radius+=dr*dt;theta+=dt
 # Turning angle derivative of the actual densely sampled spiral.
 pts=np.asarray(coords);uu=np.asarray(material);v=np.gradient(pts,axis=0);phi=np.unwrap(np.arctan2(v[:,1],v[:,0]));k=np.gradient(phi,uu)
 positions=L-uu[::-1];curvature=k[::-1]
 curvature_tables.append((positions,curvature))
 spiral_diagnostics.append({'arm':labels[i],'spiral_polar_turns':theta/math.tau,'outer_radius':radius,'inner_radius':.025,'packing_factor':1.06 if i==1 else 1.03 if i==7 else PACKING,'envelope':'max(0.83*radius,0.69*radius+cup rim height)+0.002 ML','gap_allowance_ML':.006})
def pose_arm(i,e,plane,sag=0.,tip=0.):
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
  fraction=(s1+s2)*.5/L
  lower=sag*math.sin(math.pi*(fraction-.35)/.47)**2 if .35<fraction<.82 else 0.
  tip_lift=-tip*smooth((fraction-.85)/.15)
  midtheta=theta+.5*increment;q=Quaternion(axis,midtheta+lower+tip_lift);targets.append((head.copy(),q));head+=q@directions[i]*(s2-s1);theta+=increment
 return targets,head,theta

FLOOR_Z=-.25
base_e=[.16,.42,.23,.55,.32,.48,.20,.12]
base_plane=[-.12,.08,-.18,.10,-.07,.16,-.10,0.]
def set_pose(parameters,frame=None):
 desired={'Root':rest['Root']};rig.pose.bones['Root'].matrix_basis=Matrix.Identity(4);arm_metrics=[]
 for i,(e,plane,sag,tip) in enumerate(parameters):
  targets,end,turn=pose_arm(i,e,plane,sag,tip)
  for j,(head,q) in enumerate(targets):
   name=f'{labels[i]}_{j:02d}';parent=armdata.bones[name].parent.name;target=q.to_matrix().to_4x4()@rest[name];target.translation=head
   pb=rig.pose.bones[name];pb.rotation_mode='QUATERNION';pb.matrix_basis=rest[name].inverted()@rest[parent]@desired[parent].inverted()@target;desired[name]=target
   if frame is not None:
    pb.keyframe_insert('rotation_quaternion',frame=frame,group=name);pb.keyframe_insert('location',frame=frame,group=name)
  arm_metrics.append({'arm':labels[i],'extension':e,'sag':sag,'tip_lift':tip,'turns':turn/math.tau,'chord_over_chain':(end-roots[i]).length/lengths[i]})
 bpy.context.view_layer.update()
 return arm_metrics
# Solve the contact lowering angle against the actual weighted skin and cup vertices.
contact_masks={}
for i in [0,7]:
 contact_masks[i]={}
 for ob in meshes:
  if ob.name!='Octopus_gray_skin' and not ob.name.startswith('Paired_sucker'):continue
  names={g.index:g.name for g in ob.vertex_groups};ids=[]
  for v in ob.data.vertices:
   w=sum(g.weight for g in v.groups if names[g.group].startswith(labels[i]+'_'))
   if w>.99 and (v.co-roots[i]).dot(directions[i])>.70*lengths[i]:ids.append(v.index)
  contact_masks[i][ob.name]=ids

def min_contact_z(i):
 deps=bpy.context.evaluated_depsgraph_get();value=100.
 for name,ids in contact_masks[i].items():
  ob=bpy.data.objects[name];ev=ob.evaluated_get(deps);me=ev.to_mesh();value=min(value,min((ev.matrix_world@me.vertices[k].co).z for k in ids));ev.to_mesh_clear()
 return value
contact_angles={}
for i in [0,7]:
 lo,hi=0.,1.2
 for iteration in range(18):
  mid=(lo+hi)*.5;params=[(base_e[j],base_plane[j],0.,0.)for j in range(8)];params[i]=(1.,0.,mid,0.);set_pose(params)
  if min_contact_z(i)>FLOOR_Z+.0008:lo=mid
  else:hi=mid
 contact_angles[i]=(lo+hi)*.5
contact_targets={}
for i in [0,7]:
 params=[(base_e[j],base_plane[j],0.,0.)for j in range(8)];params[i]=(1.,0.,contact_angles[i],0.);set_pose(params)
 points=[];deps=bpy.context.evaluated_depsgraph_get()
 for name,ids in contact_masks[i].items():
  ev=bpy.data.objects[name].evaluated_get(deps);me=ev.to_mesh();points.extend(ev.matrix_world@me.vertices[k].co for k in ids);ev.to_mesh_clear()
 contact_targets[i]=list(min(points,key=lambda p:p.z))
print('CONTACT_ANGLES',contact_angles,'TARGETS',contact_targets,flush=True)

def contact_sequence(t,i):
 t=t%16.
 if t<1.5:return (.12+.035*math.sin(math.pi*t/1.5)**2,base_plane[i],0.,0.)
 if t<4.5:return (.12+.88*smooth((t-1.5)/3),base_plane[i],0.,0.)
 if t<6:return (1.,0.,contact_angles[i]*smooth((t-4.5)/1.5),0.)
 if t<8:return (1.,0.,contact_angles[i],.20*math.sin(math.pi*(t-6)/2)**2)
 if t<10:return (1.,0.,contact_angles[i]*(1-smooth((t-8)/2)),0.)
 if t<13.5:return (1-.88*smooth((t-10)/3.5),base_plane[i],0.,0.)
 return (.12,base_plane[i],0.,0.)

def parameters(clip,t):
 if clip=='TightRoll':
  if t<=1:e=0.
  elif t<4:e=smooth((t-1)/3)
  elif t<=5:e=1.
  elif t<8:e=1-smooth((t-5)/3)
  else:e=0.
  return [(e if i==7 else base_e[i],base_plane[i],0.,0.)for i in range(8)]
 values=[]
 for i in range(8):
  if i==7:values.append(contact_sequence(t,i))
  elif i==0 and clip=='AlternatingTouch':values.append(contact_sequence(t+8,i))
  else:
   wave=math.sin(math.tau*t/16+i*.7)-math.sin(i*.7)
   values.append((base_e[i]+.025*wave,base_plane[i],0.,0.))
 return values

clips=[('TightRoll',10.),('ProbeTouch',16.),('AlternatingTouch',16.)]
if '--probe' in sys.argv:
 skin=bpy.data.objects['Octopus_gray_skin'];facekeys=[set(tuple(round(x,5)for x in skin.data.vertices[i].co)for i in p.vertices)for p in skin.data.polygons];reports=[]
 for clip,t in [('TightRoll',0),('TightRoll',2.5),('ProbeTouch',0),('ProbeTouch',4.5),('ProbeTouch',6),('ProbeTouch',7),('ProbeTouch',9),('ProbeTouch',11),('AlternatingTouch',0),('AlternatingTouch',6),('AlternatingTouch',14)]:
  set_pose(parameters(clip,t));deps=bpy.context.evaluated_depsgraph_get();ev=skin.evaluated_get(deps);me=ev.to_mesh();verts=[ev.matrix_world@v.co for v in me.vertices];tree=BVHTree.FromPolygons(verts,[list(p.vertices)for p in me.polygons],all_triangles=True);pairs=[(a,b)for a,b in tree.overlap(tree)if a<b and not facekeys[a].intersection(facekeys[b])];minz=min(v.z for v in verts);ev.to_mesh_clear();reports.append({'clip':clip,'time':t,'intersections':len(pairs),'example_pairs':pairs[:8],'skin_min_z':minz,'right_contact_z':min_contact_z(7),'left_contact_z':min_contact_z(0)})

 cups=bpy.data.objects['Paired_sucker_rows_512_cups'];ff=[[list(p.vertices)for p in ob.data.polygons]for ob in [skin,cups]];cc=[[sum((ob.data.vertices[v].co for v in face),Vector())/len(face)for face in faces]for ob,faces in zip([skin,cups],ff)]
 for report in reports:
  set_pose(parameters(report['clip'],report['time']));deps=bpy.context.evaluated_depsgraph_get();trees=[]
  for ob,faces in zip([skin,cups],ff):
   ev=ob.evaluated_get(deps);me=ev.to_mesh();trees.append(BVHTree.FromPolygons([ev.matrix_world@v.co for v in me.vertices],faces,all_triangles=False));ev.to_mesh_clear()
  report['nonlocal_cup_skin_intersections']=len([(a,b)for a,b in trees[0].overlap(trees[1])if(cc[0][a]-cc[1][b]).length>.15])
 (OUT/'pose-probe.json').write_text(json.dumps({'packing':PACKING,'floor_z':FLOOR_Z,'contact_angles':contact_angles,'samples':reports},indent=2)+'\n');print(json.dumps(reports));sys.exit(0)
metrics=[]
for clip,duration in clips:
 rig.animation_data_clear();rig.animation_data_create();action=bpy.data.actions.new(clip);rig.animation_data.action=action
 for f in range(round(duration*30)+1):
  t=f/30;rows=set_pose(parameters(clip,t),f+1)
  if f%15==0:metrics.append({'clip':clip,'time':t,'arms':rows})
rig.animation_data_clear();rig.animation_data_create()
for clip,duration in clips:
 tr=rig.animation_data.nla_tracks.new();tr.name=clip;st=tr.strips.new(clip,1,bpy.data.actions[clip]);st.action_frame_end=round(duration*30)+1;tr.mute=True
rig.animation_data.action=bpy.data.actions['ProbeTouch'];scene.frame_start=1;scene.frame_end=481;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for ob in [*meshes,rig]:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'octopus-actions.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'octopus-actions.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
tri=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons);assert tri<=50000
report={'kind':'octopus_contact_actions','status':'candidate','triangles':tri,'bones':len(armdata.bones),'arm_segments':N,'suckers':512,'clips':[{'name':n,'duration':d}for n,d in clips],'source_sha256':hashlib.sha256((OUT/'octopus-actions.blend').read_bytes()).hexdigest(),'model_sha256':hashlib.sha256((OUT/'octopus-actions.glb').read_bytes()).hexdigest(),'floor_z':FLOOR_Z,'contact_angles':contact_angles,'contact_targets':contact_targets,'packing_factor':PACKING,'spiral_profiles':spiral_diagnostics,'sampled_control_metrics':metrics,'limits':['Authored reference-informed reach/contact sequence; not motion capture','Root stationary; no locomotion or suction physics','Distal arm skin thickened and caps shortened; cups translated to support; original topology/UV/weights/rest bones preserved']};(OUT/'build.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='sampled_control_metrics'}))
