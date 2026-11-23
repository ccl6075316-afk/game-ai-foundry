"""Extract local palette detail where projected reference shading could create false holes."""
import numpy as np
from scipy import ndimage as ndi
from PIL import Image

from bake_reef_arch_six_view_art import DIRECTIONS, project


def texture_atlas(key, faces, xyz, corner_normals, face_normals, donors, spans):
    width = 1536
    count = len(faces)
    grid = int(np.ceil(np.sqrt(count)))
    cell = width // grid
    border = 2
    axis = np.clip((np.arange(cell)-border)/(cell-2*border-1),0.,1.)
    sx,sy=np.meshgrid(axis,axis)
    inside=sx+sy < .999
    denom=np.maximum(sx+sy,1.)
    sx,sy=sx/denom,sy/denom
    bary=np.stack([1-sx-sy,sx,sy],axis=-1)
    atlas=np.zeros((width,width,3),dtype=np.uint8)
    uvs=np.empty((count,3,2),dtype=np.float32)
    rr,cc=np.indices(sx.shape)
    owner_totals=np.zeros(len(DIRECTIONS))
    sponge = "sponge" in key
    if sponge:
        # Include branch/void art in the original six positions, but strip the
        # painted macro gradients before the model's real light and real cups.
        neutral={}
        for view,(pix,distance) in donors.items():
            rgb=pix.astype(np.float32)
            shading=ndi.gaussian_filter(rgb,sigma=(8,8,0))
            details=np.clip(rgb-shading,-16,15)
            safe=np.maximum(rgb[...,0]-rgb[...,2], 0)>38
            level=[193,134,64] if key=="reef_tube_sponge" else [149,97,84]
            neutral[view]=(np.asarray(level)+details*safe[...,None],distance)
        donors=neutral
    for i,triangle in enumerate(xyz):
        samples=bary @ triangle
        direction=.71*(bary @ corner_normals[faces[i]])+.29*face_normals[i]
        stack,weights=[],[]
        for view,(component,sign) in DIRECTIONS.items():
            color,trust=project(view,samples,spans,donors[view])
            weight=(np.maximum(sign*direction[...,component],0.)**4 + .0015)
            stack.append(color)
            weights.append(weight*np.maximum(trust,.007))
        owner=np.argmax(weights,axis=0)
        paint=np.stack(stack)[owner,rr,cc]
        for k in range(len(DIRECTIONS)):
            owner_totals[k]+=np.count_nonzero((owner==k)&inside)
        posx,posy,posz=np.moveaxis(samples,-1,0)
        if sponge:
            # Apply modest depth tone only to the actual inward-facing
            # material. The entire vertical depth is genuine geometry.
            nx, ny, nz=np.moveaxis(direction,-1,0)
            size_x,size_y,size_z=spans["front"][0],spans["front"][1],spans["top"][1]
            x,y,z=posx/size_x,posy/size_y,posz/size_z
            if key=="reef_tube_sponge":
                guides=np.array([[-.135,-.08,.96,.128],[-.366,.168,.644,.12],[.255,-.14,.68,.119],[.16,.253,.43,.139]])
            else:
                guides=np.array([[.056,-.027,.96,.40]])
            d2=np.stack([(x-cx)**2+(z-cz)**2 for cx,cz,_,_ in guides])
            pick=d2.argmin(axis=0)
            cx,cz,height,r=np.moveaxis(guides[pick],-1,0)
            radial=np.sqrt(((x-cx)**2+(z-cz)**2))
            dot=nx*(x-cx)+nz*(z-cz)
            dark=np.clip(-dot/.07,0,1)*(radial < r*1.21)
            dark=np.maximum(dark,(radial<r*.52)*(ny>.45)*np.clip((height-y)/.22,0,1))
            dark *= np.clip((y-.095)/.07,0.,1.)
            paint = np.clip(paint*(1-.19*dark[...,None]),0,255)
        # Respect nearest texels. Never resample or blend directional sources.
        x,y=i % grid*cell,i//grid*cell
        atlas[y:y+cell,x:x+cell]=paint
        lo,hi=border+.5,cell-border-.5
        uvs[i]=(np.array([[lo,lo],[hi,lo],[lo,hi]])+[x,y])/width
    ownership={view:round(float(v/owner_totals.sum()),4) for view,v in zip(DIRECTIONS,owner_totals)}
    return Image.fromarray(atlas).convert("RGBA"), uvs.reshape(-1,2), ownership
