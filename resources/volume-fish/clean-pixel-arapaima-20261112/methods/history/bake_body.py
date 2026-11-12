"""New body charts and continuous circumferential skin; no fin writes."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt
ROOT=Path('/Users/czl/projects/game-ai-foundry');W=ROOT/'work/arapaima-jaw-20261112';D=W/'bake-r1'
sys.path[:0]=[str(ROOT/'resources/scripts/volume-fish/portable'),str(ROOT/'resources/scripts/volume-fish'),str(ROOT/'resources/volume-fish/clean-pixel-yellow-croaker-20261111/method')]
from bake_material import raster,Donor,columns,biggest_component,smooth
from glb_io import sha
b=json.loads((W/'rebuilt-body.json').read_text());p=np.array(b['vertices']);faces=np.array(b['faces']);N=b['segments'];R=b['rings'];rings=p[:N*R].reshape(R,N,3);centers=rings.mean(1);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(centers,axis=0),axis=1))];s/=s[-1]
uv=[];thetas=[]
for f,oral in zip(faces,b['oral']):
 if oral:uv.append([[.5,.5]]*3);thetas.append([0.]*3);continue
 if np.max(f)>=N*R:
  q=p[f];c=centers[0];half=np.ptp(rings[0],axis=0)/2;uv.append(np.c_[.5+(q[:,2]-c[2])/half[2]*.08,.91+(q[:,1]-c[1])/half[1]*.07].tolist());thetas.append(np.arctan2(q[:,2]-c[2],q[:,1]-c[1]).tolist());continue
 j=f%N;k=f//N;j=j.astype(float)
 if np.ptp(j)>N/2:j[j==0]=N
 uv.append(np.c_[.015+.97*s[k],.015+.805*j/N].tolist());thetas.append((j/N*2*np.pi).tolist())
uv=np.array(uv);thetas=np.array(thetas)
side=np.array(Image.open(D/'body-side.png').convert('RGBA'));sheet=np.array(Image.open(D/'body-top-bottom.png').convert('RGBA'))
def donor(im,side_skin=False):
 rgb=im[:,:,:3].astype(float)
 valid=(rgb.mean(2)>52)&(rgb[:,:,2]<=rgb[:,:,1]+2)&(rgb[:,:,1]<=rgb[:,:,0]+14)
 mask=biggest_component(valid)&valid
 # Preserve only the skin. The dark actual oral gap is owned by its own material.
 mask &= (im[:,:,:3].mean(2)>43)
 if side_skin:mask[:,int(im.shape[1]*.84):] &= (im[:,int(im.shape[1]*.84):,:3].mean(2)>72)
 return Donor(im,mask,grid=1)
ds=donor(side,True);dt=donor(sheet[:sheet.shape[0]//2]);db=donor(sheet[sheet.shape[0]//2:]);left,right,upper,lower=ds.bounds
nose=p[:,0].max();tail=p[:,0].min();L=nose-tail
# Finite section envelope for local head positioning, not a second silhouette.
xs=[];yl=[];yh=[];zw=[]
for ring in rings:
 xs.append(ring[:,0].mean());yl.append(ring[:,1].min());yh.append(ring[:,1].max());zw.append(abs(ring[:,2]).max())
order=np.argsort(xs);xs=np.array(xs)[order];yl=np.array(yl)[order];yh=np.array(yh)[order];zw=np.array(zw)[order]
def axial(d,along,cross):
 l,r,up,down=d.bounds;x=l+along*(r-l);ix=np.rint(x).astype(int);y=up[ix]+cross*(down[ix]-up[ix]);return d.sample(x,y)
def skin(points,theta):
 u=np.clip((points[:,0]-tail)/L,0,1);x=left+u*(right-left);ix=np.rint(x).astype(int);cos=np.cos(theta);cross=.035+.93*np.arccos(np.clip(cos,-1,1))/np.pi
 head=smooth((u-.86)/.07);lo=np.interp(points[:,0],xs,yl);hi=np.interp(points[:,0],xs,yh);vertical=np.clip((hi-points[:,1])/np.maximum(hi-lo,1e-5),.04,.96)
 cross=cross*(1-head)+vertical*head;y=upper[ix]+cross*(lower[ix]-upper[ix]);color=ds.sample(x,y)
 # Only the real dorsal forehead and ventral throat use axial donors; do not
 # project the lateral gill cover across the head centerline.
 width=np.interp(points[:,0],xs,zw);transverse=np.clip(.5+.43*points[:,2]/np.maximum(width,1e-5),.07,.93)
 top=axial(dt,u,transverse);bottom=axial(db,u,transverse);mix=smooth((abs(cos)-.48)/.44)*smooth((u-.72)/.10)
 color=color*(1-mix[:,None])+np.where((cos>0)[:,None],top,bottom)*mix[:,None]
 return np.rint(np.clip(color,0,255)).astype('uint8')
H,WID=1536,3072;out=np.full((H,WID,4),255,np.uint8);out[:,:,:3]=[60,63,59];rank=np.zeros((H,WID),np.float32)
for f,o,t,us in zip(faces,b['oral'],thetas,uv):
 if o:continue
 pixels,bary,priority=raster(us,WID,H,2.);xx,yy=pixels.T;keep=priority>rank[yy,xx];xx,yy,bary,priority=xx[keep],yy[keep],bary[keep],priority[keep]
 if not len(xx):continue
 q=bary@p[f];angle=bary@t;color=skin(q,angle);out[yy,xx,:3]=color;rank[yy,xx]=priority
# Texture coordinates above are image-down; Blender author flips V explicitly.
Image.fromarray(out).save(D/'body-atlas.png');np.save(D/'body-domain.npy',rank>0)
(D/'body-uv.json').write_text(json.dumps({'uv_image_down_per_face':uv.tolist(),'body_rings':R,'segments':N},separators=(',',':')))
concept=np.array(Image.open(W/'material-concept-r1/arapaima-gray-green-concept.png').convert('RGBA'))
# Approved eye pixels only, independent patch, no duplicate eye on the body.
Image.fromarray(concept[537:554,1390:1407]).save(D/'eye.png')
# Approved mouth recess is sampled independently from skin and kept dark.
oral=concept[561:565,1427:1431];Image.fromarray(oral).save(D/'oral.png')
report={'stage':'body_bake','model_input_sha256':sha(W/'rebuild-r2/fish.glb'),'donors':{str(q):sha(q) for q in [D/'body-side.png',D/'body-top-bottom.png',W/'material-concept-r1/arapaima-gray-green-concept.png']},'body_texels':int((rank>0).sum()),'body_atlas_sha256':sha(D/'body-atlas.png'),'side_fallback':ds.fallback,'method':'Continuous circumferential body coordinate from one complete finless skin; axial donors only for forehead/throat; independent eyes and oral cavity. New source-owned UV. All fin images untouched.','status':'local_visual_review_pending'}
(D/'body-bake.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
