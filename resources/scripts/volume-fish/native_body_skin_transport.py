"""Native two-dimensional skin donor across an unseen dorsal/ventral surface.

Color coordinates only. The body outline, skeleton and original side UV stay
independent. No generated-front anatomy, column stretch or dark-color filter.
"""
import numpy as np


def smooth(q):
    q=np.clip(q,0,1);return q*q*(3-2*q)


def native_skin_spans(pixels,profile):
    H,W,_=pixels.shape;valid=pixels[::-1,:,3]>.95
    yy,xx=np.mgrid[:H,:W];xx=(xx+.5)/W;yy=(yy+.5)/H
    for fin in profile['fins']:
        if fin['paired']:continue
        polygon=fin['polygon'];inside=np.zeros((H,W),dtype=bool)
        for (ax,ay),(bx,by)in zip(polygon,polygon[1:]+polygon[:1]):
            if abs(by-ay)<1e-12:continue
            inside^=((ay>yy)!=(by>yy))&(xx<(bx-ax)*(yy-ay)/(by-ay)+ax)
        valid&=~inside
    result=[]
    for col in valid.T:
        ids=np.flatnonzero(col);runs=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1);ids=max(runs,key=len)
        result.append([float(ids[0]),float(ids[-1])]if len(ids)>4 else[np.nan,np.nan])
    return np.array(result)


def native_roof_coordinates(points,sections,W,H,spans,cfg):
    sections=np.asarray(sections);u=points[:,0]+.5
    top,bottom,width=[np.interp(u,sections[:,0],sections[:,i])for i in [1,2,3]]
    v=.5-points[:,2]/(H/W);q=(v-(top+bottom)/2)/((bottom-top)/2)
    start,full,end,stop=cfg['longitudinal_window']
    amount=smooth((abs(q)-cfg['latitude_fade_start'])/(cfg['latitude_full']-cfg['latitude_fade_start']))*smooth((u-start)/(full-start))*(1-smooth((u-end)/(stop-end)))
    col=np.clip(np.rint(u*W).astype(int),0,W-1);bounds=spans[col];height=bounds[:,1]-bounds[:,0]
    # Signed transverse position gives one continuous real 2D patch over the
    # center. It is not a reflected one-column strip. Limit physical pixel
    # density only where the available own-species source skin is narrower.
    density=np.minimum(cfg['pixel_density'],cfg['transverse_source_fraction']*height/np.maximum(width*W,1e-9))
    center=np.where(q<0,cfg['dorsal_center_fraction'],cfg['ventral_center_fraction'])
    y=bounds[:,0]+height*center+points[:,1]*W*density
    y=np.clip(y,bounds[:,0]+3,bounds[:,1]-3)
    return np.stack([u*W,y],axis=1),amount,density
