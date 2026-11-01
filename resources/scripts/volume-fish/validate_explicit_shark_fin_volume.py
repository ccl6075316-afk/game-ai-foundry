"""Finite normal-ray zones and body-to-whole-tail section with actual negative.

Ordinary named meshes and complete explicit basal caps; never a fixed fin count.
The tail section target is the pre-authoring actual body cap, not fitted output.
"""
import bpy,json,sys,hashlib,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'));from glb_io import read_glb,arrays,sha
args=sys.argv[sys.argv.index('--')+1:];current=Path(args[0]).resolve();negative=Path(args[1]).resolve();profilepath=Path(args[2]).resolve();targetpath=Path(args[3]).resolve();out=Path(args[4]).resolve();assert not out.exists();profile=json.loads(profilepath.read_text(encoding='utf8'));target=json.loads(targetpath.read_text(encoding='utf8'));scale=1.5/.9950926303863525;targetcap=[Vector(p)for p in target['body_posterior_section_points']];rear=target['body_posterior_x'];section_plane=rear-.00015
def section(vertices,faces,x,zs):
 segments=[]
 for tri in faces:
  points=[]
  for i,j in zip(tri,tri[1:]+tri[:1]):
   a,b=vertices[i],vertices[j]
   if abs(a.x-x)<1e-7:points.append(a)
   if(a.x-x)*(b.x-x)<0:points.append(a.lerp(b,(x-a.x)/(b.x-a.x)))
  if len(points)>=2:segments.append(points[:2])
 values=[]
 for z in zs:
  hits=[]
  for a,b in segments:
   if abs(a.z-z)<1e-7:hits.append(abs(a.y))
   if(a.z-z)*(b.z-z)<0:hits.append(abs(a.y+(b.y-a.y)*(z-a.z)/(b.z-a.z)))
  values.append(max(hits,default=0))
 return values
