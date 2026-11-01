"""Erase only manually traced ventral gill-line marks on the original material.

Repair in a native-density anatomical underside chart, then transfer only those
small polygons back to the original atlas. No broad skin recoloring/quilting.
"""
import argparse,json,hashlib,io,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=json.loads(a.config.read_text());out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();model=ROOT/c['model'];assert sha(model)==c['model_sha256'];d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];pos=arrays(d,b,pr['attributes']['POSITION']);uv=arrays(d,b,pr['attributes']['TEXCOORD_0']);ids=arrays(d,b,pr['indices']).reshape(-1);bv=d['bufferViews'][d['images'][0]['bufferView']];old=np.array(Image.open(io.BytesIO(b[bv.get('byteOffset',0):bv.get('byteOffset',0)+bv['byteLength']])).convert('RGBA'));H,W=old.shape[:2];scale=c['native_density'];u0,u1,z0,z1=c['chart_bounds'];CW,CH=int(np.ceil((u1-u0)*scale)),int(np.ceil((z1-z0)*scale));chart=np.zeros((CH,CW,3),np.uint8);depth=np.full((CH,CW),np.inf);triangles=[]
def chart_xy(xyz):return np.c_[(xyz[:,0]+.5-u0)*scale,(xyz[:,2]-z0)*scale]
def pixels(q,width,height,padding=0):
 matrix=np.stack([q[1]-q[0],q[2]-q[0]],axis=1)
 if abs(np.linalg.det(matrix))<1e-8:return None
 lo=np.maximum(np.floor(q.min(0)).astype(int)-padding,0);hi=np.minimum(np.ceil(q.max(0)).astype(int)+padding,[width-1,height-1])
 if (hi<lo).any():return None
 yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];t=np.c_[xx.ravel()+.5,yy.ravel()+.5];bary=(t-q[0])@np.linalg.inv(matrix).T;bary=np.c_[1-bary.sum(1),bary];valid=(bary>=-1e-6).all(1)
 if padding:
  # GPU nearest can read a texel whose centre lies just outside a triangle.
  # Repair that finite texel footprint, not only centres strictly inside UV.
  clipped=np.maximum(bary,0);clipped/=clipped.sum(1)[:,None];valid|=np.linalg.norm(clipped@q-t,axis=1)<=1.5;bary=clipped
 return xx.ravel()[valid],yy.ravel()[valid],bary[valid]
for part in d['extras']['geometry_parts']:
 if part['role']!='body_skin':continue
 for index in ids[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3):
  xyz=pos[index];tuv=uv[index];triangles.append((xyz,tuv));r=pixels(chart_xy(xyz),CW,CH)
  if r is None:continue
  x,y,bary=r;points=bary@xyz;take=points[:,1]<depth[y,x];x,y,bary,points=x[take],y[take],bary[take],points[take];sample=np.floor((bary@tuv)*[W,H]).astype(int);sample=np.clip(sample,[0,0],[W-1,H-1]);chart[y,x]=old[sample[:,1],sample[:,0],:3];depth[y,x]=points[:,1]
valid=np.isfinite(depth);_,nearest=distance_transform_edt(~valid,return_indices=True);chart[~valid]=chart[nearest[0][~valid],nearest[1][~valid]]
mask=np.zeros((CH,CW),np.uint8);screen=c['reference_capture'];polygons=[]
for polygon in c['gill_line_polygons_capture_px']:
 q=np.asarray(polygon,float);u=.5+(screen['focus_x_m']+(.5-q[:,0]/screen['width'])*screen['camera_size_m'])/screen['model_scale'];z=(q[:,1]-screen['height']/2)/screen['width']*screen['camera_size_m']/screen['model_scale'];xy=np.c_[(u-u0)*scale,(z-z0)*scale];cv2.fillPoly(mask,[np.rint(xy).astype(np.int32)],255);polygons.append(xy.tolist())
