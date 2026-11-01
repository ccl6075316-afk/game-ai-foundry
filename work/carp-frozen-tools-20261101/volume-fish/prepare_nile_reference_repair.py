"""Undo rejected row-clamp/patch fills; preserve 2D donors and measured A mouth."""
from pathlib import Path
import json,hashlib,re,math
import numpy as np
from PIL import Image
repo=Path(__file__).resolve().parents[3];trial=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial';old=trial/'round4-ab-textured';out=trial/'round6-reference-repair';out.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
side=np.array(Image.open(old/'shared/body-side.png').convert('RGBA'));atlas=np.array(Image.open(old/'shared/body-atlas.png').convert('RGBA'));h,w=side.shape[:2];ah=atlas.shape[0]
profile=read(repo/'resources/volume-fish/nile-tilapia-reference-cage-163.profile.json');sec=np.array(profile['body']['sections'])
theta=np.arange(ah)/ah*2*np.pi;u=(np.arange(w)+.5)/w;px=np.broadcast_to(np.arange(w)[None,:],(ah,w))
top=np.interp(u,sec[:,0],sec[:,1]);bottom=np.interp(u,sec[:,0],sec[:,2]);radius=(bottom-top)/2*h/1961;width=np.interp(u,sec[:,0],sec[:,3])
v=(top[None,:]+bottom[None,:])/2-(bottom-top)[None,:]/2*np.cos(theta[:,None])
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
# Integrate actual ellipse metric from the ventral midline to each side.
# The donor traverses a 2D native-pixel skin band. No y clamp, repeated row,
# Gaussian blur, arbitrary flat fill or rescaled tiny mouth rectangles.
q=np.linspace(0,math.pi/2,1025)
metric=np.sqrt((width[None,:]*np.cos(q[:,None]))**2+(radius[None,:]*np.sin(q[:,None]))**2)
arc=np.vstack([np.zeros((1,w)),np.cumsum((metric[:-1]+metric[1:])*.5*(q[1]-q[0]),axis=0)])
angle=np.arctan2(np.abs(np.sin(theta)),np.abs(np.cos(theta)));at=angle/(math.pi/2)*1024;i=np.minimum(np.floor(at).astype(int),1023);t=at-i
distance=arc[i]* (1-t[:,None])+arc[i+1]*t[:,None]
donor_y=np.rint(bottom[None,:]*h-24-distance*1961).astype(int)
assert np.all((donor_y>=0)&(donor_y<h))
lower=smooth((px-1160)/65)*smooth((1500-px)/65)*smooth((v*h-660)/30)
donor=side[donor_y,px]
selected=lower>0;assert np.all(donor[:,:,3][selected]==255),'Belly donor leaves accepted body interior'
fixed=atlas.copy();fixed[:,:,:3]=np.round(atlas[:,:,:3]*(1-lower[:,:,None])+donor[:,:,:3]*lower[:,:,None]).astype('uint8')

