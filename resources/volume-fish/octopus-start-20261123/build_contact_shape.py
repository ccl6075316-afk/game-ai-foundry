"""R6 single-arm authored contact corrective; source morphs export with native bones."""
import bpy,json,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;O=R/'motion-r6';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'motion-r5/octopus-actions.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');coll=bpy.data.collections['GRAY_REVIEW'];skin=bpy.data.objects['Octopus_gray_skin'];cups=bpy.data.objects['Paired_sucker_rows_512_cups']
for tr in rig.animation_data.nla_tracks:tr.mute=True
rig.animation_data.action=bpy.data.actions['TightRoll'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
path=json.loads((R/'motion-r3/rest/gray-build.validation.json').read_text())['control_paths'][7];root=np.array(path[0]);direction=np.array(path[-1])-root;L=np.linalg.norm(direction);direction/=L;axis=np.cross(direction,[0,0,-1]);axis/=np.linalg.norm(axis)
patches=[json.loads((O/'contact-probe.json').read_text())['patches'][i] for i in [1,5]]
for patch in patches:
 n=np.array(patch['normal']);n-=axis*np.dot(n,axis);n/=np.linalg.norm(n);patch['normal']=n.tolist();patch['tangent']=np.cross(axis,n).tolist()
def ease(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def choose(p,f):
 best=(0.,None,0)
 for k,patch in enumerate(patches):
  c=np.array(patch['center']);n=np.array(patch['normal']);t=np.array(patch['tangent']);a,b=patch['fractions'];side=1 if abs(f-a)<abs(f-b)else-1;target=a if side==1 else b
  signed=side*np.dot(p-c,n)
  if signed>.001 or signed<-.12:continue
  material=ease(1-abs(f-target)/(.075 if side==1 else .045));tangent=ease((.075-abs(np.dot(p-c,t)))/.035);width=ease((.075-abs(np.dot(p-c,axis)))/.035);w=material*tangent*width
  if w>best[0]:best=(float(w),k,side)
 return best

def deform(p,f):
 w,k,side=choose(p,f)
 if k is None or w<1e-6:return p.copy(),None
 patch=patches[k];c=np.array(patch['center']);n=np.array(patch['normal']);q=p+n*side*(patch['distance']*.5+.025)*w
 depth=side*np.dot(q-c,n)
 compressed=bool(depth>0)
 if compressed:q-=n*side*depth
 return q,{'patch':k,'side':side,'weight':w,'compressed':compressed}

bonemats={b.name:np.array(b.matrix@b.bone.matrix_local.inverted())for b in rig.pose.bones};evidence=[];targetsets={};assignments={}
for ob in [skin,cups]:
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();posed=np.array([v.co for v in me.vertices]);ev.to_mesh_clear();rest=np.array([v.co for v in ob.data.vertices]);names={g.index:g.name for g in ob.vertex_groups};owned=np.array([sum(g.weight for g in v.groups if names[g.group].startswith('R_IV_'))>.99 for v in ob.data.vertices]);f=((rest-root)@direction)/L;target=posed.copy();infos=[None]*len(rest)
 if ob==skin:
  for i in np.where(owned&(f>.35))[0]:target[i],infos[i]=deform(posed[i],f[i])
  # Regularize the displacement over original topology, retaining a central common-plane contact patch.
  adj=[set()for v in ob.data.vertices]
  for edge in ob.data.edges:
   a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
  original_delta=target-posed;delta=original_delta.copy();movable=np.where(owned&(f>.35))[0];pins=[]
  for i in movable:
   info=infos[i]
   if info and info['compressed'] and info['weight']>.60:
    patch=patches[info['patch']];t=np.array(patch['tangent']);c=np.array(patch['center'])
    if abs((posed[i]-c)@t)<.028:pins.append((i,info['patch']))
  constraints=[]
  for k,patch in enumerate(patches):
   c=np.array(patch['center']);n=np.array(patch['normal']);t=np.array(patch['tangent']);a,b=patch['fractions']
   for side,fc,fw in [(1,a,.065),(-1,b,.040)]:
    selected={int(i)for i in movable if abs(f[i]-fc)<fw and abs((posed[i]-c)@t)<.080 and abs((posed[i]-c)@axis)<.085 and abs((posed[i]-c)@n)<.085}
    grown=set(selected)
    for i in selected:
     for j in adj[i]:
      if owned[j] and abs(f[j]-fc)<fw*1.35:grown.add(j)
    constraints.extend((i,k,side)for i in grown)
  for iteration in range(50):
   new=delta.copy()
   for i in movable:new[i]=.20*original_delta[i]+.80*delta[list(adj[i])].mean(axis=0)
   for i,k in pins:
    n=np.array(patches[k]['normal']);c=np.array(patches[k]['center']);new[i]-=n*((posed[i]+new[i]-c)@n)
   for i,k,side in constraints:
    n=np.array(patches[k]['normal']);c=np.array(patches[k]['center']);penetration=side*((posed[i]+new[i]-c)@n)
    if penetration>0:new[i]-=side*n*penetration
   delta=new
  target=posed+delta
  # Extend the shared contact halfspaces over complete crossing triangles at the boundary.
  faces=[tuple(poly.vertices)for poly in ob.data.polygons];face_sets=[set(x)for x in faces];boundary_steps=[]
  def transverse(A,B):
   na=np.cross(A[1]-A[0],A[2]-A[0]);nb=np.cross(B[1]-B[0],B[2]-B[0]);na/=max(1e-20,np.linalg.norm(na));nb/=max(1e-20,np.linalg.norm(nb));da=(A-B[0])@nb;db=(B-A[0])@na
   return da.min()<-1e-5 and da.max()>1e-5 and db.min()<-1e-5 and db.max()>1e-5
  for iteration in range(12):
   tree=BVHTree.FromPolygons([Vector(v)for v in target],faces,all_triangles=True);bad=[(a,b)for a,b in tree.overlap(tree)if a<b and not face_sets[a].intersection(face_sets[b])and transverse(target[list(faces[a])],target[list(faces[b])])]
   boundary_steps.append(len(bad))
   if not bad:break
   for a,b in bad:
    fa=float(f[list(faces[a])].mean());fb=float(f[list(faces[b])].mean())
    if abs(fa-fb)<.08:continue
    k=min(range(len(patches)),key=lambda k:min(abs(fa-patches[k]['fractions'][0])+abs(fb-patches[k]['fractions'][1]),abs(fa-patches[k]['fractions'][1])+abs(fb-patches[k]['fractions'][0])))
    c=np.array(patches[k]['center']);n=np.array(patches[k]['normal'])
    for face,fc in [(a,fa),(b,fb)]:
     side=1 if abs(fc-patches[k]['fractions'][0])<abs(fc-patches[k]['fractions'][1])else-1
     for j in faces[face]:
      depth=side*((target[j]-c)@n)
      if depth>0:target[j]-=side*n*depth
  print('CONTACT_BOUNDARY',boundary_steps,[(a,b,float(f[list(faces[a])].mean()),float(f[list(faces[b])].mean()))for a,b in bad],flush=True)
 else:
  adj=[set()for v in ob.data.vertices]
  for edge in ob.data.edges:
   a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
  unseen=set(range(len(adj)))
  while unseen:
   stack=[unseen.pop()];ids=[]
   while stack:
    j=stack.pop();ids.append(j)
    for k in adj[j]:
     if k in unseen:unseen.remove(k);stack.append(k)
   if not all(owned[ids]):continue
   center=posed[ids].mean(axis=0);fraction=float(f[ids].mean());q,info=deform(center,fraction)
   if info is None:
    for k,patch in enumerate(patches):
     c=np.array(patch['center']);t=np.array(patch['tangent']);a,b=patch['fractions'];side=1 if abs(fraction-a)<abs(fraction-b)else-1;fc=a if side==1 else b
     if abs(fraction-fc)<(.065 if side==1 else .04) and abs((center-c)@t)<.10:
      info={'patch':k,'side':side,'weight':.5,'compressed':False};q=center.copy();break
   if info is None:continue
   k=info['patch'];side=info['side'];w=info['weight'];c=np.array(patches[k]['center']);n=np.array(patches[k]['normal']);local=posed[ids]-center
   # Preserve positive cup depth; flatten the bowl along contact normal, then seat it behind the plane.
   scale=1-.65*w;newlocal=local-np.outer(local@n,n)*(1-scale);newpts=q+newlocal;excess=max(0,float((side*((newpts-c)@n)).max())+.00015)
   newpts-=side*n*excess;target[ids]=newpts
   for j in ids:infos[j]=info
 ob.shape_key_add(name='Basis');key=ob.shape_key_add(name='CoilContact_R_IV');key.value=0
 errors=[];changed=0
 for i in np.where(np.linalg.norm(target-posed,axis=1)>1e-8)[0]:
  mat=sum((g.weight*bonemats[names[g.group]]for g in ob.data.vertices[i].groups),np.zeros((4,4)));delta=np.linalg.solve(mat[:3,:3],target[i]-posed[i]);key.data[i].co=Vector(rest[i]+delta);errors.append(float(np.linalg.norm(mat[:3,:3]@delta-(target[i]-posed[i]))));changed+=1
 evidence.append({'object':ob.name,'changed_vertices':changed,'max_posed_displacement':float(np.linalg.norm(target-posed,axis=1).max()),'inverse_skin_error':max(errors,default=0),'flat_contact_vertices':sum(bool(x and x['compressed'])for x in infos)})
 targetsets[ob.name]=target;assignments[ob.name]=infos
 key.value=1
bpy.context.view_layer.update()
# Explicit shape actions share track names with the retained bone actions.
for ob in [skin,cups]:
 keys=ob.data.shape_keys;keys.animation_data_create()
 for clip,duration in [('TightRoll',10),('ProbeTouch',16),('AlternatingTouch',16)]:
  action=bpy.data.actions.new(clip+'_'+ob.name+'_Contact');keys.animation_data.action=action
  for frame in range(duration*30+1):
   t=frame/30
   if clip!='TightRoll':v=0.
   elif t<=.4:v=1.
   elif t<1:v=1-float(ease((t-.4)/.6))
   elif t<8:v=0.
   elif t<8.6:v=float(ease((t-8)/.6))
   else:v=1.
   keys.key_blocks['CoilContact_R_IV'].value=v;keys.key_blocks['CoilContact_R_IV'].keyframe_insert('value',frame=frame+1)
  tr=keys.animation_data.nla_tracks.new();tr.name=clip;st=tr.strips.new(clip,1,action);st.action_frame_end=duration*30+1;tr.mute=True
 keys.animation_data.action=None;keys.key_blocks['CoilContact_R_IV'].value=0
rig.animation_data.action=None
bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=481
bpy.ops.object.select_all(action='DESELECT')
for ob in coll.objects:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'octopus-actions.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(O/'octopus-actions.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_merge_animation='NLA_TRACK',export_force_sampling=True,export_frame_range=False,export_anim_slide_to_zero=True)
d={'kind':'octopus_contact_corrective_trial','source_sha256':hashlib.sha256((O/'octopus-actions.blend').read_bytes()).hexdigest(),'model_sha256':hashlib.sha256((O/'octopus-actions.glb').read_bytes()).hexdigest(),'triangles':sum(len(p.vertices)-2 for ob in coll.objects if ob.type=='MESH'for p in ob.data.polygons),'bones':len(rig.data.bones),'patches':patches,'correctives':evidence,'limits':['Single R_IV full-curl corrective only','Authored compression/relaxation, not dynamic soft body or suction']};oldconfig=json.loads((R/'motion-r5/build.validation.json').read_text());d.update({k:oldconfig[k]for k in ['contact_targets','floor_z','clips']});(O/'build.validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(evidence))
# Preserve intended posed target / patch ownership for an independent source-vs-import check.
np.savez_compressed(O/'contact-targets.npz',skin=targetsets[skin.name],cups=targetsets[cups.name])
(O/'contact-ownership.json').write_text(json.dumps(assignments,separators=(',',':')))
