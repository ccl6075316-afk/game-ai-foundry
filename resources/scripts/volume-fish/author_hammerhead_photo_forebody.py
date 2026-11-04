"""Photo-constrained continuous forebody section edit, no rigid head drop.

Source-art meshes/UV/skin/action curves retained. Photos constrain appearance,
not calibrated anatomy; input configuration declares the engineering envelope.
"""
import bpy,bmesh,json,hashlib,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable.source_snapshot import rig_action_snapshot

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def kdtree(points):
    kd=KDTree(len(points))
    for i,p in enumerate(points):kd.insert(Vector(p),i)
    kd.balance();return kd
def main():
    cp,out=map(lambda p:Path(p).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert not out.exists()and'/experiments/'in str(out)
    for p,h in c['inputs'].items():assert sha(p)==h,p
    src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);actions=rig_action_snapshot()['actions']
    body=bpy.data.objects[c['body']];body.data.update();body.data.calc_loop_triangles();old=np.array([v.co[:]for v in body.data.vertices]);faces=np.array([t.vertices[:]for t in body.data.loop_triangles]);tri=old[faces];tree=BVHTree.FromPolygons([Vector(p)for p in old],faces.tolist(),all_triangles=True)
    oral_ids=sorted({i for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'for i in f.vertices});oral=kdtree(old[oral_ids]);eye_ids=sorted({i for f in body.data.polygons if body.data.materials[f.material_index].name.startswith('Own original side eye pixels')for i in f.vertices});assert oral_ids and eye_ids
    preserved_normals={li:tuple(body.data.corner_normals[li].vector)for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'or body.data.materials[f.material_index].name.startswith('Own original side eye pixels')for li in f.loop_indices}
    L,nose=c['length_m'],c['nose_x_m'];top=np.array(c['envelope']['top_dense']);bot=np.array(c['envelope']['bottom_dense']);end=c['envelope']['end_p'];cache={}
    def bounds(x):
        if x not in cache:
            a=tri;b=np.roll(tri,-1,axis=1);k=(a[:,:,0]-x)*(b[:,:,0]-x)<0
            q=a[k]+((x-a[:,:,0][k])/(b[:,:,0][k]-a[:,:,0][k]))[:,None]*(b[k]-a[k]);q=np.concatenate([q,a[abs(a[:,:,0]-x)<1e-7]])
            cache[x]=(float(q[:,2].min()),float(q[:,2].max()))if len(q)else None
        return cache[x]
    def envelope_delta(point):
        x,y,z=point;p=(nose-x)/L
        if p<-.00001 or p>=end:return 0.
        limits=bounds(x)
        if limits is None:return 0.
        lo,hi=limits;t=max(0.,min(1.,(z-lo)/(hi-lo)))if hi-lo>1e-9 else .5
        return float(np.interp(p,bot[:,0],bot[:,1])*(1-t)+np.interp(p,top[:,0],top[:,1])*t-(lo+(hi-lo)*t))
    eyes=[]
    for side in [-1,1]:
        points=old[[i for i in eye_ids if old[i,1]*side>0]];assert len(points)
        center=(points.min(0)+points.max(0))/2;eyes.append(dict(side=side,tree=kdtree(points),delta=envelope_delta(center),center=center.tolist()))
    def mapping(point):
        delta=envelope_delta(point)
        delta*=smooth(*c['oral_guard_m'],oral.find(Vector(point))[2])
        side=eyes[1 if point[1]>=0 else 0];w=smooth(*c['eye_guard_m'],side['tree'].find(Vector(point))[2]);delta=side['delta']*(1-w)+delta*w
        return Vector((point[0],point[1],point[2]+delta))
    for v in body.data.vertices:v.co=mapping(v.co)
    # Exact rigid domains, including shared boundary vertices.
    for i in oral_ids:body.data.vertices[i].co=Vector(old[i])
    body.data.update();mapped=np.array([v.co[:]for v in body.data.vertices]);fins=[]
    for ob in [o for o in bpy.context.scene.objects if o.type=='MESH'and o!=body]:
        before=np.array([v.co[:]for v in ob.data.vertices]);correction=0.
        for v in ob.data.vertices:
            p=v.co.copy();q=mapping(p);h,n,fi,d=tree.find_nearest(p)
            if h is not None and d<c['fin_support_m'][1]:
                ids=faces[fi];actual=barycentric_transform(h,*[Vector(old[i])for i in ids],*[Vector(mapped[i])for i in ids]);corr=(actual-mapping(h))*(1-smooth(*c['fin_support_m'],d));q+=corr;correction=max(correction,corr.length)
            v.co=q
        ob.data.update();fins.append(dict(name=ob.name,maximum_delta_m=float(np.linalg.norm(np.array([v.co[:]for v in ob.data.vertices])-before,axis=1).max()),maximum_root_support_correction_m=correction))
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT');pivots=[]
    for bone in rig.data.edit_bones:
        if bone.name=='root':continue
        delta=mapping(bone.head)-bone.head;bone.head+=delta;bone.tail+=delta;pivots.append(dict(bone=bone.name,delta=list(delta)))
    bpy.ops.object.mode_set(mode='OBJECT');assert rig_action_snapshot()['actions']==actions
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];count=0
    for ob in meshes:
        bm=bmesh.new();bm.from_mesh(ob.data);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free();ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops));ob.data.calc_loop_triangles();count+=len(ob.data.loop_triangles)
    body.data.update();normals=[tuple(n.vector)for n in body.data.corner_normals]
    for li,n in preserved_normals.items():normals[li]=n
    body.data.normals_split_custom_set(normals);body.data.update();assert count==c['expected_triangles']
    rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
    for ob in meshes+[rig]:ob.select_set(True)
    bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    fa=json.loads((src/'fin-authoring.json').read_text())
    for f in fa['fins']:f['root_points_native']=[list(bpy.data.objects[f['name']].data.vertices[i].co)for i in f['root_ids']]
    fa['photo_forebody_envelope']=str(cp);(out/'fin-authoring.json').write_text(json.dumps(fa,indent=2)+'\n')
    report=dict(ok=True,kind='photo_primary_continuous_forebody_envelope',model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),baseline_sha256=sha(src/'fish.glb'),config_sha256=sha(cp),script_sha256=sha(__file__),whole_triangles=count,source_action_curves_exact=True,body_XY_exact=bool(np.array_equal(old[:,:2],mapped[:,:2])),oral_vertices_exact=bool(np.array_equal(old[oral_ids],mapped[oral_ids])),eye_rigid_translations=[{k:v for k,v in e.items()if k!='tree'}for e in eyes],fins=fins,pivots=pivots,changes=[dict(vertex=i,old=old[i].tolist(),delta_z_m=float(mapped[i,2]-old[i,2]))for i in range(len(old))if abs(mapped[i,2]-old[i,2])>1e-8],formal_acceptance=False,visual_review='pending')
    (out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='changes'}))
if __name__=='__main__':main()
