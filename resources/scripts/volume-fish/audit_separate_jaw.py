"""Read-only evidence for actual part ownership, removal and cupped placement."""
import argparse,hashlib,json,sys,math
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'cli'))
from volume_mouth import slit_v
p=argparse.ArgumentParser();p.add_argument('--blend',required=True);p.add_argument('--profile',required=True);p.add_argument('--output',required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);profile=json.loads(Path(a.profile).read_text(encoding='utf-8'));settings=profile['oral_jaws'];lower=settings['separate_lower'];aspect=1/profile['source_aspect_ratio']
bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
body=bpy.data.objects['Closed_body'];jaw=bpy.data.objects.get('Lower_jaw_separate');failures=[]
if jaw is None:
    Path(a.output).write_text(json.dumps({'ok':False,'failures':['Missing actual independent lower-jaw mesh'],'blend_sha256':hashlib.sha256(Path(a.blend).read_bytes()).hexdigest()},indent=2),encoding='utf-8')
    sys.exit(1)
reference_pose=lower.get('reference_shape',{}).get('open_degrees')
if reference_pose is not None:
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    rig.pose.bones['jaw_lower'].rotation_mode='XYZ';rig.pose.bones['jaw_lower'].rotation_euler=(0,math.radians(reference_pose),0)
    bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get()
    body=body.evaluated_get(graph);jaw=jaw.evaluated_get(graph)

def tree(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);closed=all(e.is_manifold for e in bm.edges);volume=bm.calc_volume(signed=True);t=BVHTree.FromBMesh(bm);bm.free();return t,closed,volume
upper,body_closed,body_volume=tree(body);bottom,jaw_closed,jaw_volume=tree(jaw)
rows=[]
for t in [.25,.5,.75]:
    u=settings['corner'][0]+(settings['front'][0]-settings['corner'][0])*t;x=u-.5
    roof=upper.ray_cast(Vector((x,0,-.5)),Vector((0,0,1)),1)[0]
    cup=bottom.ray_cast(Vector((x,0,.5)),Vector((0,0,-1)),1)[0]
    z=(.5-slit_v(settings,u))*aspect-lower['cup_depth']-lower['thickness']-.008
    old_volume_hit=upper.ray_cast(Vector((x,-.3,z)),Vector((0,1,0)),.6)[0] is not None
    gap=roof.z-cup.z if roof is not None and cup is not None else None
    ok=not old_volume_hit and gap is not None and gap>0
    rows.append({'t':t,'u':u,'old_lower_volume_still_in_head':old_volume_hit,'central_roof_to_cup_native':gap,'ok':ok})
    if not ok:failures.append('Old lower volume or invalid central cup clearance at t='+str(t))
roots=[]
for v in jaw.data.vertices:
    if v.co.x+.5<=settings['corner'][0]-.007:
        near,normal,_,distance=upper.find_nearest(v.co)
        roots.append(distance*(1 if (v.co-near).dot(normal)>=0 else -1))
if not roots or min(roots)>=0:failures.append('No embedded posterior root joining independent jaw to head')
if not body_closed or not jaw_closed or body_volume<=0 or jaw_volume<=0:failures.append('Both separate parts must be positive-volume closed manifolds')
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
report={'ok':not failures,'scope':'Independent mesh ownership, removed old lower shell, central cup clearance and embedded root. Does not certify natural lip contour or exact soft-tissue occlusion.','blend_sha256':sha(a.blend),'profile_sha256':sha(a.profile),'upper_closed':body_closed,'jaw_closed':jaw_closed,'upper_volume_native':body_volume,'jaw_volume_native':jaw_volume,'placement_samples':rows,'root_samples':len(roots),'root_min_signed_native':min(roots) if roots else None,'root_max_signed_native':max(roots) if roots else None,'failures':failures}
Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if failures:sys.exit(1)
