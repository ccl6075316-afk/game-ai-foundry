exec((__import__('pathlib').Path(__file__).parent/'check_local.py').read_text().split('rows=[]')[0])
from mathutils import Vector
def weight(i,bone):
 return sum(g.weight for g in ob.data.vertices[i].groups if ob.vertex_groups[g.group].name==bone)
toothfaces=[tuple(p.vertices)for p in ob.data.polygons if p.material_index==4]
categories={}
for which in ['jaw_lower','jaw_upper']:
 categories[which]=[f for f in faces if sum(weight(i,which)for i in f)/3>.5]
rows=[]
for t in [0,.7,1.1,1.2,1.38,1.56,1.66,1.8,2.18,2.85,3.3,4.2]:
 scene.frame_set(1);apply(rig,curve(t));bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();v=np.array([list(x.co)for x in m.vertices]);ev.to_mesh_clear();bad=[]
 for ti,f in enumerate(toothfaces):
  own='jaw_upper' if sum(weight(i,'jaw_upper')for i in f)>.5 else 'jaw_lower';other='jaw_lower' if own=='jaw_upper' else 'jaw_upper'
  for j,g in enumerate(categories[other]):
   if intersect(v[list(f)],v[list(g)]):bad.append([ti,other,j])
 def point(native,bone):
  b=rig.pose.bones[bone];return b.matrix@b.bone.matrix_local.inverted()@Vector(native)
 up=point((1.19542694,0,-.26475),'jaw_upper');lo=point((1.189027,0,-.27055),'jaw_lower')
 rows.append({'t':t,'opposing_jaw_contacts':len(bad),'examples':bad[:5],'center_rim_distance_mm':(up-lo).length*1000})
r={'model_sha256':hashlib.sha256((W/'candidate/fish.glb').read_bytes()).hexdigest(),'scope':'12 times, native frame1; tooth triangles vs opposing jaw faces whose mean direct jaw weight >.5. Own base embed intentional; mixed junction faces not covered. Not full continuous collision proof.','samples':rows,'ok':all(x['opposing_jaw_contacts']==0 for x in rows)}
from motion_math import config_file
r['motion_sha256']=hashlib.sha256((W/config_file).read_bytes()).hexdigest()
(W/('teeth-small.validation.json' if config_file=='motion-small.json' else 'teeth.validation.json')).write_text(json.dumps(r,indent=2));print(r)
