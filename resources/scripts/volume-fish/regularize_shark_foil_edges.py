"""Resolve a measured folded sliver by a local diagonal, without moving tissue."""
import bpy,bmesh,sys,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));author=json.loads((src/'fin-authoring.json').read_text());failed=json.loads((src/'thickness.validation.json').read_text());records=[]
for result in failed['records']:
 if not result['missing_rays']:continue
 ob=bpy.data.objects[result['name']];root=set(next(r for r in author['fins']if r['name']==ob.name)['root_ids']);mesh=ob.data;original=[v.co.copy()for v in mesh.vertices]
 def score(bm):
  bm.verts.ensure_lookup_table();bm.verts.index_update();bm.normal_update();tree=BVHTree.FromBMesh(bm);uv=bm.loops.layers.uv.active;bad=0
  for f in bm.faces:
   if all(v.index in root for v in f.verts):continue
   a,b,c=[loop[uv].uv for loop in f.loops]
   if abs((b-a).cross(c-a))<1e-10:continue
   pts=[v.co for v in f.verts]
   for weights in[(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
    p=sum((v*w for v,w in zip(pts,weights)),Vector());hit,_,_,_=tree.ray_cast(p-f.normal*1e-7,-f.normal)
    if hit is None:bad+=1
  return bad
 for missing in result['missing_faces']:
  pts=[Vector((q[0],-q[2],q[1]))for q in missing['positions']];ids=[min(mesh.vertices,key=lambda v:(v.co-p).length).index for p in pts];attempts=[];chosen=None
  for a,b in zip(ids,ids[1:]+ids[:1]):
   if a in root and b in root:continue
   bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();edge=next(e for e in bm.verts[a].link_edges if bm.verts[b]in e.verts);done=bmesh.ops.rotate_edges(bm,edges=[edge],use_ccw=True)
   if not done['edges']:bm.free();continue
   before=bmesh.new();before.from_mesh(mesh);previous=score(before);before.free();count=score(bm);attempts.append(dict(edge=[a,b],missing_rays=count))
   if count<previous:chosen=bm;break
   bm.free()
  assert chosen is not None,(ob.name,attempts);chosen.to_mesh(mesh);chosen.free();records.append(dict(fin=ob.name,measured_missing_face=ids,attempts=attempts))
 assert all((v.co-p).length==0 for v,p in zip(mesh.vertices,original));bm=bmesh.new();bm.from_mesh(mesh);assert all(len(e.link_faces)==2 for e in bm.edges);assert score(bm)==0;bm.free()
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in['MESH','ARMATURE']:ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());(out/'diagonal-authoring.json').write_text(json.dumps(dict(records=records,positions_and_root_domain_unchanged=True,formal_acceptance=False),indent=2)+'\n');print('REGULARIZED',records)
