"""Bake user-requested plain ventral-head color; no lateral gill donor imagery."""
import argparse,json,hashlib,io,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=json.loads(a.config.read_text());out=a.output.resolve();assert not out.exists() and out.is_relative_to(ROOT/'projects/fishing-2d/experiments');model=ROOT/c['model'];assert sha(model)==c['model_sha256'];profile=json.loads((ROOT/c['profile']).read_text());d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];pos=arrays(d,b,pr['attributes']['POSITION']);uv=arrays(d,b,pr['attributes']['TEXCOORD_0']);indices=arrays(d,b,pr['indices']).reshape(-1);v=d['bufferViews'][d['images'][0]['bufferView']];rgba=np.array(Image.open(io.BytesIO(b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).convert('RGBA'));H,W=rgba.shape[:2];old=rgba.copy();weights=np.zeros((H,W),np.float32);sections=np.array(profile['body']['sections']);aspect=1/profile['source_aspect_ratio']
def field(points):
 u=points[:,0]+.5;top=np.interp(u,sections[:,0],sections[:,1]);bottom=np.interp(u,sections[:,0],sections[:,2]);center=(.5-(top+bottom)/2)*aspect;height=(bottom-top)/2*aspect;width=np.interp(u,sections[:,0],sections[:,3]);ventral=(center-points[:,1])/np.maximum(height,1e-6);side=np.abs(points[:,2])/np.maximum(width,1e-6)
 return smooth((u-c['head_start_u'])/(c['head_full_u']-c['head_start_u']))*(1-smooth((u-c['lip_fade_start_u'])/(c['lip_protected_u']-c['lip_fade_start_u'])))*smooth((ventral-c['ventral_start'])/(c['ventral_full']-c['ventral_start']))*(1-smooth((side-c['side_full'])/(c['side_protected']-c['side_full'])))
native_material=c.get('native_material')
native_pixels=None
if native_material:
 source=ROOT/native_material['source'];assert sha(source)==native_material['source_sha256'];native_pixels=np.array(Image.open(source).convert('RGBA'))
 x0,y0,x1,y1=native_material['roi_px'];assert np.all(native_pixels[y0:y1,x0:x1,3]==255),'Native skin donor must be entirely opaque'
 if native_material.get('normalize_illumination'):
  from scipy.ndimage import gaussian_filter
  patch=native_pixels[y0:y1,x0:x1,:3].astype(float)
  # Remove donor baked lighting, keeping measured native paint residual.
  detail=patch-gaussian_filter(patch,(native_material['illumination_sigma_px'],native_material['illumination_sigma_px'],0))
  normalized=np.clip(np.rint(np.array(c['plain_RGB'])+detail*native_material['detail_gain']),0,255).astype(np.uint8)
 if native_material.get('material_tile'):
  tile=ROOT/native_material['material_tile'];assert sha(tile)==native_material['material_tile_sha256'];material_tile=np.array(Image.open(tile).convert('RGB'))
def pigment(points):
 if native_material:
  u=points[:,0]+.5;width=np.interp(u,sections[:,0],sections[:,3]);x0,y0,x1,y1=native_material['roi_px'];start,end=native_material['target_u_range'];tx=np.clip((u-start)/(end-start),0,1);ty=np.clip(.5+.5*points[:,2]/np.maximum(width,1e-6),0,1)
  if native_material.get('material_tile'):
   sx=np.clip(np.floor((u-start)*2028).astype(int),0,material_tile.shape[1]-1);sy=np.clip(np.floor(points[:,2]*2028+material_tile.shape[0]/2).astype(int),0,material_tile.shape[0]-1)
   return material_tile[sy,sx]
  if native_material.get('normalize_illumination'):
   def reflect(q,span):
    q=np.mod(np.floor(q).astype(int),2*span);return np.where(q<span,q,2*span-1-q)
   sx=reflect((u-start)*2028,x1-x0);sy=reflect(points[:,2]*2028,y1-y0)
   return normalized[sy,sx]
  sx=np.rint(x0+tx*(x1-x0-1)).astype(int);sy=np.rint(y0+ty*(y1-y0-1)).astype(int)
  return native_pixels[sy,sx,:3]
 style=c.get('pixel_clusters')
 if not style:return np.tile(c['plain_RGB'],(len(points),1))
 # Continuous anatomical coordinates, snapped to native-size brush pixels.
 # Broad connected tonal islands, not per-texel random noise or side-gill imagery.
 xy=np.floor(np.c_[points[:,0]+.5,points[:,2]]*2028/style['pixel_step_px'])*style['pixel_step_px']
 def value_noise(scale,seed):
  q=xy/scale;ij=np.floor(q);t=smooth(q-ij)
  def h(x,y):return np.mod(np.sin(x*127.1+y*311.7+seed)*43758.5453,1)
  a=h(ij[:,0],ij[:,1]);b=h(ij[:,0]+1,ij[:,1]);cc=h(ij[:,0],ij[:,1]+1);dd=h(ij[:,0]+1,ij[:,1]+1)
  return (a*(1-t[:,0])+b*t[:,0])*(1-t[:,1])+(cc*(1-t[:,0])+dd*t[:,0])*t[:,1]
 n=.7*value_noise(style['cluster_scale_px'],13)+.3*value_noise(style['detail_scale_px'],29)
 tone=np.digitize(n,style['tone_thresholds']);return np.asarray(style['palette_RGB'])[tone]
target=np.empty_like(rgba[:,:,:3]);target[:]=c['plain_RGB']
for part in d['extras']['geometry_parts']:
 if part['role']!='body_skin':continue
 for ids in indices[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3):
  xyz=pos[ids];q=uv[ids]*[W,H];matrix=np.stack([q[1]-q[0],q[2]-q[0]],axis=1)
  if abs(np.linalg.det(matrix))<1e-8:continue
  if field(xyz).max()==0 and xyz[:,0].max()+.5<c['head_start_u']:continue
  lo=np.maximum(np.floor(q.min(0)).astype(int)-2,0);hi=np.minimum(np.ceil(q.max(0)).astype(int)+2,[W-1,H-1]);yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];t=np.c_[xx.ravel()+.5,yy.ravel()+.5];bc=(t-q[0])@np.linalg.inv(matrix).T;bc=np.c_[1-bc.sum(1),bc];inside=(bc>=-.02).all(1);bc=np.maximum(bc,0);bc/=bc.sum(1)[:,None];points=bc@xyz;w=field(points);w[~inside]=0;view=weights[lo[1]:hi[1]+1,lo[0]:hi[0]+1];take=w.reshape(view.shape)>view;patch=target[lo[1]:hi[1]+1,lo[0]:hi[0]+1];patch[take]=pigment(points).reshape(*view.shape,3)[take];np.maximum(view,w.reshape(view.shape),out=view)
