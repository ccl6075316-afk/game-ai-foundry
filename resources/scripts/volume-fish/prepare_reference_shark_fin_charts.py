"""Transport this fish's accepted painted fin pixels onto reference-mask charts.

Art correspondence is independent of measured shape; skin RGB is sampled
nearest from the declared exact image, never inferred from triangle normals.
"""
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import distance_transform_edt,binary_erosion

p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=json.loads(a.config.read_text());layout=json.loads(Path(c['fin_layout']).read_text());profile=json.loads(Path(c['art_profile']).read_text());assert not a.output.exists();a.output.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();records=[]
def paths(poly,ends,tip):
    poly=np.array(poly,float);ia,ib=[int(np.linalg.norm(poly-np.array(p),axis=1).argmin())for p in ends];it=int(np.linalg.norm(poly-np.array(tip),axis=1).argmin())
    def walk(step):
        out=[poly[ia]];i=ia
        while i!=ib:i=(i+step)%len(poly);out.append(poly[i])
        return np.array(out)
    pair=[walk(1),walk(-1)];free=next(x for x in pair if np.linalg.norm(x-poly[it],axis=1).min()<1e-7);root=next(x for x in pair if x is not free);j=int(np.linalg.norm(free-poly[it],axis=1).argmin());return root,free[:j+1],free[j:][::-1]
def sample(path,t):
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))];return np.array([np.interp(t*arc[-1],arc,path[:,i])for i in range(2)])
def feature_segments(poly,anchors):
    poly=np.array(poly,float);ids=[int(np.linalg.norm(poly-np.array(p),axis=1).argmin())for p in anchors];N=len(poly);forward=sum((b-a)%N for a,b in zip(ids,ids[1:]+ids[:1]));step=1 if forward==N else-1;assert sum(((b-a)*step)%N for a,b in zip(ids,ids[1:]+ids[:1]))==N,'Anatomical boundary features out of order';segments=[]
    for a,b in zip(ids,ids[1:]+ids[:1]):
        path=[poly[a]];i=a
        while i!=b:i=(i+step)%N;path.append(poly[i])
        segments.append(np.array(path))
    return segments
