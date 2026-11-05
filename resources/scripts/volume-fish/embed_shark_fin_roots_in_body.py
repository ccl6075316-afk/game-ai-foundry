"""Give complete ordinary fin caps matching finite vertices on the body.

Interpolated weights alone do not make an interior point follow a finite LBS
triangle: interpolation and weighted transformation do not commute. Subdivide
only touched body triangles by inserting every original cap vertex. Fin free
geometry/UV/pixels and the full original root ID domain remain unchanged. New body
UV and skin use barycentric interpolation of their original source triangle.
Actual current-pose root/membrane, body077 and visual checks remain mandatory.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from finite_triangle_constraints import constrain
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform,delaunay_2d_cdt
from mathutils.kdtree import KDTree
from collections import defaultdict

src,out=map(lambda x:Path(x).resolve(),sys.argv[sys.argv.index('--')+1:])
assert not out.exists() and '/experiments/' in out.as_posix()
out.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'))
body=bpy.data.objects['Reference_head_body'];old=body.data;old.calc_loop_triangles()
verts=[v.co.copy()for v in old.vertices];tri=[tuple(t.vertices)for t in old.loop_triangles]
tree=BVHTree.FromPolygons(verts,tri,all_triangles=True)
weights=[{body.vertex_groups[g.group].name:g.weight for g in v.groups}for v in old.vertices]
auth=json.loads((src/'fin-authoring.json').read_text());roots=[];segments=[];frozen={};edge_faces=defaultdict(set);vertex_faces=defaultdict(set)
for fi,ids in enumerate(tri):
 for i in ids:vertex_faces[i].add(fi)
 for a,b in zip(ids,(*ids[1:],ids[0])):edge_faces[tuple(sorted((a,b)))].add(fi)
face_points=defaultdict(list);canonical=[];snap_max=0.
def canonical_root(p):
 global snap_max
 h,n,fi,d=tree.find_nearest(p);assert d<3e-6,('Root not on original finite body',d)
 ids=tri[fi];near=min(ids,key=lambda i:(verts[i]-h).length)
 if (verts[near]-h).length<2e-6:q=verts[near].copy();owners=vertex_faces[near]
 else:
  candidates=[]
  for a,b in zip(ids,(*ids[1:],ids[0])):
   v=verts[b]-verts[a];t=max(0,min(1,(h-verts[a]).dot(v)/v.length_squared));q=verts[a]+v*t;candidates.append(((q-h).length,a,b,q))
  dist,a,b,q=min(candidates,key=lambda row:row[0])
  if dist<2e-6:owners=edge_faces[tuple(sorted((a,b)))]
  else:q=h.copy();owners={fi}
 for oldq,oldowners in canonical:
  if (oldq-q).length<8e-7:q=oldq;owners=owners|oldowners;oldowners.update(owners);break
 else:canonical.append((q, set(owners)))
 snap_max=max(snap_max,(p-q).length);assert (p-q).length<5e-6
 for face in owners:face_points[face].append(q)
 return q
for row in auth['fins']:
 ob=bpy.data.objects[row['name']];ob.data.calc_loop_triangles();ids=set(row['root_ids'])
 for i in ids:ob.data.vertices[i].co=canonical_root(ob.data.vertices[i].co)
 row['root_points_native']=[list(ob.data.vertices[i].co)for i in row['root_ids']]
 frozen[ob.name]=[(tuple(v.co),)for v in ob.data.vertices]
 for i in ids:roots.append((ob.name,i,ob.data.vertices[i].co.copy()))
 for t in ob.data.loop_triangles:
  if all(i in ids for i in t.vertices):
   for a,b in zip(t.vertices,(*t.vertices[1:],t.vertices[0])):
    segments.append((ob.data.vertices[a].co.copy(),ob.data.vertices[b].co.copy()))
def beta(p,ids):
 return barycentric_transform(p,*[verts[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
def key(p):return tuple(round(x,10)for x in p)
newverts=list(verts);newweights=list(weights);lookup={key(p):i for i,p in enumerate(verts)}
newfaces=[];uvs=[];mats=[];smooth=[];touched=[];maxoff=0.;point_matches={};collapsed=[];source_faces=[];face_debug={}
for fi,ids in enumerate(tri):
 a,b,c=[verts[i]for i in ids];n=(b-a).cross(c-a).normalized();ex=(b-a).normalized();ey=n.cross(ex)
 def inside(p):
  if abs((p-a).dot(n))>2e-6:return False
  q=beta(p,ids);return min(q)>-2e-5 and max(q)<1.00002
 points=[a,b,c];pindex={key(p):i for i,p in enumerate(points)}
 for p in face_points[fi]:
  if key(p)not in pindex:pindex[key(p)]=len(points);points.append(p)
 edges=[(0,1),(1,2),(2,0)];seen={tuple(sorted(e))for e in edges}
 constraints=[]
 for p,q in segments:
  if key(p)in pindex and key(q)in pindex:
   edge=(pindex[key(p)],pindex[key(q)]);ek=tuple(sorted(edge))
   if edge[0]!=edge[1]and ek not in seen:seen.add(ek);constraints.append(edge)
 original=old.polygons[old.loop_triangles[fi].polygon_index]
 rawuv=[[layer.data[li].uv.copy()for li in old.loop_triangles[fi].loops]for layer in old.uv_layers]
 if len(points)==3:
  faces=[ids]
 else:
  touched.append(fi)
  # Incremental finite-face insertion avoids false slivers created when a
  # float32 CDT projects nearly collinear points off an original body edge.
  # Original triangle boundaries and every original cap vertex are retained.
  xy=[]
  A=np.array([[float((b-a).dot(b-a)),float((b-a).dot(c-a))],[float((b-a).dot(c-a)),float((c-a).dot(c-a))]])
  for p in points:
   rhs=np.array([float((p-a).dot(b-a)),float((p-a).dot(c-a))]);v,w=np.linalg.solve(A,rhs);be=np.array([1-v-w,v,w]);be[abs(be)<3e-6]=0;be=np.maximum(be,0);be/=be.sum();xy.append(be[1:])
  v2=xy;orig_v=[[i]for i in range(len(points))];f2=[(0,1,2)]
  def local_beta(p,ids):
   q=np.array([xy[i]for i in ids]);v,w=np.linalg.solve(np.column_stack((q[1]-q[0],q[2]-q[0])),p-q[0]);return np.array([1-v-w,v,w])
  for j in range(3,len(xy)):
   match=None
   for k,face in enumerate(f2):
    be=local_beta(xy[j],face)
    if be.min()>-1e-8:match=(k,face,be);break
   assert match is not None,('Uninserted complete root point',fi,j)
   k,face,be=match;near=np.where(abs(be)<1e-8)[0]
   if len(near)>=2:raise AssertionError(('Duplicate topological point',fi,j,be))
   if len(near)==1:
    edge=tuple(face[i]for i in range(3)if i!=near[0]);split=[]
    for oldface in f2:
     if set(edge).issubset(oldface):
      other=next(i for i in oldface if i not in edge);split.extend([(edge[0],j,other),(j,edge[1],other)])
     else:split.append(oldface)
    f2=split
   else:
    f2.pop(k);f2.extend([(face[0],face[1],j),(face[1],face[2],j),(face[2],face[0],j)])
  f2=constrain(f2,constraints,xy)
  globalids=[]
  for j,p in enumerate(v2):
   co=points[orig_v[j][0]].copy()if orig_v[j]else a+ex*p.x+ey*p.y
   k=key(co)
   if k not in lookup:
    lookup[k]=len(newverts);newverts.append(co);w={};qs=beta(co,ids)
    for i,gain in zip(ids,qs):
     for name,value in weights[i].items():w[name]=w.get(name,0)+max(0,gain)*value
    total=sum(w.values());newweights.append({name:value/total for name,value in w.items()if value>1e-8})
   globalids.append(lookup[k])
  faces=[]
  for face in f2:
   assert len(face)==3
   ix=tuple(globalids[i]for i in face)
   bary=[beta(newverts[i],ids)for i in ix]
   if any(max(abs(row[j])for row in bary)<3e-6 for j in range(3)):
    collapsed.append(dict(original_body_face=fi,collinear_original_boundary=list(ix)))
    continue
   if (newverts[ix[1]]-newverts[ix[0]]).cross(newverts[ix[2]]-newverts[ix[0]]).dot(n)<0:ix=ix[::-1]
   if len(set(ix))<3:
    collapsed.append(dict(original_body_face=fi,identical_vertex_indices=list(ix)))
    continue
   faces.append(ix)
  face_debug[fi]=dict(original_vertices=[list(verts[i])for i in ids],points=[list(p)for p in points],edges=edges,output_faces=[list(f)for f in faces],input_point_min_barycentric=[min(beta(p,ids))for p in points])
 for face in faces:
  newfaces.append(face);source_faces.append(fi);mats.append(original.material_index);smooth.append(original.use_smooth)
  uvs.append([[sum((rawuv[k][j]*float(beta(newverts[i],ids)[j])for j in range(3)),Vector((0,0)))for i in face]for k in range(len(rawuv))])
me=bpy.data.meshes.new('Finite body with complete original fin cap constraints');me.from_pydata(newverts,[],newfaces);me.update()
for material in old.materials:me.materials.append(material)
for p,mat,sm in zip(me.polygons,mats,smooth):p.material_index=mat;p.use_smooth=sm
for k,layer in enumerate(old.uv_layers):
 dst=me.uv_layers.new(name=layer.name)
 for p,faceuv in zip(me.polygons,uvs):
  for li,uv in zip(p.loop_indices,faceuv[k]):dst.data[li].uv=uv
body.data=me;body.vertex_groups.clear()
for i,row in enumerate(newweights):
 assert len(row)<=4
 for name,w in row.items():(body.vertex_groups.get(name)or body.vertex_groups.new(name=name)).add([i],w,'REPLACE')
kd=KDTree(len(newverts))
for i,p in enumerate(newverts):kd.insert(p,i)
kd.balance();proof=[]
for name,i,p in roots:
 h,bi,d=kd.find(p);assert d<3e-6,(name,i,d);maxoff=max(maxoff,d);ob=bpy.data.objects[name]
 for g in list(ob.data.vertices[i].groups):ob.vertex_groups[g.group].remove([i])
 for bone,w in newweights[bi].items():(ob.vertex_groups.get(bone)or ob.vertex_groups.new(name=bone)).add([i],w,'REPLACE')
 proof.append(dict(fin=name,source_root_vertex=i,body_vertex=bi,static_distance_m=d))
for name,before in frozen.items():assert before==[(tuple(v.co),)for v in bpy.data.objects[name].data.vertices]
bm=bmesh.new();bm.from_mesh(me);bad=[dict(index=e.index,faces=len(e.link_faces),points=[list(v.co)for v in e.verts])for e in bm.edges if len(e.link_faces)!=2]
if bad:
 bm.faces.index_update();suspects=set(source_faces[f.index]for e in bm.edges if len(e.link_faces)!=2 for f in e.link_faces)
 (out/'topology-diagnostic.json').write_text(json.dumps(dict(bad=bad,body_vertices=len(newverts),body_triangles=len(newfaces),collapsed=collapsed,snap_max=snap_max,source_face_debug={i:face_debug.get(i)for i in sorted(suspects)}),indent=2)+'\n')
assert not bad,('Nonmanifold embedded body',bad[:3]);assert bm.calc_volume(signed=True)>0;bm.free()
assert all((p-verts[i]).length==0 for i,p in enumerate(newverts[:len(verts)]))
me.calc_loop_triangles();auth['body_triangles']=len(me.loop_triangles);total=0
for ob in bpy.context.scene.objects:
 if ob.type=='MESH':ob.data.calc_loop_triangles();total+=len(ob.data.loop_triangles)
assert total<=6000,total;auth['whole_triangles']=total
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n')
(out/'root-embedding.validation.json').write_text(json.dumps(dict(ok=True,kind='complete_original_fin_caps_embedded_in_actual_body',input_model_sha256=sha(src/'fish.glb'),source_sha256=sha(out/'fish.blend'),model_sha256=sha(out/'fish.glb'),input_body_triangles=len(tri),output_body_triangles=len(newfaces),whole_triangles=total,touched_original_body_triangles=touched,new_body_vertices=len(newverts)-len(verts),original_body_vertices_unchanged=True,complete_fin_geometry_UV_materials_unchanged=True,full_original_root_domain_unchanged=True,full_root_vertex_correspondences=proof,maximum_static_correspondence_m=maxoff,scope='Original complete cap edges constrain only touched body faces; new body vertices interpolate original UV and weights. Actual dynamic gates pending.',formal_acceptance=False),indent=2)+'\n')
print('BODY_FIN_SHARED_FINITE_SUPPORT',len(roots),len(newfaces),total)
