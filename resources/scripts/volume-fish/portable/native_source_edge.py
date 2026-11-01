"""Trace a declared tissue boundary; keep source RGB and anatomical domains separate."""
import cv2
import numpy as np

def trace(raw, crop, config):
    points=np.asarray(config['polyline_px'],float)
    assert points.shape[1]==2 and np.all(np.diff(points[:,0])>0)
    side=config['side'];assert side in ('above','below')
    radius=int(config['search_radius_px']);assert 1<=radius<=32
    # A tiny signal filter locates the color transition; it is never saved into the asset.
    gray=cv2.cvtColor(raw[:,:,:3],cv2.COLOR_RGB2GRAY).astype(float)
    signal=cv2.blur(gray,(3,3))
    xs=np.arange(max(int(points[0,0]),crop[0]),min(int(points[-1,0])+1,crop[2]))
    expected=np.interp(xs,points[:,0],points[:,1])-crop[1]
    offsets=np.arange(-radius,radius+1)
    ys=np.rint(expected[:,None]).astype(int)+offsets
    valid=(ys>=1)&(ys+2<raw.shape[0]);assert valid.any(axis=1).all()
    ys=np.clip(ys,1,raw.shape[0]-3)
    x=xs-crop[0]
    delta=(signal[ys+1,x[:,None]]-signal[ys-1,x[:,None]])*(1 if side=='below'else -1)
    costs=-np.clip(delta,0,180)/20+.6*(offsets[None,:]/radius)**2
    costs[~valid]=1e10
    paths=np.zeros_like(costs,dtype=int);best=costs[0].copy()
    for i in range(1,len(xs)):
        # Source pixel clusters can step several rows; prefer a coherent boundary.
        jump=ys[i,:,None]-ys[i-1,None,:]
        candidate=best[None,:]+.025*np.abs(jump)+.004*jump**2
        candidate[np.abs(jump)>12]=1e10
        parent=np.argmin(candidate,axis=1);paths[i]=parent
        best=costs[i]+candidate[np.arange(len(offsets)),parent]
    ids=[int(np.argmin(best))]
    for i in range(len(xs)-1,0,-1):ids.append(int(paths[i,ids[-1]]))
    ids.reverse();edge=ys[np.arange(len(xs)),ids]
    return {'side':side,'points_px':np.c_[xs,edge+crop[1]].astype(int).tolist(),
            'signal_only_filter':'3x3 mean for edge localization; selected asset RGB untouched',
            'basis':'Explicit native boundary corridor plus declared contrast direction; no universal black threshold',
            'minimum_signal_jump':float(delta[np.arange(len(xs)),ids].min()),
            'maximum_offset_px':int(np.abs(offsets[ids]).max())}