for row in layout['rows']:
    original=np.array(Image.open(row['source_path']).convert('RGB'));mask=original.max(2)<80;H,W=mask.shape
    for role in (['upper','lower']if row['paired']else['side']):
        is_lower=role=='lower';source=Path(c['ventral_source']if is_lower else c['side_source']);paint=np.array(Image.open(source).convert('RGBA'));SH,SW=paint.shape[:2];allowed=np.zeros((SH,SW),np.uint8)
        native_side=c.get('project_native_side',False) and not is_lower
        if native_side:
            assert (SH,SW)==(H,W),'Native source canvas must match inverse-X mask'
            allowed=mask[:,::-1].astype(np.uint8)
        elif is_lower:
            spec=c['ventral_fins'][row['name']];xa,ya=spec['root_endpoints_px'][0];xb,yb=spec['root_endpoints_px'][1];yy,xx=np.indices((SH,SW));root_y=ya+(yb-ya)*(xx-xa)/(xb-xa);x0,y0,x1,y1=spec['roi_px'];allowed=((paint[:,:,3]>250)&(xx>=x0)&(xx<x1)&(yy>=y0)&(yy<root_y)).astype(np.uint8);contours,_=cv2.findContours(allowed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);poly=max(contours,key=cv2.contourArea)[:,0,:].astype(float);ends=spec['root_endpoints_px'];tip=spec['tip_px']
        elif row['name']=='Caudal':
            yy,xx=np.indices((SH,SW));allowed=((paint[:,:,3]>250)&(xx<=c['tail_boundary_correspondence']['art_root_x_px'])).astype(np.uint8);contours,_=cv2.findContours(allowed,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);poly=max(contours,key=cv2.contourArea)[:,0,:].astype(float)
        else:
            f=next(f for f in profile['fins']if f['name']==row['name']);poly=np.array(f['polygon'])*[SW,SH];cv2.fillPoly(allowed,[np.rint(poly).astype(np.int32)],1);ends=[poly[-1].tolist(),poly[0].tolist()] if row['name']not in['FirstDorsal','SecondDorsal']else[poly[len(poly)//2].tolist(),poly[len(poly)//2-1].tolist()];tip=np.array(f['tip'])*[SW,SH]
        allowed=(allowed>0)&(paint[:,:,3]>250);assert allowed.sum()>100;interior=binary_erosion(allowed,iterations=4);assert interior.any();nearest=distance_transform_edt(~interior,return_distances=False,return_indices=True)
        y,x=np.indices((H,W));queries=np.stack([x.ravel(),y.ravel()],1).astype(float)
        if native_side:
            donor=np.stack([SW-1-queries[:,0],queries[:,1]],1)
        elif row['name']=='Caudal':
            contours,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);reference_poly=max(contours,key=cv2.contourArea)[:,0,:];tc=c['tail_boundary_correspondence'];refpaths=feature_segments(reference_poly,tc['reference_features_px']);artpaths=feature_segments(poly,tc['art_features_px']);controls={}
            for rp,ap in zip(refpaths,artpaths):
                for t in np.linspace(0,1,31):controls[tuple(np.round(sample(rp,t),5))]=sample(ap,t)
            warp=RBFInterpolator(np.array(list(controls)),np.array(list(controls.values())),kernel='thin_plate_spline',smoothing=1e-6);donor=np.concatenate([warp(q)for q in np.array_split(queries,16)])
        else:
            artroot,artleft,artright=paths(poly,ends,tip);refroot=np.array(row['root_curve_px']);refleft=np.array(row['leading_curve_px']);refright=np.array(row['trailing_curve_px']);controls={}
            for s in np.linspace(0,1,15):
                for q in np.linspace(0,1,7):
                    r=sample(refroot,q)if s==0 else sample(refleft,s)*(1-q)+sample(refright,s)*q;t=sample(artroot,q)if s==0 else sample(artleft,s)*(1-q)+sample(artright,s)*q;controls[tuple(np.round(r,5))]=t
            ref=np.array(list(controls));target=np.array(list(controls.values()));warp=RBFInterpolator(ref,target,kernel='thin_plate_spline',smoothing=1e-7);donor=np.concatenate([warp(q)for q in np.array_split(queries,16)])
        donor=np.rint(donor).astype(int);donor[:,0]=np.clip(donor[:,0],0,SW-1);donor[:,1]=np.clip(donor[:,1],0,SH-1);valid=allowed[donor[:,1],donor[:,0]];safe=donor.copy();safe[~valid]=np.stack([nearest[1,donor[~valid,1],donor[~valid,0]],nearest[0,donor[~valid,1],donor[~valid,0]]],1);pixels=paint[safe[:,1],safe[:,0],:3].reshape(H,W,3)
        # Pad in the TARGET reference domain too. Sparse boundary chords may be
        # a pixel outside its raster; never expose a stretched dark source edge.
        chord_inset=c.get('tail_skin_chord_inset_fraction',0)if row['name']=='Caudal'else 0
        if chord_inset:
            original=pixels.copy();safegrid=safe.reshape(H,W,2).copy()
            for yy in range(H):
                xs=np.where(mask[yy])[0]
                if not len(xs):continue
                for run in np.split(xs,np.where(np.diff(xs)>1)[0]+1):
                    lo,hi=run[0],run[-1];indices=np.rint(lo+chord_inset*(hi-lo)+(1-2*chord_inset)*(run-lo)).astype(int);pixels[yy,run]=original[yy,indices];safe.reshape(H,W,2)[yy,run]=safegrid[yy,indices]
        distance=distance_transform_edt(mask);support=distance>=10;assert support.any();pad=distance_transform_edt(~support,return_distances=False,return_indices=True);inside_pigment=pixels[pad[0],pad[1]].astype(float);gain=np.clip((distance-1)/7,0,1);gain=gain*gain*(3-2*gain);pixels=np.rint(pixels*gain[:,:,None]+inside_pigment*(1-gain[:,:,None])).astype(np.uint8);pixels[~mask]=pixels[pad[0,~mask],pad[1,~mask]];target=a.output/(row['name']+'-'+role+'.png');Image.fromarray(pixels).save(target)
        cut=paint.copy();cut[:,:,3]=allowed.astype(np.uint8)*255;cut[~allowed,:3]=0;cutpath=a.output/(row['name']+'-'+role+'-original-cutout.png');Image.fromarray(cut).save(cutpath);inside=safe[mask.ravel()];records.append(dict(name=row['name'],role=role,path=str(target.resolve()),sha256=sha(target),source_path=str(source.resolve()),source_sha256=sha(source),source_cutout=str(cutpath.resolve()),source_cutout_sha256=sha(cutpath),reference_mask_sha256=row['source_sha256'],exact_source_rgb_pixels=int((distance>=8).sum()),native_rgb_sampled_nearest=True,native_rgb_scope='Main painted face at reference-boundary distance>=8px only. Rolled-edge collar is explicitly derived.',derived_rolled_edge_pixels=int(((distance>0)&(distance<8)).sum()),donor_xy_min=inside.min(0).tolist(),donor_xy_max=inside.max(0).tolist(),source_alpha_opaque=True,padding='Outside mapped art uses own4px-interior source pixels. Actual rolled-edge collar0..8 reference pixels uses smooth own10px-interior pigment continuation; no stretched 2D black outline on 3D edge. Interior face pixels retained exactly.',shape_claim='None: art UV correspondence only; mask geometry is not resized to fit painted fish.'))
edges=[]
for row in layout['rows']:
    raw=np.array(Image.open(row['source_path']).convert('RGB'));mask=raw.max(2)<80;contours,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE);poly=max(contours,key=cv2.contourArea)[:,0,:].astype(float);path=np.r_[poly,poly[:1]];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))];phase=np.arange(2048)/2048*arc[-1];samples=np.stack([np.interp(phase,arc,path[:,i])for i in range(2)],1);support=binary_erosion(mask,iterations=9);assert support.any();nearest=distance_transform_edt(~support,return_distances=False,return_indices=True);q=np.rint(samples).astype(int);xx=nearest[1,q[:,1],q[:,0]];yy=nearest[0,q[:,1],q[:,0]];upper=next(r for r in records if r['name']==row['name']and r['role']==('upper'if row['paired']else'side'));lower=next(r for r in records if r['name']==row['name']and r['role']=='lower')if row['paired']else upper;top=np.array(Image.open(upper['path']).convert('RGB'))[yy,xx].astype(float);bottom=np.array(Image.open(lower['path']).convert('RGB'))[yy,xx].astype(float);t=np.linspace(0,1,16)[:,None,None];strip=np.rint(top[None,:,:]*(1-t)+bottom[None,:,:]*t).astype(np.uint8);target=a.output/(row['name']+'-sealed-edge.png');Image.fromarray(strip).save(target);edges.append(dict(name=row['name'],path=str(target.resolve()),sha256=sha(target),reference_closed_contour_px=path.tolist(),reference_arc_px=arc.tolist(),body_cap_excluded_by_topology=True,derivation='Actual thickness seal only: own9px-interior fin pigment, upper/lower interpolation across thickness. This strip is derived, not unchanged 2D outline pixels. Main fin faces keep native charts.'))
r=dict(ok=True,kind='same_fish_native_fin_pixel_charts',records=records,sealed_edges=edges,input_sha256=sha(a.config),formal_acceptance=False,scope='Actual per-part cutouts, immutable accepted art, exact RGB nearest transfer with fin-only opaque support. Bilateral side color reuse is a design choice; paired undersides use the accepted ventral image. Thickness-edge strips are declared derived. Shape/thickness/poses remain independent validation.');(a.output/'validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=True,charts=len(records),derived_sealed_edges=len(edges))))
