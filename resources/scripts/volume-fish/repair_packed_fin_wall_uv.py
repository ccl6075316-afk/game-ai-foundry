"""Match closing-wall alpha addresses to their adjacent native fin cap.

An opaque inset tissue UV on a wall spanning transparent cap pixels produces a
floating wire. Reuse the cap's native address at each anatomical source point;
the atlas already owns the bounded tissue-color repair. No geometry is changed.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
p=argparse.ArgumentParser(description=__doc__)
for k in ['anatomical-source','blend','packing','tool-root','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);tool=a.tool_root.resolve();sys.path[:0]=[str(tool/'portable'),str(tool)]
from export_packed_fish_source import geometry_signature,normal_attribute_signature,float_uv_signature,part_signature,material_signature,EXACT_UV,PART_ID
from export_source import export_source
from source_snapshot import rig_action_snapshot
out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists();packing=read(a.packing);aw,ah=packing['atlas']['size'];sources={}
bpy.ops.wm.open_mainfile(filepath=str(a.anatomical_source.resolve()))
for ob in bpy.data.objects:
 if ob.type!='MESH' or 'foundry_fin_source_u'not in ob.data.attributes:continue
 mesh=ob.data;u=[x.value for x in mesh.attributes['foundry_fin_source_u'].data];v=[x.value for x in mesh.attributes['foundry_fin_source_v'].data];q=np.c_[u,v];cap_uv={}
 for face in mesh.polygons:
  coords=q[list(face.vertices)];area=sum(np.cross(coords[i]-coords[0],coords[i+1]-coords[0])for i in range(1,len(coords)-1))
  if abs(area)<1e-10:continue
  for li in face.loop_indices:cap_uv.setdefault(mesh.loops[li].vertex_index,tuple(mesh.uv_layers.active.data[li].uv))
 sources[ob.name]={'positions':[tuple(v.co)for v in mesh.vertices],'q':q,'uv':cap_uv}
assert sources
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));ob=next(o for o in bpy.data.objects if o.type=='MESH');mesh=ob.data;mat=mesh.materials[0]
def geometry_without_uv():return repr(([tuple(v.co)for v in mesh.vertices],[tuple(f.vertices)for f in mesh.polygons],[[tuple((g.group,g.weight))for g in v.groups]for v in mesh.vertices],tuple(ob.matrix_world),tuple(ob.matrix_basis),tuple(ob.matrix_parent_inverse),ob.parent.name,[m.name for m in mesh.materials]))
assert geometry_signature(ob)==mesh['foundry_normal_geometry_sha256']
frozen=[geometry_without_uv(),normal_attribute_signature(ob),part_signature(mesh),rig_action_snapshot(),material_signature(mat)];assert float_uv_signature(mesh)==mesh['foundry_exact_uv_sha256'];old_uv=[tuple(v.vector)for v in mesh.attributes[EXACT_UV].data];part_ids=[int(round(v.value))for v in mesh.attributes[PART_ID].data];parts=json.loads(mesh['foundry_geometry_parts_json']);records=[];changed=set()
for part in parts:
 if part['role']!='fin':continue
 name=part['source_node'];s=sources[name];positions=s['positions'];kd=KDTree(len(positions))
 for i,co in enumerate(positions):kd.insert(Vector(co),i)
 kd.balance();source_ids={}
 for vertex in mesh.vertices:
  if part_ids[vertex.index]!=part['part_id']:continue
  _,source_id,distance=kd.find(vertex.co);assert distance<2e-6,(name,distance);source_ids[vertex.index]=source_id
 tile=next(t for t in packing['parts']if t['node']==name);W,H=tile['source_size'];ox,oy=tile['virtual_crop_origin'];ax,ay=tile['atlas_placement'];walls=0
 for face in mesh.polygons:
  if part_ids[face.vertices[0]]!=part['part_id']:continue
  ids=[source_ids[i]for i in face.vertices];q=s['q'][ids];area=float(np.cross(q[1]-q[0],q[2]-q[0]))
  if abs(area)>1e-10:continue
  walls+=1
  for li,sid in zip(face.loop_indices,ids):
   assert sid in s['uv'],(name,'No adjacent cap UV',sid)
   u,v=s['uv'][sid];new=((u*W-ox+ax)/aw,((1-v)*H-oy+ay)/ah)
   mesh.attributes[EXACT_UV].data[li].vector=new;mesh.uv_layers['UVMap'].data[li].uv=(new[0],1-new[1]);changed.add(li)
 records.append({'name':name,'closing_wall_triangles':walls,'source_mapping_maximum_tolerance_native':2e-6,'cap_UV_exact':True,'wall_color_and_alpha_share_native_cap_address':True})
assert len(records)==7
assert all(tuple(v.vector)==old_uv[i]for i,v in enumerate(mesh.attributes[EXACT_UV].data)if i not in changed)
assert frozen==[geometry_without_uv(),normal_attribute_signature(ob),part_signature(mesh),rig_action_snapshot(),material_signature(mat)]
mesh['foundry_exact_uv_sha256']=float_uv_signature(mesh);mesh['foundry_normal_geometry_sha256']=geometry_signature(ob);out.mkdir(parents=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));proof=export_source(out/'fish.glb')
report={'ok':True,'kind':'native_cap_alpha_matched_fin_wall_uv_repair','input_blend_sha256':sha(a.blend),'anatomical_source_sha256':sha(a.anatomical_source),'packing_sha256':sha(a.packing),'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'geometry_normals_weights_parts_rig_actions_exact':True,'non_wall_UV_exact':True,'atlas_RGBA_exact':True,'changed_wall_loops':len(changed),'fins':records,'export_proof':proof,'scope':'Explicit source-domain zero-area closing walls use adjacent cap source addresses for both RGB and alpha. No alpha erosion, geometry deletion, extra rendering overlay or runtime static repair.'};(out/'wall-uv.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'fins':len(records),'changed_wall_loops':len(changed)}))
