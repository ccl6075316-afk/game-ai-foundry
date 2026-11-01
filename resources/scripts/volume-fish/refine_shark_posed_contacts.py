"""Split actual failed finite-fin contacts in the editable shark source.

Uses frozen Godot posed geometry, not guessed bone poses. A source construction
step only; exported candidate must run fresh actual body/fin/motion gates.
"""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha
args=sys.argv[sys.argv.index('--')+1:];preserve_rest='--preserve-rest-shape'in args;src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();export=src/('fin490'if(src/'fin490').exists()else'local-fin')/'blacktip_reef_shark/export.validation.json';ex=json.loads(export.read_text(encoding='utf8'));assert sha(src/'fish.glb')==ex['model_sha256'];selected=list(range(len(ex['samples'])))
if len(selected)==490:
 failures=json.loads((export.parent/'membranes.validation.json').read_text(encoding='utf8'));wanted={(v['worst_pose']['action'],v['worst_pose']['seconds'])for v in failures['summary'].values()if v['failed_poses']};seen=set();selected=[0]
 for i,row in enumerate(failures['samples']):
  if any(v['inside_samples']for v in row['fins'].values())and row['action']not in seen:seen.add(row['action']);selected.append(i)
 for i,row in enumerate(ex['samples']):
  if(row['action'],row['seconds'])in wanted:selected.append(i)
 selected=sorted(set(selected))
doc,blob=read_glb(src/'fish.glb');bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));author=json.loads((src/'fin-authoring.json').read_text());sources={r['name']:r for r in author['fins']};marked={n:set()for n in sources};ray=Vector((.231,.371,.899)).normalized();counts={n:0 for n in sources}
for sample in[ex['samples'][i]for i in selected]:
 assert sha(sample['posed_mesh_json'])==sample['sha256'];p=json.loads(Path(sample['posed_mesh_json']).read_text());bv=[Vector(q)for q in p['body_vertices_m']];bt=p['body_triangles']
 if sum(bv[a].dot(bv[b].cross(bv[c]))for a,b,c in bt)<0:bt=[list(reversed(t))for t in bt]
 tree=BVHTree.FromPolygons(bv,bt,all_triangles=True)
 for name,mem in p['membranes'].items():
  if len(args)>2 and name not in args[2:]:continue
  ob=bpy.data.objects[name];rnode=next(n for n in doc['nodes']if n.get('name')==name and 'mesh'in n);prim=doc['meshes'][rnode['mesh']]['primitives'][0];rest=arrays(doc,blob,prim['attributes']['POSITION']);mapping=[]
  for q in rest:
   point=Vector((float(q[0]),float(-q[2]),float(q[1])));best=min(ob.data.vertices,key=lambda v:(v.co-point).length_squared);assert(best.co-point).length<1e-6;mapping.append(best.index)
  vs=[Vector(q)for q in mem['vertices_m']];tri=mem['triangles'];roots=p['roots'][name]['points_m'];kd=KDTree(len(roots))
  for i,q in enumerate(roots):kd.insert(Vector(q),i)
  kd.balance();rid={i for i,q in enumerate(vs)if kd.find(q)[2]<1e-8};rf=[tri[i:i+3]for i in range(0,len(tri),3)if all(j in rid for j in tri[i:i+3])];rt=BVHTree.FromPolygons(vs,rf,all_triangles=True)if rf else None
  for i in range(0,len(tri),3):
   ids=tri[i:i+3];q=[vs[j]for j in ids];a,b,c=q;probes=[*q,(a+b+c)/3,a*.6+b*.2+c*.2,a*.2+b*.6+c*.2,a*.2+b*.2+c*.6]+[x.lerp(y,t)for x,y in zip(q,q[1:]+q[:1])for t in[.25,.5,.75]];bad=False
   for pt in probes:
    h,n,_,dist=tree.find_nearest(pt);rh,rn,_,_=tree.ray_cast(pt,ray);signed=-dist if rh is not None and rn.dot(ray)>0 else dist;rd=kd.find(pt)[2]
    if rt:rd=min(rd,rt.find_nearest(pt)[3])
    if rd<=.0005 and signed>=-.0005:continue
    if signed<-.00002:bad=True;break
   if bad:
    edge=max((tuple(sorted((mapping[a],mapping[b])))for a,b in zip(ids,ids[1:]+ids[:1])),key=lambda e:(ob.data.vertices[e[0]].co-ob.data.vertices[e[1]].co).length_squared);marked[name].add(edge);counts[name]+=1
