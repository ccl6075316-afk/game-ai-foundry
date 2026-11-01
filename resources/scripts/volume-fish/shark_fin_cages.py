"""Author closed variable-thickness shark fins from frozen native contours."""
import bpy,bmesh,math,json
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon,barycentric_transform
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

def build(layout,body,rig,material,aspect,weights):
 body.data.calc_loop_triangles();bv=[v.co.copy()for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);records=[];objects=[]
 def surface_weight(hit,face):
  ids=bt[face];a,b,c=[bv[i]for i in ids];bw=barycentric_transform(hit,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
  for vi,gain in zip(ids,bw):
   for group in body.data.vertices[vi].groups:
    name=body.vertex_groups[group.group].name;mix[name]=mix.get(name,0)+max(0,gain)*group.weight
  total=sum(mix.values());return {k:v/total for k,v in mix.items()if v>1e-7}
 for f in layout['rows']:
  xy=[Vector(p)for p in f['contour']];count=len(xy);root=list(f['root']);tris=[tuple(v if isinstance(v,int)else xy.index(v)for v in t)for t in tessellate_polygon([xy])]
  for seed in f['seeds']:
   q=Vector(seed)
   for ti,ids in enumerate(tris):
    a,b,c=[xy[i]for i in ids];ab=b-a;ac=c-a;ap=q-a;den=ab.x*ac.y-ab.y*ac.x
    if abs(den)<1e-12:continue
    u=(ap.x*ac.y-ap.y*ac.x)/den;v=(ab.x*ap.y-ab.y*ap.x)/den
    if min(u,v,1-u-v)>1e-6:
     n=len(xy);xy.append(q);root.append(False);tris[ti]=(ids[0],ids[1],n);tris.extend([(ids[1],ids[2],n),(ids[2],ids[0],n)]);break
  source=f['source'];anchor=Vector(source['anchor']);tip=Vector(source['tip']);axis=tip-anchor;span=max(axis.length,1e-5);N=len(xy)
  for sign in([-1,1]if f['paired']else[1]):
   name=f['name']+('_left'if sign<0 else'_right')if f['paired']else f['name'];verts=[];wts=[];rids=[];full_thickness=[]
   for layer in[-1,1]:
    for i,q in enumerate(xy):
     u,v=q;along=max(0,min(1,(q-anchor).dot(axis)/(span*span)));av=anchor.y;v3=av+(v-av)*f['vertical_scale'];depth=(source['root_depth']+(source['tip_depth']-source['root_depth'])*along)*sign if f['paired']else 0.;p=Vector((u-.5,depth,(.5-v3)*aspect))
     # Chord envelope at this source height; foil's maximum is ahead of midchord.
     cuts=[]
     for a,b in zip(xy[:count],xy[1:count]+xy[:1]):
      if min(a.y,b.y)-1e-8<=v<=max(a.y,b.y)+1e-8 and abs(a.y-b.y)>1e-9:cuts.append(a.x+(v-a.y)/(b.y-a.y)*(b.x-a.x))
     lo,hi=(min(cuts),max(cuts))if len(cuts)>1 else(u-.0001,u+.0001);chord=max(hi-lo,.0002);t=max(0,min(1,(hi-u)/chord));shape=.2969*math.sqrt(t)-.126*t-.3516*t*t+.2843*t**3-.1036*t**4
     half=max(f['edge_half_thickness'],min(f['maximum_half_thickness'],5*f['thickness_ratio']*chord*shape));normal=Vector((0,0,1))if f['paired']else Vector((0,1,0));p+=normal*layer*half
     hit,normal_body,face,dist=tree.find_nearest(p)
     if root[i]:
      p=hit+normal_body*.00008;w=surface_weight(hit,face);rids.append(len(verts))
     else:
      # The free surface must remain exterior, including its two finite layers.
      if (p-hit).dot(normal_body)<.00045:p=hit+normal_body*.00008
      t=max(0,min(1,(dist-.012)/.035));gain=.8*t*t*(3-2*t);w={k:v*(1-gain)for k,v in surface_weight(hit,face).items()};w[name]=gain
     verts.append(p);wts.append(w);full_thickness.append(half*2)
   faces=[tuple(reversed(t))for t in tris]+[tuple(i+N for i in t)for t in tris]+[(i,(i+1)%count,(i+1)%count+N,i+N)for i in range(count)]
   # Refine only actual curved body contacts. Never replace full fin silhouettes
   # with dense regular grids, or change the frozen complete basal interface.
   uvpoints=[q.copy()for q in xy]*2;flags=[bool(x)for x in root]*2
   faces=[(q[0],q[i],q[i+1])for q in faces for i in range(1,len(q)-1)];ray=Vector((.231,.371,.899)).normalized();history=[]
   outward=Vector((0,sign,0))if f['paired']else Vector((0,0,-1 if name in['Anal','CaudalLower']else 1))
   def signed(q):
    h,n,face,dist=tree.find_nearest(q);rh,rn,_,_=tree.ray_cast(q,ray);return (-dist if rh is not None and rn.dot(ray)>0 else dist),h,n,face
   def attach(q,isroot):
    dist,h,n,face=signed(q)
    if isroot:return h+n*.00008,surface_weight(h,face)
    axis=1 if f['paired']else 2;sgn=outward[axis];origin=q.copy();origin[axis]=sgn*2;hh,nn,ff,_=tree.ray_cast(origin,-outward,4)
    if hh is not None and(q[axis]-hh[axis])*sgn<.0012:q[axis]=hh[axis]+sgn*.0012
    dist,h,n,face=signed(q)
    if dist<.0009:q=h+n*.0009
    t=max(0,min(1,(max(0,dist)-.012)/.035));gain=.8*t*t*(3-2*t);w={k:v*(1-gain)for k,v in surface_weight(h,face).items()};w[name]=gain;return q,w
   for i,q in enumerate(verts):verts[i],wts[i]=attach(q.copy(),flags[i])
   for iteration in range(14):
    rootfaces=[t for t in faces if all(flags[i]for i in t)];rt=BVHTree.FromPolygons(verts,rootfaces,all_triangles=True)if rootfaces else None;marked=set();rootpoints=[q for q,g in zip(verts,flags)if g];rootedges={tuple(sorted((a,b)))for t in faces for a,b in zip(t,t[1:]+t[:1])if flags[a]and flags[b]};marked.update(e for e in rootedges if(verts[e[0]]-verts[e[1]]).length>.012)
    for a,b in rootedges:rootpoints.extend(verts[a].lerp(verts[b],i/8)for i in range(1,8))
    kd=KDTree(len(rootpoints))
    for i,q in enumerate(rootpoints):kd.insert(q,i)
    kd.balance()
    faults=[]
    for tri in faces:
     q=[verts[i]for i in tri];a,b,c=q;probes=[(a+b+c)/3,a*.6+b*.2+c*.2,a*.2+b*.6+c*.2,a*.2+b*.2+c*.6]+[x.lerp(y,t)for x,y in zip(q,q[1:]+q[:1])for t in[.25,.5,.75]];bad=False
     for point in probes:
      dist,_,_,_=signed(point)
      rootdistance=kd.find(point)[2]
      if rt is not None:rootdistance=min(rootdistance,rt.find_nearest(point)[3])
      if rootdistance<=.00030 and dist>=-.00030:continue
      if dist<-.000006:
       bad=True
       if len(faults)<2:faults.append({'ids':tri,'flags':[flags[i]for i in tri],'point':list(point),'dist':dist,'rootdist':rt.find_nearest(point)[3]if rt else None,'vertices':[list(verts[i])for i in tri],'vertex_distances':[signed(verts[i])[0]for i in tri]})
       break
     if bad:marked.add(max((tuple(sorted((a,b)))for a,b in zip(tri,tri[1:]+tri[:1])),key=lambda e:(verts[e[0]]-verts[e[1]]).length_squared))
    history.append(dict(round=iteration,triangles=len(faces),split_edges=len(marked)));print('CONTACT_REFINEMENT',name,history[-1],flush=True)
    if not marked:break
    if len(faces)+len(marked)*2>=900:
     print('CONTACT_FAILURE',name,faults,flush=True)
     raise AssertionError('Unexpected local cage density '+name)
    mids={}
    for a,b in sorted(marked):
     q=(verts[a]+verts[b])/2;flag=flags[a]and flags[b];q,w=attach(q,flag);mids[(a,b)]=len(verts);verts.append(q);wts.append(w);uvpoints.append((uvpoints[a]+uvpoints[b])/2);flags.append(flag)
    refined=[]
    for tri in faces:
     pending=[tri]
     for edge,mid in mids.items():
      nextfaces=[]
      for t in pending:
       if edge[0]in t and edge[1]in t:
        for j in range(3):
         a,b,c=t[j],t[(j+1)%3],t[(j+2)%3]
         if {a,b}==set(edge):nextfaces.extend([(a,mid,c),(mid,b,c)]);break
       else:nextfaces.append(t)
      pending=nextfaces
     refined.extend(pending)
    faces=refined
   rids=[i for i,g in enumerate(flags)if g]
   mesh=bpy.data.meshes.new(name+' finite foil');mesh.from_pydata(verts,[],faces);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);ob.parent=rig;mesh.materials.append(material);uv=mesh.uv_layers.new(name='Native fin source')
   for poly in mesh.polygons:
    poly.use_smooth=True
    for li in poly.loop_indices:
     q=uvpoints[mesh.loops[li].vertex_index];uv.data[li].uv=(q.x,1-q.y)
   for i,w in enumerate(wts):
    for k,g in w.items():
     if g>1e-7:(ob.vertex_groups.get(k)or ob.vertex_groups.new(name=k)).add([i],g,'REPLACE')
   bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges),name;bm.to_mesh(mesh);bm.free();mod=ob.modifiers.new('Native shark skin','ARMATURE');mod.object=rig;mesh.calc_loop_triangles()
   records.append(dict(name=name,triangles=len(mesh.loop_triangles),vertices=len(mesh.vertices),root_ids=rids,root_points_native=[list(verts[i])for i in rids],source_root_curve=[list(xy[i])for i in range(count)if root[i]],foil_full_thickness_native_range=[min(full_thickness),max(full_thickness)],source_contour=f['contour'],source_uv_pixels_preserved=True,contact_refinement=history,thickness_is='engineering candidate, not species measurement'));objects.append(ob)
 return objects,records

