"""Finite wall RGB from native tissue, alpha from the original cap domain.

Moving the wall UV to an opaque donor also moves its alpha and creates a
detached outline around sparse support cages. Keep those ownerships separate
in a saved RGBA chart; no source color synthesis or geometry change.
"""
import math
import numpy as np
import bpy


def bake(ob,image,safe,inset,pixels_per_native,make_material):
    assert pixels_per_native>0
    W,H=image.size;raw=np.asarray(image.pixels[:]).reshape(H,W,4)
    mesh=ob.data;uv=mesh.uv_layers.active.data;tiles=[];suppressed=0;count=0
    center=np.mean(safe,axis=0)
    for face in mesh.polygons:
        old=np.array([uv[i].uv[:]for i in face.loop_indices]);area=sum(np.cross(old[i]-old[0],old[i+1]-old[0])for i in range(1,len(old)-1))
        if abs(area)>1e-10:continue
        co=np.array([mesh.vertices[i].co[:]for i in face.vertices]);axis=co[1]-co[0];axis/=np.linalg.norm(axis);normal=np.array(face.normal);other=np.cross(normal,axis);other/=np.linalg.norm(other)
        q=np.stack([(co-co[0])@axis,(co-co[0])@other],1)*pixels_per_native;low=np.floor(q.min(0))-2;high=np.ceil(q.max(0))+2;tw,th=(high-low+1).astype(int);assert 0<tw*th<100000
        donor=[]
        for original in old:
            xy=original*[W,-H]+[0,H];direction=center-xy;sample=xy+direction/max(np.linalg.norm(direction),1e-9)*(inset+6);donor.append(safe[np.argmin(((safe-sample)**2).sum(1))])
        donor=np.asarray(donor);yy,xx=np.mgrid[:th,:tw];plane=np.c_[xx.ravel()+low[0],yy.ravel()+low[1]];rgba=np.zeros((len(plane),4),np.float32);chosen=np.full(len(plane),np.inf)
        for k in range(1,len(co)-1):
            ids=[0,k,k+1];points=q[ids];matrix=np.stack([points[1]-points[0],points[2]-points[0]],1)
            if abs(np.linalg.det(matrix))<1e-12:continue
            b=(plane-points[0])@np.linalg.inv(matrix).T;bary=np.c_[1-b.sum(1),b];clipped=np.maximum(bary,0);clipped/=clipped.sum(1)[:,None];error=((clipped@points-plane)**2).sum(1);take=error<chosen
            source_uv=clipped@old[ids];sx=np.floor(source_uv[:,0]*W).astype(int);sy=np.floor(source_uv[:,1]*H).astype(int);valid=(sx>=0)&(sx<W)&(sy>=0)&(sy<H);alpha=np.where(valid,raw[np.clip(sy,0,H-1),np.clip(sx,0,W-1),3],0)
            tissue=clipped@donor[ids];ix=np.clip(np.floor(tissue[:,0]).astype(int),0,W-1);iy=np.clip(np.floor(tissue[:,1]).astype(int),0,H-1);rgb=raw[H-1-iy,ix,:3].copy();unsafe=raw[H-1-iy,ix,3]<.95
            for i in np.flatnonzero(unsafe):
                x,y=safe[np.argmin(((safe-tissue[i])**2).sum(1))].astype(int);rgb[i]=raw[H-1-y,x,:3]
            rgba[take,:3]=rgb[take];rgba[take,3]=alpha[take];chosen[take]=error[take]
        assert np.isfinite(chosen).all();suppressed+=int((rgba[:,3]<.5).sum());count+=len(rgba)
        tiles.append({'face':face.index,'q':q-low,'w':tw,'h':th,'pixels':rgba.reshape(th,tw,4)})
    assert tiles
    aw=512;x=y=3;row=0
    for t in tiles:
        if x+t['w']+3>aw:x=3;y+=row+3;row=0
        assert t['w']+6<=aw;t['at']=(x,y);x+=t['w']+3;row=max(row,t['h'])
    ah=2**math.ceil(math.log2(y+row+3));atlas=np.zeros((ah,aw,4),np.float32)
    for t in tiles:
        x,y=t['at'];atlas[y:y+t['h'],x:x+t['w']]=t['pixels']
    chart=bpy.data.images.new(ob.name+'_native_wall_RGB_original_cap_alpha',aw,ah,alpha=True);chart.colorspace_settings.name=image.colorspace_settings.name;chart.pixels.foreach_set(atlas.ravel());chart.pack()
    material=make_material(ob.name+'_native_wall_with_cap_alpha',chart,True);index=len(mesh.materials);mesh.materials.append(material)
    for t in tiles:
        face=mesh.polygons[t['face']];face.material_index=index
        for li,q in zip(face.loop_indices,t['q']):uv[li].uv=((q[0]+t['at'][0]+.5)/aw,(q[1]+t['at'][1]+.5)/ah)
    return {'wall_faces':len(tiles),'chart_size':[aw,ah],'native_alpha_suppressed_texels':suppressed,'wall_chart_texels':count,'cap_UV_unchanged':True,'alpha_ownership':'Original cap UV alpha; inboard tissue donor affects RGB only','geometry_changed':False}
