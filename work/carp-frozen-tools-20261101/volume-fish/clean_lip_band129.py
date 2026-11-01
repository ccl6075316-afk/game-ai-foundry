"""Remove confirmed near-black drawn ink only inside manually bounded lip atlas."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);args=parser.parse_args();p=json.loads(args.plan.read_text());root=args.plan.parent
assert sha(p['source_atlas'])==p['source_atlas_sha256'];assert sha(p['lip_plan'])==p['lip_plan_sha256']
lip=json.loads(Path(p['lip_plan']).read_text());a=np.asarray(Image.open(p['source_atlas']).convert('RGBA')).copy();original=a.copy();mask=np.zeros(a.shape[:2],bool);rows=[]
for name,band in lip['bands'].items():
 y0=band['atlas_offset_y'];y1=y0+band['atlas_rows'];area=a[y0:y1]
 # This threshold operates exclusively in the manually traced pale lip chart.
 # Body, eyes, cavity, actual model slit and all other source content are absent.
 ink=area[:,:,:3].max(2)<p['confirmed_ink_max_channel_below'];donor=area[:,:,:3].max(2)>=p['interior_donor_min_channel_max'];sy,sx=np.where(donor);ty,tx=np.where(ink);assert len(sy)
 if len(ty):
  _,index=cKDTree(np.c_[sx,sy]).query(np.c_[tx,ty]);area[ty,tx]=original[y0+sy[index],sx[index]];mask[y0+ty,tx]=True
 rows.append({'band':name,'derived_atlas_ink_pixels_replaced':len(ty),'donors':'Nearest existing native pale-lip texel inside same manually bounded lip chart; no head/cavity color and no new flat color.'})
assert (a[:,:,3]==255).all();Image.fromarray(a).save(root/'lip-band-clean.png');Image.fromarray((mask*255).astype('uint8')).save(root/'lip-band-ink-mask.png')
report={'schema_version':1,'ok':True,'command':'fish.clean-lip-band129','stage':'validate','status':'done','next_action':'human_review','inputs':{'plan_sha256':sha(args.plan),'helper_sha256':sha(__file__),'source_atlas_sha256':sha(p['source_atlas']),'lip_plan_sha256':sha(p['lip_plan'])},'outputs':[{'path':str((root/n).resolve()),'sha256':sha(root/n)} for n in ['lip-band-clean.png','lip-band-ink-mask.png']],'summary':{'scope':p['scope'],'bands':rows,'source_image_modified':False,'all_other_derived_atlas_pixels_exactly_preserved':bool(np.array_equal(a[~mask],original[~mask])),'whole_fish_outline_classifier':False,'visual_ink_mask_review':'Required; local material classification only, no cross-species automatic claim.'},'failures':[]}
(root/'material.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
