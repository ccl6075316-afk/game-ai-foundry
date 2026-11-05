"""Split explicit native body/fin facets at axial planes without sculpting.

Keep every old vertex, linear per-face UV/pixels and skin, complete old roots;
new points on basal edges extend the same complete root domain. Parallel cuts
avoid long diagonal fans across a curved skinning segment. Fresh gates required.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
src,config,out=map(lambda x:Path(x).resolve(),sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();c=json.loads(config.read_text());assert sha(src/'fish.glb')==c['model_sha256'];assert not out.exists()and'/experiments/'in str(out);out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));auth=json.loads((src/'fin-authoring.json').read_text());finrows={r['name']:r for r in auth['fins']};planes=sorted(c['planes_x_m']);records=[]
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def mixrows(rows,beta):
 keys=set().union(*rows);r={name:sum(row.get(name,0)*float(g)for row,g in zip(rows,beta))for name in keys};r={k:v for k,v in r.items()if v>1e-8};total=sum(r.values());assert len(r)<=4 and total>0;return {k:v/total for k,v in r.items()}
plateau_records=[]
for points in c.get('subpixel_skin_plateaux_gltf',[]):
 body=bpy.data.objects['Reference_head_body'];ids=[];native=[Vector((p[0],-p[2],p[1]))for p in points]
 for p in native:
  i=min(range(len(body.data.vertices)),key=lambda i:(body.data.vertices[i].co-p).length);assert(body.data.vertices[i].co-p).length<2e-6;ids.append(i)
 rows=[{body.vertex_groups[g.group].name:g.weight for g in body.data.vertices[i].groups}for i in ids];mix=mixrows(rows,[1/len(rows)]*len(rows));changes=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH'or ob.name.startswith('Eye_'):continue
  allowed=set(finrows[ob.name]['root_ids'])if ob.name in finrows else set(ids)
  for v in ob.data.vertices:
   if v.index not in allowed or min((v.co-p).length for p in native)>2e-6:continue
   for g in list(v.groups):ob.vertex_groups[g.group].remove([v.index])
   for name,w in mix.items():(ob.vertex_groups.get(name)or ob.vertex_groups.new(name=name)).add([v.index],w,'REPLACE')
   changes.append([ob.name,v.index])
 plateau_records.append(dict(points_gltf=points,common_mix=mix,changed=changes))
for ob in bpy.context.scene.objects:
 if ob.type!='MESH'or ob.name.startswith('Eye_'):continue
 old=ob.data;old.calc_loop_triangles();coords=np.array([tuple(v.co)for v in old.vertices],float);vertices=[Vector(p)for p in coords];weights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups}for v in old.vertices];newweights=list(weights);sources=[(i,)for i in range(len(vertices))];root=set(finrows[ob.name]['root_ids'])if ob.name in finrows else set();lookup={};faces=[];uvrows=[];materials=[];smooth=[]
 for t in old.loop_triangles:
  ids=list(t.vertices);points=coords[ids];polys=[[np.eye(3)[i]for i in range(3)]]
  is_cap=ob.name not in finrows or all(i in root for i in ids)
  if not is_cap:
   poly=[]
   for k in range(3):
    a,b=k,(k+1)%3;poly.append(np.eye(3)[a]);xa,xb=points[a,0],points[b,0]
    if ids[a]in root and ids[b]in root:
     cuts=[x for x in planes if min(xa,xb)+1e-9<x<max(xa,xb)-1e-9]
     for plane in sorted(cuts,reverse=xb<xa):
      blend=(plane-xa)/(xb-xa);q=np.zeros(3);q[a]=1-blend;q[b]=blend;poly.append(q)
   polys=[poly]
  for plane in (planes if is_cap else []):
   result=[]
   for poly in polys:
    xs=np.array([float(b@points[:,0])for b in poly])
    if xs.min()>=plane-1e-9 or xs.max()<=plane+1e-9:result.append(poly);continue
    sides=[[],[]]
    for k,(a,b)in enumerate(zip(poly,poly[1:]+poly[:1])):
     xa,xb=float(a@points[:,0]),float(b@points[:,0]);side=0 if xa<plane else 1;sides[side].append(a)
     if(xa-plane)*(xb-plane)<0:
      q=a+(b-a)*(plane-xa)/(xb-xa);sides[0].append(q);sides[1].append(q)
    for side in sides:
     clean=[]
     for q in side:
      if not clean or np.linalg.norm(q-clean[-1])>1e-10:clean.append(q)
     if len(clean)>2 and np.linalg.norm(clean[0]-clean[-1])<1e-10:clean.pop()
     assert len(clean)>=3
     result.append(clean)
   polys=result
  rawuv=[[old.uv_layers[k].data[li].uv.copy()for li in t.loops]for k in range(len(old.uv_layers))]
  for poly in polys:
   p=np.array([b@points for b in poly])
   def variants(a,b):
    if b<=a+1:return [[]]
    result=[]
    for k in range(a+1,b):
     if np.linalg.norm(np.cross(p[k]-p[a],p[b]-p[a]))<1e-18:continue
     for left in variants(a,k):
      for right in variants(k,b):result.append(left+right+[(a,k,b)])
    return result
   choices=variants(0,len(poly)-1);assert choices,('Degenerate axial polygon',poly)
   def score(tris):return min(np.linalg.norm(np.cross(p[b]-p[a],p[d]-p[a]))/max(np.linalg.norm(p[x]-p[y])**2 for x,y in [(a,b),(b,d),(d,a)])for a,b,d in tris)
   parts=max(choices,key=score)
   mapped=[]
   for beta in poly:
    active=np.where(abs(beta)>1e-9)[0]
    if len(active)==1:i=ids[int(active[0])]
    else:
     assert len(active)==2,('Axial parallel cut must land on an original triangle edge',beta)
     edge=tuple(sorted(ids[j]for j in active));p=beta@points;plane=min(planes,key=lambda x:abs(x-p[0]));key=(edge,plane)
     if key not in lookup:
      lookup[key]=len(vertices);vertices.append(Vector(p));newweights.append(mixrows([weights[j]for j in ids],beta));sources.append((ids,beta.tolist()))
      if set(edge)<=root:root.add(lookup[key])
     i=lookup[key]
    mapped.append(i)
   for part in parts:
    face=tuple(mapped[k]for k in part);assert len(set(face))==3
    faces.append(face);materials.append(old.polygons[t.polygon_index].material_index);smooth.append(old.polygons[t.polygon_index].use_smooth);uvrows.append([[sum((rawuv[k][j]*float(poly[i][j])for j in range(3)),Vector((0,0)))for i in part]for k in range(len(rawuv))])
 me=bpy.data.meshes.new(old.name+' axial finite sections');me.from_pydata(vertices,[],faces);me.update()
 for mat in old.materials:me.materials.append(mat)
 for p,mat,sm in zip(me.polygons,materials,smooth):p.material_index=mat;p.use_smooth=sm
 for k,layer in enumerate(old.uv_layers):
  dst=me.uv_layers.new(name=layer.name)
  for p,row in zip(me.polygons,uvrows):
   for li,q in zip(p.loop_indices,row[k]):dst.data[li].uv=q
 for attr in old.attributes:
  if attr.domain!='POINT'or attr.name.startswith('.')or attr.name=='position':continue
  assert attr.data_type in ['FLOAT','INT','BOOLEAN'],(attr.name,attr.data_type);dst=me.attributes.new(attr.name,attr.data_type,'POINT')
  for i,s in enumerate(sources):
   if len(s)==1:value=attr.data[s[0]].value
   else:ids,beta=s;value=sum(attr.data[j].value*gain for j,gain in zip(ids,beta))
   dst.data[i].value=value
 ob.data=me;ob.vertex_groups.clear()
 for i,row in enumerate(newweights):
  for name,w in row.items():(ob.vertex_groups.get(name)or ob.vertex_groups.new(name=name)).add([i],w,'REPLACE')
 bm=bmesh.new();bm.from_mesh(me);bad=[e.index for e in bm.edges if not e.is_manifold];assert not bad,(ob.name,bad[:10]);assert bm.calc_volume(signed=True)>0;bm.free();assert all((me.vertices[i].co-Vector(p)).length==0 for i,p in enumerate(coords))
 if ob.name in finrows:
  row=finrows[ob.name];assert set(row['root_ids'])<=root;row.update(root_ids=sorted(root),root_points_native=[list(me.vertices[i].co)for i in sorted(root)],vertices=len(vertices),triangles=len(faces))
 else:auth['body_triangles']=len(faces)
 records.append(dict(name=ob.name,new_vertices=len(vertices)-len(coords),triangles=len(faces)))
total=0
for ob in bpy.context.scene.objects:
 if ob.type=='MESH':ob.data.calc_loop_triangles();total+=len(ob.data.loop_triangles)
assert total<=c['hard_limit'],('Complete fish budget',total);auth['whole_triangles']=total;bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Reference_head_body'];bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');(out/'axial-facet-authoring.validation.json').write_text(json.dumps(dict(ok=True,kind='parallel_axial_finite_facet_authoring',input_model_sha256=c['model_sha256'],config_sha256=sha(config),source_sha256=sha(out/'fish.blend'),model_sha256=sha(out/'fish.glb'),whole_triangles=total,planes_x_m=planes,parts=records,original_vertices_static_positions_exact=True,original_UV_field_and_source_pixels_unchanged=True,complete_original_root_ids_preserved=True,scope='Parallel clipping, per-original-face UV and skin interpolation. Adds actual shared cap edge points; no sculpting, fin flattening, source RGB edits or motion/tolerance reduction. Fresh gates pending.',formal_acceptance=False),indent=2)+'\n');print('AXIAL_FINITE_FACETS',total)
