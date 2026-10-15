"""Exact native baseline/candidate comparison; no accepted source writes."""
from pathlib import Path
import bpy,json,hashlib
root=Path(__file__).resolve().parents[1]
base=root/'projects/fishing-2d/experiments/blender-fish/models/arapaima'
original=base/'044-arapaima-v11.handoff-artifacts/fish.blend'
target=base/'058d-mouth.handoff-artifacts/fish.blend'
p=json.loads((root/'resources/volume-fish/arapaima-mouth-058d.profile.json').read_text(encoding='utf-8'))
def capture(path):
 bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False)
 data={}
 for obj in bpy.context.scene.objects:
  if obj.type!='MESH':continue
  data[obj.name]=dict(vertices=[tuple(v.co) for v in obj.data.vertices],faces=[tuple(f.vertices) for f in obj.data.polygons],
   uv=[tuple(v.uv) for v in obj.data.uv_layers.active.data],
   weights=[{obj.vertex_groups[g.group].name:round(g.weight,7) for g in v.groups} for v in obj.data.vertices])
 return data
a=capture(original);b=capture(target)
checks=dict(objects_unchanged=set(a)==set(b),topology_unchanged=True,uv_unchanged=True,body_before_u_865_unchanged=True,
 unpaired_fin_geometry_unchanged=True,paired_distal_geometry_unchanged=True,projected_root_own_fin_weight_zero=True)
details={}
for name,old in a.items():
 new=b[name];checks['topology_unchanged'] &= old['faces']==new['faces'] and len(old['vertices'])==len(new['vertices'])
 checks['uv_unchanged'] &= old['uv']==new['uv']
 errors=[sum((x-y)**2 for x,y in zip(v,w))**.5 for v,w in zip(old['vertices'],new['vertices'])]
 details[name]=dict(max_vertex_displacement=max(errors),changed_vertices=sum(v>1e-7 for v in errors))
 if name in ['Closed_body','Frontal_head_overlay']:
  checks['body_before_u_865_unchanged'] &= all(e<1e-7 for v,e in zip(old['vertices'],errors) if v[0]+.5<=.865)
 for fin in p['fins']:
  if name==fin['name'] and not fin['paired']:checks['unpaired_fin_geometry_unchanged'] &= max(errors)<1e-7
  if fin['paired'] and name in [fin['name']+'_left',fin['name']+'_right']:
   t=[v.value for v in bpy.data.objects[name].data.attributes['foundry_fin_source_t'].data]
   checks['paired_distal_geometry_unchanged'] &= all(e<1e-7 for value,e in zip(t,errors) if value>=.35)
   checks['projected_root_own_fin_weight_zero'] &= all(w.get(name,0)<1e-7 for value,w in zip(t,new['weights']) if value<=.0500001)
out=root/'output/arapaima-mouth-058/native-preservation.validation.json'
report=dict(schema_version=1,command='volume.arapaima.native-preservation',ok=all(checks.values()),status='done' if all(checks.values()) else 'failed',
 next_action='human_review',baseline_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),checks=checks,details=details,failures=[])
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report['checks']))
assert report['ok']
