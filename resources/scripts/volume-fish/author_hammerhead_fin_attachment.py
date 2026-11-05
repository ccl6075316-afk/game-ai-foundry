"""Move pectoral attachments and remove the finite peduncle/caudal ledge.

Explicit artistic repair of these two candidates, not biological measurement.
The accepted R27 head/forebody and all original pixels remain the input.
"""
import bpy,bmesh,json,sys,shutil,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from source_snapshot import rig_action_snapshot

def section(T,x):
    points=[]
    for i,j in [(0,1),(1,2),(2,0)]:
        a,b=T[:,i],T[:,j];s=((a[:,0]-x)*(b[:,0]-x)<=0)&(abs(b[:,0]-a[:,0])>1e-10)
        points.extend(a[s]+(b[s]-a[s])*((x-a[s,0])/(b[s,0]-a[s,0]))[:,None])
    p=np.array(points);assert len(p)
    return np.array([p[:,2].min(),p[:,2].max(),abs(p[:,1]).max()])

def triangles(ob):
    ob.data.calc_loop_triangles();v=np.array([p.co[:]for p in ob.data.vertices])
    return v[np.array([t.vertices[:]for t in ob.data.loop_triangles])]

def main():
    base,out=map(lambda s:Path(s).resolve(),sys.argv[sys.argv.index('--')+1:]);src=base/'candidate-r27';assert not out.exists()
    L=4. if base.name=='great'else 3.;bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'))
    body=bpy.data.objects['Reference_head_body'];tail=bpy.data.objects['Caudal'];T=triangles(body);F=triangles(tail)
    auth=json.loads((src/'fin-authoring.json').read_text());before={o.name:np.array([v.co[:]for v in o.data.vertices])for o in bpy.context.scene.objects if o.type=='MESH'};actions=rig_action_snapshot();records=[]
    # Reallocate coplanar old chest support vertices, rather than exceeding the
    # smooth hammerhead's 4000-triangle budget when inserting its new full caps.
    protected=set()
    for r in auth['fins']:
        if r['name'].startswith('Pectoral'):continue
        for p in r['root_points_native']:
            d=np.linalg.norm(before[body.name]-p,axis=1);protected.update(np.where(d<3e-6)[0].tolist())
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table();remove=[]
    for v in bm.verts:
        if v.index in protected or len(v.link_faces)<3 or v.co.x>float(T[:,:,0].max())-.215*L:continue
        if not all(f.material_index==v.link_faces[0].material_index for f in v.link_faces):continue
        n=v.link_faces[0].normal
        if all(n.dot(f.normal)>1-1e-8 for f in v.link_faces):
            # Only a vertex strictly interior to its planar fan is removable.
            if all(e.is_manifold for e in v.link_edges):remove.append(v)
    bmesh.ops.dissolve_verts(bm,verts=remove,use_face_split=False,use_boundary_tear=False)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges)
    bm.to_mesh(body.data);bm.free();body.data.update()
    T=triangles(body);m=body.data;tree=BVHTree.FromPolygons([v.co.copy()for v in m.vertices],[list(t.vertices)for t in m.loop_triangles],all_triangles=True)
    for r in auth['fins']:
        if not r['name'].startswith('Pectoral'):continue
        ob=bpy.data.objects[r['name']];v=before[ob.name];ids=np.array(r['root_ids']);root=v[ids];height=[]
        target_fraction=json.loads((base/'blue-white-boundary.validation.json').read_text())['target_height_fraction']
        for p in root:
            lo,hi,_=section(T,p[0]);height.append(lo+target_fraction*(hi-lo)-p[2])
        dz=float(np.mean(height));new=v.copy();new[:,2]+=dz
        projected=[]
        sign=1 if root[:,1].mean()>0 else-1
        for i in ids:
            p=new[i];hit,_,_,_=tree.ray_cast(Vector((p[0],0,p[2])),Vector((0,sign,0)))
            assert hit is not None;projected.append(np.array(hit));new[i]=hit
        lateral=float(np.mean(np.array(projected)[:,1]-root[:,1]));free=np.ones(len(v),bool);free[ids]=False;new[free,1]+=lateral
        for p,q in zip(ob.data.vertices,new):p.co=q
        ob.data.update();ob.data.normals_split_custom_set([(0,0,0)]*len(ob.data.loops))
        r['root_points_native']=[list(ob.data.vertices[i].co)for i in r['root_ids']]
        records.append(dict(fin=ob.name,vertical_translation_m=dz,lateral_translation_m=lateral,target_root_height_fraction=target_fraction,complete_original_root_ids_retained=True,root_points_native=r['root_points_native']))
    # Actual finite side envelopes expose an upper V-notch behind the cap,
    # missed by a single-plane width check. Both adjoining meshes use ONE
    # continuous envelope on both sides of that plane, not two independent caps.
    rear=float(T[:,:,0].min());xf=rear+L*.025;xb=rear-L*.035;span=xf-xb
    start=section(T,xf);end=section(F,xb);eps=L*.0005
    ds=(section(T,xf+eps)-section(T,xf-eps))/(2*eps)
    de=(section(F,xb+eps)-section(F,xb-eps))/(2*eps)
    # Quintic endpoint values/slopes with zero endpoint curvature.
    A=np.array([[1,1,1],[3,4,5],[6,12,20]],float)
    coefficients=[]
    for k in range(3):
        a0=start[k];a1=-ds[k]*span;a2=0.;rhs=[end[k]-a0-a1,-de[k]*span-a1,0.]
        coefficients.append([a0,a1,a2,*np.linalg.solve(A,rhs)])
    def target(x):
        q=(xf-x)/span;return np.array([sum(c*q**i for i,c in enumerate(row))for row in coefficients])
    edits=[]
    for ob,original in [(body,T),(tail,F)]:
        changed=[]
        for v in ob.data.vertices:
            p=np.array(v.co);x=p[0]
            if not xb<x<xf:continue
            old=section(original,x);new=target(x);z=(p[2]-old[0])/max(old[1]-old[0],1e-8)
            q=p.copy();q[2]=new[0]+z*(new[1]-new[0]);q[1]*=new[2]/max(old[2],1e-8);v.co=q;changed.append(dict(index=v.index,before=p.tolist(),after=q.tolist()))
        ob.data.update();ob.data.normals_split_custom_set([(0,0,0)]*len(ob.data.loops));edits.append(dict(mesh=ob.name,changed_vertices=changed))
    for r in auth['fins']:
        ob=bpy.data.objects[r['name']];r['root_points_native']=[list(ob.data.vertices[i].co)for i in r['root_ids']]
        ob.data.calc_loop_triangles();r.update(vertices=len(ob.data.vertices),triangles=len(ob.data.loop_triangles))
    assert actions==rig_action_snapshot()
    for name in ['Eye_left','Eye_right','FirstDorsal','SecondDorsal','Pelvic_left','Pelvic_right','Anal']:
        assert np.array_equal(before[name],np.array([v.co[:]for v in bpy.data.objects[name].data.vertices]))
    for ob in [body,tail,*[bpy.data.objects['Pectoral_'+s]for s in ['left','right']]]:
        bm=bmesh.new();bm.from_mesh(ob.data);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume(signed=True)>0;bm.free()
    out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
    bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    auth['body_triangles']=len(body.data.loop_triangles);auth['whole_triangles']=sum(len(triangles(o))for o in bpy.context.scene.objects if o.type=='MESH')
    (out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');shutil.copyfile(src/'body-color-mask.npz',out/'body-color-mask.npz')
    (out/'attachment-authoring.validation.json').write_text(json.dumps(dict(ok=True,baseline_sha256=hashlib.sha256((src/'fish.glb').read_bytes()).hexdigest(),removed_redundant_planar_body_vertices=len(remove),pectoral=records,tail_window_native=[xb,xf],tail_envelope_coefficients=coefficients,geometry_edits=edits,all_source_pixels_unchanged=True,source='User requested actual chest relocation into blue flank and continuous tail connection; engineering interpolation, not biological measurement.',scope='New full-cap insertion and actual pose/visual checks required. Earlier R32 material-only repair rejected by user.',formal_acceptance=False),indent=2)+'\n')
    print('FIN_ATTACHMENT_SOURCE',base.name,auth['whole_triangles'],len(remove),records[0]['vertical_translation_m'])
if __name__=='__main__':main()
