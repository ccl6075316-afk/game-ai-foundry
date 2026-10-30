"""Author editable per-loop normals from a frozen GLB without changing geometry, UV or skin.
Repaired meshes may weld GLB UV-split vertices; their default smooth normals are
not the GLB's area-weighted row normals. Match complete triangles semantically.
"""
import bpy,hashlib,json,sys
from pathlib import Path
from itertools import permutations
sys.path.insert(0,str(Path(__file__).resolve().parent))
from patch_existing_fin_meshes import read
from repair_fin_clearance import values

EXACT_NORMAL_ATTRIBUTE='_FOUNDRY_NORMAL_GLTF'
def geometry_signature(ob):
 assert all(m.type=='ARMATURE'for m in ob.modifiers),ob.name+' unsupported modifier invalidates authored normals'
 matrix=lambda m:[list(row)for row in m]
 modifiers=[]
 for m in ob.modifiers:
  assert m.object and m.object.type=='ARMATURE',ob.name+' missing rest binding'
  rig=m.object
  modifiers.append({'type':m.type,'object':rig.name,'matrix_world':matrix(rig.matrix_world),'settings':{k:getattr(m,k,None)for k in ['show_viewport','show_render','vertex_group','use_vertex_groups','use_bone_envelopes','use_deform_preserve_volume','use_multi_modifier']},'rest_bones':[{'name':bone.name,'parent':bone.parent.name if bone.parent else None,'matrix_local':matrix(bone.matrix_local),'use_deform':bone.use_deform}for bone in rig.data.bones]})
 data={'guard_version':2,'matrix_basis':matrix(ob.matrix_basis),'matrix_world':matrix(ob.matrix_world),'matrix_parent_inverse':matrix(ob.matrix_parent_inverse),'parent':ob.parent.name if ob.parent else None,'armature_bindings':modifiers,'positions':[tuple(v.co)for v in ob.data.vertices],'triangles':[tuple(p.vertices)for p in ob.data.polygons],'uv':[tuple(p.uv)for p in ob.data.uv_layers.active.data],'skin':[[[ob.vertex_groups[g.group].name,g.weight]for g in v.groups]for v in ob.data.vertices],'materials':[m.name for m in ob.data.materials]}
 return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def normal_attribute_signature(ob):
 return hashlib.sha256(json.dumps([tuple(v.vector)for v in ob.data.attributes[EXACT_NORMAL_ATTRIBUTE].data],separators=(',',':')).encode()).hexdigest()
def apply_frozen_normals(model,targets):
 d,b=read(model);report={}
 def error(x,y):
  if set(x[2])!=set(y[2]):return float('inf')
  return max([abs(u-v)for u,v in zip(x[0]+x[1],y[0]+y[1])]+[abs(x[2][k]-y[2][k])for k in x[2]])
 for name in targets:
  ob=bpy.data.objects[name];mesh=ob.data;node=next(n for n in d['nodes']if n.get('name')==name and'mesh'in n);jn=[d['nodes'][j]['name']for j in d['skins'][node['skin']]['joints']];tri=[]
  for pr in d['meshes'][node['mesh']]['primitives']:
   at={k:values(d,b,v)for k,v in pr['attributes'].items()};ids=[q[0]for q in values(d,b,pr['indices'])]
   for k in range(0,len(ids),3):
    rows=[]
    for i in ids[k:k+3]:
     p=at['POSITION'][i];uv=at['TEXCOORD_0'][i];n=at['NORMAL'][i];rows.append(((p[0],-p[2],p[1]),(uv[0],1-uv[1]),{jn[j]:w for j,w in zip(at['JOINTS_0'][i],at['WEIGHTS_0'][i])if w>1e-7},(n[0],-n[2],n[1])))
    tri.append(rows)
  assert len(tri)==len(mesh.polygons),(name,'triangle inventory');normals=[None]*len(mesh.loops);maxerr=0.
  for face in mesh.polygons:
   source=[]
   for li in face.loop_indices:
    v=mesh.vertices[mesh.loops[li].vertex_index];source.append((tuple(v.co),tuple(mesh.uv_layers.active.data[li].uv),{ob.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-7}))
   match=None
   for i,row in enumerate(tri):
    for order in permutations(row):
     err=max(error(x,y)for x,y in zip(source,order))
     if err<=1e-6:match=(i,order,err);break
    if match:break
   assert match,(name,face.index,'source triangle POSITION/UV/skin mismatch');i,order,err=match;tri.pop(i);maxerr=max(maxerr,err)
   for li,row in zip(face.loop_indices,order):normals[li]=row[3]
  assert not tri and all(n is not None for n in normals)
  mesh.normals_split_custom_set(normals);mesh.update()
  # Blender's INT16_2D viewport codec snaps some near-axis components. Keep exact
  # static export normals as authored float corner data, independently guarded.
  attr=mesh.attributes.get(EXACT_NORMAL_ATTRIBUTE)or mesh.attributes.new(EXACT_NORMAL_ATTRIBUTE,'FLOAT_VECTOR','CORNER')
  assert attr.data_type=='FLOAT_VECTOR'and attr.domain=='CORNER'
  for i,n in enumerate(normals):attr.data[i].vector=(n[0],n[2],-n[1])
  mesh['foundry_normal_geometry_sha256']=geometry_signature(ob);mesh['foundry_exact_normal_sha256']=normal_attribute_signature(ob);mesh['foundry_normal_provenance_sha256']=hashlib.sha256(Path(model).read_bytes()).hexdigest()
  report[name]={'custom_loop_normals':len(normals),'geometry_UV_skin_matching_max_error':maxerr}
 return report

def main():
 import argparse,shutil
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--blend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--targets',nargs='+',required=True);p.add_argument('--backup',type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();modelhash=sha(a.model);oldhash=sha(a.blend)
 if a.output.resolve()==a.blend.resolve():assert a.backup and not a.backup.exists(),'In-place source edit requires a new explicit backup';a.backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.blend,a.backup);assert sha(a.backup)==oldhash
 else:assert not a.output.exists(),'Refuse overwrite'
 bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));records=apply_frozen_normals(a.model,a.targets);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(a.output.resolve()));assert sha(a.model)==modelhash;r={'ok':True,'model_sha256':modelhash,'source_before_sha256':oldhash,'source_after_sha256':sha(a.output),'targets':records,'source_geometry_UV_skin_unchanged_by_operation':True,'exact_float_corner_attribute':EXACT_NORMAL_ATTRIBUTE,'export_procedure':'export_source_with_frozen_normals.py verifies mesh and normal hashes, exports authored float corner data and binds only NORMAL to that exported data; ordinary Blender File Export may retain viewport codec error.','backup':str(a.backup)if a.backup else None,'scope':'Only editable source per-loop custom normals authored from frozen model. Fresh actual source re-export parity required.'};a.report.write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':main()
