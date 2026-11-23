import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;O=R/'motion-r5';reports=[];original=None;shape_error=0.
for version in ['motion-r4','motion-r5']:
 bpy.ops.wm.open_mainfile(filepath=str(R/version/'octopus-actions.blend'));skin=bpy.data.objects['Octopus_gray_skin'];cups=bpy.data.objects['Paired_sucker_rows_512_cups'];tree=BVHTree.FromPolygons([v.co for v in skin.data.vertices],[list(f.vertices)for f in skin.data.polygons],all_triangles=True)
 adjacent=[set()for v in cups.data.vertices]
 for e in cups.data.edges:
  a,b=e.vertices;adjacent[a].add(b);adjacent[b].add(a)
 unseen=set(range(len(adjacent)));groups=[];positions=[v.co.copy()for v in cups.data.vertices]
 while unseen:
  todo=[min(unseen)];unseen.remove(todo[0]);ids=[]
  while todo:
   i=todo.pop();ids.append(i)
   for j in adjacent[i]:
    if j in unseen:unseen.remove(j);todo.append(j)
  groups.append(sorted(ids))
 samples=[]
 for ids in groups:
  assert len(ids)==24
  anchor=sum((positions[i]for i in ids[:8]),Vector())/8
  hit,n,fi,dist=tree.find_nearest(anchor);signed=(anchor-hit).dot(n)
  samples.append({'first_vertex':ids[0],'base_anchor_signed_distance':signed,'base_anchor_distance':dist})
  if original is not None:
   delta=positions[ids[0]]-original[ids[0]];shape_error=max(shape_error,max((positions[i]-original[i]-delta).length for i in ids))
 reports.append({'version':version,'source_sha256':hashlib.sha256((R/version/'octopus-actions.blend').read_bytes()).hexdigest(),'cup_count':len(groups),'min_signed_distance':min(s['base_anchor_signed_distance']for s in samples),'max_signed_distance':max(s['base_anchor_signed_distance']for s in samples),'samples':samples})
 if original is None:original=positions
old=reports[0]['samples'];new=reports[1]['samples'];change=max(abs(a['base_anchor_signed_distance']-b['base_anchor_signed_distance'])for a,b in zip(old,new));checks={'all_512_cup_shapes_preserved_by_translation':shape_error<1e-6 and all(r['cup_count']==512 for r in reports),'no_new_detached_anchor':all(b['base_anchor_signed_distance']<max(.002,a['base_anchor_signed_distance']+.001)for a,b in zip(old,new))}
d={'ok':all(checks.values()),'checks':checks,'model_sha256':hashlib.sha256((O/'octopus-actions.glb').read_bytes()).hexdigest(),'max_cup_shape_error':shape_error,'max_anchor_signed_distance_change':change,'versions':reports,'limits':['Rest-space base-ring center support only; not comprehensive cup rim/skin contact or suction']};(O/'support.validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items()if k!='versions'}))
