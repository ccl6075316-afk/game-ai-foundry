"""Freeze shared material, image landmarks and accepted source provenance for A/B."""
from pathlib import Path
import json, hashlib, re, os, time
import cv2
import numpy as np
from PIL import Image

repo = Path(__file__).resolve().parents[3]
game = repo / 'projects/fishing-2d'
trial = game / 'experiments/nile-dorsal-route-trial'
base = trial / 'round2'
out = trial / 'round4-ab-textured'
shared = out / 'shared'
assert out.resolve().is_relative_to(trial.resolve())
shared.mkdir(parents=True, exist_ok=True)
started = time.perf_counter()
read = lambda p: json.loads(Path(p).read_text(encoding='utf8'))
write = lambda p,d: Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
image = lambda p: np.array(Image.open(p).convert('RGBA'))
source = image(base/'Closed_body-0-source_texture.png')
generated = image(base/'body-clean-reference.png')
mask = image(base/'body-projection-label.png')[:,:,0]
count, labels, stats, _ = cv2.connectedComponentsWithStats((mask>127).astype('uint8'))
body = labels == (1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))
protect = image(base/'Closed_body-0-pectoral142_mask.png')[:,:,0]/255.
h,w = body.shape
y,x = np.mgrid[:h,:w]
H = np.array(read(base/'image-registration.validation.json')['homography_normalized'])
q = np.stack(((x+.5)/w,(y+.5)/h,np.ones_like(x)),axis=0).reshape(3,-1)
mapped = H@q
gx = (mapped[0]/mapped[2]*generated.shape[1]-.5).reshape(h,w).astype('float32')
gy = (mapped[1]/mapped[2]*generated.shape[0]-.5).reshape(h,w).astype('float32')
side = cv2.remap(generated,gx,gy,cv2.INTER_NEAREST,borderMode=cv2.BORDER_CONSTANT)
# Keep the unit-made whole skin as one continuous donor. Only the explicitly
# body-owned connector is restored, with a narrow transition inside its mask.
distance = cv2.distanceTransform((protect>.5).astype('uint8'),cv2.DIST_L2,5)
alpha = np.clip(distance/10.,0,1)*protect
side[:,:,:3] = np.round(side[:,:,:3]*(1-alpha[:,:,None])+source[:,:,:3]*alpha[:,:,None]).astype('uint8')
side[:,:,3] = (body*255).astype('uint8')
Image.fromarray(side).save(shared/'body-side.png')

