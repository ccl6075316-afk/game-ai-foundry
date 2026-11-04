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
args=sys.argv[sys.argv.index('--')+1:];folder=Path(args[0]).resolve();output=Path(args[1]).resolve();assert not output.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();contract=json.loads(Path(args[2]).read_text()) if len(args)>2 else {};source_blend=Path(contract.get('source_blend',folder/'fish.blend'));model_path=Path(contract.get('model',folder/'fish.glb'));bpy.ops.wm.open_mainfile(filepath=str(source_blend));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';auth=json.loads((folder/'fin-authoring.json').read_text());doc,blob=read_glb(model_path);rows=[]
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
report=dict(ok=all(r['ok']for r in rows),kind='reference_shark_actual_closed_foil_volume',model_sha256=sha(model_path),editable_source_sha256=sha(source_blend),checker_sha256=sha(__file__),fins=rows,whole_triangles=auth['whole_triangles'],scope='Actual closed source shells, inward surface-normal rays on both main skins, ordinary final GLB position correspondence and deliberately planar zero-volume negatives. Complete cap domains retained. No measured biological tissue thickness claim; source outline/end-on/shape, tail attachment, full072/490 and visual review are separate.',formal_acceptance=False)
if len(args)>2:
    contract=json.loads(Path(args[2]).read_text());profile=json.loads(Path(contract['profile']).read_text());tail=json.loads(Path(contract['tail_section']).read_text());assert tail['current']['model_sha256']==report['model_sha256'];body=bpy.data.objects['Reference_head_body'];body.data.calc_loop_triangles();body_tree=BVHTree.FromPolygons([v.co.copy()for v in body.data.vertices],[tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True);current_rows=[]
    for fin,row in zip(auth['fins'],rows):
        ob=bpy.data.objects[fin['name']];roots=set(fin['root_ids']);contact=[ob.data.vertices[i].co.copy()for i in roots]
        for t in ob.data.loop_triangles:
            if all(i in roots for i in t.vertices):
                pts=[ob.data.vertices[i].co for i in t.vertices];contact.extend([sum(pts,Vector())/3]+[a.lerp(b,q)for a,b in zip(pts,pts[1:]+pts[:1])for q in[.25,.5,.75]])
        distances=[body_tree.find_nearest(p)[3]for p in contact];contact_ok=bool(distances)and max(distances)<=.0005;zones={name:row['zones'][old]for name,old in [('proximal','near_root'),('middle','middle'),('distal','tip')]};ratio=zones['proximal']['min_median_max_mm'][1]/zones['distal']['min_median_max_mm'][1];definition=next(f for f in profile['fins']if f['name']==fin['name'].removesuffix('_left').removesuffix('_right'));current_rows.append(dict(name=fin['name'],ok=bool(row['ok']and ratio>=1.5 and contact_ok),source_root_band=definition['root_attachment']['root_band'],zones=zones,proximal_to_distal_median_ratio=ratio,missing_opposing_ray_count=len(row['missing_opposing_rays']),attachment_contact=dict(ok=contact_ok,complete_original_root_vertices=len(roots),finite_contact_samples=len(contact),maximum_absolute_distance_mm=max(distances)*1000,tolerance_mm=.5),final_geometry_correspondence=dict(maximum_bidirectional_position_error_native=row['source_glb_bidirectional_position_error_m'])))
    current=dict(ok=all(r['ok']for r in current_rows)and tail['current']['ok'],fin_inventory=[r['name']for r in current_rows],fins=current_rows,tail_cross_section=tail['current']);report.update(kind='actual_authored_fin_volume_and_tail_section',species=profile['species'],profile_sha256=sha(contract['profile']),original_basal_domains_preserved=True,current=current,rejected_original=dict(ok=False,construction='Actual vertices projected to their least-variance plane; original topology retained and signed finite volume recomputed.',flattened_fins=[dict(name=r['name'],volume_m3=r['flattened_negative_volume_m3'],rejected=r['negative_rejected'])for r in rows],thin_tail_negative=tail['rejected_original']),tail_reference_report_sha256=sha(contract['tail_section']),ok=bool(current['ok']and all(r['negative_rejected']for r in rows)and tail['ok']))
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(ok=report['ok'],fins=[dict(name=r['name'],ok=r['ok'],thickness_mm=r['normal_thickness_min_median_max_mm'],missing=len(r['missing_opposing_rays']))for r in rows])));raise SystemExit(0 if report['ok']else 1)
