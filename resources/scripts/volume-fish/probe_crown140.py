import json,sys
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector
root=Path(sys.argv[sys.argv.index('--')+1])
for s in ['grass_carp','nile_tilapia']:
 cfg=json.loads((root/s/'geometry.plan.json').read_text());d=json.loads(Path(cfg['body']).read_text());vs=[];ts=[];offset=0
 for p in d['parts']:
  vs.extend(p['vertices']);ts.extend((np.array(p['triangles']).reshape(-1,3)+offset).tolist());offset+=len(p['vertices'])
 tree=BVHTree.FromPolygons(vs,ts,all_triangles=True);samples=[]
 for x in np.arange(.39,.495,.005):
  hit,normal,face,dist=tree.ray_cast(Vector((x,.3,0)),Vector((0,-1,0)))
  samples.append([round(float(x),4),round(float(hit.y),6) if hit else None])
 print(s,samples,flush=True)
