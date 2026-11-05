"""Register generated clean skin only inside explicit own-source defect masks.

Original PNGs/lips remain immutable. Geometry only defines 2D body ownership;
this is not a silhouette/geometry author and never imports generated anatomy.
"""
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np,cv2
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt,binary_erosion
sys.path.insert(0,str(Path(__file__).parent));from check_project_art_tail_section import mesh
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(base,out,head_limit=.87):
 assert .87<=head_limit<=.95
 assert not out.exists();out.mkdir();c=json.loads((base/'preparation-r2/config.json').read_text());ref=json.loads((base/'shape-r2/reference.input.json').read_text());profile=json.loads(Path(c['art_profile']).read_text());model=base/'candidate-r13/fish.glb';tri=mesh(model,'Reference_head_body');L=c['display_length_m'];origin=ref['source_canvas']['origin_u'];span=ref['head_span_m'];plate=Image.open(base/'feedback-r14/generated-skin-plate.png').convert('RGB').resize((2048,2048),Image.Resampling.NEAREST);panels=json.loads((base/'feedback-r14/skin-edit-panels.json').read_text());rows=[];indices={};maps={};board=Image.new('RGB',(1600,1050),'#25343c');draw=ImageDraw.Draw(board)
 intervals=[(min(p[0]for p in f['polygon']),max(p[0]for p in f['polygon']))for f in profile['fins']if not f['name'].startswith('Caudal')]
 for i,role in enumerate(['side','top','bottom']):
  raw=np.array(Image.open(base/f'sources/{role}.png').convert('RGBA'));old=np.array(Image.open(base/f'skin-input-r2/clean-{role}.png').convert('RGBA'));H,W=raw.shape[:2];yy,xx=np.indices((H,W));u=xx/W;opaque=raw[:,:,3]>250;alpha=np.zeros((H,W),np.uint8);p=tri.copy();p[:,:,0]=(p[:,:,0]/L+origin)*(W-1);protect=np.zeros((H,W),bool)
  if role=='side':p[:,:,1]=(.5-p[:,:,2]/(H/W*L))*(H-1)
  else:
   hy=np.where(opaque&(u>.87))[0];center=(hy.min()+hy.max())/2;p[:,:,1]=center+tri[:,:,1]/span*(hy.max()-hy.min())
  for t in p:cv2.fillConvexPoly(alpha,np.rint(t[:,:2]).astype(np.int32),1)
  alpha=alpha>0;alpha[u>=head_limit]=old[u>=head_limit,3]>250
  if role=='side':
   mask=np.zeros((H,W),np.uint8)
   for f in profile['fins']:
    if not f['name'].startswith('Caudal'):cv2.fillPoly(mask,[np.rint(np.array(f['polygon'])*[W,H]).astype(np.int32)],1)
   core=(cv2.dilate(mask,np.ones((55,55),np.uint8))>0)&alpha;protect=(u>=.748)&(u<.89)&(yy>H*.43)&(yy<H*.9);core[protect]=False
  else:
   ext=opaque&~alpha&(u<head_limit);core=(cv2.dilate(ext.astype(np.uint8),np.ones((61,61),np.uint8))>0)&alpha;lo=np.zeros(W);hi=np.zeros(W)
   for x in range(W):
    y=np.where(alpha[:,x])[0];lo[x]=y.min()if len(y)else center;hi[x]=y.max()if len(y)else center
   r=abs((yy-(lo+hi)[None,:]/2)/np.maximum((hi-lo)[None,:]/2,1))
   for a,b in intervals:core|=alpha&(u>a-.012)&(u<b+.012)&(r>.22)
   if role=='top':core|=alpha&(u>.21)&(u<.86)&(abs(yy-center)<H*.035)
   else:core|=alpha&(u>.22)&(u<.46)
   core|=alpha&(u<head_limit)
  # The rejected auxiliary and lateral trunk fields also contained stretched
  # silhouette hatch marks outside individual fin polygons. Restore the full
  # posterior skin field; the native lateral gill ROI and head remain exact.
  core|=alpha&(u<head_limit)
  core|=alpha&~opaque
  # Painted silhouette ink must not wrap around a volumetric body. Its true
  # silhouette is provided by geometry, including previously hidden tissue.
  core|=alpha&(distance_transform_edt(alpha)<18)&(u<head_limit)
  core&=u<head_limit;core[protect]=False;distance=distance_transform_edt(~core);gain=np.clip(1-distance/16,0,1);gain=gain*gain*(3-2*gain);gain[protect|(u>=head_limit)|~alpha]=0
  panel=next(p for p in panels if p['role']==role);x,y,w,h=[panel[k]for k in ['x','y','width','height']];donor=np.array(plate.crop((x,y,x+w,y+h)).resize((W,H),Image.Resampling.NEAREST));tissue=donor.min(2)<244;n,labels,stats,_=cv2.connectedComponentsWithStats(tissue.astype(np.uint8));assert n>1;mask=labels==(1+stats[1:,4].argmax());safe=binary_erosion(mask,iterations=4);assert safe.sum()>1000;near=distance_transform_edt(~safe,return_distances=False,return_indices=True)
  # Register the TWO-dimensional body tissue domain before sampling. A nearest
  # opaque fallback outside a differently shaped donor extrudes contour ink
  # into fence-like stripes. X remains longitudinal; every Y varies across
  # the actual body section and an interior donor section, never one row.
  alo=np.full(W,np.nan);ahi=alo.copy();dlo=alo.copy();dhi=alo.copy()
  for col in range(W):
   ay=np.where(alpha[:,col])[0];dy=np.where(safe[:,col])[0]
   if len(ay):alo[col]=ay.min();ahi[col]=ay.max()
   if len(dy):dlo[col]=dy.min();dhi[col]=dy.max()
  for array in [alo,ahi,dlo,dhi]:
   good=np.isfinite(array);array[:]=np.interp(np.arange(W),np.where(good)[0],array[good])
  relative=np.clip((yy-alo[None,:])/np.maximum(ahi-alo,1)[None,:],0,1)
  dy=np.clip(np.rint(dlo[None,:]+(.08+.84*relative)*(dhi-dlo)[None,:]).astype(int),0,H-1);dx=xx.copy();bad=~safe[dy,dx];dy[bad],dx[bad]=near[0,dy[bad],dx[bad]],near[1,dy[bad],dx[bad]];near=np.stack([dy,dx]);donor=donor[dy,dx]
  result=raw.copy();result[:,:,:3]=np.rint(raw[:,:,:3]*(1-gain[:,:,None])+donor*gain[:,:,None]).astype(np.uint8);result[:,:,3]=alpha.astype(np.uint8)*255;head=u>=head_limit;result[head]=old[head];Image.fromarray(result).save(out/f'clean-{role}.png');changed=gain>0;assert np.array_equal(result[~changed&~head,:3],raw[~changed&~head,:3]);assert np.array_equal(result[protect,:3],raw[protect,:3]);assert np.array_equal(result[head],old[head]);maps[role+'_target_xy']=np.c_[xx[changed],yy[changed]].astype(np.int16);maps[role+'_generated_donor_xy']=np.c_[near[1,changed],near[0,changed]].astype(np.int16);indices[{'side':'clean_side','top':'dorsal','bottom':'clean_bottom'}[role]]=distance_transform_edt(~binary_erosion(result[:,:,3]>250,iterations=2),return_distances=False,return_indices=True).astype(np.int16)
  rows.append(dict(role=role,source_sha256=sha(base/f'sources/{role}.png'),previous_sha256=sha(base/f'skin-input-r2/clean-{role}.png'),output_sha256=sha(out/f'clean-{role}.png'),synthesized_or_blended_pixels=int(changed.sum()),original_rgb_exact_outside_mask=True,original_side_gills_exact=True,previous_head_rgba_exact=True,generated_source='feedback-r14/generated-skin-plate.png',geometry_change=False))
  for j,img in enumerate([old,result]):
   im=Image.fromarray(img);im.thumbnail((790,310),Image.Resampling.NEAREST);board.paste(im,(j*800+(800-im.width)//2,i*350+30),im);draw.text((j*800+6,i*350+6),role+(' previous rejected'if j==0 else' masked synthetic restoration'),fill='white')
 np.savez_compressed(out/'donor-addresses.npz',**maps);np.savez_compressed(out/'sampler-indices.npz',**indices);board.save(out/'skin-before-after.jpg',quality=94);report=dict(ok=True,kind='masked_generated_hidden_skin_preparation',species=c['species'],model_sha256=sha(model),generated_plate_sha256=sha(base/'feedback-r14/generated-skin-plate.png'),generation_record_sha256=sha(base/'feedback-r14/generation-record.json'),repairs=rows,donor_map_sha256=sha(out/'donor-addresses.npz'),visual_review='pending',head_limit=head_limit,scope='Posterior and explicitly extended neck skin use declared generated donor pixels/edge blend with full two-dimensional registration. Original source/lip PNG immutable; own head and actual geometry not generated or replaced.');(out/'preparation.validation.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--head-limit',type=float,default=.87);p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.base.resolve(),a.output.resolve(),a.head_limit);print('SKIN_PREPARED',a.base.name)
