"""Own-reference head, curved finite fins and continuous native skin repair.

Author-time only; retains the native rig/actions and complete basal selections.
"""
import bpy,bmesh,json,sys,math,hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def smooth(a,b,x):t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def distance_poly(q,points):
    best=1e9
    for a,b in zip(points,points[1:]):
        d=b-a;t=max(0,min(1,(q-a).dot(d)/max(d.length_squared,1e-18)));best=min(best,(q-a-d*t).length)
    return best
def main():
    args=sys.argv[sys.argv.index('--')+1:];cfg=Path(args[0]).resolve();charts=Path(args[1]).resolve();out=Path(args[2]).resolve();c=read(cfg);src=ROOT/c['baseline'];assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists();out.mkdir()
    bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Closed_body'];rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');assert len(rig.data.bones)==18
    legacy=read(ROOT/c['legacy_profile']);sec=np.array(legacy['body']['sections']);sec[-2,3]=.032;sec[-1,3]=.015;aspect=1/legacy['source_aspect_ratio']
    measurements=c['head_photo_measurements'];us=np.array([r['u']for r in measurements]);ws=np.array([r['half_width_native']for r in measurements])
    def width(u):return math.sqrt(max(0,float(np.interp(u,us,ws*ws))))
    def theta(p):
        u=p.x+.5;top,bottom,half=[float(np.interp(u,sec[:,0],sec[:,i]))for i in [1,2,3]];zc=(.5-(top+bottom)/2)*aspect;rh=(bottom-top)/2*aspect
        return math.atan2(p.y/max(half,1e-9),(p.z-zc)/max(rh,1e-9))%math.tau
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();uv=bm.loops.layers.uv.active;tl=bm.verts.layers.float.new('review_theta');oral=bm.faces.layers.int.new('review_oral')
    original_body=[v.co.copy()for v in bm.verts];head_changed=0
    for v in bm.verts:
        v[tl]=theta(v.co);u=v.co.x+.5
        if us[0]<=u:
            old=float(np.interp(u,sec[:,0],sec[:,3]));target=width(min(u,c['front_cap_ring_u']));v.co.y*=target/max(old,1e-10);head_changed+=1
    for f in bm.faces:f[oral]=int(f.material_index==2)
    xmax=max(v.co.x for v in bm.verts);cap=[f for f in bm.faces if all(abs(v.co.x-xmax)<1e-7 for v in f.verts)];ring=sorted({v for f in cap for v in f.verts},key=lambda v:v[tl]);assert len(ring)>=12 and cap
    old_center=sum((v.co for v in ring),Vector())/len(ring);old_u=xmax+.5;ring_u=c['front_cap_ring_u'];top,bottom=[float(np.interp(ring_u,sec[:,0],sec[:,i]))for i in [1,2]];new_center_z=(.5-(top+bottom)/2)*aspect
    old_height=(float(np.interp(old_u,sec[:,0],sec[:,2]))-float(np.interp(old_u,sec[:,0],sec[:,1])))*aspect/2;new_height=(bottom-top)*aspect/2
    for v in ring:v.co.x=ring_u-.5;v.co.z=new_center_z+(v.co.z-old_center.z)*new_height/max(old_height,1e-9)
    bmesh.ops.delete(bm,geom=cap,context='FACES_ONLY')
    bmesh.ops.delete(bm,geom=[e for e in bm.edges if not e.link_faces],context='EDGES')
    deform=bm.verts.layers.deform.active;previous=ring
    for fraction in [.5,.8660254]:
        u=ring_u+(c['front_cap_pole_u']-ring_u)*fraction;ratio=width(u)/max(width(ring_u),1e-9);next_ring=[]
        for r in ring:
            v=bm.verts.new((u-.5,r.co.y*ratio,new_center_z+(r.co.z-new_center_z)*ratio));v[tl]=r[tl]
            if deform:
                for group,gain in r[deform].items():v[deform][group]=gain
            next_ring.append(v)
        for i in range(len(ring)):f=bm.faces.new((previous[i],previous[(i+1)%len(ring)],next_ring[(i+1)%len(ring)],next_ring[i]));f[oral]=0
        previous=next_ring
    pole=bm.verts.new((c['front_cap_pole_u']-.5,0,new_center_z));pole[tl]=0
    if deform:
        for group,gain in ring[0][deform].items():pole[deform][group]=gain
    for i in range(len(ring)):f=bm.faces.new((previous[i],previous[(i+1)%len(ring)],pole));f[oral]=0
    # The former oral-ring construction skipped two actual reference stations
    # on the upper/lateral snout. Add finite support there; a sparse chord must
    # not silently replace the frozen photographed transverse envelope.
    for u in c.get('head_support_planes_u',[]):
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=Vector((u-.5,0,0)),plane_no=Vector((1,0,0)),clear_inner=False,clear_outer=False)
        plane=[v for v in bm.verts if abs(v.co.x-(u-.5))<2e-7];actual=max(abs(v.co.y)for v in plane);desired=width(u)
        top,bottom=[float(np.interp(u,sec[:,0],sec[:,i]))for i in [1,2]];zc=(.5-(top+bottom)/2)*aspect;rh=(bottom-top)/2*aspect
        for v in plane:
            v.co.y*=desired/max(actual,1e-12);v[tl]=math.atan2(v.co.y/max(desired,1e-12),(v.co.z-zc)/max(rh,1e-12))%math.tau
    # One continuous angular chart; no per-triangle directional material switch.
    def material(name,path):
        m=bpy.data.materials.new(name);m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=1;bs.inputs['Specular IOR Level'].default_value=0
        im=bpy.data.images.load(str(path),check_existing=False);im.pack();tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;tex.interpolation='Closest';tex.extension='EXTEND';m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.35;return m
    skin=material('Own native continuous shark skin / opaque',charts/'body-angular.png');cavity=body.data.materials[2];body.data.materials.clear();body.data.materials.append(skin);body.data.materials.append(cavity)
    for f in bm.faces:
        f.material_index=1 if f[oral] else 0;ts=[v[tl]/math.tau for v in f.verts];wrap=max(ts)-min(ts)>.5
        for loop in f.loops:
            t=loop.vert[tl]/math.tau
            if wrap and t<.5:t+=1
            if loop.vert==pole:t=sum((v[tl]/math.tau for v in f.verts if v!=pole))/2
            loop[uv].uv=(loop.vert.co.x+.5,1-t)
        f.smooth=not bool(f[oral])
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(len(e.link_faces)==2 for e in bm.edges),'Body closure';bm.to_mesh(body.data);bm.free();body.data.update();body.data.calc_loop_triangles()
    bodytree=BVHTree.FromPolygons([v.co for v in body.data.vertices],[t.vertices for t in body.data.loop_triangles],all_triangles=True)
    ray=Vector((.231,.371,.899)).normalized()
    def signed(p):
        h,n,fi,dist=bodytree.find_nearest(p);rh,rn,_,_=bodytree.ray_cast(p,ray);return (-dist if rh is not None and rn.dot(ray)>0 else dist),h,n
    layout=read(ROOT/'resources/volume-fish/blacktip-fin-cages-20261101.json');old=read(src/'fin-authoring.json');finmat=material('Native shark fins / separate anatomical undersides',charts/'fin-two-sided.png');records=[]
    for oldrow in old['fins']:
        name=oldrow['name'];ob=bpy.data.objects[name];f=next(f for f in layout['rows']if name==f['name'] or name.startswith(f['name']+'_'));paired=f['paired'];sign=-1 if name.endswith('_left')else 1;normal=Vector((0,sign*.35,.93675)).normalized()if paired else Vector((0,1,0));outward=Vector((0,sign,0))if paired else Vector((0,0,-1 if name in ['Anal','CaudalLower']else 1))
        bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table();uv=bm.loops.layers.uv.active;root=bm.verts.layers.int.new('review_root')
        for v in bm.verts:v[root]=int(v.index in oldrow['root_ids'])
        def key(v):return tuple(round(float(k),7)for k in v.link_loops[0][uv].uv)
        def point(v):q=v.link_loops[0][uv].uv;return Vector((q.x,1-q.y))
        # Paired splits preserve native source parameters and all basal vertices.
        candidates=defaultdict(list)
        for e in bm.edges:
            if any(v[root]for v in e.verts)or e.calc_length()<.015:continue
            ka,kb=[key(v)for v in e.verts]
            if ka==kb:continue
            candidates[tuple(sorted((ka,kb)))].append(e)
        selected=sorted(candidates,key=lambda k:max(e.calc_length()for e in candidates[k]),reverse=True)[:c['fin_edge_pair_splits']]
        edges=[e for k in selected for e in candidates[k]]
        if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=False)
        bm.verts.ensure_lookup_table();bm.verts.index_update();groups=defaultdict(list)
        for v in bm.verts:groups[key(v)].append(v)
        mids={k:sum((v.co for v in g),Vector())/len(g)for k,g in groups.items()};contour=[Vector(q)for q in f['contour']];base=[q for q,g in zip(contour,f['root'])if g];span=max(distance_poly(q,base)for q in contour)
        maximum_curve=0.;changed_groups=0;minimum_thickness=1e9
        for k,g in groups.items():
            if any(v[root]for v in g):
                for v in g:
                    if v[root]:_,hit,nb=signed(v.co);v.co=hit+nb*c['root_offset_native']
                continue
            if len(g)<2:continue
            q=point(g[0]);ordered=sorted(g,key=lambda v:v.co.dot(normal));oldpositions=[v.co.copy()for v in ordered];mid=(ordered[0].co+ordered[-1].co)*.5;original_mid=mid.copy();oldhalf=abs((ordered[-1].co-ordered[0].co).dot(normal))*.5
            coefficients=[max(-1,min(1,(v.co-mid).dot(normal)/max(oldhalf,1e-10)))for v in ordered]
            # Round source corners, retaining the full, independently defined
            # basal band. Original black/white tip pixels stay on that tissue.
            ci=next((i for i,p in enumerate(contour)if(q-p).length<2e-6),None)
            if ci is not None and not f['root'][ci] and not f['root'][(ci-1)%len(contour)] and not f['root'][(ci+1)%len(contour)]:
                keys=[(round(p.x,7),round(1-p.y,7))for p in [contour[(ci-1)%len(contour)],contour[(ci+1)%len(contour)]]]
                if all(z in mids for z in keys):
                    delta=(mids[keys[0]]+mids[keys[1]]-2*mid)*c['fin_curve_weight'];limit=c['fin_curve_max_displacement_native']
                    if delta.length>limit:delta*=limit/delta.length
                    mid+=delta;maximum_curve=max(maximum_curve,delta.length)
            sd=distance_poly(q,base);s=min(1,sd/max(span,1e-9));cuts=[]
            for a,b in zip(contour,contour[1:]+contour[:1]):
                if min(a.y,b.y)-1e-8<=q.y<=max(a.y,b.y)+1e-8 and abs(a.y-b.y)>1e-9:cuts.append(a.x+(q.y-a.y)/(b.y-a.y)*(b.x-a.x))
            lo,hi=(min(cuts),max(cuts))if len(cuts)>1 else(q.x-.0001,q.x+.0001);t=max(0,min(1,(hi-q.x)/max(hi-lo,1e-8)));shape=max(0,(.2969*math.sqrt(t)-.126*t-.3516*t*t+.2843*t**3-.1036*t**4)/.1001)
            tr,tm,te=c['fin_full_thickness_native'][f['name']];full=te+(float(np.interp(s,[0,.55,1],[tr,tm,te]))-te)*shape
            rootdistance=min((mid-mids[z]).length for z,gg in groups.items()if all(v[root]for v in gg));blend=smooth(.012,.035,rootdistance);extra=max(0,full*.5-oldhalf)*blend;minimum_thickness=min(minimum_thickness,2*(oldhalf+extra))
            # Preserve the accepted curved attachment fillet as a complete
            # field. Strengthen free tissue smoothly; independently clamping
            # its two layers or translating sparse near-root pairs folds faces.
            delta=mid-original_mid
            for attempt in range(16):
                new=[p+delta+normal*extra*gain for p,gain in zip(oldpositions,coefficients)]
                if all(signed(p)[0]>=.00035 for p in new):break
                extra*=.5;delta*=.5
            for v,p in zip(ordered,new):v.co=p
            changed_groups+=1
        ob.data.materials.clear();ob.data.materials.append(finmat)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces))
        for face in bm.faces:
            lower=paired and face.normal.dot(normal)<-.15;face.material_index=0;face.smooth=True
            for loop in face.loops:
                q=loop[uv].uv.copy();loop[uv].uv=(q.x*.5+(.5 if lower else 0),q.y)
        assert all(len(e.link_faces)==2 for e in bm.edges),name+' closure'
        rids=[v.index for v in bm.verts if v[root]];points=[list(bm.verts[i].co)for i in rids];bm.to_mesh(ob.data);bm.free();ob.data.calc_loop_triangles()
        records.append(dict(oldrow,triangles=len(ob.data.loop_triangles),vertices=len(ob.data.vertices),root_ids=rids,root_points_native=points,review_changed_free_groups=changed_groups,source_upper_pixels_retained_in_atlas=True,finite_lower_skin_is_distinct=paired,maximum_corner_rounding_native=maximum_curve,minimum_authored_halfpair_full_thickness_native=minimum_thickness,root_offset_native=c['root_offset_native']))
    total=len(body.data.loop_triangles)+sum(r['triangles']for r in records);assert total<=c['triangle_budget']['hard'],total
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    (out/'fin-authoring.json').write_text(json.dumps({'fins':records,'body_triangles':len(body.data.loop_triangles),'whole_triangles':total,'operator_visual_acceptance':False},indent=2)+'\n',encoding='utf-8')
    result={'ok':True,'kind':'blacktip_current_user_findings_author_repair','config_sha256':sha(cfg),'baseline_model_sha256':sha(src/'fish.glb'),'baseline_blend_sha256':sha(src/'fish.blend'),'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'triangles':total,'bones':len(rig.data.bones),'body_triangles':len(body.data.loop_triangles),'head_vertices_changed':head_changed,'head_basis':c['head_photo'],'front_cap_replaces_old_flat_faces':len(cap),'full_original_root_counts_preserved':{r['name']:len(r['root_ids'])for r in records},'formal_acceptance':False,'scope':'Author candidate only; fresh cold read, local appearance, full roots/membrane/body/action checks remain required.'};(out/'repair.validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
