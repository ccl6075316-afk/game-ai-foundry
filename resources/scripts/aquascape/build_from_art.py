"""Reconstruct an experimental volume from actual illustrated silhouettes.

Solid objects: closed contour-distance volume, original front/rear paintings.
Plants: separately illustrated leaves, traced row boundaries, curved closed shells.
Never paints replacement stone/wood/leaf textures. No primitive scenery generator.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import struct
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.measure import marching_cubes, find_contours
from scipy.spatial import Delaunay


class Glb:
    def __init__(self):
        self.doc={"asset":{"version":"2.0","generator":"Foundry source-art reconstruction experiment"},"scene":0,"scenes":[{"nodes":[]}],"nodes":[],"meshes":[],"materials":[],"textures":[],"images":[],"samplers":[{"magFilter":9728,"minFilter":9728,"wrapS":33071,"wrapT":33071}],"buffers":[{"byteLength":0}],"bufferViews":[],"accessors":[]}
        self.bin=bytearray()
        self.triangles=0
    def view(self,b, target=None):
        while len(self.bin)%4:self.bin.append(0)
        d={"buffer":0,"byteOffset":len(self.bin),"byteLength":len(b)}
        if target:d['target']=target
        i=len(self.doc['bufferViews']);self.doc['bufferViews'].append(d);self.bin.extend(b);return i
    def accessor(self,a,typ):
        a=np.ascontiguousarray(a,dtype='<f4')
        idx=len(self.doc['accessors'])
        self.doc['accessors'].append({"bufferView":self.view(a.tobytes(),34962),"componentType":5126,"count":len(a),"type":typ,"min":a.min(0).tolist(),"max":a.max(0).tolist()})
        return idx
    def material(self,img,name):
        stream=io.BytesIO();img.save(stream,format='PNG')
        ii=len(self.doc['images']);self.doc['images'].append({'bufferView':self.view(stream.getvalue()),'mimeType':'image/png','name':name})
        ti=len(self.doc['textures']);self.doc['textures'].append({'source':ii,'sampler':0})
        mi=len(self.doc['materials']);self.doc['materials'].append({'name':name,'pbrMetallicRoughness':{'baseColorTexture':{'index':ti},'metallicFactor':0,'roughnessFactor':1},'doubleSided':False})
        return mi
    def mesh(self,verts,faces,uv,material,name):
        verts=np.asarray(verts,dtype=np.float32);faces=np.asarray(faces,dtype=np.int32);uv=np.asarray(uv,dtype=np.float32)
        tri=verts[faces]
        cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(cross,axis=1)
        good=area>1e-20;tri=tri[good];cross=cross[good];area=area[good];f=faces[good]
        normals=np.repeat(cross/area[:,None],3,0)
        v=tri.reshape(-1,3);u=uv[f].reshape(-1,2)
        assert np.isfinite(v).all() and np.isfinite(u).all()
        prim={'attributes':{'POSITION':self.accessor(v,'VEC3'),'NORMAL':self.accessor(normals,'VEC3'),'TEXCOORD_0':self.accessor(u,'VEC2')},'material':material,'mode':4}
        mid=len(self.doc['meshes']);self.doc['meshes'].append({'name':name,'primitives':[prim]})
        ni=len(self.doc['nodes']);self.doc['nodes'].append({'name':name,'mesh':mid});self.doc['scenes'][0]['nodes'].append(ni)
        self.triangles+=len(f)
    def save(self,path):
        self.doc['buffers'][0]['byteLength']=len(self.bin)
        js=json.dumps(self.doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
        binary=bytes(self.bin)+b'\0'*((-len(self.bin))%4)
        path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(js)+len(binary))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(binary),b'BIN\0')+binary)


def foreground(image):
    a=np.asarray(image.convert('RGBA'))
    mask=a[:,:,3]>128
    if mask.all():mask=a[:,:,:3].min(2)<235
    # Matting leaves a few fully opaque RGB=0 rim specks. They are invalid
    # color donors and would spread black wedges across transparent margins.
    return mask & (a[:,:,:3].max(2)>15)


def donor(image):
    a=np.asarray(image.convert('RGBA')).copy();mask=foreground(image)
    trusted=ndi.binary_erosion(mask,iterations=3)&(a[:,:,:3].max(2)>40)
    if not trusted.any():trusted=mask
    nearest=ndi.distance_transform_edt(~trusted,return_distances=False,return_indices=True)
    replace=(~mask)|(a[:,:,:3].max(2)<25)
    colors=a[nearest[0],nearest[1],:3]
    a[:,:,:3][replace]=colors[replace];a[:,:,3]=255
    return Image.fromarray(a,'RGBA')


def cropped(path):
    im=Image.open(path).convert('RGBA');m=foreground(im);yy,xx=np.nonzero(m)
    return im.crop((xx.min(),yy.min(),xx.max()+1,yy.max()+1))


def solid(spec,root,config,output):
    primary=root/config['sources']['masters']/spec['master']
    rear=root/config['sources'][spec['back']]
    front=cropped(primary);back=cropped(rear)
    w,h=front.size;width=spec['width_m'];height=width*h/w
    nx=spec['grid_width'];ny=round(nx*h/w);step=width/(nx-5)
    mask=np.asarray(Image.fromarray((foreground(front)*255).astype('uint8')).resize((nx-6,ny-6),Image.Resampling.NEAREST))>0
    mask=ndi.binary_closing(mask,iterations=1)
    mask=np.pad(mask,3)
    dist=ndi.distance_transform_edt(mask)*step
    distance=ndi.gaussian_filter(dist,.65)
    luminance=np.asarray(front.convert('L').resize((nx-6,ny-6),Image.Resampling.BILINEAR),dtype=float)/255
    luminance=np.pad(ndi.gaussian_filter(luminance,2.0),3)
    # Thickness follows the actual contour, including every connected fork.
    half_depth=distance*spec['depth_ratio']*(.90+luminance*.16)
    nz=max(30,math.ceil(2*half_depth.max()/step)+8)
    z=(np.arange(nz)-(nz-1)/2)*step
    field=half_depth[:,:,None]-np.abs(z)[None,None,:]
    field[~mask,:]=-step*3
    verts,faces,_,_=marching_cubes(field.astype('float32'),step*.173,spacing=(step,step,step),allow_degenerate=False)
    # marching axes are image rows, image cols, depth. Convert to right/up/front.
    v=np.c_[verts[:,1]-(nx-1)*step/2,(ny-1)*step-verts[:,0],verts[:,2]-(nz-1)*step/2]
    v[:,1]-=v[:,1].min()
    # Reflecting one axis changes winding; check orientation by signed volume.
    signed=np.einsum('ij,ij->i',v[faces[:,0]],np.cross(v[faces[:,1]],v[faces[:,2]])).sum()/6
    if signed<0:faces=faces[:,[0,2,1]]
    normals=np.cross(v[faces[:,1]]-v[faces[:,0]],v[faces[:,2]]-v[faces[:,0]])
    centers=v[faces].mean(1)
    is_front=normals[:,2]>=0
    g=Glb();fm=g.material(donor(front),'original_front_painting');bm=g.material(donor(back),'generated_rear_painting')
    u=(verts[:,1]/step-3)/(nx-7);vv=(verts[:,0]/step-3)/(ny-7)
    for front_side,mat in [(True,fm),(False,bm)]:
        # Rear art shows the reversed camera direction.
        uv=np.c_[u if front_side else 1-u,vv]
        g.mesh(v,faces[is_front==front_side],np.clip(uv,0,1),mat,'front_shell' if front_side else 'rear_shell')
    path=output/(spec['id']+'.glb');g.save(path)
    return {'id':spec['id'],'output':str(path),'triangles':g.triangles,'size_m':np.ptp(v,axis=0).tolist(),'construction':'source silhouette and contour-distance depth; front/back artwork projection','depth_accuracy':'inferred, not measured; no accepted orthographic top constraint','sources':[str(primary),str(rear)]}


def split_leaves(path):
    image=Image.open(path).convert('RGBA');mask=foreground(image)
    labels,n=ndi.label(mask)
    regions=[]
    for i in range(1,n+1):
        ys,xs=np.nonzero(labels==i)
        if len(xs)>800:regions.append((ys.mean(),xs.mean(),xs.min(),ys.min(),xs.max()+1,ys.max()+1,i))
    assert len(regions)==6,f'Expected six isolated leaves, got {len(regions)} in {path}'
    regions.sort()
    regions=sorted(regions[:3],key=lambda r:r[1])+sorted(regions[3:],key=lambda r:r[1])
    leaves=[]
    for _,_,x0,y0,x1,y1,i in regions:
        a=np.asarray(image.crop((x0,y0,x1,y1))).copy()
        a[:,:,3]=np.where(labels[y0:y1,x0:x1]==i,a[:,:,3],0)
        leaves.append(Image.fromarray(a,'RGBA'))
    return leaves


def rotation(x,y,z):
    x,y,z=np.radians([x,y,z]);cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
    return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])


def leaf_shell(image,length,thickness,bend):
    return contour_leaf_shell(image,length,thickness,bend)


def contour_leaf_shell(image,length,thickness,bend):
    m=foreground(image);h,w=m.shape
    contours=find_contours(np.pad(m,1),.5)
    points=[]
    for contour in contours:
        contour=contour[::2]-1
        points.extend(np.c_[contour[:,1],contour[:,0]])
    yy,xx=np.mgrid[0:h:7,0:w:7]
    keep=m[yy,xx]
    points.extend(np.c_[xx[keep],yy[keep]])
    p=np.asarray(points)
    p[:,0]=np.clip(p[:,0],0,w-1);p[:,1]=np.clip(p[:,1],0,h-1)
    # Snap contour samples to the closest real foreground pixel, not an empty
    # chord joining the extremes of a curled leaf's disjoint row segments.
    nearest=ndi.distance_transform_edt(~m,return_distances=False,return_indices=True)
    iy=np.rint(p[:,1]).astype(int);ix=np.rint(p[:,0]).astype(int)
    p=np.c_[nearest[1,iy,ix],nearest[0,iy,ix]].astype(float)
    p=np.unique(p,axis=0)
    faces=Delaunay(p).simplices
    triangles=p[faces]
    valid=np.ones(len(faces),dtype=bool)
    for weights in [(1/3,1/3,1/3),(.5,.5,0),(0,.5,.5),(.5,0,.5),(.75,.25,0),(0,.75,.25),(.25,0,.75)]:
        probe=np.einsum('fvc,v->fc',triangles,np.array(weights))
        ix=np.clip(np.rint(probe[:,0]).astype(int),0,w-1);iy=np.clip(np.rint(probe[:,1]).astype(int),0,h-1)
        valid&=m[iy,ix]
    faces=faces[valid]
    stem=m[max(0,h-4):].nonzero()[1].mean()
    top=m[:4].nonzero()[1].mean()
    t=1-p[:,1]/max(1,h-1);scale=length/max(1,h-1)
    local_x=(p[:,0]-stem)*scale
    z=bend*length*t*t+np.sin(np.pi*t)*length*.025
    front=np.c_[local_x,t*length,z+thickness*.5]
    back=np.c_[local_x,t*length,z-thickness*.5]
    verts=np.r_[front,back]
    uv=np.tile(p/np.array([max(1,w-1),max(1,h-1)]),(2,1))
    cross=np.cross(front[faces[:,1]]-front[faces[:,0]],front[faces[:,2]]-front[faces[:,0]])
    faces[cross[:,2]<0]=faces[cross[:,2]<0][:,[0,2,1]]
    count=len(p)
    result=[*map(tuple,faces),*map(tuple,faces[:,[0,2,1]]+count)]
    edges={}
    for face in faces:
        for a,b in zip(face,np.roll(face,-1)):
            key=tuple(sorted((int(a),int(b))))
            edges.setdefault(key,[]).append((int(a),int(b)))
    for uses in edges.values():
        if len(uses)==1:
            a,b=uses[0]
            result.extend([(a,a+count,b+count),(a,b+count,b)])
    axis_angle=math.atan2((top-stem)*scale,length)
    verts=verts@rotation(0,0,math.degrees(axis_angle)).T
    return verts,np.asarray(result),uv


def root_curve(points,radii):
    verts=[];uv=[];faces=[];sides=10
    for i,(p,r) in enumerate(zip(points,radii)):
        tangent=points[min(i+1,len(points)-1)]-points[max(i-1,0)];tangent/=np.linalg.norm(tangent)
        a=np.cross(tangent,[0,0,1]);a/=np.linalg.norm(a);b=np.cross(a,tangent)
        for j in range(sides):
            angle=math.tau*j/sides;verts.append(p+r*(a*math.cos(angle)+b*math.sin(angle)));uv.append((i/(len(points)-1),j/sides))
    for i in range(len(points)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;c=b+sides;d=a+sides
            faces.extend([(a,d,c),(a,c,b)])
    for j in range(1,sides-1):
        faces.append((0,j,j+1))
        offset=(len(points)-1)*sides
        faces.append((offset,offset+j+1,offset+j))
    return np.asarray(verts),np.asarray(faces),np.asarray(uv)


def plant(spec,root,config,output):
    parts=root/config['sources'][spec['parts']];images=split_leaves(parts);g=Glb()
    mats=[g.material(donor(im),f'generated_leaf_{i+1}') for i,im in enumerate(images)]
    L=spec['rhizome_length_m'];base=spec['base_y_m'];count=len(spec['lengths_m'])
    for i,length in enumerate(spec['lengths_m']):
        image=images[i%6]
        v,f,uv=leaf_shell(image,length,spec['shell_thickness_m'],.11+(.09 if i%2 else -.025))
        angle=spec['angles_degrees'][i]
        R=rotation(spec['pitch_degrees'][i],spec['depth_rotations_degrees'][i],-angle)
        at=np.array([(i/(count-1)-.5)*L,base,0.003*math.sin(i*2.4)])
        v=v@R.T+at
        g.mesh(v,f,uv,mats[i%6],f'traced_leaf_{i+1}')
    master=root/config['sources']['masters']/spec['master'];im=Image.open(master).convert('RGBA')
    # Sample only existing rhizome paint from the master, never synthesize a replacement texture.
    w,h=im.size;crop=im.crop((int(w*.40),int(h*.58),int(w*.69),int(h*.67)))
    root_mat=g.material(donor(crop),'source_rhizome_paint')
    pts=np.array([[-L*.52,base*.8,0],[-L*.2,base,0],[L*.14,base*.90,.002],[L*.52,base,.004]])
    v,f,uv=root_curve(pts,[.004,.005,.0045,.003]);g.mesh(v,f,uv,root_mat,'creeping_rhizome')
    for i in range(8):
        x=(i/7-.5)*L
        pts=np.array([[x,base*.9,0],[x+.001,base*.4,.003],[x+.003,0,.007]])
        v,f,uv=root_curve(pts,[.0008,.0006,.00015]);g.mesh(v,f,uv,root_mat,f'attachment_root_{i}')
    path=output/(spec['id']+'.glb');g.save(path)
    return {'id':spec['id'],'scientific_name':spec['scientific_name'],'output':str(path),'triangles':g.triangles,'leaf_sources':6,'leaf_instances':count,'construction':'each blade traced from a complete generated isolated leaf, closed curved shell; source-painted surfaces','sources':[str(parts),str(master)]}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--root',required=True,type=Path);args=p.parse_args()
    config=json.loads(args.input.read_text(encoding='utf-8'));args.output.mkdir(parents=True,exist_ok=True)
    results=[solid(s,args.root,config,args.output) for s in config['solid_assets']]
    results.extend(plant(s,args.root,config,args.output) for s in config['plants'])
    hashes={}
    for r in results:
        for s in r['sources']+[r['output']]:hashes[s]=hashlib.sha256(Path(s).read_bytes()).hexdigest()
    report={'command':'aquascape.build-from-art','ok':True,'status':'done','next_action':'human_review','outputs':results,'failures':[],'input_hashes':hashes,'limitations':['Solid depth is inferred from contour distance, not recovered from orthographic multi-view','Do not accept style or 3D quality until actual GPU front/back/oblique views are inspected'],'user_acceptance':'pending'}
    (args.output/'build.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
