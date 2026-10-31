"""Blender: actual normal-ray fin thickness and finite tail-section negative.

Measures closed authored shells, and proves their positions match the final
packed GLB. Does not equate this test to visual/species/motion acceptance.
"""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
sys.path.insert(0,str(HERE))
from glb_io import read_glb,arrays
from closed_body_index140 import build as inside_index


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))


def measure(blend,cfg,profile,packed=None):
    bpy.ops.wm.open_mainfile(filepath=str(blend));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(0);scale=cfg['model_scale'];records=[]
    body=bpy.data.objects[cfg['body']];body.data.calc_loop_triangles();bv=[v.co.copy()for v in body.data.vertices];bt=[tuple(t.vertices)for t in body.data.loop_triangles];body_tree=BVHTree.FromPolygons(bv,bt,all_triangles=True);body_inside=inside_index(np.array(bv),np.array(bt))
    for fin in profile['fins']:
        for suffix in(['_left','_right']if fin['paired']else['']):
            name=fin['name']+suffix+'_mesh';ob=bpy.data.objects[name];mesh=ob.data;mesh.calc_loop_triangles();vertices=[v.co.copy()for v in mesh.vertices];triangles=[tuple(t.vertices)for t in mesh.loop_triangles];volume=sum(vertices[a].dot(vertices[b].cross(vertices[c]))for a,b,c in triangles)/6
            assert abs(volume)>1e-12,(name,'Collapsed shell');assert all(np.isfinite(q).all()for q in vertices)
            if volume<0:triangles=[tuple(reversed(t))for t in triangles]
            tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True);ts=[x.value for x in mesh.attributes['foundry_fin_source_t'].data];uv=mesh.uv_layers.active.data;probes=[];missing=[];attachment_rays=[];band=fin['root_attachment']['root_band']
            for tri in mesh.loop_triangles:
                xyz=[vertices[i]for i in tri.vertices];q=np.array([uv[i].uv[:]for i in tri.loops]);a,b=q[1]-q[0],q[2]-q[0]
                if abs(a[0]*b[1]-a[1]*b[0])<1e-10:continue # closing rim has no source area
                normal=(xyz[1]-xyz[0]).cross(xyz[2]-xyz[0]).normalized()*(1 if volume>0 else-1)
                for bary in[(1/3,1/3,1/3),(.8,.1,.1),(.1,.8,.1),(.1,.1,.8)]:
                    p=sum((v*w for v,w in zip(xyz,bary)),Vector());hit,_,_,distance=tree.ray_cast(p-normal*1e-7,-normal,.2)
                    t=sum(ts[i]*w for i,w in zip(tri.vertices,bary))
                    if t<=band+1e-7:
                        attachment_rays.append({'source_t':t,'normal_ray_mm':(distance+1e-7)*scale*1000 if hit is not None else None});continue
                    if hit is None:
                        missing.append({'face':tri.polygon_index,'source_t':[ts[i]for i in tri.vertices],'area_native':tri.area,'point_native':tuple(p),'normal':tuple(normal),'vertices_native':[tuple(v)for v in xyz]});continue
                    probes.append({'source_t':t,'local_normal_thickness_mm':(distance+1e-7)*scale*1000})
            zones={}
            for label,a,b in[('proximal',band+1e-7,.4),('middle',.4,.75),('distal',.75,1.01)]:
                v=[p['local_normal_thickness_mm']for p in probes if a<=p['source_t']<b];zones[label]={'samples':len(v),'min_median_max_mm':np.percentile(v,[0,50,100]).tolist()if v else None}
            complete=all(v['samples']for v in zones.values())
            ratio=zones['proximal']['min_median_max_mm'][1]/zones['distal']['min_median_max_mm'][1]if complete else 0.
            correspondence=None
            if packed is not None:
                points=packed[name];kd=KDTree(len(points))
                for i,q in enumerate(points):kd.insert(Vector(q),i)
                kd.balance();error=max(kd.find(v)[2]for v in vertices);back=KDTree(len(vertices))
                for i,v in enumerate(vertices):back.insert(v,i)
                back.balance();error=max(error,max(back.find(Vector(q))[2]for q in points));assert error<2e-6,(name,'Authored source and final GLB differ',error);correspondence={'maximum_bidirectional_position_error_native':error,'source_vertices':len(vertices),'final_UV_split_vertices':len(points)}
            # Closing skin buried in the body is not exposed membrane. Keep its
            # complete original domain and independently check EVERY root point
            # and finite all-root face against the ACTUAL closed body surface.
            roots={i for i,t in enumerate(ts)if t<=band+1e-7};contact_points=[vertices[i]for i in roots]
            for ids in triangles:
                if not all(i in roots for i in ids):continue
                pts=[vertices[i]for i in ids];contact_points+=[sum(pts,Vector())/3]+[p.lerp(q,f)for p,q in zip(pts,pts[1:]+pts[:1])for f in[.25,.5,.75]]
            signed=[]
            for point in contact_points:
                distance=body_tree.find_nearest(point)[3]*scale*1000;signed.append(-distance if body_inside(point)else distance)
            limit=cfg.get('attachment_contact_tolerance_mm',.5);contact={'ok':bool(signed)and max(abs(v)for v in signed)<=limit,'source_root_band':band,'complete_original_root_vertices':len(roots),'finite_contact_samples':len(signed),'maximum_gap_mm':max(0,max(signed,default=1e10)),'maximum_inset_mm':max(0,-min(signed,default=-1e10)),'tolerance_mm':limit,'scope':'Complete original root domain, actual closed body, finite static vertex/edge/face samples. Full posed072/490 remain required; no root selection/collar change.'}
            records.append({'name':name,'ok':complete and ratio>=1.5 and not missing and contact['ok'],'zones':zones,'source_root_band':band,'proximal_to_distal_median_ratio':ratio,'missing_opposing_ray_count':len(missing),'missing_opposing_rays':missing,'attachment_rays_not_exposed_membrane':attachment_rays,'attachment_contact':contact,'final_geometry_correspondence':correspondence,'actual_probes':probes})
    body=bpy.data.objects[cfg['body']];rear=min(v.co.x for v in body.data.vertices);cap=[v.co for v in body.data.vertices if abs(v.co.x-rear)<1e-6];tail=bpy.data.objects['Caudal_mesh'];f=next(f for f in profile['fins']if f['name']=='Caudal');root=[v.co for v,t in zip(tail.data.vertices,tail.data.attributes['foundry_fin_source_t'].data)if t.value<=f['root_attachment']['root_band']+1e-7]
    heights=sorted(set(round(v.z,7)for v in root));widths=[max(abs(v.y)for v in root if abs(v.z-z)<1e-6)for z in heights];sections=[]
    for z in sorted(set(round(v.z,7)for v in cap)):
        expected=2*max(abs(v.y)for v in cap if abs(v.z-z)<1e-6);observed=2*float(np.interp(z,heights,widths));sections.append({'z_native':z,'body_width_mm':expected*scale*1000,'tail_root_width_mm':observed*scale*1000,'difference_mm':abs(expected-observed)*scale*1000})
    error=max(r['difference_mm']for r in sections);tolerance=cfg.get('tail_cross_section_tolerance_mm',.4)
    return {'ok':all(r['ok']for r in records)and error<=tolerance,'blend_sha256':sha(blend),'fin_inventory':[r['name']for r in records],'fins':records,'tail_cross_section':{'ok':error<=tolerance,'maximum_width_error_mm':error,'tolerance_mm':tolerance,'sections':sections,'complete_basal_band_retained':True},'scope':'Actual source normal rays, finite posterior section and optional final GLB geometry correspondence. End-on/full outline/camber images and full posed roots/membranes remain separate.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in['blend','config','output']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--source-only',action='store_true',help='Fast source geometry diagnostic, never a final volume/SOP report')
    p.add_argument('--model',type=Path);p.add_argument('--rejected-blend',type=Path)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=read(a.config);ROOT=HERE.parents[2];profile=read(ROOT/cfg['profile']);baseline=read(ROOT/cfg['baseline_profile']);original={f['name']:f for f in baseline['fins']};assert {f['name']for f in profile['fins']}==set(original)
    assert all(f['source_baseline']==original[f['name']]['source_baseline']and f['root_attachment']['root_band']==original[f['name']]['root_attachment']['root_band']for f in profile['fins']),'Do not shrink or enlarge the original anatomical basal domain to alter thickness/contact results'
    if a.source_only:
        assert not a.model and not a.rejected_blend
        current=measure(a.blend,cfg,profile);report={'ok':current['ok'],'kind':'diagnostic_source_fin_volume_only','species':profile['species'],'current':current,'config_sha256':sha(a.config),'checker_sha256':sha(__file__),'formal_acceptance':False,'scope':'Fast authored-source geometry only, before color baking. No finalGLB correspondence or rejected-model proof; cannot satisfy the SOP final volume criterion.'}
        assert not a.output.exists();a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':report['ok'],'failed_fins':[{k:r[k]for k in['name','proximal_to_distal_median_ratio','missing_opposing_ray_count']}for r in current['fins']if not r['ok']]}));raise SystemExit(0 if report['ok']else 1)
    assert a.model and a.rejected_blend,'Final volume mode needs final packed GLB and rejected original source'
    d,b=read_glb(a.model);pr=d['meshes'][0]['primitives'][0];positions=arrays(d,b,pr['attributes']['POSITION']);packed={}
    for part in d['extras']['geometry_parts']:
        if part['role']!='fin':continue
        v=positions[part['vertex_start']:part['vertex_start']+part['vertex_count']];packed.setdefault(part['logical_name'],[]).extend(np.column_stack([v[:,0],-v[:,2],v[:,1]]).tolist())
    current=measure(a.blend,cfg,profile,packed);negative=measure(a.rejected_blend,cfg,profile);report={'ok':current['ok']and not negative['ok'],'kind':'actual_authored_fin_volume_and_tail_section','species':profile['species'],'model_sha256':sha(a.model),'profile_sha256':sha(ROOT/cfg['profile']),'baseline_profile_sha256':sha(ROOT/cfg['baseline_profile']),'original_basal_domains_preserved':True,'config_sha256':sha(a.config),'checker_sha256':sha(__file__),'current':current,'rejected_original':negative,'scope':'Exposed proximal/middle/distal normal thickness, complete original attachment-band signed contact, finite tail section and constant-shell/flat-tail negative under same thresholds. Full posed roots/whole membrane and actual visuals remain mandatory; no user acceptance.'};assert not a.output.exists();a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':report['ok'],'current_ratios':{r['name']:r['proximal_to_distal_median_ratio']for r in current['fins']},'tail_width_error_mm':current['tail_cross_section']['maximum_width_error_mm'],'negative_tail_error_mm':negative['tail_cross_section']['maximum_width_error_mm']}));raise SystemExit(0 if report['ok']else 1)