# Restore the original chart112 forehead blend. Round4 incorrectly faded the
# dorsal chart away at the very head, leaving side-image horizontal bands.
params=next(r for r in read(trial/'round2/material-inputs.validation.json')['materials'] if r['name']=='Closed_body-0')['parameters']
def vec(key):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?',params[key].split('(',1)[1],flags=re.I)))
eye=vec('chart112_eye_rect_native');blend=vec('chart112_normal_blend');longitudinal=vec('chart112_longitudinal')
actual_arc=angle[:,None]*width[None,:]
cy=np.clip(np.floor(actual_arc*1961).astype(int),0,383)
chart=np.array(Image.open(trial/'round2/Closed_body-0-chart112_dorsal.png').convert('RGBA'))
normal_y=np.abs(np.cos(theta[:,None])/np.maximum(radius[None,:],1e-7));normal_z=np.sin(theta[:,None])/np.maximum(width[None,:],1e-7)
normal_y=normal_y/np.sqrt(normal_y**2+normal_z**2)
amount=smooth((normal_y-blend[0])/(blend[1]-blend[0]))
amount*=np.maximum(1-smooth((u[None,:]-longitudinal[2])/(longitudinal[3]-longitudinal[2])),smooth((np.cos(theta[:,None])-.4)/.35))
p_y=(.5-v)*972/1961;eye_radius=np.sqrt(((u[None,:]-.5-eye[0])/eye[2])**2+((p_y-eye[1])/eye[3])**2)
amount*=smooth((eye_radius-1)/.35)
forehead=smooth((u[None,:]-.80)/.035)*(np.cos(theta[:,None])>0)
weight=amount*forehead
fixed[:,:,:3]=np.round(fixed[:,:,:3]*(1-weight[:,:,None])+chart[cy,px,:3]*weight[:,:,None]).astype('uint8');fixed[:,:,3]=255
Image.fromarray(fixed).save(out/'body-atlas-two-dimensional.png')
np.savez_compressed(out/'belly-donor-map.npz',x=px.astype('uint16'),y=donor_y.astype('uint16'),weight=lower.astype('float32'))
Image.fromarray(np.round(weight*255).astype('uint8')).save(out/'forehead-old-chart-mask.png')

reference=read(out/'A-mouth-reference.validation.json')['samples']['A'];rows=reference['samples']
valid=[r for r in rows if r['mouth_gap_lower_upper_z']]
start=valid[0]['u']-.0005
chosen=[.944,.95,.965,.98,.987,.9905]
cut=[[start,valid[0]['mouth_gap_lower_upper_z'][0],valid[0]['mouth_gap_lower_upper_z'][0]+.0001]]
for x in chosen:
 r=min(valid,key=lambda r:abs(r['u']-x));cut.append([r['u'],*r['mouth_gap_lower_upper_z']])
cut=sorted({r[0]:r for r in cut}.values())
last=valid[-1];cut.append([reference['max_u']+.04,*last['mouth_gap_lower_upper_z']])
# The same cage remains, but its anterior station positions/envelopes are
# fitted to actual A. This is A used as a measured shaping reference, not old
# mesh topology transplanted into B.
new_sections=[]
controls=[r for r in rows if r['occupied_z_ranges']]
for row in profile['body']['sections']:
 u0,top0,bottom0,width0=row
 if u0>.94:
  u0={.965:.965,.982:.98,.9915:.9905,.995:reference['max_u']-.0001}.get(u0,u0)
  xs=[r['u'] for r in controls];tops=[max(v[1] for v in r['occupied_z_ranges']) for r in controls];bottoms=[min(v[0] for v in r['occupied_z_ranges']) for r in controls]
  ztop=np.interp(u0,xs,tops);zbottom=np.interp(u0,xs,bottoms)
  top0=.5-ztop/(972/1961);bottom0=.5-zbottom/(972/1961)
  width0=float(np.interp(u0,xs,[r['max_abs_depth'] for r in controls]))
 new_sections.append([u0,top0,bottom0,width0])
plan={'kind':'nile_reference_repair_plan','status':'local_work_in_progress','formal_acceptance':False,'inputs':{str(p.relative_to(repo)).replace('\\','/'):sha(p) for p in [old/'A-artifacts/fish.blend',old/'B-artifacts/fish.blend',old/'shared/body-side.png',old/'shared/body-atlas.png',trial/'round2/Closed_body-0-chart112_dorsal.png',out/'A-mouth-reference.validation.json']},'rejected_round5':['Belly donor_y clamp repeated a single row and blurred the ventral/neck skin','Invented tapered gap did not match A upper/lower lip boundaries','Small grey mouth donor rectangles changed appearance without removing the wrong B shape'],'belly_method':'Two-dimensional existing whole-skin donor at native pixel scale along the cross-section arc; no coordinate clamp to a row.','forehead_method':'Reuse original dorsal chart112 source and original longitudinal/eye-protection blend rather than round4 head fade.','cut_profile_native':cut,'mouth_start_u':start,'A_max_u':reference['max_u'],'body_sections':new_sections,'mouth_material':'Transport corresponding A skin UV/role; no invented forehead/chin donor rectangles.','tail_and_fins':'All unchanged','preferred_max':1500,'hard_max':2000}
write(out/'repair.plan.validation.json',plan)
print(json.dumps({'ok':True,'mouth_start':start,'A_max_u':reference['max_u'],'cut_stations':len(cut),'output':str(out)}))
