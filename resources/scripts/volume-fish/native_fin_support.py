"""Low-point source-alpha support with an independent concave basal boundary."""
import numpy as np
from refine_native_fin_cages import support_polygon

def area2(a,b,c):
 v=b-a;w=c-a;return v[0]*w[1]-v[1]*w[0]

def polygon(mask,root,sides,side,margin=2.5,subpixel_tolerance=0):
 """Clip only the body side of a convex free-edge support to the native root.

 A convex hull alone fills the fish body below a long curved dorsal base. That
 transparent support is not a free membrane and must not be projected as one.
 """
 hull=support_polygon(mask,sides);root=np.asarray(root,float)
 transpose=side in ('left','right')
 if transpose:hull=hull[:,::-1];root=root[:,::-1]
 root=root[np.argsort(root[:,0])];assert np.all(np.diff(root[:,0])>0)
 above=side in ('above','left')
 def bounds(x):
  ys=[]
  for a,b in zip(hull,np.roll(hull,-1,axis=0)):
   if min(a[0],b[0])-1e-7<=x<=max(a[0],b[0])+1e-7:
    if abs(a[0]-b[0])<1e-8:ys.extend([a[1],b[1]])
    else:ys.append(a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0]))
  assert ys;return min(ys),max(ys)
 xx=sorted(set([*hull[:,0],*root[(root[:,0]>hull[:,0].min())&(root[:,0]<hull[:,0].max()),0]]));extra=[]
 def diff(x):
  lo,hi=bounds(x);r=np.interp(x,root[:,0],root[:,1]);return (hi-r-margin)if above else(lo-r+margin)
 for x,y in zip(xx,xx[1:]):
  a,b=diff(x),diff(y)
  if a*b<0:extra.append(x+(y-x)*(-a)/(b-a))
 xx=sorted(set(xx+extra));top=[];bottom=[]
 for x in xx:
  lo,hi=bounds(x);r=np.interp(x,root[:,0],root[:,1]);lo=lo if above else max(lo,r-margin);hi=min(hi,r+margin)if above else hi
  if lo<=hi+1e-7:top.append(np.array([x,lo]));bottom.append(np.array([x,hi]))
 pts=top+bottom[::-1];clean=[]
 for q in pts:
  if not clean or np.linalg.norm(q-clean[-1])>1e-6:clean.append(q)
 if np.linalg.norm(clean[-1]-clean[0])<1e-6:clean.pop()
 changed=True
 while changed:
  changed=False
  for i in range(len(clean)):
   aa,qq,bb=clean[i-1],clean[i],clean[(i+1)%len(clean)];vv=bb-aa;tt=float(np.dot(qq-aa,vv)/max(np.dot(vv,vv),1e-12));error=float(np.linalg.norm(qq-aa-np.clip(tt,0,1)*vv))
   if abs(area2(aa,qq,bb))<1e-5 or(subpixel_tolerance>0 and 0<tt<1 and error<=subpixel_tolerance):
    clean.pop(i);changed=True;break
 result=np.array(clean)
 if transpose:result=result[:,::-1]
 return result

def triangulate(poly):
 """Ear clipping preserves the complete concave root chain (no convex fill)."""
 poly=np.asarray(poly);ids=list(range(len(poly)));signed=sum(area2(np.zeros(2),poly[i],poly[(i+1)%len(poly)])for i in ids)
 if signed<0:ids.reverse()
 triangles=[]
 while len(ids)>3:
  found=False
  for k,b in enumerate(ids):
   a=ids[k-1];c=ids[(k+1)%len(ids)]
   if area2(poly[a],poly[b],poly[c])<=1e-8:continue
   if any(min(area2(poly[a],poly[b],poly[j]),area2(poly[b],poly[c],poly[j]),area2(poly[c],poly[a],poly[j]))>=-1e-8 for j in ids if j not in (a,b,c)):continue
   triangles.append((a,b,c));ids.pop(k);found=True;break
  assert found,'Invalid independent fin support polygon'
 triangles.append(tuple(ids));return np.array(triangles,dtype=int)

def improve_interior_edges(points,triangles):
 """Constrained Lawson flips: preserve the complete outer/root polygon.

 Ear partitions alone can bypass later foil controls with long tip-to-root
 triangles. Interior flips connect nearby thickness controls without new faces.
 """
 points=np.asarray(points);triangles=np.array(triangles,int).copy()
 def ccw(f):return f if area2(*points[list(f)])>0 else(f[0],f[2],f[1])
 for iteration in range(10000):
  owners={}
  for i,f in enumerate(triangles):
   for a,b in zip(f,np.roll(f,-1)):owners.setdefault(tuple(sorted((int(a),int(b)))),[]).append(i)
  changed=False
  for (a,b),faces in owners.items():
   if len(faces)!=2:continue
   i,j=faces;c=next(int(v)for v in triangles[i]if v not in(a,b));d=next(int(v)for v in triangles[j]if v not in(a,b))
   if area2(points[a],points[b],points[c])*area2(points[a],points[b],points[d])>=-1e-8 or area2(points[c],points[d],points[a])*area2(points[c],points[d],points[b])>=-1e-8:continue
   q=points[[a,b,c]]-points[d];matrix=np.c_[q,(q*q).sum(1)];inside=np.linalg.det(matrix)*area2(points[a],points[b],points[c])
   if inside<=1e-5:continue
   triangles[i]=ccw((c,d,a));triangles[j]=ccw((d,c,b));changed=True;break
  if not changed:return triangles
 raise AssertionError('Constrained interior triangulation failed to converge')
