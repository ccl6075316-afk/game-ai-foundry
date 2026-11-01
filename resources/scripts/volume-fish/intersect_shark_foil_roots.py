"""Close loft bases on the actual body intersection, keeping free foil tissue.

Author-time exact Boolean; no runtime geometry. Full resulting basal surface
must be checked, together with every original basal point that survives.
"""
import bpy,bmesh,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists() and '/experiments/'in out.as_posix();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));author=json.loads((src/'fin-authoring.json').read_text());body=bpy.data.objects['Closed_body'];rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.view_layer.update();body.data.calc_loop_triangles();bv=[v.co.copy()for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);records=[]
for row in author['fins']:
 ob=bpy.data.objects[row['name']];oldpos=[Vector(p)for p in row['root_points_native']];olduv={v.index:next(ob.data.uv_layers.active.data[li].uv.copy()for f in ob.data.polygons for li in f.loop_indices if ob.data.loops[li].vertex_index==v.index)for v in ob.data.vertices};oldrootuv=[olduv[i]for i in row['root_ids']];mod=ob.modifiers.new('Actual body exterior intersection','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=body;mod.use_self=True;mod.use_hole_tolerant=True;mod.material_mode='TRANSFER';bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name);mesh=ob.data;capfaces=[f for f in mesh.polygons if f.material_index>0];capids={i for f in capfaces for i in f.vertices};roots=[];print('BOOLEAN',ob.name,len(mesh.vertices),'capfaces',len(capfaces),flush=True)
 for v in mesh.vertices:
  h,n,fi,dist=tree.find_nearest(v.co)
  if v.index not in capids and min((v.co-p).length for p in oldpos)>1e-6:continue
  roots.append(v.index);v.co=h+n*.00008;ids=bt[fi];beta=barycentric_transform(h,*[bv[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
  for i,w in zip(ids,beta):
   for g in body.data.vertices[i].groups:
    key=body.vertex_groups[g.group].name;mix[key]=mix.get(key,0)+max(0,w)*g.weight
  for g in ob.vertex_groups:g.remove([v.index])
  for k,w in mix.items():
   if w>1e-7:(ob.vertex_groups.get(k)or ob.vertex_groups.new(name=k)).add([v.index],w,'REPLACE')
 for f in capfaces:
  for li in f.loop_indices:
   p=mesh.vertices[mesh.loops[li].vertex_index].co;i=min(range(len(oldpos)),key=lambda i:(oldpos[i]-p).length);mesh.uv_layers.active.data[li].uv=oldrootuv[i]
 for f in mesh.polygons:f.material_index=0;f.use_smooth=True
 while len(mesh.materials)>1:mesh.materials.pop(index=len(mesh.materials)-1)
 rootpoints=[mesh.vertices[i].co.copy()for i in roots];bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges),(ob.name,'nonmanifold');bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles();roots=[v.index for v in mesh.vertices if min((v.co-p).length for p in rootpoints)<1e-7];records.append(dict(row,root_ids=roots,root_points_native=[list(mesh.vertices[i].co)for i in roots],vertices=len(mesh.vertices),triangles=len(mesh.loop_triangles),root_method='Exact complete fin-solid/body difference; every body intersection cap vertex and surviving original basal vertex; barycentric actual body skin; no source edge subset'))
total=len(body.data.loop_triangles)+sum(r['triangles']for r in records);assert total<=4000,total;rig.data.pose_position='POSE';bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in['MESH','ARMATURE']:ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_text(json.dumps(dict(body_triangles=len(body.data.loop_triangles),whole_triangles=total,fins=records),indent=2)+'\n');print('INTERSECTED',total)
