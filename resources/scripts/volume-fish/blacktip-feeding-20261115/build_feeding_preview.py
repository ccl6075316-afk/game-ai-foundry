"""Repair the rejected shallow oral pouch, preserving exterior topology/UV.
Species-local prototype; dimensions/controls are artistic, not anatomical measurements.
"""
import bpy,json,hashlib,math
import numpy as np
from pathlib import Path
from mathutils import Vector
import argparse,sys
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
source=Path(args.source).resolve();out=Path(args.output).resolve();assert source.is_file();assert out!=source.parent;out.mkdir(parents=True,exist_ok=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()=='ff0e051e34498f4d7a95ccaf1b195bf8d29fd68aee3cfbb0ab3f3ee0f5205b82','Species-local source identity required; never apply these vertex IDs to another fish.'
bpy.ops.wm.open_mainfile(filepath=str(source))
ob=bpy.data.objects['Closed_body'];rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');old=ob.data
lower=[617,618,619,746,620,833,834,621,835,836,622,749,623,624,625]
upper=[617,630,631,752,632,837,838,633,839,840,634,753,635,636,625]
loop=lower+list(reversed(upper[1:-1]));assert len(loop)==28
before_fin={o.name:([list(v.co)for v in o.data.vertices],[[ (o.vertex_groups[g.group].name,g.weight)for g in v.groups]for v in o.data.vertices])for o in bpy.data.objects if o.type=='MESH' and o!=ob}
oldpts=[v.co.copy()for v in old.vertices];oldweights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-8}for v in old.vertices]
keep=[p for p in old.polygons if p.material_index!=1]
used=sorted(set(i for p in keep for i in p.vertices));mapping={i:k for k,i in enumerate(used)}
verts=[oldpts[i].copy()for i in used];weights=[oldweights[i].copy()for i in used];faces=[];mats=[];uvs=[];smooth=[]
for p in keep:
 faces.append([mapping[i]for i in p.vertices]);mats.append(p.material_index);uvs.append([tuple(old.uv_layers.active.data[j].uv)for j in p.loop_indices]);smooth.append(p.use_smooth)
def vertex(co,w):
 i=len(verts);verts.append(Vector(co));weights.append(w);return i
def face(ids,mat=1):
 faces.append(ids);mats.append(mat);uvs.append([(0.,0.)]*len(ids));smooth.append(True)
# Build a posterior ring. Lower floor follows mandible; roof follows upper jaw.
# A longitudinal recess replaces the rejected nearly vertical entrance wall.
ring=[]
for i in loop:
 p=oldpts[i];is_lower=i in lower[1:-1];corner=i in [617,625]
 x=.370+.40*(p.x-.389);y=p.y*.76
 floor_gain=max(0.,1-(abs(p.y)/.04644)**2)
 z=p.z+(.004+.006*floor_gain if is_lower else .011)
 if corner:z=p.z+.007
 w={'oral_floor':floor_gain,'jaw_upper':1-floor_gain}if is_lower else {'jaw_upper':1.}
 if corner:w={'jaw_upper':1.}
 ring.append(vertex((x,y,z),w))
center=vertex((.346,0,-.031),{'oral_floor':.6,'jaw_upper':.4})
# Existing oral boundary uses opposite orientation from exterior skin.
boundary=[mapping[i]for i in loop]
directed=set((a,b)for p in faces for a,b in zip(p,p[1:]+p[:1]))
for k in range(len(loop)):
 j=(k+1)%len(loop);a,b=boundary[k],boundary[j];c,d=ring[k],ring[j]
 fs=[[a,b,c],[b,d,c],[c,d,center]]
 if (a,b)in directed:fs=[list(reversed(f))for f in fs]
 for f in fs:face(f)
# Modest tooth cues, sunk into the actual palate/floor; not a complete tooth inventory.
toothmat=bpy.data.materials.new('Ivory oral teeth - geometry prototype');toothmat.use_nodes=True
bs=next(n for n in toothmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.72,.69,.60,1);bs.inputs['Roughness'].default_value=.75
materials=list(old.materials)+[toothmat]
teeth=[]
for ids,bone,sign in [(upper[4:11:2],'jaw_upper',-1),(lower[3:12:2],'jaw_lower',1)]:
 for i in ids:
  p=oldpts[i].copy();p.x-=.006;p.y*=.96;p.z+=(.0015 if sign<0 else .0008)
  # Small closed triangular wedge; bases buried in the lining, tips point into lumen.
  q=[vertex(p+Vector(v),{bone:1.})for v in [(-.0016,-.0018,0),(.0016,.0018,0),(-.002,.0018,0),(-.002,0,sign*.0022)]]
  for f in [[q[0],q[2],q[1]],[q[0],q[1],q[3]],[q[1],q[2],q[3]],[q[2],q[0],q[3]]]:face(f,3)
  teeth.append(q)
