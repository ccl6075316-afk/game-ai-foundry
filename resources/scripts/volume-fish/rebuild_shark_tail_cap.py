"""Native concave caudal with an explicit complete finite body-cap station.

The two solid skins share the actual body cap at their root. Body-cap latitudes
are explicit contour points; a short posterior station controls the transition.
No finished mesh/reference outline or body shape is imported into the free fin.
"""
import bpy,bmesh,json,sys,hashlib,math
from pathlib import Path
from collections import Counter
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt,barycentric_transform
from mathutils.bvhtree import BVHTree
src,cp,out=map(lambda x:Path(x).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert sha(src/'fish.glb')==c['model_sha256'];assert not out.exists()and'/experiments/'in str(out);out.mkdir();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];tail=bpy.data.objects['Caudal'];old=tail.data;old.calc_loop_triangles();ov=[v.co.copy()for v in old.vertices];ot=[tuple(t.vertices)for t in old.loop_triangles];tree=BVHTree.FromPolygons(ov,ot,all_triangles=True);oldweights=[{tail.vertex_groups[g.group].name:g.weight for g in v.groups}for v in old.vertices];oldspan=[x.value for x in old.attributes['source_span_t'].data];layout=json.loads(Path(c['layout']).read_text());row=next(r for r in layout['rows']if r['name']=='Caudal');ref=json.loads(Path(c['reference']).read_text());scale=layout['metres_per_source_pixel'];axis=ref['reference_body_axis_m'];W,H=ref['source_canvas']['width'],ref['source_canvas']['height'];leading=np.array(row['root_endpoints_px'][0]);bv=np.array([tuple(v.co)for v in body.data.vertices]);rear=float(bv[:,0].min());cap=bv[abs(bv[:,0]-rear)<1e-7];rootx=float(leading[0]+(axis*(.5-row['onset_t'])-rear)/scale)
def cross(o,a,b):return(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
points=sorted(set(tuple(p)for p in cap[:,[1,2]]));lo=[];hi=[]
for p in points:
 while len(lo)>1 and cross(lo[-2],lo[-1],p)<=1e-14:lo.pop()
 lo.append(p)
for p in points[::-1]:
 while len(hi)>1 and cross(hi[-2],hi[-1],p)<=1e-14:hi.pop()
 hi.append(p)
hull=np.array(lo[:-1]+hi[:-1]);zs=sorted(set(hull[:,1]));zlo,zhi=zs[0],zs[-1]
def support(z):
 vals=[]
 for a,b in zip(hull,np.roll(hull,-1,axis=0)):
  if abs(z-a[1])<1e-8:vals.append(abs(a[0]))
  if(a[1]-z)*(b[1]-z)<0:vals.append(abs(a[0]+(b[0]-a[0])*(z-a[1])/(b[1]-a[1])))
 return max(vals,default=0.)
boundary=[np.array(p,float)for p in row['cdt_points_px'][:row['cdt_boundary_count']]];clipped=[]
for a,b in zip(boundary,boundary[1:]+boundary[:1]):
 if a[0]>=rootx-1e-7:clipped.append(a)
 if(a[0]-rootx)*(b[0]-rootx)<0:clipped.append(a+(b-a)*(rootx-a[0])/(b[0]-a[0]))
rootys=sorted(H/2-z/scale for z in zs);poly=[]
for a,b in zip(clipped,clipped[1:]+clipped[:1]):
 if abs(a[0]-rootx)<1e-5:a=np.array([rootx,rootys[0]if a[1]<(rootys[0]+rootys[-1])/2 else rootys[-1]])
 poly.append(a)
 if abs(a[0]-rootx)<1e-5 and abs(b[0]-rootx)<1e-5:
  poly.extend(np.array([rootx,y])for y in sorted(rootys[1:-1],reverse=b[1]<a[1]))
clean=[]
for p in poly:
 if not clean or np.linalg.norm(p-clean[-1])>1e-5:clean.append(p)
if np.linalg.norm(clean[0]-clean[-1])<1e-5:clean.pop()
poly=np.array(clean);nb=len(poly)
def inside(q):
 crossings=0
 for a,b in zip(poly,np.roll(poly,-1,axis=0)):
  if(a[1]>q[1])!=(b[1]>q[1])and q[0]<(b[0]-a[0])*(q[1]-a[1])/(b[1]-a[1])+a[0]:crossings+=1
 return crossings%2==1
allpoints=list(poly)
for p in row['cdt_points_px'][row['cdt_boundary_count']:]:
 p=np.array(p,float)
 if p[0]>rootx+.01 and inside(p):allpoints.append(p)
for z in zs:
 p=np.array([rootx+.025/scale,H/2-z/scale])
 if inside(p)and min(np.linalg.norm(p-q)for q in allpoints)>.01:allpoints.append(p)
vv,_,ff,*_=delaunay_2d_cdt([Vector(p)for p in allpoints],[],[list(range(nb))],2,1e-5,False);qq=np.array([tuple(p)for p in vv]);vertices=[];source=[];span=[];signs=[];maps=[{},{}];lookup={};roots=set();boundary_edges=Counter(tuple(sorted((a,b)))for f in ff for a,b in zip(f,f[1:]+f[:1]));rootcurve=np.array(row['root_curve_px']);maxdist=max(np.linalg.norm(q-rootcurve.mean(0))for q in qq);edge=layout['edge_full_thickness_m'];thickness=row['root_full_thickness_m']
for i,q in enumerate(qq):
 isroot=abs(q[0]-rootx)<.002;x=rear if isroot else axis*(.5-row['onset_t'])-(q[0]-leading[0])*scale;z=(H/2-q[1])*scale
 if isroot:z=min(zs,key=lambda s:abs(s-z))
 distance=float(np.min(np.linalg.norm(rootcurve-q,axis=1)));s=min(1.,distance/maxdist);aa=poly;bb=np.roll(poly,-1,axis=0);dd=bb-aa;t=np.clip(((q-aa)*dd).sum(1)/np.maximum((dd*dd).sum(1),1e-20),0,1);inset=float(np.min(np.linalg.norm(q-aa-t[:,None]*dd,axis=1)))*scale;base=edge/2+(thickness-edge)/2*(1-s)**1.1*min(1.,inset/max(thickness*.6,edge));gain=float(np.clip((x-(rear-.025))/.025,0,1));half=base*(1-gain)+support(z)*gain if zlo-1e-7<=z<=zhi+1e-7 else base
 if isroot:half=support(z)
 for layer,sign in enumerate([-1,1]):
  co=(float(x),float(sign*half),float(z));key=tuple(round(v,10)for v in co)
  if key not in lookup:lookup[key]=len(vertices);vertices.append(co);source.append(q);span.append(s);signs.append(0. if half<1e-9 else float(sign))
  maps[layer][i]=lookup[key]
  if isroot:roots.add(lookup[key])
faces=[]
for f in ff:
 for layer in range(2):faces.append(tuple(maps[layer][i]for i in(f[::-1]if layer==0 else f)))
for(a,b),count in boundary_edges.items():
 if count==1:
  ids=list(dict.fromkeys([maps[0][a],maps[0][b],maps[1][b],maps[1][a]]))
  if len(ids)>=3:faces.append(tuple(ids))
me=bpy.data.meshes.new('Native caudal with complete finite body-cap station');me.from_pydata(vertices,[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));
if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bad=[e.index for e in bm.edges if not e.is_manifold];assert not bad,bad;bm.to_mesh(me);bm.free();me.calc_loop_triangles()
for mat in old.materials:me.materials.append(mat)
for key,values in [('source_mask_x_px',[q[0]for q in source]),('source_mask_y_px',[q[1]for q in source]),('source_span_t',span),('source_layer_sign',signs)]:
 attr=me.attributes.new(key,'FLOAT','POINT')
 for a,value in zip(attr.data,values):a.value=value
charts=json.loads(Path(c['charts']).read_text());seal=next(r for r in charts['sealed_edges']if r['name']=='Caudal');path=np.array(seal['reference_closed_contour_px']);arc=np.array(seal['reference_arc_px']);uv=me.uv_layers.new(name='NativeFinProjection')
def perimeter(q):
 aa=path[:-1];dd=path[1:]-aa;t=np.clip(((q-aa)*dd).sum(1)/np.maximum((dd*dd).sum(1),1e-20),0,1);k=int(np.linalg.norm(q-aa-t[:,None]*dd,axis=1).argmin());return float((arc[k]+t[k]*(arc[k+1]-arc[k]))/arc[-1])
for f in me.polygons:
 f.use_smooth=True;is_cap=all(i in roots for i in f.vertices);q=np.array([source[i]for i in f.vertices]);is_seal=not is_cap and abs(np.cross(q[1]-q[0],q[2]-q[0]))<.25 and max(signs[i]for i in f.vertices)-min(signs[i]for i in f.vertices)>.5;f.material_index=1 if is_seal else 0;phases=np.array([perimeter(p)for p in q])
 if phases.max()-phases.min()>.5:phases[phases<.5]+=1
 for k,li in enumerate(f.loop_indices):
  i=me.loops[li].vertex_index;uv.data[li].uv=(phases[k],(signs[i]+1)/2*.9375+.03125)if is_seal else((source[i][0]+.5)/W,1-(source[i][1]+.5)/H)
tail.data=me;tail.vertex_groups.clear();capfaces=[tuple(t.vertices)for t in me.loop_triangles if all(i in roots for i in t.vertices)];captree=BVHTree.FromPolygons([Vector(p)for p in vertices],capfaces,all_triangles=True);body.data.calc_loop_triangles();bt=[tuple(t.vertices)for t in body.data.loop_triangles];bvv=[v.co.copy()for v in body.data.vertices];bodytree=BVHTree.FromPolygons(bvv,bt,all_triangles=True);bodygroups=[{body.vertex_groups[g.group].name:g.weight for g in v.groups}for v in body.data.vertices]
def bodymix(p):
 h,n,fi,d=bodytree.find_nearest(p);ids=bt[fi];beta=np.maximum(0,np.array(barycentric_transform(h,*[bvv[i]for i in ids],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))));beta/=beta.sum();mix={}
 for i,g in zip(ids,beta):
  for k,w in bodygroups[i].items():mix[k]=mix.get(k,0)+float(g)*w
 return mix