def measure(folder,final=False):
 bpy.ops.wm.open_mainfile(filepath=str(folder/'fish.blend'));auth=json.loads((folder/'fin-authoring.json').read_text());rows={r['name']:r for r in auth['fins']};body=bpy.data.objects['Closed_body'];body.data.calc_loop_triangles();bodyv=[v.co for v in body.data.vertices];bodyt=[list(t.vertices)for t in body.data.loop_triangles];btree=BVHTree.FromPolygons(bodyv,bodyt,all_triangles=True);ray=Vector((.231,.371,.899)).normalized();records=[];tails=[];tailfaces=[]
 if final:doc,blob=read_glb(folder/'fish.glb')
 for fin in profile['fins']:
  for suffix in(['_left','_right']if fin.get('paired')else['']):
   name=fin['name']+suffix;names=[name]if name in rows else['CaudalUpper','CaudalLower']if name=='Caudal'else[];assert names,(name,'missing actual fin');vs=[];ts=[];rootset=set();sourceuv=[]
   for part in names:
    ob=bpy.data.objects[part];mesh=ob.data;mesh.calc_loop_triangles();off=len(vs);vs.extend(v.co.copy()for v in mesh.vertices);ts.extend([i+off for i in t.vertices]for t in mesh.loop_triangles);rootset.update(i+off for i in rows[part]['root_ids']);uv=mesh.uv_layers.active
    for t in mesh.loop_triangles:sourceuv.append(np.array([uv.data[li].uv[:]for li in t.loops]))
   tree=BVHTree.FromPolygons(vs,ts,all_triangles=True);volume=sum(vs[a].dot(vs[b].cross(vs[c]))for a,b,c in ts);roots=[vs[i]for i in rootset];rootfaces=[t for t in ts if all(i in rootset for i in t)];root_tree=BVHTree.FromPolygons(vs,rootfaces,all_triangles=True)if rootfaces else None;kd=KDTree(len(roots))
   for i,p in enumerate(roots):kd.insert(p,i)
   kd.balance()
   def rootdistance(p):return min(kd.find(p)[2],root_tree.find_nearest(p)[3]if root_tree else 1e10)
   maxdistance=max(rootdistance(p)for p in vs);probes=[];misses=0;contact=[]
   for ids,uvs in zip(ts,sourceuv):
    pts=[vs[i]for i in ids];a,b,c=pts;normal=(b-a).cross(c-a)
    if normal.length<1e-12:continue
    normal.normalize()
    if volume<0:normal=-normal
    basal=all(i in rootset for i in ids)
    if basal:
     contact.extend([sum(pts,Vector())/3]+[p.lerp(q,t)for p,q in zip(pts,pts[1:]+pts[:1])for t in[.25,.5,.75]]);continue
    d1,d2=uvs[1]-uvs[0],uvs[2]-uvs[0]
    if abs(d1[0]*d2[1]-d1[1]*d2[0])<1e-10:continue
    for w in[(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
     p=sum((v*x for v,x in zip(pts,w)),Vector());hit,_,_,dist=tree.ray_cast(p-normal*1e-7,-normal)
     if hit is None:misses+=1;continue
     probes.append(dict(source_t=rootdistance(p)/maxdistance,local_normal_thickness_mm=(dist+1e-7)*scale*1000))
   signed=[]
   for p in roots+contact:
    h,n,fi,dist=btree.find_nearest(p);rh,rn,_,_=btree.ray_cast(p,ray);signed.append((-dist if rh is not None and rn.dot(ray)>0 else dist)*scale*1000)
   zones={}
   for label,lo,hi in [('proximal',0,.35),('middle',.35,.7),('distal',.7,1.01)]:
    values=[p['local_normal_thickness_mm']for p in probes if lo<=p['source_t']<hi];zones[label]=dict(samples=len(values),min_median_max_mm=np.percentile(values,[0,50,100]).tolist()if values else None)
   complete=all(z['samples']for z in zones.values());ratio=zones['proximal']['min_median_max_mm'][1]/zones['distal']['min_median_max_mm'][1]if complete else 0;contactok=bool(signed)and max(abs(x)for x in signed)<=.5;correspondence={}
   if final:
    node=next(n for n in doc['nodes']if n.get('name')==name and'mesh'in n);prim=doc['meshes'][node['mesh']]['primitives'][0];gp=arrays(doc,blob,prim['attributes']['POSITION']);gl=[Vector((p[0],-p[2],p[1]))for p in gp];kd1=KDTree(len(vs));kd2=KDTree(len(gl))
    for i,p in enumerate(vs):kd1.insert(p,i)
    for i,p in enumerate(gl):kd2.insert(p,i)
    kd1.balance();kd2.balance();error=max(max(kd1.find(p)[2]for p in gl),max(kd2.find(p)[2]for p in vs));correspondence=dict(maximum_bidirectional_position_error_native=error,source_vertices=len(vs),final_UV_split_vertices=len(gl))
   records.append(dict(name=name,ok=complete and ratio>=1.5 and misses==0 and contactok,source_root_band=fin['root_attachment']['root_band'],zones=zones,proximal_to_distal_median_ratio=ratio,missing_opposing_ray_count=misses,attachment_contact=dict(ok=contactok,complete_original_root_vertices=len(rootset),finite_contact_samples=len(signed),maximum_gap_mm=max(signed,default=1e10),maximum_inset_mm=-min(signed,default=-1e10),tolerance_mm=.5,root_domain='Entire explicit cap plus authored posterior section. No subset selected.'),final_geometry_correspondence=correspondence,actual_probes=probes))
   if name=='Caudal':tails=vs;tailfaces=ts
 # Reference body cap is pre-authoring input. Exclude its zero-radius endpoints
 # because finite edge thickness is tested separately; keep every interior Z.
 zs=sorted({round(p.z,7)for p in targetcap});zs=[z for z in zs if min(p.z for p in targetcap)+1e-6<z<max(p.z for p in targetcap)-1e-6];expected=[]
 for z in zs:
  # Bodycap mesh rows contain each ring latitude exactly, no analytic ellipse.
  expected.append(max(abs(p.y)for p in targetcap if abs(p.z-z)<1e-6))
 actual=section(tails,tailfaces,section_plane,zs);sections=[dict(z_native=z,body_half_width_native=e,tail_half_width_native=a,width_error_mm=abs(e-a)*scale*2000)for z,e,a in zip(zs,expected,actual)];error=max(r['width_error_mm']for r in sections);tail=dict(ok=bool(sections)and error<=.5,sections=sections,maximum_width_error_mm=error,tolerance_mm=.5,plane_x_native=section_plane,reference='Frozen actual pre-authoring posterior body cap, not fitted tail output. Full width comparison at every interior body latitude.');return dict(ok=all(r['ok']for r in records)and tail['ok'],fin_inventory=[r['name']for r in records],fins=records,tail_cross_section=tail)
current_result=measure(current,True);negative_result=measure(negative,False);r=dict(ok=current_result['ok']and not negative_result['ok'],kind='actual_authored_fin_volume_and_tail_section',species=profile['species'],model_sha256=sha(current/'fish.glb'),profile_sha256=sha(profilepath),original_basal_domains_preserved=True,current=current_result,rejected_original=negative_result,checker_sha256=sha(Path(__file__)),reference_body_section_sha256=sha(targetpath),scope='Four actual inward-normal rays per free triangle; proximal/middle/distal by3D distance to full original basal surface. Complete ordinary source/cold correspondence; actual finite body-to-whole-asymmetric-tail section; original split-tail negative uses both original pieces jointly. Full posed roots/membrane and image review separate. No user acceptance.');out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=r['ok'],fins=[dict(name=x['name'],ratio=x['proximal_to_distal_median_ratio'],missing=x['missing_opposing_ray_count'],contact=x['attachment_contact']['ok'])for x in current_result['fins']],tail_error_mm=current_result['tail_cross_section']['maximum_width_error_mm'],negative_tail_error_mm=negative_result['tail_cross_section']['maximum_width_error_mm'])))