mesh=bpy.data.meshes.new('Oral cavity recessed with independent roof and floor');mesh.from_pydata(verts,[],faces);mesh.update()
for m in materials:mesh.materials.append(m)
uv=mesh.uv_layers.new(name=old.uv_layers.active.name)
for p,mi,us,sm in zip(mesh.polygons,mats,uvs,smooth):
 p.material_index=mi;p.use_smooth=sm
 for li,xy in zip(p.loop_indices,us):uv.data[li].uv=xy
# Retain secondary source UVs and custom exterior normals for this topology edit.
for olduv in old.uv_layers:
 if olduv.name==uv.name:continue
 layer=mesh.uv_layers.new(name=olduv.name)
 for newp,oldp in zip(mesh.polygons,keep):
  for nl,ol in zip(newp.loop_indices,oldp.loop_indices):layer.data[nl].uv=olduv.data[ol].uv
mesh.uv_layers.active_index=mesh.uv_layers.find(old.uv_layers.active.name)
normals=[tuple(n.vector)for n in mesh.corner_normals]
for newp,oldp in zip(mesh.polygons,keep):
 for nl,ol in zip(newp.loop_indices,oldp.loop_indices):normals[nl]=tuple(old.corner_normals[ol].vector)
mesh.normals_split_custom_set(normals)
ob.data=mesh
# Head lift independent of the tail-first native body chain; blend only in front of fins.
bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
b=rig.data.edit_bones.new('feeding_head');b.head=(.310,0,-.020);b.tail=(.310,.04,-.020);b.parent=rig.data.edit_bones['body_00']
rig.data.edit_bones['jaw_upper'].parent=b
floor=rig.data.edit_bones.new('oral_floor');floor.head=(.370,0,-.033);floor.tail=(.370,.035,-.033);floor.parent=rig.data.edit_bones['jaw_upper']
bpy.ops.object.mode_set(mode='OBJECT')
for vg in list(ob.vertex_groups):ob.vertex_groups.remove(vg)
groups={name:ob.vertex_groups.new(name=name)for name in [b.name for b in rig.data.bones]}
for i,(p,w)in enumerate(zip(verts,weights)):
 f=max(0.,min(1.,(p.x-.305)/.085));f=f*f*(3-2*f)
 for name in list(w):
  if name not in ['jaw_lower','jaw_upper','feeding_head','oral_floor']:
   amount=w[name]*f;w[name]-=amount;w['feeding_head']=w.get('feeding_head',0)+amount
 # Match the actual four-influence game export explicitly before validation.
 w=dict(sorted(w.items(),key=lambda pair:pair[1],reverse=True)[:4]);mass=sum(w.values());w={n:v/mass for n,v in w.items()}
 for name,v in w.items():
  if v>1e-8:groups[name].add([i],v,'REPLACE')
# Preserve all existing texture images; lighten only untextured lining to reveal depth.
cavity=mesh.materials[1];cavity.name='Recessed oral lining / prototype neutral tissue'
next(n for n in cavity.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.20,.115,.10,1)
next(n for n in cavity.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Roughness'].default_value=1.
for o in bpy.data.objects:
 if o.name in before_fin:
  assert before_fin[o.name]==([list(v.co)for v in o.data.vertices],[[ (o.vertex_groups[g.group].name,g.weight)for g in v.groups]for v in o.data.vertices])
tri=sum(len(p.vertices)-2 for o in bpy.data.objects if o.type=='MESH'for p in o.data.polygons);assert tri<=4000,tri
for oldi,newi in mapping.items():assert oldpts[oldi]==mesh.vertices[newi].co
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'source_input':str(source),'input_sha256':sha(source),'model_sha256':sha(out/'fish.glb'),'source_sha256':sha(out/'fish.blend'),'triangles':tri,'bones':len(rig.data.bones),'exterior_positions_and_uv_preserved':True,'all_fin_positions_named_weights_preserved':True,'removed_oral_triangles':88,'new_cavity_triangles':84,'tooth_count':len(teeth),'old_to_new_vertex':mapping,'upper_rim':[mapping[i]for i in upper],'lower_rim':[mapping[i]for i in lower],'cavity_ring':ring,'cavity_center':center,'teeth_vertices':teeth,'scope':'Actual recessed roof/floor/sides; added local feeding head bone. No exterior reshaping, no image rebake. Prototype lining/teeth and artistic motion, not calibrated anatomy.'}
(out/'authoring.validation.json').write_text(json.dumps(report,indent=2));print('ORAL_REBUILT',tri,len(rig.data.bones),len(teeth),flush=True)
