"""Actual ordinary-source closed-foil rays, GLB correspondence and flat negative.

Reference cap domains remain complete. Measured tissue representation is not
biological thickness evidence; source/shape/motion reviews remain separate.
"""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb,arrays
args=sys.argv[sys.argv.index('--')+1:];folder=Path(args[0]).resolve();output=Path(args[1]).resolve();assert not output.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(folder/'fish.blend'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';auth=json.loads((folder/'fin-authoring.json').read_text());doc,blob=read_glb(folder/'fish.glb');rows=[]
for fin in auth['fins']:
    ob=bpy.data.objects[fin['name']];mesh=ob.data;mesh.calc_loop_triangles();vertices=[v.co.copy()for v in mesh.vertices];triangles=[tuple(t.vertices)for t in mesh.loop_triangles];roots=set(fin['root_ids']);bm=bmesh.new();bm.from_mesh(mesh);closed=all(e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=True);bm.free();assert closed and volume>1e-12
    tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True);probes=[];missing=[];domain=mesh.attributes['source_span_t'];sx=mesh.attributes['source_mask_x_px'];sy=mesh.attributes['source_mask_y_px'];layer=mesh.attributes['source_layer_sign']
    for triangle in mesh.loop_triangles:
        ids=triangle.vertices
        if all(i in roots for i in ids):continue
        xy=np.array([[sx.data[i].value,sy.data[i].value]for i in ids]);a,b=xy[1]-xy[0],xy[2]-xy[0]
        if abs(a[0]*b[1]-a[1]*b[0])<.25:continue
        if max(layer.data[i].value for i in ids)-min(layer.data[i].value for i in ids)>.01:continue
        xyz=[vertices[i]for i in ids];normal=(xyz[1]-xyz[0]).cross(xyz[2]-xyz[0]).normalized()
        for gains in[(1/3,)*3,(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
            point=sum((v*w for v,w in zip(xyz,gains)),Vector());hit,other,_,distance=tree.ray_cast(point-normal*1e-7,-normal,.3)
            if hit is None:missing.append(dict(face=triangle.polygon_index,point=list(point)));continue
            probes.append(dict(source_span=float(sum(domain.data[i].value*w for i,w in zip(ids,gains))),normal_ray_mm=(distance+1e-7)*1000,opposing_normal_dot=normal.dot(other)))
    assert probes,'Empty actual free-skin thickness probes'
    values=np.array([r['normal_ray_mm']for r in probes]);zones={}
    for label,lo,hi in [('near_root',0,.4),('middle',.4,.75),('tip',.75,1.01)]:
        q=[r['normal_ray_mm']for r in probes if lo<=r['source_span']<hi];zones[label]=dict(samples=len(q),min_median_max_mm=np.percentile(q,[0,50,100]).tolist()if q else None)
    node=next(n for n in doc['nodes']if n.get('name')==fin['name']);points=np.concatenate([arrays(doc,blob,p['attributes']['POSITION'])for p in doc['meshes'][node['mesh']]['primitives']]);points=points[:,[0,2,1]];points[:,1]*=-1;kd=KDTree(len(points))
    for i,q in enumerate(points):kd.insert(Vector(q),i)
    kd.balance();error=max(kd.find(v)[2]for v in vertices);back=KDTree(len(vertices))
    for i,v in enumerate(vertices):back.insert(v,i)
    back.balance();error=max(error,max(back.find(Vector(q))[2]for q in points))
    q=np.array([tuple(v)for v in vertices],dtype=np.float64);center=q.mean(0);_,_,vh=np.linalg.svd(q-center,full_matrices=False);flat=q-((q-center)@vh[-1])[:,None]*vh[-1];negative_volume=abs(sum(np.dot(flat[a],np.cross(flat[b],flat[c]))for a,b,c in triangles)/6)
    rows.append(dict(name=fin['name'],ok=bool(closed and volume>1e-12 and not missing and values.min()>0 and error<2e-6 and negative_volume<1e-12),triangles=len(triangles),closed=True,volume_m3=volume,source_glb_bidirectional_position_error_m=error,complete_basal_vertices=len(roots),probes=len(probes),normal_thickness_min_median_max_mm=np.percentile(values,[0,50,100]).tolist(),zones=zones,missing_opposing_rays=missing,flattened_negative_volume_m3=negative_volume,negative_rejected=bool(negative_volume<1e-12)))
report=dict(ok=all(r['ok']for r in rows),kind='reference_shark_actual_closed_foil_volume',model_sha256=sha(folder/'fish.glb'),editable_source_sha256=sha(folder/'fish.blend'),checker_sha256=sha(__file__),fins=rows,whole_triangles=auth['whole_triangles'],scope='Actual closed source shells, inward surface-normal rays on both main skins, ordinary final GLB position correspondence and deliberately planar zero-volume negatives. Complete cap domains retained. No measured biological tissue thickness claim; source outline/end-on/shape, tail attachment, full072/490 and visual review are separate.',formal_acceptance=False);output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(ok=report['ok'],fins=[dict(name=r['name'],ok=r['ok'],thickness_mm=r['normal_thickness_min_median_max_mm'],missing=len(r['missing_opposing_rays']))for r in rows])));raise SystemExit(0 if report['ok']else 1)
