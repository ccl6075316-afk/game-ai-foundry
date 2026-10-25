"""Transport a dense static overlay through exact old/new support triangles.

Applying a nonlinear field separately to dense overlays and coarse body faces
does not preserve finite contact. Keep topology/UV/skin and actual support IDs.
"""
import json,sys,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
def arrays(path):
 d=json.loads(Path(path).read_text());v=[];t=[]
 for p in d['parts']:
  o=len(v);v.extend(Vector(q)for q in p['vertices']);ids=p['triangles'];t.extend(tuple(o+j for j in ids[i:i+3])for i in range(0,len(ids),3))
 return v,t
def main():
 args=sys.argv[sys.argv.index('--')+1:];p=json.loads(Path(args[0]).read_text());old,tr=arrays(p['old_body']);new,tr2=arrays(p['new_body']);assert tr==tr2
 if sum(old[a].dot(old[b].cross(old[c]))for a,b,c in tr)<0:tr=[tuple(reversed(t))for t in tr]
 tree=BVHTree.FromPolygons(old,tr,all_triangles=True);d=json.loads(Path(p['overlay']).read_text());rows=[]
 for part in d['parts']:
  out=[];heights=[]
  for q in part['vertices']:
   q=Vector(q);hit,n,face,dist=tree.find_nearest(q);aa,bb,cc=tr[face];bw=barycentric_transform(hit,old[aa],old[bb],old[cc],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));base=new[aa]*bw.x+new[bb]*bw.y+new[cc]*bw.z;normal=(new[bb]-new[aa]).cross(new[cc]-new[aa]).normalized()
   signed=dist if(q-hit).dot(n)>=0 else-dist
   height=max(p['minimum_offset_native'],min(p['maximum_offset_native'],signed));out.append(list(base+normal*height));heights.append(height)
  part['vertices']=out;rows.append({'part':part['name'],'height_min_max':[min(heights),max(heights)]})
 Path(p['output']).write_text(json.dumps(d,separators=(',',':')))
 Path(p['output']+'.transport.validation.json').write_text(json.dumps({'ok':True,'plan_sha256':hashlib.sha256(Path(args[0]).read_bytes()).hexdigest(),'rows':rows,'scope':'Exact finite support identity; final overlay vertices/edges/faces contact still required.'},indent=2));print(json.dumps(rows))
if __name__=='__main__':main()
