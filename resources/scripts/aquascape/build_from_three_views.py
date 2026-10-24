"""Experimental visual hull from three genuine orthographic silhouettes.

Joint FRONT(X,Y), RIGHT(-Z,Y), TOP(X,Z) constraints, not single-view inflation.
Concavities and hidden branch correspondence remain ambiguous. Material donors
are generated art, never procedural paint; native donor PNGs remain unscaled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import RBFInterpolator
from skimage.measure import marching_cubes
from skimage.morphology import medial_axis
from build_from_art import Glb


def silhouette(path,fill_holes=True):
    im=Image.open(path).convert('RGB');a=np.asarray(im)
    mask=a.min(2)<215
    labels,n=ndi.label(mask);sizes=np.bincount(labels.ravel());sizes[0]=0
    mask=labels==sizes.argmax()
    if fill_holes:mask=ndi.binary_fill_holes(mask)
    yy,xx=np.nonzero(mask);box=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    return im.crop(box),mask[box[1]:box[3],box[0]:box[2]],box


def sample_sdf(mask,u,v,scale):
    sdf=(ndi.distance_transform_edt(mask)-ndi.distance_transform_edt(~mask))*scale
    # A white pad is essential; nearest image-border extension would create boxes.
    sdf=np.pad(sdf,3,constant_values=-scale*4)
    coords=np.broadcast_arrays(v*(mask.shape[0]-1)+3,u*(mask.shape[1]-1)+3)
    return ndi.map_coordinates(sdf,np.array(coords),order=1,mode='constant',cval=-scale*4)


def native_donor(path,out):
    im,mask,box=silhouette(path);rgb=np.array(im)
    trusted=ndi.binary_erosion(mask & (rgb.min(2)<230),iterations=2)
    if not trusted.any():trusted=mask
    nearest=ndi.distance_transform_edt(~trusted,return_distances=False,return_indices=True)
    rgb[~trusted]=rgb[nearest[0],nearest[1]][~trusted]
    # Fill outside donors from nearest source pixels; no resample or new paint.
    rgba=np.dstack([rgb,(mask*255).astype('uint8')])
    Image.fromarray(rgba).save(out)
    return {'source':str(path),'native_crop':list(im.size),'source_bbox':box,'output':str(out),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def build(root,spec,output):
    kind=spec['id'];review=root/spec.get('reference_dir','projects/fishing-2d/plans/reviews/aquascape-three-views-v3')
    refs={v:silhouette(review/f'{spec["reference_prefix"]}-{v}.png',not spec.get('preserve_holes',False)) for v in ['front','right','top']}
    fm,rm,tm=[refs[v][1] for v in ['front','right','top']]
    width=spec['width_m'];height=width*fm.shape[0]/fm.shape[1]
    d_right=height*rm.shape[1]/rm.shape[0];d_top=width*tm.shape[0]/tm.shape[1]
    depth=(d_right+d_top)/2
    step=width/spec.get('resolution',220)
    x=np.arange(-width/2-3*step,width/2+3.1*step,step)
    y=np.arange(-3*step,height+3.1*step,step)
    z=np.arange(-depth/2-3*step,depth/2+3.1*step,step)
    X=x[:,None,None];Y=y[None,:,None];Z=z[None,None,:]
    f=sample_sdf(fm,(X+width/2)/width,1-Y/height,width/fm.shape[1])
    r=sample_sdf(rm,(depth/2-Z)/depth,1-Y/height,height/rm.shape[0])
    t=sample_sdf(tm,(X+width/2)/width,(Z+depth/2)/depth,width/tm.shape[1])
    right_mode=spec.get('right_constraint','hard')
    if spec.get('cross_sections')=='medial_with_depth_guides':
        # Front branch anatomy supplies local radii, top drawing supplies depth
        # guides and occupied intervals; the disputed end view gives total depth.
        skeleton,distance=medial_axis(fm,return_distance=True,rng=0)
        nearest=ndi.distance_transform_edt(~skeleton,return_distances=False,return_indices=True)
        local_radius=distance[nearest[0],nearest[1]]*width/fm.shape[1]
        uv=np.broadcast_arrays(1-Y[:,:,0]/height,(X[:,:,0]+width/2)/width)
        R=ndi.map_coordinates(local_radius,np.array([uv[0]*(fm.shape[0]-1),uv[1]*(fm.shape[1]-1)]),order=1,mode='nearest')
        R=np.maximum(R,f[:,:,0])
        half=np.sqrt(np.maximum(f[:,:,0],0)*np.maximum(2*R-f[:,:,0],0))*spec.get('thickness_ratio',1.0)
        guides=np.asarray(spec['depth_guides'])
        points=np.c_[uv[1].ravel(),uv[0].ravel()]
        inferred=RBFInterpolator(guides[:,:2],guides[:,2],kernel='thin_plate_spline',smoothing=.015)(points).reshape(uv[0].shape)
        center=np.clip(inferred,0,1)*depth-depth/2
        # Clip depth centers into the actual TOP silhouette, preserving separate
        # root-foot intervals instead of one straight extrusion.
        for ix in range(len(x)):
            candidates=np.flatnonzero(t[ix,0,:]>0)
            if len(candidates):
                current=np.abs(center[ix,:,None]-z[candidates][None,:]).argmin(1)
                center[ix]=z[candidates[current]]
        field=(half[:,:,None]-np.abs(Z-center[:,:,None])).astype('float32')
        field=np.minimum(field,f)
        field=np.minimum(field,t+spec.get('top_tolerance_m',.008))
    elif spec.get('cross_sections')=='paired_ellipses':
        # Pair the visible per-X intervals, rather than extruding a flat slab.
        # High main limb corresponds to rear/top interval; low roots to front.
        def intervals(values):
            ids=np.flatnonzero(values)
            if not len(ids):return []
            runs=np.split(ids,np.where(np.diff(ids)>1)[0]+1)
            return [(r[0],r[-1]) for r in runs if len(r)>1]
        field=np.full((len(x),len(y),len(z)),-step*4,dtype='float32')
        for ix in range(len(x)):
            yruns=intervals(f[ix,:,0]>0)[::-1]
            zruns=intervals(t[ix,0,:]>0)
            if not yruns or not zruns:continue
            if len(yruns)==len(zruns):pairs=list(zip(yruns,zruns))
            elif len(yruns)==1:pairs=[(yruns[0],q) for q in zruns]
            elif len(zruns)==1:pairs=[(q,zruns[0]) for q in yruns]
            else:pairs=[(q,zruns[min(i,len(zruns)-1)]) for i,q in enumerate(yruns)]
            for (ya,yb),(za,zb) in pairs:
                cy=(y[ya]+y[yb])/2;cz=(z[za]+z[zb])/2
                ry=max(step,(y[yb]-y[ya])/2);rz=max(step,(z[zb]-z[za])/2)
                ellipse=(1-np.sqrt(((Y[0]-cy)/ry)**2+((Z[0]-cz)/rz)**2))*min(ry,rz)
                field[ix]=np.maximum(field[ix],ellipse)
        hull=np.minimum(f,t)
        # Interval splits are ambiguous at branch crotches. A recessed common
        # hull core joins adjacent sections without restoring a slab silhouette.
        core=hull-spec.get('junction_core_inset_m',.010)
        field=np.minimum(np.maximum(field,core),hull)
    elif right_mode=='depth_only':
        # A conflicting end elevation must not silently amputate the real trunk.
        # Retain this view's depth measurement but expose its silhouette residual.
        field=np.minimum(f,t).astype('float32')
    else:
        field=np.minimum(np.minimum(f,r),t).astype('float32')
    # Resolve sharp projection intersections without changing the silhouette intent.
    field=ndi.gaussian_filter(field,spec.get('smoothing_voxels',.85))
    labels,n=ndi.label(field>0);counts=np.bincount(labels.ravel());counts[0]=0
    keep=counts.argmax();discarded=int(sum(counts)-counts[keep])
    field[(labels>0)&(labels!=keep)]=-step
    verts,faces,_,_=marching_cubes(field,0,spacing=(step,)*3,allow_degenerate=False)
    verts+=np.array([x[0],y[0],z[0]])
    vol=np.einsum('ij,ij->i',verts[faces[:,0]],np.cross(verts[faces[:,1]],verts[faces[:,2]])).sum()/6
    if vol<0:faces=faces[:,[0,2,1]]
    g=Glb();uv=np.c_[(verts[:,0]+width/2)/width,1-verts[:,1]/height]
    textures={}
    for view in ['front','right','top']:
        path=root/spec['materials'][view]
        textures[view]=native_donor(path,output/f'{kind}-{view}.png')
    # Standard fallback front material; Godot installs three-way projection shader.
    fallback=Image.open(output/f'{kind}-front.png').convert('RGB').convert('RGBA')
    mat=g.material(fallback,'generated_front_fallback')
    g.mesh(verts,faces,np.clip(uv,0,1),mat,kind+'_three_view_hull')
    # Continuous field normals prevent face-by-face projection direction jumps.
    cross=np.cross(verts[faces[:,1]]-verts[faces[:,0]],verts[faces[:,2]]-verts[faces[:,0]])
    normal=np.zeros_like(verts)
    for corner in range(3):np.add.at(normal,faces[:,corner],cross)
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-30)
    good=np.linalg.norm(cross,axis=1)>1e-20
    g.doc['meshes'][0]['primitives'][0]['attributes']['NORMAL']=g.accessor(normal[faces[good]].reshape(-1,3),'VEC3')
    out=output/f'{kind}.glb';g.save(out)
    # Projection occupancy: checks actual joint reconstruction, not only input spans.
    occupied=field>0
    measures={}
    for view,actual,target in [('front',occupied.any(2),f[:,:,0]>0),('right',occupied.any(0),r[0,:,:]>0),('top',occupied.any(1),t[:,0,:]>0)]:
        intersection=int((actual&target).sum());union=int((actual|target).sum())
        measures[view]={'silhouette_iou':intersection/max(1,union),'target_coverage':intersection/max(1,int(target.sum()))}
    return {'id':kind,'output':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'triangles':g.triangles,'right_constraint':right_mode,'cross_sections':spec.get('cross_sections','visual_hull'),'depth_guides':spec.get('depth_guides',[]),'projection_bounds':{'width':width,'height':height,'depth':depth},'actual_bounds_m':[verts.min(0).tolist(),verts.max(0).tolist()],'three_view_occupancy':measures,'disconnected_components':int(n),'discarded_voxels':discarded,'materials':textures,'reference_hashes':{v:hashlib.sha256((review/f'{spec["reference_prefix"]}-{v}.png').read_bytes()).hexdigest() for v in refs},'limitations':['Silhouettes cannot recover invisible concavities or unique branch correspondences.','Small cross-view span mismatch normalized into one shared trial box.','No independent back/left artwork: opposite surfaces reuse corresponding front/right/top donor.','Native RGB donors are bounding-box registered; internal painted landmarks are not dense-registered.']+(['Right silhouette conflicts with front/top main-branch height; used for overall depth only. End-view shape is not solved.','Branch depth guides are operator inferences from top drawing, not measured reconstruction.'] if right_mode=='depth_only' else [])}


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    cfg=json.loads(a.input.read_text(encoding='utf-8'));a.output.mkdir(exist_ok=True,parents=True)
    rows=[build(a.root,s,a.output) for s in cfg['assets']]
    report={'schema_version':1,'command':'aquascape.build-three-views','ok':True,'status':'done','next_action':'human_review','outputs':rows,'failures':[],'visual_review':'pending','user_acceptance':'pending','scope':'Three-view visual-hull and generated artwork mapping trial, not final reconstruction.'}
    (a.output/'build.validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))


if __name__=='__main__':main()