body=bpy.data.objects['Closed_body'];body.data.calc_loop_triangles();bv=[v.co.copy()for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);records=[]
for name,edges in marked.items():
 if not edges:continue
 ob=bpy.data.objects[name];rootpos=[Vector(q)for q in sources[name]['root_points_native']];roots={v.index for v in ob.data.vertices if min((v.co-q).length for q in rootpos)<1e-6};bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();original=len(bm.verts);newroots=[];dlay=bm.verts.layers.deform.verify()
 for a,b in sorted(edges):
  edge=next(e for e in bm.verts[a].link_edges if bm.verts[b]in e.verts);result=bmesh.ops.subdivide_edges(bm,edges=[edge],cuts=1,use_grid_fill=False);new=[v for v in bm.verts if v.index<0]
  for v in new:
   h,n,fi,dist=tree.find_nearest(v.co);root=a in roots and b in roots
   if preserve_rest:
    if root:newroots.append(v)
    # BMesh interpolates the actual old endpoint deform weights and loop UVs.
    # Keep this exact rest midpoint: its independent skinning follows the
    # longitudinal bend instead of a long posed chord cutting through body.
    continue
   if root:v.co=h+n*.00008;newroots.append(v)
   else:
    rh,rn,_,_=tree.ray_cast(v.co,ray);inside=rh is not None and rn.dot(ray)>0
    if inside or dist<.003:v.co=h+n*.003
   ids=bt[fi];beta=barycentric_transform(h,*[bv[j]for j in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
   for j,gain in zip(ids,beta):
    for group in body.data.vertices[j].groups:
     key=body.vertex_groups[group.group].name;mix[key]=mix.get(key,0)+max(0,gain)*group.weight
   dv=v[dlay];dv.clear();total=sum(mix.values())
   for key,w in mix.items():dv[(ob.vertex_groups.get(key)or ob.vertex_groups.new(name=key)).index]=w/total
  bm.verts.index_update();bm.verts.ensure_lookup_table()
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));newids=[v.index for v in newroots];bm.to_mesh(ob.data);bm.free();ob.data.calc_loop_triangles();sources[name].update(root_ids=sorted(roots|set(newids)),root_points_native=[list(ob.data.vertices[i].co)for i in sorted(roots|set(newids))],triangles=len(ob.data.loop_triangles),vertices=len(ob.data.vertices));records.append(dict(name=name,split_edges=len(edges),failed_face_observations=counts[name]))
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.data.calc_loop_triangles()
author['whole_triangles']=sum(len(o.data.loop_triangles)for o in bpy.context.scene.objects if o.type=='MESH');assert author['whole_triangles']<=4000,author['whole_triangles'];author['fins']=list(sources.values());(out/'fin-authoring.json').write_text(json.dumps(author,indent=2)+'\n');bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in['MESH','ARMATURE']:ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'pose-refinement.validation.json').write_text(json.dumps(dict(ok=True,input_model_sha256=ex['model_sha256'],input_export_sha256=sha(export),records=records,model_sha256=sha(out/'fish.glb'),formal_acceptance=False,rest_shape_preserved=preserve_rest,scope='Only actual observed failed finite faces split; source pixels and body/mouth/rig/actions unchanged. Root selection extended to subdivision vertices of complete original basal edges; no omission. New full gates required.'),indent=2)+'\n');print(json.dumps(records))
