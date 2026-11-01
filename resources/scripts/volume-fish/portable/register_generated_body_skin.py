"""Register a generated RGB donor to a native fish canvas and protect its head.

No generated silhouette drives geometry. The explicit reviewed profile defines
the body-only alpha, while the original head/eyes/lips/gill remain byte-exact.
"""
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from fish_asset_spec import ROOT,artifact_output,require

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def prepare(config,output):
 cfg=json.loads(config.read_text(encoding='utf8'));source=ROOT/cfg['source'];donor=ROOT/cfg['generated'];profile=ROOT/cfg['profile']
 for name,p in [('source',source),('generated',donor),('profile',profile)]:require(sha(p)==cfg[name+'_sha256'],'Stale '+name)
 out=artifact_output(output,[source,donor,profile,config]);require(not out.exists(),'Fresh output required');out.mkdir(parents=True)
 original=np.array(Image.open(source).convert('RGBA'));H,W=original.shape[:2]
 # Declared normalized canvas registration only; original landmark checks are separate.
 generated=np.array(Image.open(donor).convert('RGBA').resize((W,H),Image.Resampling.NEAREST))
 end=cfg['protected_head_from_x'];start=cfg['blend_start_x'];require(0<start<end<W,'Explicit narrow join required')
 edge_inset=int(cfg.get('donor_edge_inset_px',0));require(0<=edge_inset<=64,'Bounded donor edge inset required')
 donor_y,donor_x=np.indices((H,W));generated_rgb=generated[:,:,:3].copy()
 if edge_inset:
  for x in range(end):
   ids=np.flatnonzero(generated[:,x,3]>230)
   if not len(ids):continue
   lo,hi=int(ids.min())+edge_inset,int(ids.max())-edge_inset
   if hi<=lo:continue
   donor_y[:,x]=np.clip(np.where(np.arange(H)<lo,2*lo-np.arange(H),np.where(np.arange(H)>hi,2*hi-np.arange(H),np.arange(H))),lo,hi)
  generated_rgb=generated[donor_y,donor_x,:3]
  valid=(generated[:,:,3]>128).astype('uint8');_,labels=cv2.distanceTransformWithLabels(1-valid,cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
  source_y,source_x=np.where(valid>0);missing=generated[donor_y,donor_x,3]<=128
  nearest=labels[donor_y[missing],donor_x[missing]]-1
  donor_y[missing]=source_y[nearest];donor_x[missing]=source_x[nearest]
  generated_rgb=generated[donor_y,donor_x,:3]
 result=generated.copy();mix=np.clip((np.arange(W)-start)/(end-start),0,1)[None,:,None];mix=mix*mix*(3-2*mix)
 result[:,:,:3]=np.rint(generated_rgb*(1-mix)+original[:,:,:3]*mix).astype('uint8')
 sections=np.array(json.loads(profile.read_text(encoding='utf8'))['body']['sections']);yy,xx=np.indices((H,W));u=(xx+.5)/W
 top=np.interp(u,sections[:,0],sections[:,1])*H;bottom=np.interp(u,sections[:,0],sections[:,2])*H
 inside=(u>=sections[0,0])&(u<=sections[-1,0])&(yy+.5>=top)&(yy+.5<=bottom)
 result[:,:,3]=np.where(inside,255,0).astype('uint8');result[:,end:]=original[:,end:]
 protected=inside&(xx>=end)
 # Head ownership does not include a dorsal/pelvic tip above/below its contour.
 result[~inside,3]=0
 require(np.array_equal(result[protected],original[protected]),'Native head changed')
 p=out/'body-clean.png';Image.fromarray(result).save(p)
 np.savez_compressed(out/'generated-donor-addresses.npz',x=donor_x.astype('uint16'),y=donor_y.astype('uint16'))
 sheet=Image.new('RGB',(W*2,H),'#405363')
 for n,array in enumerate([original,result]):
  rgba=Image.fromarray(array);bg=Image.new('RGBA',(W,H),'#405363');bg.alpha_composite(rgba);sheet.paste(bg.convert('RGB'),(n*W,0))
 sheet.save(out/'before-after.jpg',quality=96)
 report={'ok':True,'kind':'registered_generated_body_skin','source':str(source),'source_sha256':sha(source),'generated':str(donor),'generated_sha256':sha(donor),'profile_sha256':sha(profile),'config_sha256':sha(config),'source_size':[W,H],'registration':'Normalized full source canvas, nearest resampling; no generated shape adopted','protected_head_from_x':end,'protected_head_domain':'Within independently reviewed body silhouette, excluding external fin tips','blend_start_x':start,'head_eye_mouth_gill_RGBA_exact':True,'synthesized_body_RGB':True,'alpha_basis':'Explicit independently reviewed native body-side profile, no fins','textures':{'body_clean':{'path':str(p),'sha256':sha(p),'size':[W,H]}},'formal_acceptance':False,'visual_review':'pending'}
 report.update(donor_edge_inset_px=edge_inset,edge_extension='Reflect2D interior generated tissue; no generated-outline RGB or transparent black forced opaque',generated_donor_addresses={'path':str(out/'generated-donor-addresses.npz'),'sha256':sha(out/'generated-donor-addresses.npz'),'space':'Nearest-resized generated canvas, not original fish pixels'})
 (out/'texture-inputs.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=prepare(a.config,a.output);print(json.dumps({'ok':r['ok'],'protected_head_RGBA_exact':r['head_eye_mouth_gill_RGBA_exact']}))
