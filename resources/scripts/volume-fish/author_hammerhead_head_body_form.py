"""Apply declared part-registered head surfaces and trunk height to own source.

No reference mesh is imported. All topology, UVs, embedded art and source action
curves are retained. Fin pivots translate with their actual changed support.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform


def smooth(a,b,x):
    t=min(1.,max(0.,(x-a)/(b-a)));return t*t*(3-2*t)


def tree(ob):
    ob.data.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co.copy() for v in ob.data.vertices],[tuple(t.vertices)for t in ob.data.loop_triangles],all_triangles=True,epsilon=1e-7)


def main():
    args=sys.argv[sys.argv.index('--')+1:];cp=Path(args[0]).resolve();out=Path(args[1]).resolve();c=json.loads(cp.read_text());assert not out.exists() and '/experiments/' in str(out)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    for p,h in c['inputs'].items():assert sha(p)==h,p
    data=json.loads(Path(c['measurements']).read_text());project=json.loads(Path(c['project_reference']).read_text());L=c['length_m'];nose=c['nose_x_m']
    bpy.ops.wm.open_mainfile(filepath=c['blend']);bpy.context.scene.frame_set(1);rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST'
    body=bpy.data.objects['Reference_head_body'];oldtree=tree(body);old=np.array([v.co[:]for v in body.data.vertices]);meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    original={o.name:np.array([v.co[:]for v in o.data.vertices])for o in meshes}
    eye_x_by_side={1 if original[name][:,1].mean()>0 else -1:float((original[name][:,0].min()+original[name][:,0].max())/2)for name in ['Eye_left','Eye_right']}
    sys.path.insert(0,str(Path(__file__).resolve().parent/'portable'))
    from source_snapshot import rig_action_snapshot
    actions_before=rig_action_snapshot()['actions']
    triangles=old[np.array([t.vertices[:] for t in body.data.loop_triangles])]
    rows=project['head_transverse_stations'];ys=[r['y_m']for r in rows];front=[r['front_x_m']for r in rows];rear=[r['rear_x_m']for r in rows];half=project['head_span_m']/2
    source=data['head_rows'];fractions=[r['span_fraction']for r in source]
    cn=data['neck_span_fraction']['candidate'];rn=data['neck_span_fraction']['reference'];control=c['body_gain_controls_dense'];gp=[r[0]for r in control];gg=[r[1]for r in control]
    def bounds(x,y):
        # Float64 finite triangles avoid BVH ray misses exactly on the shared
        # centre seam; no domain padding or body/fin tolerance is introduced.
        a,b,d=triangles[:,0],triangles[:,1],triangles[:,2]
        den=(b[:,1]-d[:,1])*(a[:,0]-d[:,0])+(d[:,0]-b[:,0])*(a[:,1]-d[:,1]);valid=abs(den)>1e-15
        aa=np.zeros(len(a));bb=aa.copy()
        aa[valid]=((b[valid,1]-d[valid,1])*(x-d[valid,0])+(d[valid,0]-b[valid,0])*(y-d[valid,1]))/den[valid]
        bb[valid]=((d[valid,1]-a[valid,1])*(x-d[valid,0])+(a[valid,0]-d[valid,0])*(y-d[valid,1]))/den[valid];cc=1-aa-bb
        keep=valid&(aa>=-1e-8)&(bb>=-1e-8)&(cc>=-1e-8);hits=(aa*a[:,2]+bb*b[:,2]+cc*d[:,2])[keep]
        if len(hits)<2:return None
        return float(hits.min()),float(hits.max())
    def part_span(f):return float(np.interp(f,[r[0]for r in c['span_map_dense']],[r[1]for r in c['span_map_dense']]))
    def envelope(fr,t,key):
        values=[np.interp(t,[s['t']for s in r['samples']],[s[key]for s in r['samples']])for r in source]
        return float(np.interp(fr,fractions,values))*L+c['reference_vertical_offset_m']
    oral=set()
    for f in body.data.polygons:
        if body.data.materials[f.material_index].name=='Actual finite oral lining':oral.update(f.vertices)
    assert oral
    kd=KDTree(len(oral))
    for j,i in enumerate(sorted(oral)):kd.insert(Vector(old[i]),j)
    kd.balance()
    def body_map(p):
        x,y,z=p;pax=(nose-x)/L;gain=float(np.interp(pax,gp,gg))
        lateral=c.get('neck_lateral_transport')
        dy=0.
        if lateral:
            weight=smooth(*lateral['anterior_p'],pax)*(1-smooth(*lateral['posterior_p'],pax))*(1-smooth(*lateral['span_fade'],abs(y)/half))
            dy=y*lateral['gain_minus_one']*weight
        centres=c.get('body_center_delta_dense',[[0.,0.],[1.,0.]])
        dz=float(np.interp(pax,[r[0]for r in centres],[r[1]for r in centres]))
        if abs(gain-1)<1e-10:return Vector((x,y+dy,z+dz))
        b=bounds(x,0)
        assert b is not None,('trunk has no body support',x)
        mid=sum(b)/2
        return Vector((x,y+dy,mid+(z-mid)*gain+dz))
    def mapping(p,head=True):
        x,y,z=p;q=body_map(p)
        if not head:return q
        a=float(np.interp(y,ys,front));b=float(np.interp(y,ys,rear));w=smooth(b-c['posterior_blend_m'],b,x)
        if w<=1e-10 or abs(y)>half+1e-6:return q
        limits=bounds(x,y)
        if limits is None:return q
        lo,hi=limits;depth=hi-lo
        if depth<1e-8:return q
        t=min(1.,max(0.,(a-x)/max(a-b,1e-5)));fr=part_span(abs(y)/half)
        low=envelope(fr,t,'bottom');high=envelope(fr,t,'top')
        # A reference open lower jaw is not adopted. Use the project's own
        # near-closed lower face around the medial mouth-bearing region.
        pose=(1-smooth(cn*.7,cn*1.2,abs(y)/half))*smooth(.4,.65,t)
        low=low*(1-pose)+lo*pose
        terminal=c.get('terminal_eye_support')
        if terminal:
            side=1 if y>=0 else -1;cx=eye_x_by_side[side];cy=half-terminal['transverse_radius_m']
            radial=1-((x-cx)/terminal['longitudinal_radius_m'])**2-((abs(y)-cy)/terminal['transverse_radius_m'])**2
            if radial>0:
                mid=(low+high)/2;radius=terminal['vertical_radius_m']*radial**.5
                low=min(low,mid-radius);high=max(high,mid+radius)
        high=max(high,low+c['minimum_head_depth_m'])
        target=low+(z-lo)/depth*(high-low)
        q.z=q.z*(1-w)+target*w
        if x>c['oral_influence_min_x_m']:
            distance=kd.find(Vector(p))[2];weight=smooth(*c['oral_blend_distance_m'],distance)
            q=Vector(p)+(q-Vector(p))*weight
        return q
    for ob in meshes:
        if ob.name.startswith('Eye_'):continue
        for v in ob.data.vertices:
            if ob==body and v.index in oral:continue
            v.co=mapping(v.co,head=ob==body)
        ob.data.update();ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops))
    conformance=[]
    if c.get('finite_fin_support_transport'):
        limits=c['finite_fin_support_transport']
        for ob in meshes:
            if ob==body or ob.name.startswith('Eye_'):continue
            maximum=0.;count=0
            for v in ob.data.vertices:
                p=Vector(original[ob.name][v.index]);h,n,fi,d=oldtree.find_nearest(p)
                if h is None or d>=limits['fade_out_m']:continue
                ids=body.data.loop_triangles[fi].vertices
                actual=barycentric_transform(h,*[Vector(old[i])for i in ids],*[body.data.vertices[i].co for i in ids])
                correction=(actual-mapping(h))*(1-smooth(limits['full_distance_m'],limits['fade_out_m'],d))
                correction.x=0. # X is unchanged by both maps; discard float32 barycentric roundoff.
                v.co+=correction;maximum=max(maximum,correction.length);count+=int(correction.length>1e-9)
            ob.data.update();ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops));conformance.append({'fin':ob.name,'vertices_corrected':count,'maximum_finite_support_correction_m':maximum})
    newtree=tree(body);eyes=[]
    for name in ['Eye_left','Eye_right']:
        ob=bpy.data.objects[name];points=original[name];side=1 if points[:,1].mean()>0 else -1;cx=float((points[:,0].min()+points[:,0].max())/2);cz=float((points[:,2].min()+points[:,2].max())/2)
        h=oldtree.ray_cast(Vector((cx,side,cz)),Vector((0,-side,0)),2)[0];assert h is not None
        yy=h.y-side*c['eye_inset_m'];hi=newtree.ray_cast(Vector((cx,yy,2)),Vector((0,0,-1)),4)[0];lo=newtree.ray_cast(Vector((cx,yy,-2)),Vector((0,0,1)),4)[0];assert hi is not None and lo is not None
        shift=(hi.z+lo.z)/2-cz;supports=[]
        for v in ob.data.vertices:
            oh=oldtree.ray_cast(Vector((v.co.x,side,v.co.z)),Vector((0,-side,0)),2)[0];assert oh is not None
            offset=side*(v.co.y-oh.y);v.co.z+=shift;hit,n,fi,_=newtree.ray_cast(Vector((v.co.x,side,v.co.z)),Vector((0,-side,0)),2);assert hit is not None and n.y*side>0
            v.co.y=hit.y+side*offset;supports.append({'vertex':v.index,'support_face':fi,'offset_m':offset})
        ob.data.update();ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops));eyes.append({'name':name,'z_shift_m':shift,'supports':supports})
    # Fin pivot frames keep their directions and source rotation curves. Only
    # their actual rest origins translate with the changed body support.
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT');pivots=[]
    for bone in rig.data.edit_bones:
        if '_bone' not in bone.name and not (c.get('body_center_delta_dense') and bone.name.startswith('body_')):continue
        before=bone.head.copy();delta=body_map(before)-before;bone.head+=delta;bone.tail+=delta;pivots.append({'bone':bone.name,'delta_m':list(delta)})
    bpy.ops.object.mode_set(mode='OBJECT')
    assert rig_action_snapshot()['actions']==actions_before,'Original action curves changed'
    assert np.array_equal(np.array([v.co[:]for v in body.data.vertices])[list(oral)],old[list(oral)])
    bm=bmesh.new();bm.from_mesh(body.data);assert all(len(e.link_faces)==2 for e in bm.edges) and bm.calc_volume()>0;bm.free()
    total=0;changes=[]
    for ob in meshes:
        ob.data.calc_loop_triangles();total+=len(ob.data.loop_triangles);now=np.array([v.co[:]for v in ob.data.vertices]);assert np.array_equal(now[:,0],original[ob.name][:,0]);changes.append({'mesh':ob.name,'changed_vertices':int(np.any(abs(now-original[ob.name])>1e-9,axis=1).sum()),'maximum_delta_m':float(np.linalg.norm(now-original[ob.name],axis=1).max())})
    assert total==3998
    rig.data.pose_position='POSE';bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
    for o in meshes+[rig]:o.select_set(True)
    bpy.context.view_layer.objects.active=body;out.mkdir();bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    fin_authoring=json.loads(Path(c['fin_authoring']).read_text())
    for fin in fin_authoring['fins']:
        fin['root_points_native']=[list(bpy.data.objects[fin['name']].data.vertices[i].co)for i in fin['root_ids']]
    (out/'fin-authoring.json').write_text(json.dumps(fin_authoring,indent=2)+'\n')
    result={'ok':True,'kind':'registered_hammerhead_head_and_body_source_author','config_sha256':sha(cp),'script_sha256':sha(__file__),'model_sha256':sha(out/'fish.glb'),'blend_sha256':sha(out/'fish.blend'),'whole_triangles':total,'changes':changes,'oral_vertices_unchanged':len(oral),'eyes':eyes,'fin_pivot_translations':pivots,'finite_fin_support_transport':conformance,'formal_acceptance':False,'visual_review':'pending','scope':'Own topology/UV/material/source action curves retained; source X and terminal head span preserved, declared medial XY neck transport. Head surfaces use registered scalar envelopes; anterior body height and fins transported. Actual cold export and all affected gates required.'};(out/'authoring.validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k in ['ok','changes','whole_triangles','fin_pivot_translations','finite_fin_support_transport']}))


if __name__=='__main__':main()
