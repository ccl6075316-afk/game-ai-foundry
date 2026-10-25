"""Correct actual finite overlay probes at sharp support-face junctions.

No tolerance changes. Only vertices incident to failing probes are displaced
along the actual support normal. Keep all source UV, skin and topology.
"""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from closed_body_index140 import build
def main():
 args=sys.argv[sys.argv.index('--')+1:];body=json.loads(Path(args[0]).read_text());overlay=json.loads(Path(args[1]).read_text());v=[];tr=[]
 for p in body['parts']:
  o=len(v);v.extend(p['vertices']);tr.extend((np.array(p['triangles']).reshape(-1,3)+o).tolist())
 vv=[Vector(q)for q in v]
 if sum(vv[a].dot(vv[b].cross(vv[c]))for a,b,c in tr)<0:tr=[list(reversed(t))for t in tr]
 tree=BVHTree.FromPolygons(vv,tr,all_triangles=True);inside=build(np.array(v),np.array(tr));records=[]
 for part in overlay['parts']:
  positions=[Vector(q)for q in part['vertices']];tri=np.array(part['triangles']).reshape(-1,3);history=[]
  for iteration in range(8):
   corrections={};worst=0.;fail=0
   for ids in tri:
    aa,bb,cc=[positions[i]for i in ids]
    probes=[aa,bb,cc,(aa+bb)*.5,(aa+cc)*.5,(bb+cc)*.5,(aa+bb+cc)/3]
    for point in probes:
     hit,n,face,dist=tree.find_nearest(point);signed=-dist if inside(point)else dist
     if signed>=-.000025:continue
     fail+=1;worst=min(worst,signed);delta=n*(-signed+.000006)
     for j in ids:
      if j not in corrections or corrections[j].length<delta.length:corrections[j]=delta
   history.append({'round':iteration,'failing_probes':fail,'worst_native':worst,'affected_vertices':len(corrections)})
   if not fail:break
   for j,delta in corrections.items():positions[j]+=delta
  assert not fail,'Finite overlay contact failed to converge'
  part['vertices']=[list(q)for q in positions];records.append({'part':part['name'],'history':history})
 Path(args[1]).write_text(json.dumps(overlay,separators=(',',':')));Path(args[2]).write_text(json.dumps({'ok':True,'records':records,'scope':'Local finite probe correction only; external frozen contact gate still required.'},indent=2));print(json.dumps(records))
if __name__=='__main__':main()
