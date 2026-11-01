"""One continuous asymmetric caudal solid with native notch and body section.

Retains both original caudal bones; a single fin mesh avoids a false interlobe
gap. Body, mouth, paired fins, rig and clips are not rebuilt.
"""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
import numpy as np
args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();planpath=Path(args[1]).resolve();out=Path(args[2]).resolve();assert not out.exists()and'/experiments/'in out.as_posix();out.mkdir();plan=json.loads(planpath.read_text(encoding='utf8'));bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));author=json.loads((src/'fin-authoring.json').read_text());body=bpy.data.objects['Closed_body'];rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.view_layer.update();body.data.calc_loop_triangles();bv=[v.co.copy()for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);rear=min(v.x for v in bv);cap=[v for v in bv if abs(v.x-rear)<1e-7];lo,hi=min(v.z for v in cap),max(v.z for v in cap);center=(lo+hi)/2;aspect=618/1834;material=bpy.data.objects['Caudal'if'Caudal'in bpy.data.objects else'CaudalUpper'].data.materials[0]
def body_half(z):
 hits=[]
 for tri in bt:
  if not all(abs(bv[i].x-rear)<1e-7 for i in tri):continue
  for a,b in zip(tri,tri[1:]+tri[:1]):
   p,q=bv[a],bv[b]
   if abs(p.z-z)<1e-7:hits.append(abs(p.y))
   if(p.z-z)*(q.z-z)<0:hits.append(abs(p.y+(q.y-p.y)*(z-p.z)/(q.z-p.z)))
 return max(hits,default=0)
verts=[];qs=[];weights=[];n=len(plan['vertices']);baseline=plan['root_baseline'];rootu=max(q[0]for q in baseline)
# The original body uses longitudinal ring weights. Free fin skin must use
# its own axial station, not a closest-surface point whose x shifts along a
# steep dorsal/ventral silhouette. Root cap weights remain exact barycentric.
rings={}
for vtx in body.data.vertices:
 x=round(vtx.co.x,7)
 if x>0:continue
 row={body.vertex_groups[g.group].name:g.weight for g in vtx.groups}
 rings.setdefault(x,[]).append(row)
ringx=sorted(rings);ringw={x:{k:sum(r.get(k,0)for r in rows)/len(rows)for k in set().union(*(r.keys()for r in rows))}for x,rows in rings.items()}
def axial_weights(x):
 k=int(np.searchsorted(ringx,x));a=ringx[max(0,min(k-1,len(ringx)-1))];b=ringx[max(0,min(k,len(ringx)-1))];t=0 if a==b else max(0,min(1,(x-a)/(b-a)))
 return {name:ringw[a].get(name,0)*(1-t)+ringw[b].get(name,0)*t for name in set(ringw[a])|set(ringw[b])}
