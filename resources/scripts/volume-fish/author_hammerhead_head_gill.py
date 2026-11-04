"""Registered prebranchial side form and eyes integrated into the closed head.

The library contributes scalar measurements only. All editable geometry and
pixels remain project-authored; eye material regions share body boundary edges.
"""
import bpy,bmesh,json,hashlib,sys,math,subprocess
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform,delaunay_2d_cdt
sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable.source_snapshot import rig_action_snapshot
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def tree(ob):
 ob.data.calc_loop_triangles();return BVHTree.FromPolygons([v.co.copy()for v in ob.data.vertices],[tuple(t.vertices)for t in ob.data.loop_triangles],all_triangles=True)
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def main():
 cp,out=map(lambda x:Path(x).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());assert not out.exists()and'/experiments/'in str(out);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
 for p,h in c['inputs'].items():assert sha(p)==h,p
 src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);actions=rig_action_snapshot()['actions']
 body=bpy.data.objects['Reference_head_body'];old=np.array([v.co[:]for v in body.data.vertices]);ot=tree(body);oldtri=old[np.array([t.vertices[:]for t in body.data.loop_triangles])]
 oral=sorted({i for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'for i in f.vertices});kd=KDTree(len(oral))
 for j,i in enumerate(oral):kd.insert(Vector(old[i]),j)
 kd.balance();L,nose=c['length_m'],c['nose_x_m'];top=np.array(c['top_delta_dense']);bot=np.array(c['bottom_delta_dense'])
 def bounds(x):
  if c.get('full_projected_envelopes'):
   a=oldtri;b=np.roll(oldtri,-1,axis=1);k=(a[:,:,0]-x)*(b[:,:,0]-x)<0
   if not np.any(k) and not np.any(abs(a[:,:,0]-x)<1e-7):return None
   q=a[k]+((x-a[:,:,0][k])/(b[:,:,0][k]-a[:,:,0][k]))[:,None]*(b[k]-a[k]);q=np.concatenate([q,a[abs(a[:,:,0]-x)<1e-7]]);return float(q[:,2].min()),float(q[:,2].max())
  a,b,d=oldtri[:,0],oldtri[:,1],oldtri[:,2];y=.015*L;den=(b[:,1]-d[:,1])*(a[:,0]-d[:,0])+(d[:,0]-b[:,0])*(a[:,1]-d[:,1]);keep=abs(den)>1e-15;u=np.zeros(len(a));v=u.copy();u[keep]=((b[keep,1]-d[keep,1])*(x-d[keep,0])+(d[keep,0]-b[keep,0])*(y-d[keep,1]))/den[keep];v[keep]=((d[keep,1]-a[keep,1])*(x-d[keep,0])+(a[keep,0]-d[keep,0])*(y-d[keep,1]))/den[keep];w=1-u-v;keep&=(u>=-1e-8)&(v>=-1e-8)&(w>=-1e-8);z=(u*a[:,2]+v*b[:,2]+w*d[:,2])[keep]
  return (float(z.min()),float(z.max()))if len(z)>1 else None
 cache={}
 def oral_delta(x):
  values=np.array(c.get('oral_translation_dense',[[0,c['oral_translation_z_m']],[1,c['oral_translation_z_m']]]));return float(np.interp((nose-x)/L,values[:,0],values[:,1]))
 def mapping(p):
  x,y,z=p;pax=(nose-x)/L;hi=float(np.interp(pax,top[:,0],top[:,1]));lo=float(np.interp(pax,bot[:,0],bot[:,1]))
  if abs(hi)+abs(lo)<1e-12:return Vector(p)
  if x not in cache:cache[x]=bounds(x)
  limits=cache[x]
  if limits is None:return Vector((x,y,z+oral_delta(x)))
  low,high=limits;t=max(0.,min(1.,(z-low)/(high-low)))if high-low>1e-9 else .5;delta=lo+(hi-lo)*t
  outer=c.get('outer_head_registered_field')
  if outer and abs(y)>outer['span_blend_m'][0] and pax<.14:
   # The complete side envelope belongs to the medial body. The transverse
   # terminal cephalofoil has its separately measured library registration.
   a,b,d=oldtri[:,0],oldtri[:,1],oldtri[:,2];yy=.015*L;den=(b[:,1]-d[:,1])*(a[:,0]-d[:,0])+(d[:,0]-b[:,0])*(a[:,1]-d[:,1]);keep=abs(den)>1e-15;u=np.zeros(len(a));v=u.copy();u[keep]=((b[keep,1]-d[keep,1])*(x-d[keep,0])+(d[keep,0]-b[keep,0])*(yy-d[keep,1]))/den[keep];v[keep]=((d[keep,1]-a[keep,1])*(x-d[keep,0])+(a[keep,0]-d[keep,0])*(yy-d[keep,1]))/den[keep];w=1-u-v;keep&=(u>=-1e-8)&(v>=-1e-8)&(w>=-1e-8);zz=(u*a[:,2]+v*b[:,2]+w*d[:,2])[keep]
   if len(zz)>1 and np.ptp(zz)>1e-9:
    t=max(0.,min(1.,(z-zz.min())/np.ptp(zz)));oldtop=np.array(outer['top_delta_dense']);oldbot=np.array(outer['bottom_delta_dense']);a0=float(np.interp(pax,oldbot[:,0],oldbot[:,1]));a1=float(np.interp(pax,oldtop[:,0],oldtop[:,1]));blend=smooth(*outer['span_blend_m'],abs(y));delta=delta*(1-blend)+(a0+(a1-a0)*t)*blend
  if x>.72:
   w=smooth(*c['oral_guard_m'],kd.find(Vector(p))[2]);delta=delta*w+oral_delta(x)*(1-w)
  return Vector((x,y,z+delta))
 for v in body.data.vertices:v.co=mapping(v.co)
 for i in oral:body.data.vertices[i].co=Vector(old[i])+Vector((0,0,oral_delta(old[i][0])))
 body.data.update();body.data.calc_loop_triangles();mapped=np.array([v.co[:]for v in body.data.vertices]);source_uv=[tuple(body.data.uv_layers.active.data[k].uv)for t in body.data.loop_triangles for k in t.loops];uvtri=np.array(source_uv).reshape(-1,3,2);uvfaces=np.array([t.vertices[:]for t in body.data.loop_triangles]);uvtree=tree(body)
 fins=[]
 for ob in [o for o in bpy.data.objects if o.type=='MESH'and o!=body and o.name not in c['old_eye_mesh_names']]:
  before=np.array([v.co[:]for v in ob.data.vertices]);maximum=0.
  for v in ob.data.vertices:
   p=v.co.copy();q=mapping(p);h,n,fi,d=ot.find_nearest(p)
   if h is not None and d<c['fin_support_m'][1]:
    ids=uvfaces[fi];actual=barycentric_transform(h,*[Vector(old[i])for i in ids],*[Vector(mapped[i])for i in ids]);delta=(actual-mapping(h))*(1-smooth(*c['fin_support_m'],d));delta.x=0.;delta.y=0.;q+=delta;maximum=max(maximum,delta.length)
   v.co=q
  ob.data.update();fins.append(dict(name=ob.name,maximum_support_correction_m=maximum,maximum_delta_m=float(np.linalg.norm(np.array([v.co[:]for v in ob.data.vertices])-before,axis=1).max())))
 eye_material=bpy.data.objects[c['old_eye_mesh_names'][0]].data.materials[0].copy()
 if c.get('eye_opaque_image'):
  eye_image=bpy.data.images.load(c['eye_opaque_image'],check_existing=False);eye_image.pack()
  for node in eye_material.node_tree.nodes:
   if node.type=='TEX_IMAGE':node.image=eye_image;node.interpolation='Closest'
 if eye_material.name not in body.data.materials:body.data.materials.append(eye_material)
 eye_slot=next(i for i,m in enumerate(body.data.materials)if m==eye_material);native_layer=body.data.uv_layers.active.name
 chart=Path(c['cap_chart']);chart.parent.mkdir(parents=True,exist_ok=True);chart_uv=np.zeros((128,256,2));clean_u=np.zeros((128,256));height_fraction=clean_u.copy();boundary_blend=clean_u.copy();chart_step=L/1940;cap_skin=body.data.materials[1].copy();cap_skin.name='Own native body pixels, continuous integrated head cap';body.data.materials.append(cap_skin);skin_slot=len(body.data.materials)-1
 bm=bmesh.new();bm.from_mesh(body.data);uvlayer=bm.loops.layers.uv[native_layer];deform=bm.verts.layers.deform.verify();bone_group=body.vertex_groups['body_00'].index;records=[]
 def skin_uv(q):
  h,n,fi,d=uvtree.find_nearest(q);assert h is not None;ids=uvfaces[fi];a,b,e=[Vector(mapped[i])for i in ids];u=barycentric_transform(h,a,b,e,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));return Vector(np.array(u)@uvtri[fi])
 for side in [-1,1]:
  plane=side*c['cap_plane_abs_y_m'];bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=Vector((0,plane,0)),plane_no=Vector((0,side,0)),clear_outer=True,clear_inner=False)
  edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-plane)<1e-6 for v in e.verts)];assert edges,('no terminal ring',side)
  neighbours={v:[]for e in edges for v in e.verts}
  for e in edges:a,b=e.verts;neighbours[a].append(b);neighbours[b].append(a)
  assert all(len(v)==2 for v in neighbours.values());start=next(iter(neighbours));ring=[start];prev=None;cur=start
  while True:
   nxt=next(v for v in neighbours[cur]if v!=prev)
   if nxt==start:break
   ring.append(nxt);prev,cur=cur,nxt
   assert len(ring)<=len(neighbours)
  assert len(ring)==len(neighbours)
  poly=np.array([[v.co.x,v.co.z]for v in ring]);area=sum(cross(a,b)for a,b in zip(poly,np.roll(poly,-1,axis=0)))
  if area<0:ring.reverse();poly=poly[::-1]
  cx=nose-c['eye_reference']['center_p']*L;cz=c['eye_reference']['center_z_over_length']*L;rx,rz=c['eye_reference']['radii_xz_m'];centre=np.array([cx,cz])
  # Exact ray/polygon intersections bound the source eye circle within the
  # actual head section. Full eye pixels are retained even if physical fit scales.
  def radius(direction):
   hits=[]
   for a,b in zip(poly,np.roll(poly,-1,axis=0)):
    edge=b-a;den=cross(direction,edge)
    if abs(den)<1e-12:continue
    t=cross(a-centre,edge)/den;u=cross(a-centre,direction)/den
    if t>0 and -1e-8<=u<=1+1e-8:hits.append(t)
   assert hits,('eye centre outside section',side,centre.tolist());return min(hits)
  angles=np.arange(c['eye_sectors'])*math.tau/c['eye_sectors'];directions=np.array([[rx*math.cos(t),rz*math.sin(t)]for t in angles]);scale=min(c['eye_reference'].get('maximum_fit_scale',1.),min(radius(q)for q in directions)/1.12);assert scale>.5,('eye does not fit finite head',side,scale);rx*=scale;rz*=scale
  points=[Vector(q)for q in poly];n=len(points)
  for t in angles:points.append(Vector((cx+rx*math.cos(t),cz+rz*math.sin(t))))
  points.append(Vector((cx,cz)));edges2=[(i,(i+1)%n)for i in range(n)]+[(n+i,n+(i+1)%len(angles))for i in range(len(angles))]+[(n+len(angles),n+i)for i in range(len(angles))]
  verts2,_,faces2,orig,_,_=delaunay_2d_cdt(points,edges2,[list(range(n))],1,1e-9,True);made=[]
  depth=.3598305-c['cap_plane_abs_y_m'];eye_vids=[]
  for xy,origins in zip(verts2,orig):
   old_id=next((i for i in origins if i<n),None)
   if old_id is not None:v=ring[old_id]
   else:
    q=np.array(xy)-centre;outer=radius(q)if np.linalg.norm(q)>1e-12 else 1e9;rho=1/outer;rr=math.hypot(q[0]/rx,q[1]/rz);yy=c['cap_plane_abs_y_m']+depth*math.sqrt(max(0.,1-rho*rho))+c['eye_relief_m']*max(0.,1-rr*rr)**2;v=bm.verts.new((xy[0],side*yy,xy[1]));v[deform][bone_group]=1.;eye_vids.append(v)
   made.append(v)
  eye_faces=[];skin_faces=[]
  for ids in faces2:
   coords=np.array([verts2[i]for i in ids]);rr=np.mean([math.hypot((q[0]-cx)/rx,(q[1]-cz)/rz)for q in coords]);iseye=rr<1-1e-6;face=bm.faces.new([made[i]for i in ids]);face.material_index=eye_slot if iseye else skin_slot;face.smooth=True
   for loop in face.loops:
    q=loop.vert.co
    if iseye:loop[uvlayer].uv=((c['eye_source_center_px'][0]+.5+(q.x-cx)/rx*c['eye_source_radius_px'])/c['source_size_px'][0],1-(c['eye_source_center_px'][1]+.5-(q.z-cz)/rz*c['eye_source_radius_px'])/c['source_size_px'][1])
    else:loop[uvlayer].uv=(((0 if side<0 else 128)+64+(q.x-cx)/chart_step)/256,(64+(q.z-cz)/chart_step)/128)
   (eye_faces if iseye else skin_faces).append(face)
  for v in ring:
   for f in v.link_faces:f.smooth=True
  # Query original finite material per pixel, not once per new cap vertex.
  # Original triangle charts are discontinuous; interpolating their unrelated
  # UVs across a new face creates white/black bands and is explicitly rejected.
  offset=0 if side<0 else 128
  for py in range(128):
   for px in range(128):
    x=cx+(px+.5-64)*chart_step;z=cz+(64-py-.5)*chart_step;q=Vector((x,side*.355,z));chart_uv[py,offset+px]=skin_uv(q);clean_u[py,offset+px]=x/2.5+.585;limits=bounds(x)
    if limits:
     low=mapping(Vector((x,.015*L,limits[0]))).z;high=mapping(Vector((x,.015*L,limits[1]))).z;height_fraction[py,offset+px]=(high-z)/max(high-low,1e-6)
    else:height_fraction[py,offset+px]=.5
    point=np.array([x,z]);distance=min(np.linalg.norm(point-(a+np.clip(np.dot(point-a,b-a)/max(np.dot(b-a,b-a),1e-20),0,1)*(b-a)))for a,b in zip(poly,np.roll(poly,-1,axis=0)));boundary_blend[py,offset+px]=smooth(0,.006,distance)
  records.append(dict(side=side,cut_boundary_vertices=n,eye_triangles=len(eye_faces),skin_transition_triangles=len(skin_faces),centre_xz_m=[cx,cz],actual_radii_xz_m=[rx,rz],fit_scale=scale,central_relief_m=c['eye_relief_m'],boundary_shared_with_body=True,source_circle_complete=True))
 map_path=chart.with_suffix('.npz')
 if map_path.exists():assert np.array_equal(np.load(map_path)['uv'],chart_uv),'Stale cap pixel map; use a new declared chart path'
 else:np.savez_compressed(map_path,uv=chart_uv,clean_u=clean_u,height_fraction=height_fraction,boundary_blend=boundary_blend)
 if not chart.exists():subprocess.run([c['repository_python'],str(Path(__file__).with_name('bake_hammerhead_skin_chart.py')),'--source',str(src/'fish.glb'),'--mapping',str(map_path),'--output',str(chart),'--report',str(chart.with_suffix('.validation.json')),*(['--clean-side',c['clean_side']]if c.get('clean_side')else[])],check=True)
 proof=json.loads(chart.with_suffix('.validation.json').read_text());assert proof['source_sha256']==sha(src/'fish.glb')and proof['mapping_sha256']==sha(map_path)and proof['output_sha256']==sha(chart)
 image=bpy.data.images.load(str(chart),check_existing=False);image.pack()
 for node in cap_skin.node_tree.nodes:
  if node.type=='TEX_IMAGE':node.image=image;node.interpolation='Closest'
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges),'Open integrated head';assert bm.calc_volume()>0;bm.to_mesh(body.data);bm.free()
 for name in c['old_eye_mesh_names']:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
 bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT');pivots=[]
 for bone in rig.data.edit_bones:
  if bone.name=='root':continue
  delta=mapping(bone.head)-bone.head;bone.head+=delta;bone.tail+=delta;pivots.append(dict(bone=bone.name,delta=list(delta)))
 bpy.ops.object.mode_set(mode='OBJECT');assert rig_action_snapshot()['actions']==actions
 meshes=[o for o in bpy.data.objects if o.type=='MESH'];total=0
 for ob in meshes:ob.data.update();ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops));ob.data.calc_loop_triangles();total+=len(ob.data.loop_triangles)
 assert total<=4000,total
 rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in meshes+[rig]:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
 fa=json.loads((src/'fin-authoring.json').read_text());fa['whole_triangles']=total;fa['integrated_eyes']=records;fa.pop('eyes',None)
 for f in fa['fins']:f['root_points_native']=[list(bpy.data.objects[f['name']].data.vertices[i].co)for i in f['root_ids']]
 (out/'fin-authoring.json').write_text(json.dumps(fa,indent=2)+'\n');r=dict(ok=True,kind='registered_head_gill_and_body_integrated_eyes',model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),config_sha256=sha(cp),script_sha256=sha(__file__),whole_triangles=total,body_vertices=len(body.data.vertices),body_triangles=len(body.data.loop_triangles),oral_translation_z_m=c['oral_translation_z_m'],oral_translation_dense=c.get('oral_translation_dense'),full_projected_envelopes=c.get('full_projected_envelopes',False),eyes=records,fins=fins,pivots=pivots,native_actions_exact=True,formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='oral_translation_dense'}))
if __name__=='__main__':main()
