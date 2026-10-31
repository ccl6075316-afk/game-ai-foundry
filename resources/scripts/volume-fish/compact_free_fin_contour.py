"""Remove exact straight free-edge samples only; no animation equivalence claim.

Body, source baseline and the entire root/weight-transition domain are retained.
Any new triangulation still requires full fin/shape/motion validation.
"""
import copy,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'cli'))
from volume_shape import fin_baseline_parameter

def native_pixel_mask(polygon,source_size):
    """Exact pixel-center ownership rule used by build_fish's native cutouts.

    Do not round vertices and use a second rasterizer: that can invent a
    coverage change after removing a geometrically collinear sample.
    """
    import numpy as np
    w,h=source_size
    if any(type(v)is not int or v<=0 for v in [w,h]):raise ValueError('Positive integer native image dimensions required')
    p=np.asarray(polygon,dtype=float)
    if p.ndim!=2 or p.shape[1]!=2 or len(p)<3 or not np.isfinite(p).all() or (p<0).any() or (p>1).any():raise ValueError('Finite normalized source polygon required')
    y,x=np.mgrid[:h,:w];x=(x+.5)/w;y=(y+.5)/h;inside=np.zeros((h,w),dtype=bool)
    for a,b in zip(p,np.roll(p,-1,axis=0)):
        if a[1]==b[1]:continue
        inside^=((a[1]>y)!=(b[1]>y))&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
    return inside

def compact(fin,aspect):
    result=copy.deepcopy(fin);poly=fin['polygon'];base=fin['source_baseline'];attachment=fin['root_attachment'];protect=max(attachment['root_band'],attachment['blend_end']);remove=[]
    for i,b in enumerate(poly):
        a,c=poly[i-1],poly[(i+1)%len(poly)];v=[b[k]-a[k]for k in range(2)];w=[c[k]-b[k]for k in range(2)]
        if abs(v[0]*w[1]-v[1]*w[0])>1e-13 or sum(x*y for x,y in zip(v,w))<=0:continue
        if any(math.dist(b,q)<1e-10 for q in base):continue
        if fin_baseline_parameter(b,base,poly,aspect)<=protect+1e-7:continue
        remove.append(i)
    result['polygon']=[p for i,p in enumerate(poly)if i not in remove]
    area=lambda ps:sum(a[0]*b[1]-a[1]*b[0]for a,b in zip(ps,ps[1:]+ps[:1]))/2
    assert len(result['polygon'])>=3 and abs(area(poly)-area(result['polygon']))<1e-12
    assert result['source_baseline']==base and result['root_attachment']==attachment
    return result,remove