mask=weights>0;rgba[:,:,:3]=np.rint(old[:,:,:3]*(1-weights[:,:,None])+target*weights[:,:,None]).astype(np.uint8);assert np.array_equal(rgba[:,:,3],old[:,:,3]);assert mask.any();assert np.array_equal(rgba[~mask],old[~mask])
protected=[]
for part in d['extras']['geometry_parts']:
 if part['role']=='body_skin':continue
 # Conservative whole UV rectangle protects fins, mouth and barbels, including all wall donors.
 points=uv[part['vertex_start']:part['vertex_start']+part['vertex_count']]*[W,H];lo=np.floor(points.min(0)).astype(int);hi=np.floor(points.max(0)).astype(int);assert not mask[lo[1]:hi[1]+1,lo[0]:hi[0]+1].any(),part['name'];protected.append(part['name'])
out.mkdir(parents=True);Image.fromarray(rgba).save(out/'atlas.png');Image.fromarray((weights*255).astype(np.uint8)).save(out/'edit-weight.png');report={'ok':True,'kind':'plain_ventral_head_color_repair','repair_subject':'ventral head plain color','config_sha256':sha(a.config),'baseline_model_sha256':sha(model),'atlas':str(out/'atlas.png'),'atlas_sha256':sha(out/'atlas.png'),'alpha_exact':True,'pixels_outside_declared_edit_mask_exact':True,'changed_pixels':int(np.any(rgba!=old,axis=2).sum()),'protected_non_skin_parts':protected,'plain_RGB':c['plain_RGB'],'scope':'User-authorized authored plain color, no lateral gill/scales/eye donor image. Continuous anatomical ventral-head field with short fades; lip/anterior boundary and lateral supports excluded. Geometry and UV unchanged; final source and actual visual/gates required.'};(out/'material.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'changed_pixels':report['changed_pixels']}))
