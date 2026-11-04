"""Declared same-fish head pose and head/neck connection, ordinary source export.

Photo proposals are engineering choices, never calibrated specimen measures.
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
def main():
 cp,out=map(lambda x:Path(x).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert not out.exists()and'/experiments/'in str(out)
 for p,h in c['inputs'].items():assert sha(p)==h,p
 src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);actions=rig_action_snapshot()['actions'];body=bpy.data.objects['Reference_head_body'];body.data.calc_loop_triangles();old=np.array([v.co[:]for v in body.data.vertices]);faces=np.array([t.vertices[:]for t in body.data.loop_triangles]);tree=BVHTree.FromPolygons([Vector(p)for p in old],faces.tolist(),all_triangles=True)
 body.data.update();oral_normals={li:tuple(body.data.corner_normals[li].vector)for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'for li in f.loop_indices}
 oralids={i for f in body.data.polygons if body.data.materials[f.material_index].name=='Actual finite oral lining'for i in f.vertices};kd=KDTree(len(oralids))
 for j,i in enumerate(sorted(oralids)):kd.insert(Vector(old[i]),j)
 kd.balance();L,nose=c['length_m'],c['nose_x_m'];pose=c['head_vertical_proposal'];fade=pose['fade_p'];dz0=pose['delta_z_m']
 def mapping(point):
  x,y,z=point;p=(nose-x)/L;yy=y;undo=c.get('neck_widening_undo')
  if undo:
   w=smooth(*undo['anterior_p'],p)*(1-smooth(*undo['posterior_p'],p));lo,hi=0.,abs(y)
   for _ in range(44):
    mid=(lo+hi)/2;observed=mid*(1+undo['gain_minus_one']*w*(1-smooth(*undo['span_fade'],mid/c['half_head_span_m'])))
    if observed<abs(y):lo=mid
    else:hi=mid
   restored=(lo+hi)/2*(1 if y>=0 else -1);protection=smooth(*c['oral_lateral_guard_m'],kd.find(Vector(point))[2]);yy=y+(restored-y)*protection
  xx=x;corner=c.get('posterior_corner')
  if corner:
   fr=abs(yy)/c['half_head_span_m'];side=corner['sides']['positive'if yy>=0 else'negative'];table=np.array(side['edge_samples']);front=float(np.interp(abs(yy),table[:,0],table[:,2]));rear=float(np.interp(abs(yy),table[:,0],table[:,1]))
   if rear-.003<=x<=front+.001 and front-rear>1e-5:
    t=(front-x)/(front-rear);delta=(corner['target_dx_dy']-side['current_fit_dx_dy'])*(abs(yy)-corner['outer_anchor_y_m']);w=smooth(*corner['inner_span_fade'],fr)*(1-smooth(*corner['outer_span_fade'],fr))*smooth(*corner['posterior_chord_blend'],t);xx=x+delta*w
  recess=c.get('oral_recess');lift=0.
  if recess:lift=recess['rigid_lift_m']*(1-smooth(*recess['distance_fade_m'],kd.find(Vector(point))[2]))
  return Vector((xx,yy,z+dz0*(1-smooth(*fade,p))+lift))
 for v in body.data.vertices:v.co=mapping(v.co)
 body.data.update();mapped=np.array([v.co[:]for v in body.data.vertices]);fins=[]
 for ob in [o for o in bpy.context.scene.objects if o.type=='MESH'and o!=body]:
  before=np.array([v.co[:]for v in ob.data.vertices]);maximum=0.
  for v in ob.data.vertices:
   p=v.co.copy();q=mapping(p);h,n,fi,d=tree.find_nearest(p)
   if h is not None and d<c['fin_support_m'][1]:
    ids=faces[fi];actual=barycentric_transform(h,*[Vector(old[i])for i in ids],*[Vector(mapped[i])for i in ids]);corr=(actual-mapping(h))*(1-smooth(*c['fin_support_m'],d));q+=corr;maximum=max(maximum,corr.length)
   v.co=q
  ob.data.update();fins.append(dict(name=ob.name,maximum_delta_m=float(np.linalg.norm(np.array([v.co[:]for v in ob.data.vertices])-before,axis=1).max()),maximum_root_support_correction_m=maximum))
 bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT');pivots=[]
 for bone in rig.data.edit_bones:
  if bone.name=='root':continue
  delta=mapping(bone.head)-bone.head;bone.head+=delta;bone.tail+=delta;pivots.append(dict(bone=bone.name,delta=list(delta)))
 bpy.ops.object.mode_set(mode='OBJECT');assert rig_action_snapshot()['actions']==actions
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];count=0
 for ob in meshes:
  bm=bmesh.new();bm.from_mesh(ob.data);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;bm.free();ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops));ob.data.calc_loop_triangles();count+=len(ob.data.loop_triangles)
 # The oral surface is rigidly translated. Its source loop normals therefore
 # remain correct; neck smoothing must not average across its narrow corners.
 body.data.update();normals=[tuple(n.vector)for n in body.data.corner_normals]
 for li,n in oral_normals.items():normals[li]=n
 body.data.normals_split_custom_set(normals);body.data.update()
 assert count==c['expected_triangles'];rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in meshes+[rig]:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False)
 fa=json.loads((src/'fin-authoring.json').read_text())
 for f in fa['fins']:f['root_points_native']=[list(bpy.data.objects[f['name']].data.vertices[i].co)for i in f['root_ids']]
 fa['photo_head_pose']=pose;(out/'fin-authoring.json').write_text(json.dumps(fa,indent=2)+'\n');r=dict(ok=True,kind='user_photo_guided_head_lowering',model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),baseline_sha256=sha(src/'fish.glb'),config_sha256=sha(cp),script_sha256=sha(__file__),whole_triangles=count,head_vertical_proposal=pose,fins=fins,pivots=pivots,source_action_curves_exact=True,whole_mouth_and_eye_region_rigid_z_translation=True,oral_rigid_translation_z_m=dz0+c.get('oral_recess',{}).get('rigid_lift_m',0),oral_recess=c.get('oral_recess'),head_X_unchanged=not bool(c.get('posterior_corner')),posterior_corner=c.get('posterior_corner'),neck_widening_undo=c.get('neck_widening_undo'),whole_mouth_Y_unchanged=True,rigid_oral_source_loop_normals_preserved=True,formal_acceptance=False,visual_review='pending');(out/'authoring.validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
