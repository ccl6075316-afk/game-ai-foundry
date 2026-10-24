"""Blender: preserve retained paired source charts while correcting real clearance.

This is a physical placement/skin repair, not an independently reconstructed fin
shape. Full original basal selection remains frozen, with conforming subdivision.
"""
import json,sys,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform
sys.path.insert(0,str(Path(__file__).parent))
from subdivide_fin_contact import refine
from closed_body_index140 import build as closed_index
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(t):t=max(0.,min(1.,t));return t*t*(3-2*t)
def main():
 p=read(sys.argv[sys.argv.index('--')+1]);source=read(p['source_mesh']);old=read(p['source_fin_plan'])['items'];spec=next(x for x in old if x['species']==p['species']);scale=p['model_scale_m_per_native'];positions=[];triangles=[];skins=[];body_names=source['body'][0]['skin_joint_names']
 for body in source['body']:
  for part in body['parts']:
   offset=len(positions);positions.extend(Vector(v)for v in part['rest_vertices']);ids=part['triangles'];triangles.extend(tuple(offset+i for i in ids[k:k+3])for k in range(0,len(ids),3));skins.extend(dict(zip(j,w))for j,w in zip(part['joints'],part['weights']))
 tree=BVHTree.FromPolygons(positions,triangles,all_triangles=True);inside=closed_index([list(q)for q in positions],triangles);out=Path(p['output']);out.mkdir(parents=True,exist_ok=True);built=read(p['new_source_fins']);roots=read(p['new_source_roots']);records=[]
 for fin in source['fins']:
  name=fin['name']
  if name not in p['targets']:continue
  names=fin['skin_joint_names'];bodymap=[names.index(n)for n in body_names];rootpoints=[Vector(q)for q in spec['fins'][name]['rest_points_gltf']];kd=KDTree(len(rootpoints))
  for i,q in enumerate(rootpoints):kd.insert(q,i)
  kd.balance();parts=[];newroots=[];rootids=[];offset=0;maximum=0.;newcount=0
  for part in fin['parts']:
   rows=[{'POSITION':tuple(v),'NORMAL':tuple(n),'TEXCOORD_0':tuple(uv),'JOINTS_0':tuple(j),'WEIGHTS_0':tuple(w),'root':kd.find(Vector(v))[2]<.00003}for v,n,uv,j,w in zip(part['rest_vertices'],part['normals'],part['uv'],part['joints'],part['weights'])];ids=part['triangles'];rows,tr,refinement=refine(rows,[tuple(ids[k:k+3])for k in range(0,len(ids),3)],p.get('contact_edge_m',.003)/scale,lambda q:tree.find_nearest(Vector(q))[3]<.004/scale);side=1 if sum(r['POSITION'][2]for r in rows)>0 else-1;newcount+=refinement['added_vertices'];points=[]
   for i,row in enumerate(rows):
    before=Vector(row['POSITION']);q=before.copy();hit,normal,face,_=tree.ray_cast(Vector((q.x,q.y,side*2)),Vector((0,0,-side)),4.)
    if hit is None:hit,normal,face,_=tree.find_nearest(q)
    if normal.z*side<0:normal=-normal
    if row['root']:q.z=hit.z+side*.00004/scale
    else:
     root_dist=kd.find(before)[2];clearance=(.00024+.0015*smooth(root_dist*scale/.006))/scale;q.z=side*max(side*q.z,side*hit.z+clearance)
     near,nn,_,dist=tree.find_nearest(q)
     if inside(q)or dist<.00018/scale:
      direction=(near-q)if inside(q)else(q-near)
      if direction.length<1e-9:direction=normal
      q=near+direction.normalized()*.00018/scale
    near,_,face,_=tree.find_nearest(q);aa,bb,cc=triangles[face];bary=barycentric_transform(near,positions[aa],positions[bb],positions[cc],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));amount=1. if row['root']else 1.-smooth(kd.find(before)[2]*scale/.006);weights={}
    for vi,bw in zip([aa,bb,cc],bary):
     for j,w in skins[vi].items():weights[bodymap[j]]=weights.get(bodymap[j],0)+max(0,bw)*w*amount
    for j,w in zip(row['JOINTS_0'],row['WEIGHTS_0']):weights[j]=weights.get(j,0)+w*(1-amount)
    pairs=sorted(weights.items(),key=lambda x:-x[1])[:4]
    while len(pairs)<4:pairs.append((0,0.))
    total=sum(w for j,w in pairs);row['JOINTS_0']=tuple(j for j,w in pairs);row['WEIGHTS_0']=tuple(w/total for j,w in pairs);points.append(q);maximum=max(maximum,(q-before).length)
    if row['root']:newroots.append(list(q));rootids.append(offset+i)
   normals=[Vector()for q in points]
   for a,b,c in tr:
    n=(points[b]-points[a]).cross(points[c]-points[a])
    for vi in [a,b,c]:normals[vi]+=n
   normals=[n.normalized()if n.length>1e-12 else Vector((0,0,side))for n in normals];parts.append({'surface':part['surface'],'vertices':[list(q)for q in points],'normals':[list(n)for n in normals],'uv':[list(r['TEXCOORD_0'])for r in rows],'joints':[list(r['JOINTS_0'])for r in rows],'weights':[list(r['WEIGHTS_0'])for r in rows],'triangles':[j for t in tr for j in t]});offset+=len(rows)
  assert newroots;texture=fin['parts'][0]['texture'];built['fins'].append({'name':name,'skin_joint_names':names,'parts':parts,'texture':texture['path'],'texture_sha256':texture['sha256'],'scope':'Original retained native chart and XY outline; contact refinement/Z placement and root skin corrected, not a new source-shape reconstruction.'});roots[name]={**spec['fins'][name],'ids':rootids,'rest_points_gltf':newroots,'vertices':offset,'rule':'Complete previous basal selection retained through conforming contact subdivision; mapped onto actual body and body weights.'};records.append({'name':name,'original_source_chart_sha256':texture['sha256'],'original_xy_chart_preserved':True,'max_displacement_native':maximum,'refinement_vertices':newcount,'root_vertices':len(newroots)})
 (out/'fins.final.json').write_text(json.dumps(built));(out/'roots.final.json').write_text(json.dumps(roots));(out/'retained-repair.validation.json').write_text(json.dumps({'ok':len(records)==len(p['targets']),'records':records,'source_mesh_sha256':sha(p['source_mesh']),'scope':'Physical placement/skin preparation only; actual177/490 and GPU gates still required. No biological source silhouette approval.'},indent=2));print(json.dumps(records))
if __name__=='__main__':main()
