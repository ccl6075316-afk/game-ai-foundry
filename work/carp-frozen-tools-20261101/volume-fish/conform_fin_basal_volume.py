"""Adapt only finite basal faces that cut through a changed body support.

Conforming edge splits preserve closed topology and UVs. Every new full-basal
point is projected/skinned to the actual body, without enlarging the root collar.
"""
from pathlib import Path
import sys,json,copy,struct,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from patch_existing_fin_meshes import read,write
from repair_fin_clearance import values
from subdivide_fin_contact import midpoint
from closed_body_index140 import build
import numpy as np
def main():
 args=sys.argv[sys.argv.index('--')+1:];p=json.loads(Path(args[0]).read_text());spec=p['items'][0];out=Path(args[1]);out.mkdir(parents=True,exist_ok=True);d,b=read(spec['model']);original=bytes(b);body=json.loads(Path(spec['repair_body_geometry']).read_text());v=[];tr=[];skin=[]
 assert hashlib.sha256(Path(spec['repair_body_geometry']).read_bytes()).hexdigest()==spec['repair_body_geometry_sha256']
 for part in body['parts']:
  off=len(v);v.extend(Vector(q)for q in part['vertices']);ids=part['triangles'];tr.extend(tuple(off+j for j in ids[i:i+3])for i in range(0,len(ids),3));skin.extend(dict(zip(j,w))for j,w in zip(part['joints'],part['weights']))
 if sum(v[a].dot(v[c].cross(v[e]))for a,c,e in tr)<0:tr=[tuple(reversed(t))for t in tr]
 tree=BVHTree.FromPolygons(v,tr,all_triangles=True);inside=build(np.array(v),np.array(tr));scale=spec['scale_cm']/100;limit=.00044/scale;inset=.0002/scale;records=[]
 def attach(row):
  hit,n,face,_=tree.find_nearest(Vector(row['POSITION']));row['POSITION']=tuple(hit-n*inset);aa,bb,cc=tr[face];bw=barycentric_transform(hit,v[aa],v[bb],v[cc],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));mix={}
  for vi,g in zip((aa,bb,cc),bw):
   for bone,w in skin[vi].items():mix[bone]=mix.get(bone,0)+max(0,g)*w
  items=sorted(mix.items(),key=lambda x:-x[1])[:4]
  while len(items)<4:items.append((0,0.))
  total=sum(x[1]for x in items);row['JOINTS_0']=tuple(x[0]for x in items);row['WEIGHTS_0']=tuple(x[1]/total for x in items)
 def put(idx,rows):
  a=copy.deepcopy(d['accessors'][idx]);fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
  if a['type']=='SCALAR'and max(r[0]for r in rows)>65535:fmt='I';a['componentType']=5125
  b.extend(b'\0'*(-len(b)%4));off=len(b)
  for row in rows:b.extend(struct.pack('<'+fmt*len(row),*row))
  a.update(bufferView=len(d['bufferViews']),byteOffset=0,count=len(rows));a.pop('min',None);a.pop('max',None)
  if a['type']=='VEC3':a.update(min=[min(q[k]for q in rows)for k in range(3)],max=[max(q[k]for q in rows)for k in range(3)])
  d['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(b)-off});d['accessors'].append(a);return len(d['accessors'])-1
 for name in spec['membrane_clearance']['targets']:
  node=next(n for n in d['nodes']if n.get('name')==name and'mesh'in n);prim=d['meshes'][node['mesh']]['primitives'][0];attrs={key:values(d,b,idx)for key,idx in prim['attributes'].items()};roots=set(spec['fins'][name]['ids']);rows=[{**{key:value[i]for key,value in attrs.items()},'root':i in roots}for i in range(len(attrs['POSITION']))];indices=values(d,b,prim['indices']);tri=[tuple(x[0]for x in indices[k:k+3])for k in range(0,len(indices),3)];original_count=len(rows);history=[]
  for iteration in range(10):
   marked=set();failed=0;worst=0.
   for t in tri:
    if not all(rows[i]['root']for i in t):continue
    pts=[Vector(rows[i]['POSITION'])for i in t];a,c,e=pts;probes=[(a+c+e)/3,a*.6+c*.2+e*.2,a*.2+c*.6+e*.2,a*.2+c*.2+e*.6]+[a.lerp(c,fraction)for a,c in zip(pts,pts[1:]+pts[:1])for fraction in [.25,.5,.75]];bad=False
    for q in probes:
     dist=tree.find_nearest(q)[3]
     if dist>limit and inside(q):bad=True;worst=min(worst,-dist)
    if bad:
     failed+=1;edges=[tuple(sorted((a,c)))for a,c in zip(t,t[1:]+t[:1])];marked.add(max(edges,key=lambda e:(Vector(rows[e[0]]['POSITION'])-Vector(rows[e[1]]['POSITION'])).length))
   history.append({'round':iteration,'failed_basal_faces':failed,'worst_mm':worst*scale*1000,'split_edges':len(marked)})
   if not marked:break
   added={}
   for edge in sorted(marked):
    row=midpoint(rows[edge[0]],rows[edge[1]]);assert row['root'];attach(row);added[edge]=len(rows);rows.append(row)
   rebuilt=[]
   for t in tri:
    pieces=[t]
    for a,c in zip(t,t[1:]+t[:1]):
     mid=added.get(tuple(sorted((a,c))))
     if mid is None:continue
     split=[]
     for piece in pieces:
      if a not in piece or c not in piece:split.append(piece);continue
      for k in range(3):
       x,y,z=piece[k],piece[(k+1)%3],piece[(k+2)%3]
       if {x,y}=={a,c}:split.extend([(x,mid,z),(mid,y,z)]);break
     pieces=split
    rebuilt.extend(pieces)
   tri=rebuilt
  assert not marked,'Basal face adaptation failed to converge: '+name
  if len(rows)==original_count:records.append({'name':name,'added_vertices':0,'history':history});continue
  normals=[Vector()for _ in rows]
  for aa,bb,cc in tri:
   n=(Vector(rows[bb]['POSITION'])-Vector(rows[aa]['POSITION'])).cross(Vector(rows[cc]['POSITION'])-Vector(rows[aa]['POSITION']))
   for i in (aa,bb,cc):normals[i]+=n
  for i,row in enumerate(rows):
   if normals[i].length>1e-12:row['NORMAL']=tuple(normals[i].normalized())
  for key,idx in list(prim['attributes'].items()):prim['attributes'][key]=put(idx,[r[key]for r in rows])
  prim['indices']=put(prim['indices'],[(j,)for t in tri for j in t]);ids=[i for i,r in enumerate(rows)if r['root']];spec['fins'][name].update(ids=ids,rest_points_gltf=[list(rows[i]['POSITION'])for i in ids],vertices=len(rows));records.append({'name':name,'added_vertices':len(rows)-original_count,'history':history})
 assert bytes(b[:len(original)])==original;target=out/'fish.glb';write(target,d,b);spec.update(model=str(target.resolve()),model_sha256=hashlib.sha256(target.read_bytes()).hexdigest());(out/'candidate.plan.json').write_text(json.dumps(p,indent=2));report={'ok':True,'records':records,'model_sha256':spec['model_sha256'],'scope':'Only failing finite all-root faces adapted. Existing complete root selection retained and new roots recorded; frozen0.5mm collar unchanged. Independent whole-fin GPU/posed validation required.'};(out/'repair.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