for side in[-1,1]:
 for u,v in plan['vertices']:
  x=u-.5;z=(.5-v)*aspect;span=max(0,min(1,(rootu-u)/(rootu-.002)));chord=[]
  for a,b in zip(plan['outline'],plan['outline'][1:]+plan['outline'][:1]):
   if min(a[1],b[1])-1e-8<=v<=max(a[1],b[1])+1e-8 and abs(a[1]-b[1])>1e-9:chord.append(a[0]+(b[0]-a[0])*(v-a[1])/(b[1]-a[1]))
  t=.5 if len(chord)<2 else max(0,min(1,(u-min(chord))/max(max(chord)-min(chord),1e-9)));edge=.0004;half=edge+(.008*(1-span)**.75-edge)*math.sin(math.pi*t)**.7
  if lo<=z<=hi:
   fade=max(0,min(1,(x-(rear-.03))/.03));fade=fade*fade*(3-2*fade);half=half*(1-fade)+max(edge,body_half(z))*fade
  if plan.get('continuous_foil'):
   cf=plan['continuous_foil'];edge=cf['edge_half'];crossings=[]
   for a,b in zip(plan['outline'],plan['outline'][1:]+plan['outline'][:1]):
    if(a[1]<=v<b[1])or(b[1]<=v<a[1]):crossings.append(a[0]+(b[0]-a[0])*(v-a[1])/(b[1]-a[1]))
   crossings.sort();interval=next(((a,b)for a,b in zip(crossings[::2],crossings[1::2])if a-1e-8<=u<=b+1e-8 and b-a>1e-8),None);shape=0
   if interval:
    a,b=interval;peak=max(a+1e-9,min(a+cf['peak_from_trailing']*(b-a),rear+.5-cf['peak_posterior_offset'],b-1e-9));t=(u-a)/max(peak-a,1e-9)if u<=peak else(b-u)/max(b-peak,1e-9);shape=math.sin(math.pi*.5*max(0,min(1,t)))
   zlo=min((.5-q[1])*aspect for q in plan['outline']);zhi=max((.5-q[1])*aspect for q in plan['outline']);s=(z-center)/max(zhi-center,1e-9)if z>=center else(center-z)/max(center-zlo,1e-9);base=max(abs(p.y)for p in cap);envelope=edge+(base-edge)*max(0,1-s)
   if lo<=z<=hi:envelope=max(envelope,body_half(z))
   half=edge+(envelope-edge)*shape
   fade=max(0,min(1,(x-(rear-cf['root_blend_length']))/(cf['root_blend_length']-cf['root_plateau'])));fade=fade*fade*(3-2*fade);half=half*(1-fade)+max(edge,body_half(z))*fade
  # In front of the posterior section, use the ACTUAL local body envelope.
  # Repeating the posterior ellipse at every x leaves tiny external ventral
  # wings after Boolean subtraction when the complete source contour is used.
  # Put such tissue inside the body; the full real body intersection defines
  # the cap, while free source silhouette above/below the body is retained.
  if x>rear+1e-7:
   hit0,_,_,_=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)),4)
   hit1,_,_,_=tree.ray_cast(Vector((x,2,z)),Vector((0,-1,0)),4)
   if hit0 is not None and hit1 is not None:
    local_half=min(abs(hit0.y),abs(hit1.y))
    half=min(half,max(edge,local_half-.00015))
  p=Vector((x,side*half,z));verts.append(p);qs.append((u,1-v));hit,normal,fi,d=tree.find_nearest(p);ids=bt[fi];beta=barycentric_transform(hit,*[bv[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={};gain=.8*max(0,min(1,(rear-x)/.18))**2
  for k,w in axial_weights(x).items():mix[k]=w*(1-gain)
  up=max(0,min(1,(z-center+.008)/.016));mix['CaudalUpper']=gain*up;mix['CaudalLower']=gain*(1-up);weights.append(mix)
faces=[]
for tri in plan['triangles']:faces.append(tuple(reversed(tri)));faces.append(tuple(i+n for i in tri))
edges={}
for tri in plan['triangles']:
 for a,b in zip(tri,tri[1:]+tri[:1]):key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
assert all(count in[1,2]for count in edges.values())
for (a,b),count in edges.items():
 if count==1:faces.append((a,b,b+n,a+n))
for name in['CaudalUpper','CaudalLower','Caudal']:
 if name in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
authored_section_points=[p.copy()for p in verts if abs(p.x-rear)<1e-7 and tree.find_nearest(p)[3]<.00015]
mesh=bpy.data.meshes.new('Complete native asymmetric caudal solid');mesh.from_pydata(verts,[],faces);mesh.materials.append(material);uv=mesh.uv_layers.new()
for f in mesh.polygons:
 f.use_smooth=True
 for li in f.loop_indices:u,v=qs[mesh.loops[li].vertex_index];uv.data[li].uv=(u*.5,v)
ob=bpy.data.objects.new('Caudal',mesh);bpy.context.collection.objects.link(ob);ob.parent=rig
for i,w in enumerate(weights):
 total=sum(w.values())
 for k,v in w.items():
  if v>1e-7:(ob.vertex_groups.get(k)or ob.vertex_groups.new(name=k)).add([i],v/total,'REPLACE')
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges);bm.to_mesh(mesh);bm.free()
# Boolean against the actual finite body triangles, not its editable quads.
# Distinct temporary face IDs preserve skinning hinges that are coplanar at
# rest but cease to be coplanar in motion. Otherwise the cap silently bridges
# those hinges and penetrates the body despite every root vertex matching.
cutmesh=bpy.data.meshes.new('Temporary exact finite body');cutmesh.from_pydata(bv,[],bt);markers=[]
for i,f in enumerate(cutmesh.polygons):
 marker=bpy.data.materials.new('Temporary body finite triangle '+str(i));markers.append(marker);cutmesh.materials.append(marker);f.material_index=i
cutter=bpy.data.objects.new('Temporary exact finite body cutter',cutmesh);bpy.context.collection.objects.link(cutter);cutter.matrix_world=body.matrix_world.copy()
bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('Exact complete caudal body intersection','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;mod.use_self=True;mod.use_hole_tolerant=True;mod.material_mode='TRANSFER';bpy.ops.object.modifier_apply(modifier=mod.name);mesh=ob.data;capfaces=[f for f in mesh.polygons if f.material_index>0];roots={i for f in capfaces for i in f.vertices}
roots.update(v.index for v in mesh.vertices if authored_section_points and min((v.co-p).length for p in authored_section_points)<1e-6)
assert roots and capfaces
for i in roots:
 p=mesh.vertices[i].co;h,normal,fi,d=tree.find_nearest(p);mesh.vertices[i].co=h;ids=bt[fi];beta=barycentric_transform(h,*[bv[j]for j in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
 for j,w in zip(ids,beta):
  for g in body.data.vertices[j].groups:k=body.vertex_groups[g.group].name;mix[k]=mix.get(k,0)+max(0,w)*g.weight
 for g in ob.vertex_groups:g.remove([i])
 for k,w in mix.items():
  if w>1e-7:(ob.vertex_groups.get(k)or ob.vertex_groups.new(name=k)).add([i],w,'REPLACE')
for f in capfaces:
 for li in f.loop_indices:p=mesh.vertices[mesh.loops[li].vertex_index].co;mesh.uv_layers.active.data[li].uv=((p.x+.5)*.5,.5+p.z/aspect)
for f in mesh.polygons:f.material_index=0;f.use_smooth=True
while len(mesh.materials)>1:mesh.materials.pop(index=len(mesh.materials)-1)
bpy.data.objects.remove(cutter,do_unlink=True);bpy.data.meshes.remove(cutmesh)
for marker in markers:
 assert marker.users==0;bpy.data.materials.remove(marker)
rootpoints=[mesh.vertices[i].co.copy()for i in roots];bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.calc_loop_triangles();roots=[v.index for v in mesh.vertices if min((v.co-p).length for p in rootpoints)<1e-7];mod=ob.modifiers.new('Original native dual caudal skin','ARMATURE');mod.object=rig;records=[r for r in author['fins']if not r['name'].startswith('Caudal')];records.append(dict(name='Caudal',paired=False,root_ids=roots,root_points_native=[list(mesh.vertices[i].co)for i in roots],vertices=len(mesh.vertices),triangles=len(mesh.loop_triangles),root_method='Every actual complete body-intersection cap of one continuous asymmetric caudal; source whole-outline baseline. Both original caudal bones retained.',source_full_outline=plan['outline']));total=len(body.data.loop_triangles)+sum(r['triangles']for r in records);assert total<=4000,total;rig.data.pose_position='POSE';bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type in['MESH','ARMATURE']:o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_text(json.dumps(dict(body_triangles=len(body.data.loop_triangles),whole_triangles=total,fins=records),indent=2)+'\n');(out/'tail-authoring.json').write_text(json.dumps(dict(whole_triangles=total,tail_triangles=len(mesh.loop_triangles),full_baseline=plan['root_baseline'],body_posterior_x=rear,body_posterior_section_points=[list(p)for p in cap],upper_lower_bones_preserved=True,formal_acceptance=False),indent=2)+'\n');print('WHOLE_CAUAL',total,len(mesh.loop_triangles))
