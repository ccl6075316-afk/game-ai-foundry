"""Tuck only the posterior medial cephalofoil fillet; accepted side form fixed."""
import bpy,bmesh,json,hashlib,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable.source_snapshot import rig_action_snapshot

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def main():
    cp,out=map(lambda p:Path(p).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert not out.exists()and'/experiments/'in str(out)
    for p,h in c['inputs'].items():assert sha(p)==h,p
    src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);actions=rig_action_snapshot()['actions']
    body=bpy.data.objects[c['body']];body.data.update();original_normals=[tuple(n.vector)for n in body.data.corner_normals];old=np.array([v.co[:]for v in body.data.vertices]);q=c['inner_corner'];changed=[]
    # A positive transverse derivative prevents a fold through the narrow neck.
    assert 1.5*q['inward_m']/(q['span_rise_m'][1]-q['span_rise_m'][0])<1
    protected_faces={f.index for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'or body.data.materials[f.material_index].name.startswith('Own original side eye pixels')};protected_vertices={i for f in body.data.polygons if f.index in protected_faces for i in f.vertices}
    for v in body.data.vertices:
        x,y,z=v.co;w=smooth(*q['axial_rise_m'],x)*(1-smooth(*q['axial_fall_m'],x))*smooth(*q['span_rise_m'],abs(y))*(1-smooth(*q['span_fall_m'],abs(y)));dy=-q['inward_m']*w*(1 if y>=0 else -1)
        if abs(dy)>1e-9:
            assert v.index not in protected_vertices;v.co.y+=dy;changed.append(dict(vertex=v.index,old=old[v.index].tolist(),delta_y_m=dy))
    assert changed;ids={r['vertex']for r in changed};affected={i for f in body.data.polygons if any(v in ids for v in f.vertices)for i in f.vertices};body.data.update();body.data.normals_split_custom_set([(0.,0.,0.)]*len(body.data.loops));body.data.update();normals=[tuple(n.vector)for n in body.data.corner_normals]
    for face in body.data.polygons:
        for li in face.loop_indices:
            if face.index in protected_faces or body.data.loops[li].vertex_index not in affected:normals[li]=original_normals[li]
    body.data.normals_split_custom_set(normals);body.data.update();new=np.array([v.co[:]for v in body.data.vertices]);assert np.array_equal(old[:,[0,2]],new[:,[0,2]])
    bm=bmesh.new();bm.from_mesh(body.data);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free();meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];count=0
    for ob in meshes:ob.data.calc_loop_triangles();count+=len(ob.data.loop_triangles)
    assert count==c['expected_triangles']and rig_action_snapshot()['actions']==actions
    rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
    for ob in meshes+[rig]:ob.select_set(True)
    bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
    fa=json.loads((src/'fin-authoring.json').read_text());fa['inner_corner_revision']=str(cp);(out/'fin-authoring.json').write_text(json.dumps(fa,indent=2)+'\n')
    report=dict(ok=True,kind='local_inner_hammer_corner_tuck',model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),baseline_sha256=sha(src/'fish.glb'),config_sha256=sha(cp),script_sha256=sha(__file__),whole_triangles=count,body_axial_vertical_positions_exact=True,source_action_curves_exact=True,mouth_eye_vertices_unchanged=True,protected_normal_vectors_supplied_from_source=True,fins_and_rig_unedited=True,changed_vertices=len(changed),maximum_inward_m=max(abs(r['delta_y_m'])for r in changed),changes=changed,formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='changes'}))
if __name__=='__main__':main()
