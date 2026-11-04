"""Repair declared own fin foil thickness, keeping complete original root IDs.

The library supplies only documented scalar section ratios. Source UV, original
fin planform/control points, body and animation are not imported or rebuilt.
"""
import bpy,bmesh,json,hashlib,sys,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import closest_point_on_tri
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from source_snapshot import rig_action_snapshot

def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def main():
 cp,out=map(lambda x:Path(x).resolve(),sys.argv[sys.argv.index('--')+1:]);c=json.loads(cp.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert not out.exists() and '/experiments/'in str(out)
 for p,h in c['inputs'].items():assert sha(p)==h,p
 src=Path(c['baseline']);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';bpy.context.scene.frame_set(1);actions=rig_action_snapshot()['actions'];body=bpy.data.objects[c['body']];body.data.calc_loop_triangles();body_original=np.array([v.co[:]for v in body.data.vertices]);tree=BVHTree.FromPolygons([v.co.copy()for v in body.data.vertices],[tuple(t.vertices)for t in body.data.loop_triangles],all_triangles=True);auth=json.loads((src/'fin-authoring.json').read_text());records=[];body_faces=np.array([tuple(t.vertices)for t in body.data.loop_triangles]);body_tri=body_original[body_faces];ta,tb,tc=body_tri[:,0],body_tri[:,1],body_tri[:,2];e0=tb-ta;e1=tc-ta;d00=np.sum(e0*e0,axis=1);d01=np.sum(e0*e1,axis=1);d11=np.sum(e1*e1,axis=1);den=d00*d11-d01*d01;bn=np.cross(e0,e1);bn/=np.maximum(np.linalg.norm(bn,axis=1)[:,None],1e-20)
 def basal_anchor(old_point,requested):
  w=old_point-ta;d20=np.sum(w*e0,axis=1);d21=np.sum(w*e1,axis=1);u=(d11*d20-d01*d21)/np.maximum(den,1e-25);v=(d00*d21-d01*d20)/np.maximum(den,1e-25);inside=(den>1e-22)&(u>=-1e-5)&(v>=-1e-5)&(u+v<=1.00001)&(abs(np.sum(w*bn,axis=1))<=2e-5);ids=np.flatnonzero(inside)
  if not len(ids):return old_point.copy(),'retained_unclassified'
  common=set(body_faces[ids[0]])
  for f in body_faces[ids[1:]]:common.intersection_update(f)
  if len(common)==1:return body_original[next(iter(common))].copy(),'body_vertex'
  if len(common)==2:
   aa,bb=body_original[list(common)];edge=bb-aa;t=np.clip(np.dot(requested-aa,edge)/np.dot(edge,edge),0,1);return aa+t*edge,'body_edge'
  if len(common)==3:
   t=body_original[list(common)];return np.array(closest_point_on_tri(Vector(requested),*[Vector(x)for x in t])),'body_face'
  return old_point.copy(),'retained_boundary'
 for row in auth['fins']:
  name=row['name'];cfg=c['fins'][name];ob=bpy.data.objects[name];me=ob.data;old=np.array([v.co[:]for v in me.vertices]);roots=set(row['root_ids']);attr=lambda key:np.array([a.value for a in me.attributes[key].data]);xy=np.stack([attr('source_mask_x_px'),attr('source_mask_y_px')],axis=1);s=attr('source_span_t');layer=attr('source_layer_sign');new=old.copy();root_reprojected=0;free_lifted=[]
  if name=='Caudal':
   rear=float(body_original[:,0].min())
   for i,p in enumerate(old):
    if i in roots:continue
    free_gain=cfg['free_thickness_gain']
    if cfg.get('lower_lobe'):
     lo=cfg['lower_lobe'];ss=max(0,min(1,(lo['root_center_z_m']-p[2])/(lo['root_center_z_m']-float(old[:,2].min()))));lower_gain=float(np.interp(ss,lo['span_knots'],lo['gains']));mix=1-smooth(*lo['join_z_m'],p[2]);free_gain=free_gain*(1-mix)+lower_gain*mix
    gain=1-(1-free_gain)*smooth(*cfg['root_transition_distance_m'],rear-p[0]);edge=cfg['minimum_full_edge_m']/2;new[i,1]=math.copysign(edge+max(0,abs(p[1])-edge)*gain,p[1])
  else:
   neg=np.flatnonzero(layer<-.999);pos=np.flatnonzero(layer>.999);pairs=[]
   for i in pos:
    dist=np.linalg.norm(xy[neg]-xy[i],axis=1);j=int(neg[dist.argmin()])
    if dist.min()<.002 and np.linalg.norm(old[i]-old[j])>1e-7:pairs.append((int(i),j))
   assert len(pairs)>20,(name,len(pairs));vectors=np.array([old[i]-old[j]for i,j in pairs]);normal=np.median(vectors/np.linalg.norm(vectors,axis=1)[:,None],axis=0);normal/=np.linalg.norm(normal);points=np.array([(xy[i]+xy[j])/2 for i,j in pairs]);halves=np.array([np.dot(old[i]-old[j],normal)/2 for i,j in pairs]);assert min(halves)>0
   for i,p in enumerate(old):
    distance=np.linalg.norm(points-xy[i],axis=1);ids=np.argsort(distance)[:4];w=1/np.maximum(distance[ids],1e-6)**2;half=float(np.dot(w,halves[ids])/w.sum());gain=float(np.interp(s[i],cfg['span_knots'],cfg['thickness_gains']));edge_extra=(cfg['minimum_full_edge_m']-.0004)/2;new[i]=p+normal*float(layer[i])*(half*(gain-1)+edge_extra)
   # Preserve the original finite body facets, edges and crest vertices.
   # Reprojecting independently to arbitrary nearest facets folds cap triangles
   # across a body crease; staying inside the original support prevents that.
   anchors={}
   for i in roots:
    new[i],kind=basal_anchor(old[i],new[i]);anchors[kind]=anchors.get(kind,0)+1;root_reprojected+=1
   # Keep free points outside, without ever converting them into root IDs.
   for i in range(len(new)):
    if i in roots:continue
    p=Vector(new[i]);hit,no,_,dist=tree.find_nearest(p);signed=(p-hit).dot(no)
    if signed<.0001:
     corrected=p+no*(.0001-signed);free_lifted.append(dict(vertex=i,displacement_m=(corrected-p).length));new[i]=corrected
  for v,q in zip(me.vertices,new):v.co=q
  me.update();me.normals_split_custom_set([(0,0,0)]*len(me.loops));me.update();bm=bmesh.new();bm.from_mesh(me);assert all(e.is_manifold for e in bm.edges)and bm.calc_volume()>0;volume=bm.calc_volume();bm.free();me.calc_loop_triangles();row['root_points_native']=[list(me.vertices[i].co)for i in row['root_ids']];row['thickness_revision']=str(cp);row['vertices']=len(me.vertices);row['triangles']=len(me.loop_triangles);records.append(dict(name=name,vertices=len(me.vertices),triangles=len(me.loop_triangles),root_ids_retained=len(roots),roots_reprojected=root_reprojected,basal_support_classes=anchors if name!='Caudal'else{},free_point_contact_corrections=free_lifted,maximum_displacement_m=float(np.linalg.norm(new-old,axis=1).max()),volume_m3=volume,normal=normal.tolist()if name!='Caudal'else[0,1,0]))
 assert np.array_equal(body_original,np.array([v.co[:]for v in body.data.vertices]));assert rig_action_snapshot()['actions']==actions;meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];count=0
 for ob in meshes:ob.data.calc_loop_triangles();count+=len(ob.data.loop_triangles)
 assert count==c['expected_triangles'];rig.data.pose_position='POSE';out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in meshes+[rig]:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);auth['fin_thickness_revision']=str(cp);(out/'fin-authoring.json').write_text(json.dumps(auth,indent=2)+'\n');report=dict(ok=True,kind='library_scalar_guided_fin_thickness_author',baseline_sha256=sha(src/'fish.glb'),model_sha256=sha(out/'fish.glb'),blend_sha256=sha(out/'fish.blend'),config_sha256=sha(cp),author_sha256=sha(__file__),whole_triangles=count,accepted_body_positions_exact=True,source_action_curves_exact=True,original_complete_root_ids_retained=True,source_UV_topology_weights_unedited=True,fins=records,visual_review='pending',formal_acceptance=False);(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
