"""Record original-canvas source mismatch and actual body occlusion separately."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mask(path):return np.min(np.asarray(Image.open(path).convert('RGB')),axis=2)>240
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--species',required=True);p.add_argument('--after',default='preview-v7');a=p.parse_args();r=a.root;rows=[]
 try:
  paths={tag:r/folder/'capture.validation.json' for tag,folder in [('before','preview-before'),('after',a.after)]};captures={tag:json.loads(path.read_text()) for tag,path in paths.items()};data={tag:next(x for x in d['rows'] if x['species']==a.species) for tag,d in captures.items()}
  for fin in data['after']['fins']:
   name=fin['name'];reference_path=r/'audit'/a.species/(name+'-source-mask.png');reference=np.asarray(Image.open(reference_path))>0
   if fin['camera_side']<0:reference=np.fliplr(reference)
   row={'name':name,'reference_mask_sha256':sha(reference_path)}
   for tag in ['before','after']:
    record=next(x for x in data[tag]['fins'] if x['name']==name);full=mask(record['files']['full_mask']['path']);visible=mask(record['files']['body_visible_mask']['path']);assert full.shape==reference.shape and full.sum()>0 and visible.sum()>0
    row[tag]={'full_projected_pixels':int(full.sum()),'body_visible_pixels':int(visible.sum()),'visible_fraction':float(visible.sum()/full.sum()),'source_iou':float((full&reference).sum()/max((full|reference).sum(),1)),'source_pixels_missing_in_projection':int((reference&~full).sum()),'extra_projected_pixels':int((full&~reference).sum())}
   rows.append(row)
  result={'ok':len(rows)==len(data['after']['fins']),'records':rows,'capture_sha256':{tag:sha(path) for tag,path in paths.items()},'scope':'Complete static GPU measurements, not automatic shape acceptance. Original full canvas; no local registration. Body occlusion, source footprint and inferred basal transport are separate.'}
 except Exception as e:result={'ok':False,'error':str(e),'records':rows}
 (r/f'visibility-{a.after}.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,ensure_ascii=False));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
