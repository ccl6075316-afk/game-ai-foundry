"""Pure array tools for material transport; never alter fish geometry.

Along-rim coordinates come from the actual unbranched 3D skin/oral boundary.
The supplied 2D side-source curve remains a two-dimensional color donor.
"""
import numpy as np

def native_lip_ownership(distance_px,width_px,fade_px):
    """Complete semantic lip is native-only; any fade lies OUTSIDE its boundary."""
    if not(np.all(np.isfinite(width_px))and np.all(np.asarray(width_px)>0)and np.isfinite(fade_px)and fade_px>0):raise ValueError('Positive traced lip width and outer fade required')
    t=np.clip((np.asarray(distance_px)-width_px)/fade_px,0,1)
    return 1-t*t*(3-2*t)

def ordered_boundary(coords,edges):
    adjacent={}
    for a,b in edges:
        adjacent.setdefault(a,[]).append(b);adjacent.setdefault(b,[]).append(a)
    ends=[i for i,v in adjacent.items()if len(v)==1]
    if len(ends)!=2 or any(len(v)>2 for v in adjacent.values()):raise ValueError('Expected one unbranched open rim')
    chain=[min(ends,key=lambda i:coords[i,1])];previous=None
    while True:
        following=[i for i in adjacent[chain[-1]]if i!=previous]
        if not following:break
        previous=chain[-1];chain.append(following[0])
        if len(chain)>len(adjacent):raise ValueError('Cyclic rim')
    if len(chain)!=len(adjacent):raise ValueError('Disconnected rim')
    points=coords[chain];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    if arc[-1]<=0:raise ValueError('Empty-length rim')
    return points,arc

def nearest_arc(points,boundary):
    line,arc=boundary;best=np.full(len(points),np.inf);phase=np.zeros(len(points))
    for i,(a,b)in enumerate(zip(line,line[1:])):
        delta=b-a;length=float(delta@delta)
        if length<=1e-16:continue
        t=np.clip((points-a)@delta/length,0,1);foot=a+t[:,None]*delta;distance=np.linalg.norm(points-foot,axis=1);take=distance<best
        best[take]=distance[take];phase[take]=arc[i]+t[take]*(arc[i+1]-arc[i])
    return best,phase

def side_curve_donor(phase,total,distance_px,curve,upper):
    """Both sides meet at one front point; never repeat/refelect source stripes."""
    curve=np.asarray(curve,float);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))]
    fraction=np.clip(phase/total,0,1);along=(1-np.abs(2*fraction-1))*arc[-1]
    xy=np.stack([np.interp(along,arc,curve[:,0]),np.interp(along,arc,curve[:,1])],axis=1)
    i=np.clip(np.searchsorted(arc,along,side='right')-1,0,len(curve)-2);tangent=curve[i+1]-curve[i];normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1)*(-1 if upper else 1);normal/=np.linalg.norm(normal,axis=1)[:,None]
    return xy+normal*distance_px[:,None]

def bounded_roi_coordinates(x_fraction,y_fraction,roi,image_size):
    x0,y0,x1,y1=roi;w,h=image_size
    if not (0<=x0<x1<w and 0<=y0<y1<h):raise ValueError('ROI must be strictly within the donor')
    return np.stack([x0+np.clip(x_fraction,0,1)*(x1-x0),y0+np.clip(y_fraction,0,1)*(y1-y0)],axis=1)
