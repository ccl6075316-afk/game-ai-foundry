"""A leaf's continuous outer polygon, without mask-rejected Delaunay faces.

Healthy painted leaves use one exterior contour. Small alpha pinholes are not
promoted into tunnels. Subpixel simplification retains species-scale waves.
"""
import numpy as np
import cv2
from scipy import ndimage as ndi
from skimage.measure import find_contours

def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]

def polygon(mask,tolerance=.65):
    filled=ndi.binary_fill_holes(mask)
    contour=max(find_contours(np.pad(filled,1),.5),key=len)-1
    points=contour[:,[1,0]]
    points=cv2.approxPolyDP(points.astype('float32'),tolerance,True)[:,0,:].astype(float)
    area=cross(points,np.roll(points,-1,axis=0)).sum()/2
    if area<0:points=points[::-1]
    return points

def ears(points):
    ids=list(range(len(points)));faces=[]
    while len(ids)>3:
        found=False
        for k in range(len(ids)):
            a,b,c=ids[k-1],ids[k],ids[(k+1)%len(ids)];A,B,C=points[[a,b,c]]
            if cross(B-A,C-B)<=1e-9:continue
            others=np.array([i for i in ids if i not in [a,b,c]],dtype=int);P=points[others]
            inside=(cross(B-A,P-A)>=-1e-9)&(cross(C-B,P-B)>=-1e-9)&(cross(A-C,P-C)>=-1e-9)
            if inside.any():continue
            faces.append([a,b,c]);ids.pop(k);found=True;break
        if not found:raise ValueError('Cannot triangulate simple leaf polygon; inspect contour rather than discard faces')
    faces.append(ids)
    return np.asarray(faces,dtype=int)

def clip_y(points,y,above):
    result=[]
    for p,q in zip(points,np.roll(points,-1,axis=0)):
        pin=(p[1]>=y-1e-9) if above else (p[1]<=y+1e-9)
        qin=(q[1]>=y-1e-9) if above else (q[1]<=y+1e-9)
        if pin:result.append(p)
        if pin!=qin:result.append(p+(q-p)*((y-p[1])/(q[1]-p[1])))
    return np.asarray(result)

def triangulate(mask,tolerance=.65):
    boundary=polygon(mask,tolerance);faces=ears(boundary);pieces=[]
    low=boundary[:,1].min();high=boundary[:,1].max();lines=np.linspace(low,high,49)
    # Shared horizontal slices supply enough longitudinal samples for bending.
    # Every triangle uses the same cuts, so adjacent faces remain conforming.
    for face in faces:
        tri=boundary[face]
        for a,b in zip(lines[:-1],lines[1:]):
            if tri[:,1].max()<a or tri[:,1].min()>b:continue
            q=clip_y(tri,a,True)
            if len(q)<3:continue
            q=clip_y(q,b,False)
            if len(q)<3:continue
            for i in range(1,len(q)-1):
                t=q[[0,i,i+1]]
                if abs(cross(t[1]-t[0],t[2]-t[0]))>1e-8:pieces.append(t)
    vertices,inverse=np.unique(np.round(np.asarray(pieces).reshape(-1,2),7),axis=0,return_inverse=True)
    faces=inverse.reshape(-1,3)
    area=sum(abs(cross(vertices[f[1]]-vertices[f[0]],vertices[f[2]]-vertices[f[0]]))/2 for f in faces)
    expected=abs(cross(boundary,np.roll(boundary,-1,axis=0)).sum()/2)
    if abs(area-expected)>max(1e-4,expected*1e-8):raise ValueError('Incomplete or overlapping polygon triangulation')
    return vertices,faces,{'contour_vertices':len(boundary),'polygon_area_px2':expected,'triangle_area_px2':area,'simplification_tolerance_px':tolerance}
