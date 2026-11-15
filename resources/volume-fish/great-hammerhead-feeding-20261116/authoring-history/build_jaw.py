import bpy,json,hashlib,math
import numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('E:/game-ai-foundry');W=R/'work/great-hammerhead-feeding-20261116';O=W/'candidate';O.mkdir(exist_ok=True)
source=R/'projects/fishing-2d/assets/source/fish/great_hammerhead/fish.blend'
inspection=json.loads((W/'baseline-inspection.json').read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==inspection['source_sha256']
bpy.ops.wm.open_mainfile(filepath=str(source));ob=bpy.data.objects['Reference_head_body'];old=ob.data;rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
loop=json.loads((W/'oral-boundary.json').read_text())['boundary'];start=loop.index(733);loop=loop[start:]+loop[:start];split=loop.index(737);lower=set(loop[:split+1]);upper=set(loop)-lower
oldpts=[v.co.copy()for v in old.vertices];oldw=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups}for v in old.vertices]
keep=[p for p in old.polygons if p.material_index!=1];used=sorted(set(i for p in keep for i in p.vertices));mapping={i:k for k,i in enumerate(used)}
vs=[oldpts[i].copy()for i in used];weights=[oldw[i].copy()for i in used];faces=[];mats=[];uvs=[]
for p in keep:faces.append([mapping[i]for i in p.vertices]);mats.append(p.material_index);uvs.append([tuple(old.uv_layers.active.data[j].uv)for j in p.loop_indices])
def s(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def vert(co,w):
 i=len(vs);vs.append(Vector(co));weights.append(w);return i
def face(ids,mi=3):faces.append(ids);mats.append(mi);uvs.append([(0.,0.)]*len(ids))
# Existing lower lip is the posterior side of the ventral mouth arc.
# Bind the skin continuously back into the chin, not an independent lip strip.
rim=np.array([oldpts[i]for i in loop]);lowpts=np.array([oldpts[i]for i in lower])
for oi,ni in mapping.items():
 p=oldpts[oi];w=weights[ni]
 head=s(.60,.94,p.x)
 w={n:v*(1-head)for n,v in w.items()};w['feeding_head']=head
 if oi in loop:
  gain=1.;jaw='jaw_lower' if oi in lower else 'jaw_upper'
 else:
  near=lowpts[np.argmin(np.linalg.norm(lowpts[:,:2]-np.array(p)[:2],axis=1))]
  behind=1-s(float(near[0])-.001,float(near[0])+.010,p.x)
  below=1-s(float(near[2])-.003,float(near[2])+.020,p.z)
  gain=s(.92,1.075,p.x)*(1-s(.094,.15,abs(p.y)))*behind*below
  jaw='jaw_lower'
  # Upper lip skin band receives a very local palatoquadrate displacement.
  if gain<.01:
   dist=float(np.min(np.linalg.norm(rim-np.array(p),axis=1)))
   gain=(1-s(.005,.045,dist))*(1-s(.094,.13,abs(p.y)))*(1-s(-.255,-.21,p.z))
   jaw='jaw_upper'
 gain=max(0.,min(head,gain))
 for n in list(w):w[n]*=(1-gain)
 w[jaw]=gain
 weights[ni]={n:v for n,v in w.items()if v>1e-8}
# Preserve the source's proven corner triangulation and its paired interior arc.
# The failed radial rings crossed the extremely narrow paired corner edges.
# Move the original 34 interior points posterior/up as a continuous field instead.
oral_polys=[p for p in old.polygons if p.material_index==1]
interior=sorted(set(i for p in oral_polys for i in p.vertices)-set(used))
ring=[];bound=[mapping[i]for i in loop]
for i in interior:
 p=oldpts[i];g=1-s(.078,.0936,abs(p.y));lo=i>=69
 w={'oral_floor':g,'jaw_lower':1-g}if lo else {'jaw_upper':1.}
 q=(p.x-.125*g,p.y*(1-.25*g),p.z+.025*g)
 mapping[i]=vert(q,w);ring.append(mapping[i])
for p in oral_polys:face([mapping[i]for i in p.vertices])
center=None
def material(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.85;return m
materials=list(old.materials)+[material('Recessed oral lining',(.20,.12,.105)),material('Small triangular tooth cues',(.72,.71,.63))]
teeth=[]
for ids,bone,sign in [(upper,'jaw_upper',-1),(lower,'jaw_lower',1)]:
 for y in [-.060,-.040,-.020,0,.020,.040,.060]:
  i=min(ids,key=lambda i:abs(oldpts[i].y-y));p=oldpts[i].copy();p.x-=.007;p.z+=(.002 if sign<0 else 0)
  q=[vert(p+Vector(x),{bone:1.})for x in [(-.004,-.004,0),(.002,.004,0),(-.004,.004,0),(-.002,0,sign*.003*(1-.6*(abs(y)/.06)**2))]]
  for f in [[q[0],q[2],q[1]],[q[0],q[1],q[3]],[q[1],q[2],q[3]],[q[2],q[0],q[3]]]:face(f,4)
  teeth.append(q)
# Continuous deformation of the whole jaw region, not an enlarged lip strip.
# Full 1.7x transverse scale over both rims; smoothly returns to identity before
# the hammer wing/eyes, head dorsum, posterior neck or any fin support surface.
def widen(p):
 x,y,z=p
 g=s(.80,1.02,x)*(1-s(1.24,1.43,x))*(1-s(-.23,-.145,z))
 lateral=1-s(.10,.34,abs(y))
 return Vector((x,y*(1+.7*g*lateral),z))
before=[p.copy() for p in vs];vs=[widen(p)for p in vs]
changed=[i for i,(a,b)in enumerate(zip(before,vs))if (a-b).length>1e-8]
assert all(before[i].x>.8 and before[i].z<-.145 and abs(before[i].y)<.34 for i in changed)
m=bpy.data.meshes.new('Continuous articulated oral body');m.from_pydata(vs,[],faces);m.update()
for x in materials:m.materials.append(x)
uv=m.uv_layers.new(name=old.uv_layers.active.name)
for p,mi,us in zip(m.polygons,mats,uvs):
 p.material_index=mi;p.use_smooth=True
 for li,xy in zip(p.loop_indices,us):uv.data[li].uv=xy
for layer in old.uv_layers:
 if layer.name==uv.name:continue
 nu=m.uv_layers.new(name=layer.name)
 for npoly,opoly in zip(m.polygons,keep):
  for nl,ol in zip(npoly.loop_indices,opoly.loop_indices):nu.data[nl].uv=layer.data[ol].uv
m.uv_layers.active_index=m.uv_layers.find(old.uv_layers.active.name)
norms=[tuple(n.vector)for n in m.corner_normals]
for npoly,opoly in zip(m.polygons,keep):
 for nl,ol in zip(npoly.loop_indices,opoly.loop_indices):
  # Transform original custom normal by the exact local map's finite Jacobian.
  q=before[m.loops[nl].vertex_index];eps=1e-5
  jac=np.column_stack([np.array(widen(q+Vector(tuple(eps if j==k else 0 for j in range(3))))-widen(q-Vector(tuple(eps if j==k else 0 for j in range(3)))))/(2*eps)for k in range(3)])
  n=np.linalg.solve(jac.T,np.array(old.corner_normals[ol].vector));n/=np.linalg.norm(n);norms[nl]=tuple(n)
m.normals_split_custom_set(norms);ob.data=m
# Low-frequency lining color follows the actual cavity depth, leaving skin pixels intact.
col=m.color_attributes.new(name='OralDepth',type='FLOAT_COLOR',domain='CORNER')
inner=set(ring)
for poly in m.polygons:
 for li in poly.loop_indices:
  col.data[li].color=(.045,.025,.023,1)if poly.material_index==3 and m.loops[li].vertex_index in inner else ((.19,.105,.085,1)if poly.material_index==3 else (1,1,1,1))
node=materials[3].node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='OralDepth'
bs=next(n for n in materials[3].node_tree.nodes if n.type=='BSDF_PRINCIPLED');materials[3].node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for name,co,parent in [('feeding_head',(.70,0,-.18),'body_00'),('jaw_upper',(1.06,0,-.20),'feeding_head'),('jaw_lower',(1.06,0,-.20),'jaw_upper'),('oral_floor',(.99,0,-.265),'jaw_upper')]:
 b=rig.data.edit_bones.new(name);b.head=co;b.tail=Vector(co)+Vector((0,.08,0));b.parent=rig.data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
for vg in list(ob.vertex_groups):ob.vertex_groups.remove(vg)
groups={b.name:ob.vertex_groups.new(name=b.name)for b in rig.data.bones}
for i,w in enumerate(weights):
 w=dict(sorted(w.items(),key=lambda p:p[1],reverse=True)[:4]);total=sum(w.values())
 for name,value in w.items():
  if value>1e-8:groups[name].add([i],value/total,'REPLACE')
# Existing eye components follow the same rigid head as their supporting skin.
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.startswith('Eye_'):
  for vg in list(o.vertex_groups):o.vertex_groups.remove(vg)
  o.vertex_groups.new(name='feeding_head').add(list(range(len(o.data.vertices))),1.,'REPLACE')
for oi in used:assert widen(oldpts[oi])==m.vertices[mapping[oi]].co
tri=sum(len(p.vertices)-2 for o in bpy.data.objects if o.type=='MESH'for p in o.data.polygons);assert tri<=6000
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'fish.blend'))
bpy.ops.export_scene.gltf(filepath=str(O/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
ref=lambda p:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
report={'status':'candidate_not_accepted','input':ref(source),'source':ref(O/'fish.blend'),'model':ref(O/'fish.glb'),'triangles':tri,'bones':len(rig.data.bones),'outer_positions_and_uv_preserved':False,'uv_preserved':True,'oral_width_scale':1.7,'mouth_width_native':max(vs[i].y for i in bound)-min(vs[i].y for i in bound),'changed_vertices':changed,'protected_outside_local_jaw_map':True,'mouth_boundary':bound,'lower_rim':[mapping[i]for i in lower],'upper_rim':[mapping[i]for i in upper],'old_to_new_vertex':mapping,'cavity_ring':ring,'cavity_center':center,'teeth_vertices':teeth,'notes':'14 simplified tooth cues, not an anatomical tooth count. Local continuous whole-jaw transverse deformation. New4-bone oral controller; dimensions artistic. Existing eye mesh position unchanged, bound to head. Full validation pending.'}
(O/'authoring.validation.json').write_text(json.dumps(report,indent=2));print('BUILT',tri,len(rig.data.bones))
