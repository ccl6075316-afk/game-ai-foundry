"""Read-only anatomical/packed fin compatibility before a wall-only UV repair."""
import bpy,json,hashlib,sys
from pathlib import Path
from mathutils.kdtree import KDTree
ROOT=Path('E:/game-ai-foundry');base=ROOT/'projects/fishing-2d/experiments/red-seabream-lowpoly-sop-20261101'
packed=base/'eye-small-r2-20261101/candidate/author/fish.blend'
bpy.ops.wm.open_mainfile(filepath=str(packed));ob=next(o for o in bpy.data.objects if o.type=='MESH');m=ob.data
parts=json.loads(m['foundry_geometry_parts_json']);ids=[round(v.value)for v in m.attributes['foundry_part_id'].data] if 'foundry_part_id'in m.attributes else None
if ids is None:
 sys.path.insert(0,str(ROOT/'resources/scripts/volume-fish'));from export_packed_fish_source import PART_ID
 ids=[round(v.value)for v in m.attributes[PART_ID].data]
targets={p['source_node']:[tuple(v.co)for v in m.vertices if ids[v.index]==p['part_id']]for p in parts if p['role']=='fin'}
rows=[]
for relative in ['eye-small-r2-20261101/body-chart/fish.blend','eye-small-r2-20261101/body-input/fish.blend','neck-transition-20261101/candidate-r2/anatomical-witness/fish.blend','neck-transition-20261101/candidate/anatomical-witness/fish.blend','clearance-r1/anatomical-witness/fish.blend','native-fin-cages-r2/fish.blend','pbr-r3/fish.blend']:
 p=base/relative
 if not p.exists():continue
 bpy.ops.wm.open_mainfile(filepath=str(p));fins=[]
 for name,coords in targets.items():
  o=bpy.data.objects.get(name)
  if o is None or 'foundry_fin_source_u'not in o.data.attributes:fins.append({'name':name,'compatible':False});continue
  kd=KDTree(len(o.data.vertices))
  for v in o.data.vertices:kd.insert(v.co,v.index)
  kd.balance();distance=max(kd.find(c)[2]for c in coords)
  fins.append({'name':name,'source_vertices':len(o.data.vertices),'packed_vertices':len(coords),'maximum_native_distance':distance,'compatible':distance<2e-6,'source_uv_attributes':True})
 rows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'all_seven_compatible':len(fins)==7 and all(x['compatible']for x in fins),'fins':fins})
out=ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104/red_seabream/wall-source-compatibility.validation.json'
out.write_text(json.dumps({'ok':any(x['all_seven_compatible']for x in rows),'packed_source':str(packed),'packed_sha256':hashlib.sha256(packed.read_bytes()).hexdigest(),'sources':rows},indent=2)+'\n')
print(json.dumps([{'path':x['path'],'all_seven_compatible':x['all_seven_compatible'],'maximum':max([r.get('maximum_native_distance',1)for r in x['fins']])}for x in rows]))