# Body landmarks are image-space controls. Transverse dimensions are explicit
# existing artistic dimensions, not old dense mesh topology or biological data.
old_profile = repo/'resources/volume-fish/nile_tilapia-082g.profile.json'
profile = read(old_profile)
original_sections = np.array(profile['body']['sections'])
material = next(r for r in read(base/'material-inputs.validation.json')['materials'] if r['name']=='Closed_body-0')
numbers = list(map(float,re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?',material['parameters']['chart112_sections'].split('(',1)[1],flags=re.I)))
dimensions = np.array(numbers).reshape(-1,4)
stations = [.149,.17,.20,.235,.27,.31,.35,.39,.43,.47,.51,.55,.60,.65,.70,.75,.80,.84,.88,.91,.94,.965,.982,.9915,.995]
sections=[]
for u in stations:
    col=min(w-1,max(0,round(u*w)))
    ys=np.flatnonzero(body[:,col])
    if not len(ys):
        col=min(np.flatnonzero(body.any(axis=0)),key=lambda c:abs(c-col));ys=np.flatnonzero(body[:,col])
    width=float(np.interp(u-.5,dimensions[:,0],dimensions[:,3]))
    t=np.clip((u-.149)/.045,0,1);s=t*t*(3-2*t)
    width*=.35+.65*s
    top,bottom=float(ys.min()/h),float(ys.max()/h)
    if u>=.975:
        # Before making the oral cut the body must contain the complete head
        # envelope. At the last columns the artwork mask contains only the
        # lower lip; do not mistake that disconnected lip for a full section.
        top=min(top,float(np.interp(u,original_sections[:,0],original_sections[:,1])))
        bottom=max(bottom,float(np.interp(u,original_sections[:,0],original_sections[:,2])))
    sections.append([u,top,bottom,width])
profile['body']={'sections':sections,'rings':len(stations),'radial':16}
profile['fins']=[]
profile['eyes']=None
profile['oral_jaws']['lip_bevel']=0
# The accepted three-point slit is collinear; the same straight oral cut avoids
# needless duplicate cutter stations in this budget experiment.
profile['oral_jaws'].pop('slit_path',None)
profile['notes'].append('163 A/B trial: image-fitted sparse cage body; explicit artistic transverse dimensions; fins built separately from native cutouts. No dense-body reduction in B.')
new_profile=repo/'resources/volume-fish/nile-tilapia-reference-cage-163.profile.json'
write(new_profile,profile)

# Shared cylindrical atlas: all static sampling decisions are frozen offline.
# The engine receives ordinary opaque texture pixels, not VERTEX_ID color LUTs.
AH=1024;theta=np.arange(AH,dtype=float)/AH*2*np.pi
u=(np.arange(w)+.5)/w
sec=np.array(sections)
top=np.interp(u,sec[:,0],sec[:,1]);bottom=np.interp(u,sec[:,0],sec[:,2])
v=(top[None,:]+bottom[None,:])/2-(bottom-top)[None,:]/2*np.cos(theta[:,None])
px=np.broadcast_to(np.arange(w)[None,:],(AH,w));py=np.clip(np.floor(v*h).astype(int),0,h-1)
safe=(cv2.distanceTransform((body&(side[:,:,3]>242)).astype('uint8'),cv2.DIST_L2,5)>7)
# Keep mouth outline/cavity pixels in their oral role rather than spreading them
# over unseen nose or thickness surfaces. Natural dark markings remain valid.
mouth_line=.552+(.502-.552)*np.clip((x/w-.95)/(.995-.95),0,1)
safe &= ~((x/w>.943)&(np.abs(y/h-mouth_line)<.011))
_,nearest=cv2.distanceTransformWithLabels((~safe).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
sy,sx=np.where(safe);indices=np.clip(nearest[py,px]-1,0,len(sx)-1)
inside=safe[py,px];donor_x=np.where(inside,px,sx[indices]);donor_y=np.where(inside,py,sy[indices])
atlas=side[donor_y,donor_x].copy()
# The old independently saved dorsal/ventral skin charts are retained as
# directional texture donors and baked now; no runtime recoloring is required.
amount=np.clip((np.abs(np.cos(theta))-.35)/.5,0,1);amount=amount*amount*(3-2*amount)
amount=amount[:,None]*np.ones((1,w));amount[:,u>.84]*=np.clip((.94-u[u>.84])/.10,0,1)
arc=np.arctan2(np.abs(np.sin(theta)),np.abs(np.cos(theta)))
width=np.interp(u,sec[:,0],sec[:,3])
cy=np.clip(np.floor(arc[:,None]*width[None,:]*1961).astype(int),0,383)
for sign,name in ((1,'dorsal'),(-1,'ventral')):
    chart=image(base/('Closed_body-0-chart112_'+name+'.png'))
    use=(np.cos(theta)*sign>0)[:,None]
    factor=amount*use
    atlas[:,:,:3]=np.round(atlas[:,:,:3]*(1-factor[:,:,None])+chart[cy,px,:3]*factor[:,:,None]).astype('uint8')
atlas[:,:,3]=255
Image.fromarray(atlas).save(shared/'body-atlas.png')

accepted=game/'experiments/blender-fish/models/nile_tilapia/082g.handoff.json'
original=read(accepted);art=accepted.parent/'082g.handoff-artifacts'
mapping={'accepted_handoff':accepted,'profile':old_profile,'blend':art/'fish.blend','glb':art/'fish.glb',
 'source':accepted.parent/'082-source-inputs/char_nile_tilapia_082_nobg.png',
 'reference':game/'assets/sprites/鱼_尼罗罗非鱼_角色/frame_0001.png',
 'review_images':{k:art/'review'/{'style_comparison':'style-comparison','master_comparison':'master-comparison'}.get(k,k).__add__('.png') for k in original['style_review']['hashes']['review_images']}}
mapping['reference']=game/'game/assets/sprites/鱼_尼罗罗非鱼_角色/frame_0001.png'
for key,value in list(mapping.items()):
 if key=='review_images':mapping[key]={k:str(v.resolve()) for k,v in value.items()}
 else:mapping[key]=str(value.resolve())
write(out/'accepted-source-archive.json',mapping)
recipe={'kind':'nile_AB_textured_recipe','preferred_max':1500,'hard_max':2000,'profile':str(new_profile.relative_to(repo)).replace('\\','/'),
 'A_source':'projects/fishing-2d/experiments/nile-dorsal-route-trial/round3-whole-budget-probe/whole-1500-source-fin-probe.blend',
 'A_source_sha256':'13000072684e0dd34bd427d7316a856d420256dc3606d9a2467368e1b2b50a91',
 'B_method':'Simple sparse reference cage; local nonuniform extrusion loops fitted to body-only drawing, then transverse volume and integrated oral cut; no dense mesh reduction',
 'body_loop_u':stations,'radial_points':16,'body_dimensions_basis':'Frozen current artistic width dimensions from material-inputs chart112_sections; side top/bottom from body-only image landmark mask. No biological thickness claim.',
 'fin_boundary_vertices':{'Dorsal':40,'Anal':24,'Caudal':28,'Pectoral_left':12,'Pectoral_right':12,'Pelvic_left':10,'Pelvic_right':10},
 'shared_material_inputs':{name:sha(base/name) for name in ['body-clean-reference.png','Closed_body-0-source_texture.png','Closed_body-0-pectoral142_mask.png','Closed_body-0-chart112_dorsal.png','Closed_body-0-chart112_ventral.png']},
 'shared_material_outputs':{name:sha(shared/name) for name in ['body-side.png','body-atlas.png']},'connector_pixels_original_exact':int((alpha>=1).sum()),'connector_feather_width_pixels':10,
 'common_preparation_seconds':time.perf_counter()-started,'new_external_model_calls':0,'new_external_API_fee':0,'historical_Codex_and_image_generation_cost':'unknown; not estimated'}
write(out/'comparison.plan.validation.json',recipe)
print(json.dumps({'ok':True,'output':str(out),'profile':str(new_profile),'sections':len(sections),'shared_preparation_seconds':recipe['common_preparation_seconds']}))