for v in me.vertices:
 mix=None
 if v.index in roots:mix=bodymix(v.co)
 else:
  nearest=min(range(len(ov)),key=lambda i:(ov[i]-v.co).length)
  if (ov[nearest]-v.co).length<2e-6:mix=oldweights[nearest]
  else:
   d=captree.find_nearest(v.co)[3];u=float(np.clip((d-.004)/.051,0,1));gain=.85*u*u*(3-2*u);mix={k:w*(1-gain)for k,w in bodymix(v.co).items()};fraction=float(np.clip((v.co.z-c['tail_center_z_m']+.005)/.010,0,1));mix['CaudalUpper_bone']=gain*fraction;mix['CaudalLower_bone']=gain*(1-fraction)
 mix={k:w for k,w in mix.items()if w>1e-8};total=sum(mix.values());assert len(mix)<=4 and total>0
 for name,w in mix.items():(tail.vertex_groups.get(name)or tail.vertex_groups.new(name=name)).add([v.index],w/total,'REPLACE')
auth=json.loads((src/'fin-authoring.json').read_text());record=next(r for r in auth['fins']if r['name']=='Caudal');record.update(vertices=len(me.vertices),triangles=len(me.loop_triangles),root_ids=sorted(roots),root_points_native=[list(me.vertices[i].co)for i in sorted(roots)],full_body_cap_station=True);total=0
for ob in bpy.context.scene.objects:
 if ob.type=='MESH':ob.data.calc_loop_triangles();total+=len(ob.data.loop_triangles)
assert total<=c['hard_limit'],total;auth['whole_triangles']=total;bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
 if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');(out/'full-tail-cap-authoring.validation.json').write_text(json.dumps(dict(ok=True,input_model_sha256=c['model_sha256'],model_sha256=sha(out/'fish.glb'),source_sha256=sha(out/'fish.blend'),whole_triangles=total,tail_triangles=record['triangles'],complete_cap_vertices=len(roots),actual_body_cap_latitudes=zs,posterior_support_m=.025,source_q_clip=rootx,body_and_other_fins_unchanged=True,scope='Own native concave free outline; explicit entire CURRENT finite body cap, new full cap selection. Earlier narrow-sheet root rejected; no inherited old cap pass. Fresh gates pending.',formal_acceptance=False),indent=2)+'\n');print('FULL_NATIVE_TAIL_CAP',total,record['triangles'],len(roots))