if c.get('gill_region_uvz_polygon'):
 q=np.asarray(c['gill_region_uvz_polygon']);xy=np.c_[(q[:,0]-u0)*scale,(q[:,1]-z0)*scale];cv2.fillPoly(mask,[np.rint(xy).astype(np.int32)],255);polygons.append(xy.tolist())
margin=c.get('line_margin_native_px',1);mask=cv2.dilate(mask,np.ones((2*margin+1,2*margin+1),np.uint8));assert not np.any((mask>0)&~valid),'Gill mask extends beyond actual underside'
if c.get('protect_actual_mouth_rim_native'):
 from collections import Counter
 from scipy.spatial import cKDTree
 edges=Counter();coords={}
 for part in d['extras']['geometry_parts']:
  if part['role']!='mouth':continue
  for tri in ids[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3):
   keys=[tuple(np.round(pos[i].astype(float),7))for i in tri]
   for key in keys:coords[key]=np.array(key)
   for aa,bb in zip(keys,keys[1:]+keys[:1]):edges[tuple(sorted((aa,bb)))]+=1
 rim=[(coords[aa],coords[bb])for (aa,bb),count in edges.items()if count==1];assert rim,'No actual mouth boundary'
 samples=np.array([aa*(1-t)+bb*t for aa,bb in rim for t in np.linspace(0,1,17)])
 yy,xx=np.where(mask>0);points=np.c_[u0+(xx+.5)/scale-.5,depth[yy,xx],z0+(yy+.5)/scale];distance=cKDTree(samples).query(points)[0];mask[yy[distance<c['protect_actual_mouth_rim_native']],xx[distance<c['protect_actual_mouth_rim_native']]]=0
 assert (mask>0).any()
if c.get('generated_texture'):
 g=c['generated_texture'];image=ROOT/g['path'];review=ROOT/g['review'];assert sha(image)==g['sha256']and sha(review)==g['review_sha256'];assert json.loads(review.read_text(encoding='utf8'))['ok']
 generated=np.array(Image.open(image).convert('RGBA'));assert np.all(generated[:,:,3]==255),'Local generated material must be opaque'
 yy,xx=np.where(mask>0);xmin,xmax,ymin,ymax=int(xx.min()),int(xx.max()),int(yy.min()),int(yy.max());tile=cv2.resize(generated[:,:,:3],(xmax-xmin+1,ymax-ymin+1),interpolation=cv2.INTER_NEAREST)
 source=chart.copy();source[ymin:ymax+1,xmin:xmax+1]=tile;weight=np.clip(distance_transform_edt(mask>0)/g['feather_native_px'],0,1);weight=weight*weight*(3-2*weight)
 fixed=np.rint(chart*(1-weight[:,:,None])+source*weight[:,:,None]).astype(np.uint8);fixed[mask==0]=chart[mask==0]
