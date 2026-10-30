"""Protect real lateral eyes without masking the shared-UV central forehead."""
import numpy as np

def smooth(value):
    value=np.clip(value,0,1)
    return value*value*(3-2*value)

def target_eye_material_allowance(source_xy,side,rects,fade_px,side_start,side_full):
    if fade_px<=0 or not 0<=side_start<side_full<=1:raise ValueError('Invalid eye protection parameters')
    source_xy=np.asarray(source_xy,float);side=np.asarray(side,float)
    lateral=smooth((side-side_start)/(side_full-side_start));allow=np.ones(len(side))
    for x0,y0,x1,y1 in rects:
        if x1<=x0 or y1<=y0:raise ValueError('Invalid target eye rectangle')
        distance=np.hypot(np.maximum(np.maximum(x0-source_xy[:,0],source_xy[:,0]-x1),0),np.maximum(np.maximum(y0-source_xy[:,1],source_xy[:,1]-y1),0))
        allow*=1-lateral*(1-smooth(distance/fade_px))
    return allow
