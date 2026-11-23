import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'motion-r3/rest'
# Preserve the pre-refinement rest source once, then refine from it deterministically.
base=O/'unrefined-rest.blend'
if not base.exists():base.write_bytes((O/'octopus-gray.blend').read_bytes())
bpy.ops.wm.open_mainfile(filepath=str(base));ob=bpy.data.objects['Octopus_gray_skin'];build=json.loads((O/'gray-build.validation.json').read_text());paths=build['control_paths'];roots=[Vector(p[0])for p in paths];dirs=[(Vector(p[-1])-Vector(p[0])).normalized()for p in paths];Ls=[(Vector(p[-1])-Vector(p[0])).length for p in paths]
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update();vs=[v.co.copy()for v in bm.verts];fs=[tuple(v.index for v in f.verts)for f in bm.faces];bm.free();assert len(fs)==26000,len(fs)
def loc(p):
 return min(((p-roots[i]-((p-roots[i]).dot(dirs[i]))*dirs[i]).length,i,(p-roots[i]).dot(dirs[i]))for i in range(8))[1:]
def edge(a,b):return (min(a,b),max(a,b))
counts=[]
for it in range(2):
 info=[loc(v)for v in vs];eligible=[]
 for a,b in set(edge(f[j],f[(j+1)%3])for f in fs for j in range(3)):
  i,s=info[a];j,t=info[b]
  if i==j and min(s,t)>.90*Ls[i] and abs(s-t)>.030:eligible.append((abs(s-t)/max(.025,(1-(s+t)*.5/Ls[i])*.6+.025),(a,b)))
 eligible.sort(reverse=True);selected=[e for _,e in eligible[:max(0,(29920-len(fs))//2)]];mids={}
 for a,b in selected:mids[(a,b)]=len(vs);vs.append((vs[a]+vs[b])*.5)
 out=[]
 for f in fs:
  a,b,c=f;ab=mids.get(edge(a,b));bc=mids.get(edge(b,c));ca=mids.get(edge(c,a));n=sum(m is not None for m in [ab,bc,ca])
  if n==0:out.append(f)
  elif n==3:out.extend([(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)])
  elif n==1:
   if bc is not None:a,b,c=b,c,a;ab=bc
   elif ca is not None:a,b,c=c,a,b;ab=ca
   out.extend([(a,ab,c),(ab,b,c)])
  else:
   if ab is None:a,b,c=b,c,a;ab,bc=bc,ca
   elif bc is None:a,b,c=c,a,b;ab,bc=ca,ab
   out.append((ab,b,bc))
   if (vs[a]-vs[bc]).length<(vs[ab]-vs[c]).length:out.extend([(a,ab,bc),(a,bc,c)])
   else:out.extend([(a,ab,c),(ab,bc,c)])
 fs=out;counts.append({'iteration':it,'split_edges':len(selected),'skin_triangles':len(fs)})
mesh=bpy.data.meshes.new('Tight_coil_skin');mesh.from_pydata(vs,[],fs);mesh.update();old=ob.data
for m in old.materials:mesh.materials.append(m)
ob.data=mesh;bpy.data.meshes.remove(old)
for p in mesh.polygons:p.use_smooth=True
bm=bmesh.new();bm.from_mesh(mesh);print('TRIANGLES',len(fs),'MIN',min(f.calc_area()for f in bm.faces),'CLOSED',all(e.is_manifold for e in bm.edges));assert all(e.is_manifold for e in bm.edges);assert min(f.calc_area()for f in bm.faces)>1e-12;bm.free()
build['parts'][ob.name]=len(fs);build['distal_refinement']=counts;build['refinement_method']='Conforming triangle midpoint split; one/two/three-edge cases explicitly triangulated without collinear ngon fans';(O/'gray-build.validation.json').write_text(json.dumps(build,indent=2)+'\n')
bpy.ops.object.select_all(action='DESELECT')
for x in bpy.data.collections['GRAY_REVIEW'].objects:x.select_set(True)
bpy.context.view_layer.objects.active=ob;bpy.ops.wm.save_as_mainfile(filepath=str(O/'octopus-gray.blend'),compress=True);bpy.ops.export_scene.gltf(filepath=str(O/'octopus-gray.glb'),export_format='GLB',use_selection=True,export_animations=False)
