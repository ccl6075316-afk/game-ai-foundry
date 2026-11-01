"""Continuous positive harmonic foil thickness; whole native outline/root fixed.

The previous independent horizontal-chord formula created multiple free-face
peaks and misclassified notch boundary thickness. This solves one scalar field
on the actual sheet instead. Body contact is a frozen geometric obstacle.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
src=Path(sys.argv[sys.argv.index('--')+1]).resolve();out=Path(sys.argv[sys.argv.index('--')+2]).resolve();assert not out.exists();out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));author=json.loads((src/'fin-authoring.json').read_text(encoding='utf8'));ob=bpy.data.objects['Caudal'];mesh=ob.data;row=next(r for r in author['fins']if r['name']=='Caudal');roots=set(row['root_ids']);before=np.array([v.co[:]for v in mesh.vertices]);body=bpy.data.objects['Closed_body'];body.data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co[:]for v in body.data.vertices],[tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True);uv=mesh.uv_layers.active
def fingerprint(o):return hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],[tuple(v.uv)for v in o.data.uv_layers.active.data])).encode()).hexdigest()
others={o.name:fingerprint(o)for o in bpy.data.objects if o.type=='MESH'and o!=ob};groups={};members=defaultdict(list);gid=[]
for i,p in enumerate(before):
 key=(round(p[0],7),round(p[2],7))
 if key not in groups:groups[key]=len(groups)
 g=groups[key];gid.append(g);members[g].append(i)
edges=Counter();active=set();adj=defaultdict(set)
for f in mesh.polygons:
 ids=list(f.vertices)
 if all(i in roots for i in ids)or np.mean(before[ids,1])<=0:continue
 q=np.array([uv.data[li].uv[:]for li in f.loop_indices]);a,b,c=q[:3]
 if abs(np.cross(b-a,c-a))<1e-10:continue
 gs=[gid[i]for i in ids];active.update(gs)
 for a,b in zip(gs,gs[1:]+gs[:1]):
  if a==b:continue
  edges[tuple(sorted((a,b)))]+=1;adj[a].add(b);adj[b].add(a)
positions={g:before[members[g][0],[0,2]]for g in active};h0={g:float(max(abs(before[members[g],1])))for g in active};fixed={};obstacle={};boundary=set(g for e,n in edges.items()if n==1 for g in e);edge_half=.0004
rear=min(v.co.x for v in body.data.vertices);cap=[v.co.z for v in body.data.vertices if abs(v.co.x-rear)<1e-7];cap_lo,cap_hi=min(cap),max(cap)
for g in active:
 root_members=[i for i in members[g]if i in roots]
 if root_members:fixed[g]=h0[g];continue
 x,z=positions[g];a,_,_,_=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)),4);b,_,_,_=tree.ray_cast(Vector((x,2,z)),Vector((0,-1,0)),4);minimum=edge_half
 if x>=rear-.0015 and cap_lo<=z<=cap_hi:fixed[g]=h0[g];continue
 if a is not None and b is not None:minimum=max(minimum,min(abs(a.y),abs(b.y))+.00008)
 obstacle[g]=minimum
 if g in boundary:fixed[g]=minimum
weights={}
for a in active:
 for b in adj[a]:weights[a,b]=1/max(np.linalg.norm(positions[a]-positions[b]),1e-5)
h={**h0,**fixed};iterations=0
while True:
 free=sorted(active-set(fixed));lookup={g:i for i,g in enumerate(free)};A=np.zeros((len(free),len(free)));b=np.zeros(len(free))
 for g,i in lookup.items():
  for n in adj[g]:
   w=weights[g,n];A[i,i]+=w
   if n in lookup:A[i,lookup[n]]-=w
   else:b[i]+=w*fixed[n]
 values=np.linalg.solve(A,b)if free else[];h.update(zip(free,map(float,values)));h.update(fixed);violations=[g for g in free if h[g]<obstacle.get(g,edge_half)-1e-10]
 if not violations:break
 for g in violations:fixed[g]=obstacle[g]
 iterations+=1;assert iterations<100
changed=[]
for i,v in enumerate(mesh.vertices):
 g=gid[i]
 if i in roots or g not in active:continue
 v.co.y=(-1 if before[i,1]<0 else 1)*h[g]
 if abs(v.co.y-before[i,1])>1e-9:changed.append(i)
assert changed
after=np.array([v.co[:]for v in mesh.vertices]);assert np.array_equal(before[:,[0,2]],after[:,[0,2]])and np.array_equal(before[sorted(roots)],after[sorted(roots)])
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges);bm.to_mesh(mesh);bm.free();assert all(fingerprint(o)==others[o.name]for o in bpy.data.objects if o.type=='MESH'and o!=ob)
maxima_before=[g for g in active-set(fixed)if h0[g]>max(h0[n]for n in adj[g])+1e-6];maxima_after=[g for g in active-set(fixed)if h[g]>max(h[n]for n in adj[g])+1e-9];assert not maxima_after
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_bytes((src/'fin-authoring.json').read_bytes());report=dict(ok=True,kind='continuous_caudal_harmonic_thickness',changed_vertices=len(changed),sheet_nodes=len(active),fixed_nodes=len(fixed),free_nodes=len(active-set(fixed)),unconstrained_peak_count_before=len(maxima_before),unconstrained_peak_count_after=len(maxima_after),maximum_thickness_change_native=float(abs(after[:,1]-before[:,1]).max()),source_outline_and_midplane_exact=True,complete_root_positions_exact=True,all_other_meshes_exact=True,topology_uv_weights_unchanged=True,edge_half_native=edge_half,obstacle_active_iterations=iterations,thickness_evidence='Engineering smooth-foil construction only; not biological tissue measurements.',visual_review='pending');(out/'thickness-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
