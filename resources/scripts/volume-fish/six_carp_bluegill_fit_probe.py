"""Read-only finite static-body probe for the measured detached bluegill pectorals."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
base=Path(__file__).resolve().parents[3]/'projects/fishing-2d/experiments/six-fish-database-20261104/bluegill';sample=base/'delivery-r2/fin490/bluegill/sample-000.json';d=json.loads(sample.read_text());tree=BVHTree.FromPolygons([Vector(v)for v in d['body_vertices_m']],d['body_triangles'],all_triangles=True);rows=[]
for amount in [i*.00005 for i in range(16,33)]:
 vals=[]
 for name in ['Pectoral_left_mesh','Pectoral_right_mesh']:
  points=d['roots'][name]['points_m'];sign=1 if sum(p[2]for p in points)>0 else -1
  for v in points:
   p=Vector(v);p.z-=sign*amount;loc,n,face,dist=tree.find_nearest(p);signed=dist if (p-loc).dot(n)<0 else -dist;vals.append(signed*1000)
 rows.append({'offset_inward_Z_mm':amount*1000,'static_min_signed_mm':min(vals),'static_max_signed_mm':max(vals),'static_margin_score':max(max(vals)-.696,-.228-min(vals),0)})
out=base/'pectoral-static-fit-probe.validation.json';out.write_text(json.dumps({'kind':'read_only_static_pectoral_offset_probe','poses':1,'known_old_490_dynamic_minimum_below_static_mm':.272,'known_old_490_dynamic_maximum_above_static_mm':.304,'options':rows,'scope':'Exact static posed-body BVH probing. Old dynamic spread only guides proposal; new full490 needed. No geometry changed or tolerance relaxed.'},indent=2)+'\n');print(json.dumps(sorted(rows,key=lambda r:r['static_margin_score'])[:4]))