elif c.get('adjacent_native_donor_uvz'):
 # Replace the complete false gill mark, including its lighter/darker tissue
 # shape, using a reviewed clean patch of THIS original underside material.
 du0,du1,dz0,dz1=c['adjacent_native_donor_uvz'];dx0,dx1=np.rint((np.array([du0,du1])-u0)*scale).astype(int);dy0,dy1=np.rint((np.array([dz0,dz1])-z0)*scale).astype(int)
 donor=chart[dy0:dy1,dx0:dx1].copy();assert donor.size and valid[dy0:dy1,dx0:dx1].all() and not mask[dy0:dy1,dx0:dx1].any(),'Donor must exclude false gill and remain on actual underside'
 yy,xx=np.where(mask>0);xmin,xmax,ymin,ymax=int(xx.min()),int(xx.max()),int(yy.min()),int(yy.max());source=chart.copy();source[ymin:ymax+1,xmin:xmax+1]=cv2.resize(donor,(xmax-xmin+1,ymax-ymin+1),interpolation=cv2.INTER_NEAREST)
 # OpenCV may mutate its mask argument; keep the authored ownership mask intact.
 fixed=cv2.seamlessClone(source,chart,mask.copy(),((xmin+xmax)//2,(ymin+ymax)//2),cv2.NORMAL_CLONE);fixed[mask==0]=chart[mask==0]
 if c.get('retain_adjacent_pixel_detail'):
  # Preserve native tiny paint marks without copying the donor's large shade
  # bands or putting the removed gill contours back into the repaired region.
  f=donor.astype(np.float32);detail=np.clip(f-cv2.GaussianBlur(f,(0,0),1.5),-5,5)
  iy,ix=np.indices(mask.shape);grain=detail[iy%donor.shape[0],ix%donor.shape[1]]*c['retain_adjacent_pixel_detail']
  active=mask>0;fixed[active]=np.clip(np.rint(fixed[active].astype(float)+grain[active]),0,255).astype(np.uint8)
else:fixed=cv2.inpaint(chart,mask,c.get('inpaint_radius_px',3),cv2.INPAINT_TELEA)
assert np.array_equal(fixed[mask==0],chart[mask==0]);atlas=old.copy();changed=np.zeros((H,W),bool)
for xyz,tuv in triangles:
 r=pixels(tuv*[W,H],W,H,2)
 if r is None:continue
 x,y,bary=r;points=bary@xyz;cx=np.floor(chart_xy(points)).astype(int);inside=(cx[:,0]>=0)&(cx[:,0]<CW)&(cx[:,1]>=0)&(cx[:,1]<CH);x,y,points,cx=x[inside],y[inside],points[inside],cx[inside];take=(mask[cx[:,1],cx[:,0]]>0)&(np.abs(points[:,1]-depth[cx[:,1],cx[:,0]])<.003)
 x,y,cx=x[take],y[take],cx[take];atlas[y,x,:3]=fixed[cx[:,1],cx[:,0]];changed[y,x]=True
assert changed.any()and np.array_equal(atlas[~changed],old[~changed])and np.array_equal(atlas[:,:,3],old[:,:,3]);protected=[]
for part in d['extras']['geometry_parts']:
 if part['role']=='body_skin':continue
 q=uv[part['vertex_start']:part['vertex_start']+part['vertex_count']]*[W,H];lo=np.floor(q.min(0)).astype(int);hi=np.floor(q.max(0)).astype(int);assert not changed[lo[1]:hi[1]+1,lo[0]:hi[0]+1].any(),part['name'];protected.append(part['name'])
out.mkdir(parents=True);Image.fromarray(atlas).save(out/'atlas.png');Image.fromarray(chart).save(out/'underside-before.png');Image.fromarray(fixed).save(out/'underside-after.png');Image.fromarray(mask).save(out/'gill-lines-only-mask.png');Image.fromarray(changed.astype(np.uint8)*255).save(out/'atlas-edit-mask.png');report={'ok':True,'kind':'original_material_gill_lines_only_repair','baseline_model_sha256':sha(model),'config_sha256':sha(a.config),'atlas':str(out/'atlas.png'),'atlas_sha256':sha(out/'atlas.png'),'alpha_exact':True,'pixels_outside_declared_edit_mask_exact':True,'changed_pixels':int(np.any(atlas!=old,axis=2).sum()),'scoped_atlas_pixels':int(changed.sum()),'gill_chart_pixels':int((mask>0).sum()),'protected_non_skin_parts':protected,'scope':'Original pre-recoloring material retained byte-for-byte outside three manually traced ventral gill markings. Local surrounding original colors fill those lines only via native-density underside chart. No broad donor, flat fill, pigment field or global color cleaning. Actual mouth/side/underside review required.'};report.update(scope=c.get('scope',report['scope']),adjacent_native_donor_uvz=c.get('adjacent_native_donor_uvz'),retain_adjacent_pixel_detail=c.get('retain_adjacent_pixel_detail',0));(out/'material.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'changed_pixels':report['changed_pixels'],'gill_chart_pixels':report['gill_chart_pixels']}))
