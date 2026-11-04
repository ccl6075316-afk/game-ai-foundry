"""Retract the whole oblique shoulder into the crossbar, not pinch the neck.

Uses a few measured library rear-line parameters registered to the existing
outer crossbar. Own front scallops, span, side boundary, eyes and mouth remain.
"""
import bpy,bmesh,json,hashlib,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable.source_snapshot import rig_action_snapshot

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def main():
    cp,out=map(lambda p:Path(p).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert not out.exists()and'/experiments/'in str(out)
    for p,h in c['inputs'].items():assert sha(p)==h,p
    src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);actions=rig_action_snapshot()['actions']
    body=bpy.data.objects[c['body']];body.data.update();body.data.calc_loop_triangles();old=np.array([v.co[:]for v in body.data.vertices]);tri=old[np.array([t.vertices[:]for t in body.data.loop_triangles])];original_normals=[tuple(n.vector)for n in body.data.corner_normals]
    protected_faces={f.index for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'or body.data.materials[f.material_index].name.startswith('Own original side eye pixels')};protected_vertices={i for f in body.data.polygons if f.index in protected_faces for i in f.vertices};protected_vertices.update(c.get('protected_side_vertex_ids',[]));q=c['bridge'];W,nose=c['head_span_m'],c['nose_x_m'];cache={};changes=[];clipped=0
    def bounds(x):
        if x not in cache:
            a=tri;b=np.roll(tri,-1,axis=1);k=(a[:,:,0]-x)*(b[:,:,0]-x)<0;points=a[k]+((x-a[:,:,0][k])/(b[:,:,0][k]-a[:,:,0][k]))[:,None]*(b[k]-a[k]);points=np.concatenate([points,a[abs(a[:,:,0]-x)<1e-7]]);cache[x]=(float(points[:,2].min()),float(points[:,2].max()))if len(points)else None
        return cache[x]
    for v in body.data.vertices:
        x,y,z=old[v.index];fr=abs(y)/(W/2)
        if v.index in protected_vertices or x<=q['axial_guard_m'][0]or not q['span_rise'][0]<fr<q['span_fall'][1]:continue
        side=q['sides']['1'if y>=0 else'-1'];table=np.array(side['edge_samples_fraction_front_rear_x_m']);front=float(np.interp(fr,table[:,0],table[:,1]));rear=float(np.interp(fr,table[:,0],table[:,2]))
        if not rear-.003<=x<=front+.000001 or front-rear<1e-5:continue
        t=(front-x)/(front-rear)
        if t<=q['chord_blend'][0]:continue
        target_pH=side['library_line_intercept_pH']+side['library_line_slope_pH_per_transverseH']*(fr/2)+side['rigid_axial_registration_offset_pH'];target_rear=nose-W*target_pH;delta=min(q['maximum_forward_shift_m'],max(0.,target_rear-rear));limits=bounds(x)
        if limits is None:continue
        margin=min(z-limits[0],limits[1]-z);weight=smooth(*q['span_rise'],fr)*(1-smooth(*q['span_fall'],fr))*smooth(*q['chord_blend'],t)*smooth(*q['side_boundary_guard_m'],margin)*smooth(*q['axial_guard_m'],x);delta*=weight
        if delta<1e-9:continue
        def inside(xx):
            lim=bounds(xx);return lim is not None and lim[0]+1e-6<=z<=lim[1]-1e-6
        if not inside(x+delta):
            lo,hi=0.,delta
            for _ in range(36):
                mid=(lo+hi)/2
                if inside(x+mid):lo=mid
                else:hi=mid
            delta=lo;clipped+=1
        if delta>1e-9:v.co.x+=delta;changes.append(dict(vertex=v.index,old=old[v.index].tolist(),delta_x_m=delta,half_span_fraction=fr,chord_fraction=t))
    assert changes;ids={r['vertex']for r in changes};affected={i for f in body.data.polygons if any(v in ids for v in f.vertices)for i in f.vertices};body.data.update();body.data.normals_split_custom_set([(0.,0.,0.)]*len(body.data.loops));body.data.update();normals=[tuple(n.vector)for n in body.data.corner_normals]
    for f in body.data.polygons:
        for li in f.loop_indices:
            if f.index in protected_faces or body.data.loops[li].vertex_index not in affected:normals[li]=original_normals[li]
    body.data.normals_split_custom_set(normals);body.data.update();new=np.array([v.co[:]for v in body.data.vertices]);assert np.array_equal(old[:,1:],new[:,1:]);bm=bmesh.new();bm.from_mesh(body.data);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];count=0
    for ob in meshes:ob.data.calc_loop_triangles();count+=len(ob.data.loop_triangles)
    assert count==c['expected_triangles']and rig_action_snapshot()['actions']==actions;rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
    for ob in meshes+[rig]:ob.select_set(True)
    bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    fa=json.loads((src/'fin-authoring.json').read_text());fa['library_bridge_revision']=str(cp);(out/'fin-authoring.json').write_text(json.dumps(fa,indent=2)+'\n');report=dict(ok=True,kind='whole_oblique_bridge_retracted_to_library_crossbar_direction',model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),baseline_sha256=sha(src/'fish.glb'),config_sha256=sha(cp),script_sha256=sha(__file__),whole_triangles=count,body_transverse_vertical_positions_exact=True,source_action_curves_exact=True,mouth_eye_positions_unchanged=True,protected_normal_vectors_supplied_from_source=True,fins_and_rig_unedited=True,changed_vertices=len(changes),maximum_retraction_m=max(r['delta_x_m']for r in changes),changed_half_span_range=[min(r['half_span_fraction']for r in changes),max(r['half_span_fraction']for r in changes)],side_guard_clipped_vertices=clipped,side_profile_protected_vertices=c.get('protected_side_vertex_ids',[]),changes=changes,formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='changes'}))
if __name__=='__main__':main()
