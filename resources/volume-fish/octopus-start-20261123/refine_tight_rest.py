import bpy,bmesh,json
from mathutils import Vector
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'motion-r3/rest';bpy.ops.wm.open_mainfile(filepath=str(O/'octopus-gray.blend'));build=json.loads((O/'gray-build.validation.json').read_text());paths=build['control_paths'];roots=[Vector(p[0])for p in paths];dirs=[(Vector(p[-1])-Vector(p[0])).normalized()for p in paths];Ls=[(Vector(p[-1])-Vector(p[0])).length for p in paths];ob=bpy.data.objects['Octopus_gray_skin'];bm=bmesh.new();bm.from_mesh(ob.data)
def loc(p):
 candidates=[]
 for i in range(8):
  s=(p-roots[i]).dot(dirs[i]);delta=p-roots[i]-s*dirs[i];candidates.append((delta.length,i,s))
 _,i,s=min(candidates);return i,s
counts=[]
for iteration in range(2):
 info={v:loc(v.co)for v in bm.verts};edges=[]
 for e in bm.edges:
  a,b=e.verts;i,s=info[a];j,t=info[b]
  if i==j and min(s,t)>.90*Ls[i] and abs(s-t)>.030:edges.append(e)
 if not edges:break
 def priority(e):
  i,s=info[e.verts[0]];_,t=info[e.verts[1]]
  return abs(s-t)/max(.025,(1-(s+t)*.5/Ls[i])*.6+.025)
 edges.sort(key=priority,reverse=True)
 capacity=(29920-len(bm.faces))//2
 edges=edges[:max(0,capacity)]
 if not edges:break
 bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));counts.append({'iteration':iteration,'split_edges':len(edges),'skin_tris':len(bm.faces)})
 print(counts[-1])
# This refines planar rest faces only; no sculpted geometry or length changes.
tri=len(bm.faces)+sum(len(p.vertices)-2 for x in bpy.data.collections['GRAY_REVIEW'].objects if x.type=='MESH' and x!=ob for p in x.data.polygons)
print('TOTAL',tri);assert tri<=50000,(tri,counts)
bm.to_mesh(ob.data);bm.free();ob.data.update();build['parts'][ob.name]=len(ob.data.polygons);build['distal_refinement']=counts;(O/'gray-build.validation.json').write_text(json.dumps(build,indent=2)+'\n')
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.collections['GRAY_REVIEW'].objects:o.select_set(True)
bpy.context.view_layer.objects.active=ob;bpy.ops.wm.save_as_mainfile(filepath=str(O/'octopus-gray.blend'),compress=True);bpy.ops.export_scene.gltf(filepath=str(O/'octopus-gray.glb'),export_format='GLB',use_selection=True,export_animations=False)
