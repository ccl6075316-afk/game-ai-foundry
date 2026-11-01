"""Local full-basal/free-surface tests on static reference-shark fins.

Not a replacement for posed177/490. No root subset or empty inventory allowed.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args=sys.argv[sys.argv.index('--')+1:];src=Path(args[0]).resolve();out=Path(args[1]).resolve();assert not out.exists();bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));auth=json.loads((src/'fin-authoring.json').read_text());body=bpy.data.objects['Reference_head_body'];body.data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co.copy()for v in body.data.vertices],[tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True);rays=[Vector(v).normalized()for v in[(.231,.371,.899),(-.571,.781,.23),(.43,-.12,.895)]]
def signed(p):
    h,n,fi,d=tree.find_nearest(p);votes=[]
    for ray in rays:
        rh,rn,_,_=tree.ray_cast(p+ray*1e-9,ray);votes.append(rh is not None and rn.dot(ray)>0)
    return -d if sum(votes)>=2 else d
rows=[]
for row in auth['fins']:
    ob=bpy.data.objects[row['name']];me=ob.data;me.calc_loop_triangles();vs=[v.co.copy()for v in me.vertices];root=set(row['root_ids']);assert root and len(root)==len(row['root_points_native']);assert max((vs[i]-Vector(p)).length for i,p in zip(sorted(root),row['root_points_native']))<1e-7
    rt=[tuple(t.vertices)for t in me.loop_triangles if all(i in root for i in t.vertices)];assert rt,(row['name'],'missing full basal cap');rtre=BVHTree.FromPolygons(vs,rt,all_triangles=True);basal=[];free=[];faults=[]
    for tri in me.loop_triangles:
        pts=[vs[i]for i in tri.vertices];points=pts+[sum(pts,Vector())/3]+[a.lerp(b,t)for a,b in zip(pts,pts[1:]+pts[:1])for t in[.25,.5,.75]]
        for p in points:
            d=signed(p);rd=rtre.find_nearest(p)[3]
            if all(i in root for i in tri.vertices):basal.append(d)
            elif rd<=.00030 and d>=-.00030:continue
            else:
                free.append(d)
                if d<-.000006 and len(faults)<8:faults.append(dict(triangle=list(tri.vertices),point=list(p),signed_distance_m=d,root_distance_m=rd))
    bm=bmesh.new();bm.from_mesh(me);closed=all(len(e.link_faces)==2 for e in bm.edges);bm.free();contact_ok=bool(basal)and min(basal)>=-.0005 and max(basal)<=.0005;free_ok=bool(free)and min(free)>=-.000006
    rows.append(dict(name=row['name'],ok=closed and contact_ok and free_ok,triangles=len(me.loop_triangles),closed=closed,full_basal_vertices=len(root),full_basal_triangles=len(rt),basal_samples=len(basal),maximum_gap_m=max(basal),maximum_inset_m=-min(basal),basal_ok=contact_ok,free_samples=len(free),free_maximum_inset_m=max(0,-min(free)),free_ok=free_ok,faults=faults))
expected=['FirstDorsal','SecondDorsal','Pectoral_left','Pectoral_right','Pelvic_left','Pelvic_right','Anal','Caudal'];assert sorted(r['name']for r in rows)==sorted(expected);r=dict(ok=all(row['ok']for row in rows),kind='local_static_shark_fin_complete_basal_and_surface_trial',model_sha256=hashlib.sha256((src/'fish.glb').read_bytes()).hexdigest(),fins=rows,limits=dict(basal_gap_m=.0005,basal_inset_m=.0005,free_inset_m=.000006,declared_root_seam_width_m=.00030),scope='All8 actual static meshes and their frozen entire basal domains. Closed-body majority-ray classification and vertices/edges/face probes. Not skinning, native loop, Godot actions or177/490; no complete-fish acceptance.',formal_acceptance=False);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=r['ok'],fins=[{k:v for k,v in x.items()if k not in['faults']}for x in rows])));sys.exit(0 if r['ok']else 1)
