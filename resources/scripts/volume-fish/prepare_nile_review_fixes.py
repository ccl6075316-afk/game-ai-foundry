"""Local RGB repair from the existing whole-skin donor; no image generation."""
from pathlib import Path
import json,hashlib,cv2
import numpy as np
from PIL import Image
repo=Path(__file__).resolve().parents[3]
trial=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial'
old=trial/'round4-ab-textured';out=trial/'round5-user-review-fixes';out.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
side=np.asarray(Image.open(old/'shared/body-side.png').convert('RGBA'))
atlas=np.asarray(Image.open(old/'shared/body-atlas.png').convert('RGBA')).copy()
h,w=side.shape[:2];ah=atlas.shape[0]
profile=read(repo/'resources/volume-fish/nile-tilapia-reference-cage-163.profile.json');sec=np.array(profile['body']['sections'])
theta=np.arange(ah)/ah*2*np.pi;u=(np.arange(w)+.5)/w
top=np.interp(u,sec[:,0],sec[:,1]);bottom=np.interp(u,sec[:,0],sec[:,2])
v=(top[None,:]+bottom[None,:])/2-(bottom-top)[None,:]/2*np.cos(theta[:,None])
px=np.broadcast_to(np.arange(w)[None,:],(ah,w));py=np.clip(np.floor(v*h).astype(int),0,h-1)
safe=cv2.distanceTransform((side[:,:,3]>242).astype('uint8'),cv2.DIST_L2,5)>7
yy,xx=np.mgrid[:h,:w]
mouth_line=.552+(.502-.552)*np.clip((xx/w-.95)/.045,0,1)
safe &= ~((xx/w>.943)&(np.abs(yy/h-mouth_line)<.011))
_,nearest=cv2.distanceTransformWithLabels((~safe).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
sy,sx=np.where(safe);idx=np.clip(nearest[py,px]-1,0,len(sx)-1)
donor_x=np.where(safe[py,px],px,sx[idx]);donor_y=np.where(safe[py,px],py,sy[idx])
# Registration/mask boundaries can include the generated drawing's dark lower
# outline. The repaired belly strip samples bounded interior skin, not that rim.
donor_y=np.minimum(donor_y,np.broadcast_to(np.floor((bottom-.024)*h).astype(int)[None,:],(ah,w)))
clean=side[donor_y,donor_x]
# The old ventral chart contains repeated pectoral ray fragments. Replace only
# the below-pectoral domain with the already coherent whole-body donor.
# The accepted grey142 connector lies above this domain and stays intact.
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
amount=smooth((px-1160)/65)*smooth((1500-px)/65)*smooth((v*h-660)/30)
fixed=atlas.copy();fixed[:,:,:3]=np.round(atlas[:,:,:3]*(1-amount[:,:,None])+clean[:,:,:3]*amount[:,:,None]).astype('uint8');fixed[:,:,3]=255
Image.fromarray(fixed).save(out/'body-atlas-clean-pectoral.png')
Image.fromarray(np.round(amount*255).astype('uint8')).save(out/'pectoral-atlas-repair-mask.png')

# B's newly exposed inward jaw faces use bounded same-jaw skin, not darkest
# mouth-outline pixels. Freeze explicit donor domains, keeping eyes/gill lines out.
regions={'upper':(1860,1900,454,485),'lower':(1855,1870,554,562)}
original=np.asarray(Image.open(trial/'round2/Closed_body-0-source_texture.png').convert('RGBA'))
lining=np.zeros_like(side);lining[:]=side
for name,(x0,x1,y0,y1) in regions.items():
 assert np.all(side[y0:y1,x0:x1,3]==255),name+' donor crosses background'
 Image.fromarray(side[y0:y1,x0:x1]).save(out/(name+'-lining-donor.png'))
# The source mouth outline also wraps onto the inward-facing lip corners in
# B's cylindrical atlas. Clear only dark ink in the annotated anterior oral
# band, using the separate same-jaw donor rectangles above. The real opening
# is geometry; no black stripe is painted to impersonate it.
b_atlas=fixed.copy();line=.552+(.502-.552)*np.clip((u-.95)/.045,0,1)
mouth_domain=(px/1961>.945)&(np.abs(v-line[None,:])<.038)
ink=mouth_domain&(np.max(fixed[:,:,:3],axis=2)<137)&(np.mean(fixed[:,:,:3],axis=2)<112)
for name,(x0,x1,y0,y1) in regions.items():
 selected=ink&((v<line[None,:]) if name=='upper' else (v>=line[None,:]))
 dx=np.clip(np.floor(x0+.5+(x1-x0-1)*np.clip((px/1961-.95)/.045,0,1)).astype(int),x0,x1-1)
 dy=np.broadcast_to(np.floor(y0+.5+(y1-y0-1)*np.abs(np.sin(theta[:,None]))).astype(int),(ah,w))
 b_atlas[selected]=side[dy[selected],dx[selected]]
Image.fromarray(b_atlas).save(out/'B-body-atlas-no-inward-outline.png')
write(out/'repair.plan.validation.json',{'kind':'nile_user_review_repair_plan','formal_acceptance':False,'preferred_max':1500,'hard_max':2000,'inputs':{str(p.relative_to(repo)).replace('\\','/'):sha(p) for p in [old/'A-artifacts/fish.blend',old/'B-artifacts/fish.blend',old/'shared/body-side.png',old/'shared/body-atlas.png',repo/'resources/volume-fish/nile-tilapia-reference-cage-163.profile.json']},'pectoral_cause':'Old directional ventral chart repeats old pectoral rays on the body. Whole-body clean donor does not contain them.','pectoral_domain_pixels':{'u_edges':[1160,1500],'side_y_start':660,'feather_pixels':[65,30]},'protected142':'Only lower chart pollution targeted; existing side donor and upper body-owned connector retained.','jaw_donor_domains_px':regions,'B_inward_ink_domain':{'u_min':.945,'source_v_distance_from_slit':.038,'ink_max_channel':137,'ink_mean':112,'changed_pixels':int(ink.sum())},'jaw_cut':'B only: tapered real oral subtraction, upper/lower inward ledges reduced; no separately outlined lip strip.','tail':'Keep all existing caudal vertices/topology/UV/weights/material.','fins':'Measure existing actual thickness and retain source geometry for now; no arbitrary global thickening.','outputs':{p.name:sha(p) for p in [out/'body-atlas-clean-pectoral.png',out/'B-body-atlas-no-inward-outline.png',out/'pectoral-atlas-repair-mask.png',out/'upper-lining-donor.png',out/'lower-lining-donor.png']}})
print(json.dumps({'ok':True,'local_changed_atlas_pixels':int(np.any(fixed!=atlas,axis=2).sum()),'output':str(out)}))
