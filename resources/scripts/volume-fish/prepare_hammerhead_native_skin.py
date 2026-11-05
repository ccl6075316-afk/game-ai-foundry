"""Prepare explicit own-source body donors and full native ventral lip curves.

Pixel copies are confined to declared moving-fin/eye/auxiliary mouth/gill
footprints. RGB comes from 2D same-view safe tissue, never from a flat color.
"""
from pathlib import Path
import argparse,json,hashlib
import cv2,numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt,binary_erosion,gaussian_filter
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def prepare(base,out,suffix=''):
 assert not out.exists();out.mkdir();c=json.loads((base/('preparation'+suffix)/'config.json').read_text());profile=json.loads(Path(c['art_profile']).read_text());ref=json.loads((base/('shape'+suffix)/'reference.input.json').read_text());sources={v:base/'sources'/(v+'.png')for v in ['side','top','bottom','front']};images={v:np.array(Image.open(p).convert('RGBA'))for v,p in sources.items()};maps={};summaries=[]
 def clean(role,alpha,target,safe,dx):
  original=images[role];H,W=original.shape[:2];assert alpha.shape==(H,W);safe&=original[:,:,3]>250;safe=binary_erosion(safe,iterations=3);assert safe.sum()>500
  yy,xx=np.indices((H,W));sx=np.clip(xx+dx,0,W-1);sy=yy.copy()
  if role in ['top','bottom']:
   hy,hx=np.where((original[:,:,3]>250) & (xx>.9*W));center=(hy.min()+hy.max())/2;at_head=(xx>.88*W)&target;sy[at_head]=np.rint(center+(yy[at_head]-center)*.78).astype(int);sx[at_head]=np.clip(xx[at_head]-int(.009*W),0,W-1)
  bad=~safe[sy,sx];nearest=distance_transform_edt(~safe,return_distances=False,return_indices=True);sy[bad],sx[bad]=nearest[0,sy[bad],sx[bad]],nearest[1,sy[bad],sx[bad]]
  result=original.copy();donor=original[sy,sx,:3].astype(float)
  # A literal patch copy fails when its illumination differs from the target.
  # Keep native2D grain, matching only low-frequency light inside the footprint.
  guide_rgb=original[:,:,:3].copy();outer=(original[:,:,3]<250)|~alpha;pad=distance_transform_edt(~safe,return_distances=False,return_indices=True);guide_rgb[outer]=original[pad[0,outer],pad[1,outer],:3]
  guide=cv2.inpaint(guide_rgb,target.astype('uint8')*255,7,cv2.INPAINT_TELEA).astype(float)
  low=gaussian_filter(guide,(3,3,0));detail=donor-gaussian_filter(donor,(3,3,0));derived=np.clip(np.rint(low+detail),0,255).astype('uint8');result[target,:3]=derived[target];result[:,:,3]=alpha.astype(np.uint8)*255;assert np.all(result[target,3]==255)
  maps[role+'_target_xy']=np.c_[xx[target],yy[target]].astype(np.int16);maps[role+'_donor_xy']=np.c_[sx[target],sy[target]].astype(np.int16);p=out/('clean-'+role+'.png');Image.fromarray(result).save(p)
  summaries.append(dict(role=role,source=str(sources[role]),source_sha256=sha(sources[role]),output=str(p),output_sha256=sha(p),copied_pixels=int(target.sum()),safe_donor_pixels=int(safe.sum()),rgb_policy='Derived own-source2D high-frequency pigment with Gaussian sigma3 local illumination match to inpaint guide, only in declared footprint. Not rawRGB-exact or biological tissue. Donor2D XY preserved; alpha is derived body ownership.',unchanged_non_target_rgb=bool(np.array_equal(result[~target,:3],original[~target,:3]))));return result
 side=images['side'];H,W=side.shape[:2];yy,xx=np.indices((H,W));u=xx/W;sections=np.array(c['body_sections_override']);top=np.interp(u,sections[:,0],sections[:,1])*H;bottom=np.interp(u,sections[:,0],sections[:,2])*H;body=(u>=c['body_rear_u'])&(yy>=top)&(yy<=bottom);body|=(u>=.86)&(side[:,:,3]>250);body&=side[:,:,3]>250
 fin=np.zeros((H,W),np.uint8);roots=np.zeros_like(fin)
 for f in profile['fins']:
  poly=np.array(f['polygon'])*[W,H];cv2.fillPoly(fin,[np.rint(poly).astype('int32')],1);cv2.polylines(roots,[np.rint(np.array(f['source_baseline'])*[W,H]).astype('int32')],False,1,3)
 target=(fin>0)&body&(roots==0);safe=body&(cv2.dilate(fin,np.ones((9,9),np.uint8))==0)&(u<.84);clean_side=clean('side',body,target,safe,-int(.15*W))
 for role in ['top','bottom']:
  src=images[role];H,W=src.shape[:2];yy,xx=np.indices((H,W));u=xx/W;mask=src[:,:,3]>250;hy,hx=np.where(mask[:,int(c['head_neck_u']*W):]);center=(hy.min()+hy.max())/2;half=(hy.max()-hy.min())/2;bodyhalf=np.interp(u,sections[:,0],sections[:,3])/(c['target_head_span_over_length'])*2*half;central=(np.abs(yy-center)<=bodyhalf);alpha=mask&((u>=c['head_neck_u'])|central)&(u>=c['body_rear_u'])
  # Auxiliary-view gills/mouth are excluded from skin, while native side gills
  # and native lip donor remain untouched in their separate source images.
  edge_band=(np.abs(yy-center)>bodyhalf*.48)&(np.abs(yy-center)<bodyhalf*1.8)
  if role=='top':
   target=alpha&((((u>.70)&(u<.94))&edge_band)|((u>.9)&(np.abs(yy-center)>.83*half)))
  else:
   target=alpha&((((u>.70)&(u<.94))&edge_band)|((u>.94)&(np.abs(yy-center)>.83*half)))
   # Only the actual old mouth footprint is replaced, not a whole pale block.
   mouth_roi=c.get('native_mouth_roi_uv',[.84,.94,.30,.70]);mouth=(src[:,:,:3].max(2)<115)&(u>mouth_roi[0])&(u<mouth_roi[1])&(yy>mouth_roi[2]*H)&(yy<mouth_roi[3]*H)&(src[:,:,3]>250)
   target|=alpha&(cv2.dilate(mouth.astype('uint8'),np.ones((13,13),np.uint8))>0)
  safe=alpha&~(cv2.dilate(target.astype('uint8'),np.ones((9,9),np.uint8))>0)
  clean(role,alpha,target,safe,int(.04*W))
 # Identify the long mouth component in the original accepted ventral source.
 src=images['bottom'];H,W=src.shape[:2];roi=c.get('native_mouth_roi_uv',[.84,.94,.30,.70]);x0,x1=int(roi[0]*W),int(roi[1]*W);y0,y1=int(roi[2]*H),int(roi[3]*H);dark=((src[y0:y1,x0:x1,:3].max(2)<110)&(src[y0:y1,x0:x1,3]>250)).astype('uint8');n,lab,stats,_=cv2.connectedComponentsWithStats(cv2.dilate(dark,np.ones((3,3),np.uint8)))
 candidates=[(int(s[4]),i,s)for i,s in enumerate(stats)if i and s[3]>H*.08 and s[3]>2*s[2] and s[0]>0 and s[0]+s[2]<x1-x0]
 assert candidates,'No distinct native mouth component';_,i,s=max(candidates);xa,ya,w,h,area=map(int,s);xa+=x0;ya+=y0;curves={'upper':[],'lower':[]};tested=[]
 for y in np.linspace(ya+3,ya+h-4,31):
  iy=int(round(y));xs=np.where(src[iy,max(x0,xa-3):min(x1,xa+w+14),:3].max(1)<110)[0]+max(x0,xa-3)
  if not len(xs):
   near=min(range(max(0,iy-2),min(H,iy+3)),key=lambda y:0 if (src[y,max(x0,xa-3):min(x1,xa+w+14),:3].max(1)<110).any()else 1);iy=near;xs=np.where(src[iy,max(x0,xa-3):min(x1,xa+w+14),:3].max(1)<110)[0]+max(x0,xa-3)
  assert len(xs)>0
  curves['upper'].append([int(xs.max()),iy]);curves['lower'].append([int(xs.min()),iy])
 # Exact complete outward strips preflight; no opacity/out-of-bounds clamping.
 domain=dict(upper_width_px=3,lower_width_px=3,outer_fade_px=4)
 for name,curve in curves.items():
  q=np.array(curve,float);dd=np.gradient(q,axis=0);norm=np.c_[dd[:,1],-dd[:,0]];norm/=np.linalg.norm(norm,axis=1)[:,None]
  if name=='lower':norm*=-1
  samples=np.concatenate([q+norm*d for d in np.arange(0,8,.25)]);ix=np.rint(samples[:,0]).astype(int);iy=np.rint(samples[:,1]).astype(int);assert ix.min()>=0 and iy.min()>=0 and ix.max()<W and iy.max()<H;assert np.all(src[iy,ix,3]>250);tested.append(dict(lip=name,samples=len(ix),minimum_alpha=int(src[iy,ix,3].min())))
 pic=Image.fromarray(src);draw=ImageDraw.Draw(pic)
 for name,color in [('upper','#ff3030'),('lower','#20b8ff')]:draw.line([tuple(p)for p in curves[name]],fill=color,width=2)
 pic.crop((int(.82*W),int(.29*H),W,int(.71*H))).save(out/'native-lip-domain.png');np.savez_compressed(out/'donor-addresses.npz',**maps)
 indices={}
 for role,file in [('clean_side','clean-side.png'),('dorsal','clean-top.png'),('clean_bottom','clean-bottom.png')]:
  opaque=np.array(Image.open(out/file))[:,:,3]>250;support=binary_erosion(opaque,iterations=2);indices[role]=distance_transform_edt(~support,return_distances=False,return_indices=True).astype(np.int16)
 np.savez_compressed(out/'sampler-indices.npz',**indices)
 input_sources={name:dict(path=str(path.resolve()),sha256=sha(path))for name,path in dict(side=sources['side'],clean_side=out/'clean-side.png',dorsal=out/'clean-top.png',clean_bottom=out/'clean-bottom.png',ventral=sources['bottom'],front=sources['front']).items()}
 skin=dict(species=profile['species'],baseline=str((base/('fins'+suffix)).resolve()),baseline_sha256=sha(base/('fins'+suffix)/'fish.glb'),reference=str((base/('shape'+suffix)/'reference.input.json').resolve()),pixels_per_m=Image.open(sources['side']).width/c['display_length_m'],sources=input_sources,head_neck_u=c['head_neck_u'],skin_material_slots=[0],upper_source_curve_px=curves['upper'],lower_source_curve_px=curves['lower'],lip_domain=domain,default_side_patch_rects=[],additional_side_patch_rects=[[f['name'],float(min(np.array(f['polygon'])[:,0])),float(max(np.array(f['polygon'])[:,0])),float(min(np.array(f['polygon'])[:,1])),float(max(np.array(f['polygon'])[:,1]))]for f in profile['fins']if f['name']!='Caudal'],front_skin_roi_px=None)
 write(out/'skin.config.json',skin);write(out/'preparation.validation.json',dict(ok=True,species=profile['species'],kind='own_source_2d_skin_and_native_lip_preflight',source_sha256={k:sha(v)for k,v in sources.items()},repairs=summaries,native_lip_curves_px=curves,native_mouth_component=dict(x=xa,y=ya,width=w,height=h,area=area),complete_lip_strip_preflight=tested,domain=domain,donor_map_sha256=sha(out/'donor-addresses.npz'),limits=['Occluded body/auxiliary feature replacement uses same-view native2D pigment, not biological hidden-skin observations.','Body ownership alpha is a declared sparse-cage projection. Source pixels outside replacement footprints remain RGB-exact.','Native side gills, original eyes and original ventral mouth sources preserved separately. Final actual3D transport, whole-sheet visual and cold checks remain pending.']))
 skin.update(sampler_indices=str((out/'sampler-indices.npz').resolve()),dorsal_head_span_registration=True);write(out/'skin.config.json',skin)
 # Plain 2D sheet is reviewed before assigning the result to the body.
 board=Image.new('RGB',(1400,900),'#25343c');dr=ImageDraw.Draw(board)
 for i,(role,p)in enumerate([('side',out/'clean-side.png'),('top',out/'clean-top.png'),('bottom',out/'clean-bottom.png')]):
  for j,im in enumerate([Image.open(sources[role]),Image.open(p)]):
   im=im.convert('RGBA');im.thumbnail((680,260));bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);board.paste(bg.convert('RGB'),(j*700+(700-im.width)//2,i*300+30));dr.text((j*700+8,i*300+8),role+(' original'if j==0 else' body-owned'),fill='white')
 board.save(out/'skin-source-review.jpg',quality=92)
 return skin
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--generation-suffix',default='');a=p.parse_args();d=prepare(a.base.resolve(),a.output.resolve(),a.generation_suffix);print(json.dumps(dict(ok=True,species=d['species'])))
