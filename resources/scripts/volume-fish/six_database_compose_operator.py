"""Compose hash-bound current captures for operator review; never approves them."""
import argparse,hashlib,io,json,sys
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
from compose_source_comparison import compose

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main(a):
 root=a.directory.resolve();delivery=a.delivery.resolve();plan=read(delivery/'review.plan.json');review=delivery/'review';capture=read(review/'review-capture.validation.json');model=Path(plan['model'])
 assert root.is_relative_to(ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104')
 root.mkdir(exist_ok=True)
 assert capture['ok']and capture['model_sha256']==sha(model)==plan['model_sha256']
 if a.cutouts:
  receipt=review/'source-composition.validation.json'
  if receipt.exists():
   previous=read(receipt);assert previous['ok']and previous['model_sha256']==sha(model)
   for p,h in previous['inputs'].items():assert sha(p)==h
   for p,h in previous['outputs'].items():assert sha(review/p)==h
  else:compose(delivery/'review.plan.json',review,a.cutouts.resolve(),a.finviews.resolve()if a.finviews else None)
 inputs={str((review/'review-capture.validation.json').resolve()):sha(review/'review-capture.validation.json')};outputs={}
 def sheet(name,files,cols):
  out=root/name;rows=(len(files)+cols-1)//cols;canvas=Image.new('RGB',(cols*400,rows*265),(37,52,60));draw=ImageDraw.Draw(canvas)
  for n,p in enumerate(files):
   inputs[str(p.resolve())]=sha(p);im=Image.open(p).convert('RGB');im.thumbnail((400,240),Image.Resampling.NEAREST);x=n%cols*400;y=n//cols*265
   canvas.paste(im,(x+(400-im.width)//2,y+25+(240-im.height)//2));draw.text((x+5,y+5),p.stem,fill='white')
  stream=io.BytesIO();canvas.save(stream,format='JPEG',quality=96);data=stream.getvalue()
  if out.exists():assert out.read_bytes()==data,'Existing sheet belongs to a different composition'
  else:out.write_bytes(data)
  outputs[str(out.resolve())]=sha(out)
 sheet('root-head-review.jpg',[review/f'head-{v}-{m}.png'for v in ['left','front','top','bottom','oblique','right']for m in ['clay','texture']],4)
 sheet('root-whole-skin-review.jpg',[review/p for p in ['whole-left-texture.png','whole-right-texture.png','whole-top-texture.png','whole-bottom-texture.png','body-without-fins-top-texture.png','body-without-fins-bottom-texture.png','water-natural-freshwater-oblique.png','water-natural-freshwater-left.png']],4)
 sheet('root-motion-review.jpg',[review/f'frames/frame-{n:04d}.jpg'for n in [0,24,48,96,144,192,240,252,264,276]],5)
 write(root/'root-contact-sheets.validation.json',{'ok':True,'kind':'hash_bound_actual_capture_contact_sheets','model_sha256':sha(model),'inputs':inputs,'outputs':outputs,'composition':'Unchanged actual captures, nearest uniform thumbnail scaling; labels outside images.','scope':'Contact composition only, no visual acceptance or continuous-time inference.'})
 d,b=read_glb(model);errors=[]
 for anim in d['animations']:
  for sampler in anim['samplers']:
   v=arrays(d,b,sampler['output']);errors.append(float(abs(v[0]-v[-1]).max()))
 assert errors and max(errors)<1e-6
 write(root/'native-loop.validation.json',{'ok':True,'kind':'actual_current_native_clip_endpoint_check','species':plan['species'],'model_sha256':sha(model),'channels_checked':len(errors),'maximum_endpoint_error':max(errors),'scope':'Actual stored sampler endpoints only; current playback and transitions are separate capture/control receipts.'})
 print(json.dumps({'ok':True,'species':plan['species'],'model_sha256':sha(model),'sheets':len(outputs),'operator_review_required':True}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ['directory','delivery']:p.add_argument('--'+key,type=Path,required=True)
 for key in ['cutouts','finviews']:p.add_argument('--'+key,type=Path)
 main(p.parse_args())
