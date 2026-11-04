"""Exact projected triangle overlay: whole front eye versus finite body.

Every eye/body projected intersection polygon is linear in depth. Its vertices
therefore suffice to bound side-view occlusion across each complete triangle;
no pupil-only selection or vertex-only contact proxy is used.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from portable.glb_io import read_glb,arrays
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def clip(poly,tri):
 sign=1 if cross(tri[1]-tri[0],tri[2]-tri[0])>0 else -1
 for a,b in zip(tri,np.roll(tri,-1,axis=0)):
  result=[]
  if not len(poly):return []
  for p,q in zip(poly,np.roll(poly,-1,axis=0)):
   u=sign*cross(b-a,p-a);v=sign*cross(b-a,q-a)
   if u>=-1e-12:result.append(p)
   if (u>=0)!=(v>=0):result.append(p+(q-p)*u/(u-v))
  poly=result
 return poly
def depth(tri,p):
 a,b,c=tri;den=cross(b[:2]-a[:2],c[:2]-a[:2]);v=cross(p-a[:2],c[:2]-a[:2])/den;w=cross(b[:2]-a[:2],p-a[:2])/den;return a[2]+v*(b[2]-a[2])+w*(c[2]-a[2])
def check(path):
 d,b=read_glb(path)
 def triangles(name):
  n=next(n for n in d['nodes']if n.get('name')==name);ts=[]
  for p in d['meshes'][n['mesh']]['primitives']:
   v=arrays(d,b,p['attributes']['POSITION']).astype(float);ts.extend(v[arrays(d,b,p['indices']).reshape(-1,3)])
  return np.array(ts)
 body=triangles('Reference_head_body');body=body[np.abs(np.cross(body[:,1]-body[:,0],body[:,2]-body[:,0])[:,2])>1e-14];lo=body[:,:,:2].min(1);hi=body[:,:,:2].max(1);rows=[]
 for name in ['Eye_left','Eye_right']:
  eye=triangles(name);side=1 if eye[:,:,2].mean()>0 else -1;normal=np.cross(eye[:,1]-eye[:,0],eye[:,2]-eye[:,0]);front=eye[normal[:,2]*side>1e-14];dist=[];polygons=0
  for t in front:
   mn=t[:,:2].min(0);mx=t[:,:2].max(0);ids=np.flatnonzero(np.all(hi>=mn-1e-12,axis=1)&np.all(lo<=mx+1e-12,axis=1))
   for k in ids:
    poly=clip(list(t[:,:2]),body[k,:,:2])
    if not len(poly):continue
    polygons+=1
    for q in poly:dist.append(side*(depth(t,q)-depth(body[k],q)))
  assert dist and len(front)==24
  rows.append(dict(name=name,front_triangles=len(front),intersection_polygons=polygons,exact_polygon_vertices=len(dist),minimum_front_clearance_mm=float(min(dist)*1000),maximum_front_clearance_mm=float(max(dist)*1000),occluded_vertices=int(sum(x< -1e-7 for x in dist)),ok=bool(min(dist)>=-.0000001)))
 return rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',type=Path,required=True);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();rows=check(a.model);old=check(a.baseline);r=dict(ok=all(x['ok']for x in rows)and not all(x['ok']for x in old),kind='complete_finite_eye_front_body_projection_visibility',model_sha256=hashlib.sha256(a.model.read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256(a.baseline.read_bytes()).hexdigest(),current=rows,rejected_baseline=old,scope='Whole24 front faces per eye, all finite projected eye/body triangle intersections; rear half deliberately embedded. Oblique/other views and actual motion/GPU review remain separate. No reduced iris/pupil domain.');a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if r['ok']else 1
if __name__=='__main__':raise SystemExit(main())
