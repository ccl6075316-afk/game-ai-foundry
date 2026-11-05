"""Closed native-mask caudal with a true concave terminal notch.

A horizontal single-interval loft cannot represent every shark caudal. This
alternative keeps the entire finite contour in a constrained planar mesh.
Construction stage only: it does not certify the full transverse tail cap.
Match the actual body with rebuild_shark_tail_cap and validate every current
cap latitude before calling the result a review candidate.
"""
from pathlib import Path
import math
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

def build(row,cfg,body_vertices):
    scale=cfg['metres_per_source_pixel'];axis=cfg['axis'];leading=np.asarray(row['root_endpoints_px'][0]);root=np.asarray(row['root_curve_px']);canvas_h=row['source_canvas_height_px']
    points=row['cdt_points_px'];boundary=np.array(points[:row['cdt_boundary_count']]);
    vv,_,ff,*_=delaunay_2d_cdt([Vector(v)for v in points],[],[list(range(len(boundary)))],2,1e-5,False)
    assert ff and all(len(f)==3 for f in ff)
    p=np.array([tuple(q)for q in vv]);N=len(p);all_body=np.array([tuple(v)for v in body_vertices]);rear=all_body[:,0].min();cap=all_body[np.abs(all_body[:,0]-rear)<1e-6];assert len(cap)>=8
    order=np.argsort(cap[:,2]);zcap=cap[order,2];ycap=np.abs(cap[order,1]);zlo,zhi=zcap.min(),zcap.max();maxdist=max(np.linalg.norm(q-root.mean(0))for q in p);free_thickness=float(row['root_full_thickness_m']);edge=float(cfg['edge_full_thickness_m']);verts=[];qs=[];ss=[]
    for sign in [-1,1]:
        for q in p:
            x=axis*(.5-row['onset_t'])-(q[0]-leading[0])*scale;z=(canvas_h/2-q[1])*scale
            dist=float(np.min(np.linalg.norm(root-q,axis=1)));span=min(1.,dist/maxdist)
            aa=boundary;bb=np.roll(boundary,-1,axis=0);dd=bb-aa;uv=np.clip(((q-aa)*dd).sum(1)/np.maximum((dd*dd).sum(1),1e-20),0,1);inset=float(np.min(np.linalg.norm(q-(aa+uv[:,None]*dd),axis=1)))*scale
            half=edge/2+(free_thickness-edge)/2*(1-span)**1.1*min(1.,inset/max(free_thickness*.6,edge))
            if zlo-1e-7<=z<=zhi+1e-7 and x>=rear-.018:
                # Elliptic finite body end supplies the entire supported root.
                mid=(zlo+zhi)/2;h=(zhi-zlo)/2;support=max(abs(cap[:,1]))*math.sqrt(max(0,1-((z-mid)/h)**2))
                gain=np.clip((x-(rear-.018))/.018,0,1);half=half*(1-gain)+max(half,support+.0005)*gain
            assert half>0
            verts.append((float(x),float(sign*half),float(z)));qs.append(q.tolist());ss.append(span)
    faces=[]
    for f in ff:faces.append(tuple(f[::-1]));faces.append(tuple(i+N for i in f))
    from collections import Counter
    edges=Counter(tuple(sorted((a,b)))for f in ff for a,b in zip(f,f[1:]+f[:1]))
    for(a,b),count in edges.items():
        if count==1:faces.append((a,b,b+N,a+N))
    assert all(count<=2 for count in edges.values())
    return verts,faces,qs,ss,N
