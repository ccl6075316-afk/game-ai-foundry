"""Finite exterior transition clearance; full original roots stay frozen."""
import bpy,bmesh,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));author=json.loads((src/'fin-authoring.json').read_text());body=bpy.data.objects['Closed_body'];body.data.calc_loop_triangles();bv=[v.co for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);ray=Vector((.231,.371,.899)).normalized();records=[]
for row in author['fins']:
 ob=bpy.data.objects[row['name']];root=set(row['root_ids']);moved=[]
 for v in ob.data.vertices:
  if len(args)>2 and row['name']not in args[2:]:continue
  if v.index in root:continue
  clearance=.0008
  h,n,fi,dist=tree.find_nearest(v.co);rh,rn,_,_=tree.ray_cast(v.co,ray);inside=rh is not None and rn.dot(ray)>0
  if not inside and dist>=clearance:continue
  before=v.co.copy();v.co=h+n*clearance;moved.append(dict(vertex=v.index,old=list(before),new=list(v.co),displacement_native=(v.co-before).length))
  # Proximal transition follows the same body support, while free foil keeps
  # the original fin-bone animation. This cannot be used to exempt free tissue.
  ids=bt[fi];beta=barycentric_transform(h,*[bv[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
  for i,b in zip(ids,beta):
   for g in body.data.vertices[i].groups:
    k=body.vertex_groups[g.group].name;mix[k]=mix.get(k,0)+g.weight*max(0,b)
  for g in ob.vertex_groups:g.remove([v.index])
  for k,w in mix.items():
   if w>1e-7:(ob.vertex_groups.get(k)or ob.vertex_groups.new(name=k)).add([v.index],w,'REPLACE')
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();records.append(dict(name=ob.name,moved=moved,complete_root_ids_unchanged=True))
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in['MESH','ARMATURE']:ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());(out/'clearance-authoring.json').write_text(json.dumps(dict(records=records,scope='Author candidate only; full frozen root domain and collision limits unchanged; new current gates and actual contour review required.'),indent=2)+'\n');print('CLEARANCE',[(r['name'],len(r['moved']))for r in records])
