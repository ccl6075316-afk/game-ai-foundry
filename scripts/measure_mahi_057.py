"""Read-only experiment-specific landmark and FULL long-fin-base sampling."""
import sys,json,hashlib,math
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parents[1]
profile=root/'resources/volume-fish/mahi-mahi-057e.profile.json'
native=root/'projects/fishing-2d/experiments/blender-fish/models/mahi_mahi/057e.handoff-artifacts/fish.blend'
p=json.loads(profile.read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(native),use_scripts=False)
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
rig.data.pose_position='REST';bpy.context.view_layer.update()
objects=[o for o in scene.objects if o.type=='MESH']
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
cm=120/(max(v.x for v in points)-min(v.x for v in points))
body=bpy.data.objects['Closed_body'];sections=p['body']['sections'];aspect=1/p['source_aspect_ratio']
def interp(u,col):
 for a,b in zip(sections,sections[1:]):
  if a[0]<=u<=b[0]:return a[col]+(b[col]-a[col])*(u-a[0])/(b[0]-a[0])
 return sections[0 if u<sections[0][0] else -1][col]
selections={}
for f in p['fins']:
 if not f['name'].startswith(('Dorsal_','Anal_')):continue
 o=bpy.data.objects[f['name']];col=1 if f['name'].startswith('Dorsal_') else 2
 # Full authored longitudinal base curve; BOTH endpoints and every interior edge point.
 a=min(x[0] for x in f['polygon']);b=max(x[0] for x in f['polygon'])
 av=interp(a,col)+(.004 if col==1 else -.004);bv=interp(b,col)+(.004 if col==1 else -.004)
 ids=[]
 for v in o.data.vertices:
  u=v.co.x+.5;vv=.5-v.co.z/aspect
  target=av+(bv-av)*(u-a)/(b-a)
  if abs(vv-target)<1e-5:ids.append(v.index)
 edges=[list(e.vertices) for e in o.data.edges if all(i in ids for i in e.vertices)]
 if not ids or not edges:raise ValueError('Empty full base '+o.name)
 selections[o.name]=dict(ids=ids,edges=edges)
report=dict(schema_version=1,command='volume.mahi.full-base-landmarks',ok=True,status='done',next_action='human_review',
 blend_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),cm_per_unit=cm,
 full_base_selection='Every rest vertex on the authored longitudinal base line, both solidify faces, every edge wholly in that line, 15 interior samples per edge; no source-t shortcut.',
 source_landmarks=dict(nose_u=.998,caudal_base_u=.178,opercular_back_u=.835),
 measurements={},full_base_samples=[],failures=[])
report['measurements']['standard_length_proxy_cm']=(.998-.178)*cm
report['measurements']['head_length_proxy_cm']=(.998-.835)*cm
eyes=[]
for o in objects:
 if not o.name.startswith('Textured_eye_'):continue
 vs=[o.matrix_world@v.co for v in o.data.vertices]
 eyes.append(dict(name=o.name,geometry_horizontal_cm=(max(v.x for v in vs)-min(v.x for v in vs))*cm,
  geometry_vertical_cm=(max(v.z for v in vs)-min(v.z for v in vs))*cm,
  nose_to_anterior_patch_cm=(.998-.5-max(v.x for v in vs))*cm,
  limitation='Patch bounds include iris donor surround. Eye aperture and biological snout landmark still require pigment interpretation.'))
report['measurements']['eyes']=eyes
paired=[]
for f in p['fins']:
 if not f['paired']:continue
 bone=rig.data.bones[f['name']+'_left']
 paired.append(dict(name=f['name'],actual_bone_root_tip_cm=(bone.tail_local-bone.head_local).length*cm,
  limitation='Authored root-tip axis proxy, not longest curved/anterior fin margin.'))
report['measurements']['paired_fin_axes']=paired
root_positions={name:[[v.co.x,v.co.y,v.co.z] for v in bpy.data.objects[name].data.vertices if v.index in s['ids']] for name,s in selections.items()}
contact_path=root/'output/mahi-057/final-native-contact.validation.json'
if not contact_path.exists():
 contact_path=root/'projects/fishing-2d/plans/reviews/fish-volume-055-058-evidence/057/final-native-contact.validation.json'
native_contact=json.loads(contact_path.read_text(encoding='utf-8'))
caudal_ids=set(native_contact['fins']['Caudal']['root_vertex_indices'])
root_positions['Caudal']=[[v.co.x,v.co.y,v.co.z] for v in bpy.data.objects['Caudal'].data.vertices if v.index in caudal_ids]
roots_path=root/'output/mahi-057/godot/roots.json'
roots_path.parent.mkdir(parents=True,exist_ok=True)
roots_path.write_text(json.dumps(root_positions),encoding='utf-8')
def sample(label):
 deps=bpy.context.evaluated_depsgraph_get();evalbody=body.evaluated_get(deps);mesh=evalbody.to_mesh()
 bvh=BVHTree.FromPolygons([body.matrix_world@v.co for v in mesh.vertices],[list(f.vertices) for f in mesh.polygons]);evalbody.to_mesh_clear()
 row=dict(label=label,fins={})
 for name,s in selections.items():
  obj=bpy.data.objects[name];ev=obj.evaluated_get(deps);mesh=ev.to_mesh();vs=[obj.matrix_world@v.co for v in mesh.vertices]
  pts=[vs[i] for i in s['ids']]
  for a,b in s['edges']:pts.extend(vs[a].lerp(vs[b],k/16) for k in range(1,16))
  vals=[]
  for point in pts:
   near,normal,_,dist=bvh.find_nearest(point);vals.append(dist*cm*(1 if (point-near).dot(normal)>=0 else -1))
  ev.to_mesh_clear();row['fins'][name]=dict(vertices=len(s['ids']),edges=len(s['edges']),sample_points=len(vals),min_cm=min(vals),max_cm=max(vals),pass_contact=max(vals)<=.10 and min(vals)>=-.60)
 report['full_base_samples'].append(row)
sample('rest');rig.data.pose_position='POSE'
for i in range(18):
 frame=(scene.frame_end-scene.frame_start)*i/18
 scene.frame_set(int(frame),subframe=frame%1)
 bpy.context.view_layer.update();sample('native_%02d'%i)
report['full_base_summary']={name:dict(max_gap_cm=max(0,max(s['fins'][name]['max_cm'] for s in report['full_base_samples'])),
 deepest_embedding_cm=-min(0,min(s['fins'][name]['min_cm'] for s in report['full_base_samples'])),
 failed_phases=sum(not s['fins'][name]['pass_contact'] for s in report['full_base_samples'])) for name in selections}
for name,value in report['full_base_summary'].items():
 if value['failed_phases']:report['failures'].append(dict(kind='validation',code='long_fin_full_base_contact',message=name,**value))
report['ok']=not report['failures']
if not report['ok']:report.update(status='failed',next_action='fix_input')
out=root/'output/mahi-057/full-base-landmarks.validation.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(ok=report['ok'],measurements=report['measurements'],summary=report['full_base_summary'])))
