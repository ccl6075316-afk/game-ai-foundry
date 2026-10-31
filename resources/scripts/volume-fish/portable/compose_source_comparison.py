"""Compose actual source/cold-capture evidence, without approving its appearance."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
from parts import read,sha,fresh_output

def compose(plan_path,review,cutouts):
 plan=read(plan_path);capture=read(review/'review-capture.validation.json')
 assert capture['ok'] and capture['model_sha256']==sha(plan['model'])==plan['model_sha256']
 source=Path(plan['review_sources'][0]['path']);assert sha(source)==plan['review_sources'][0]['sha256']
 inputs={str(source):sha(source)};outputs={}
 def load(p):
  inputs[str(p.resolve())]=sha(p);return Image.open(p).convert('RGBA')
 src=load(source);actual=load(review/'whole-left-texture.png');w,h=actual.size
 # Same orthographic projection: no independent fit/crop of the source fish.
 scale=plan['model_scale']*w/plan['whole_camera_size']/src.width
 expected=Image.new('RGBA',(w,h),(37,52,60,255));size=(round(src.width*scale),round(src.height*scale));src=src.resize(size,Image.Resampling.NEAREST)
 expected.alpha_composite(src,((w-size[0])//2,(h-size[1])//2))
 sheet=Image.new('RGB',(w*2,h+35),(37,52,60));sheet.paste(expected.convert('RGB'),(0,35));sheet.paste(actual.convert('RGB'),(w,35));draw=ImageDraw.Draw(sheet)
 draw.text((10,10),'Own source | fixed full-canvas projection',fill='white');draw.text((w+10,10),'Actual cold GLB | static rest | same projection',fill='white')
 target=review/'source-pose-comparison.png';assert not target.exists();sheet.save(target);outputs[target.name]=sha(target)
 for page in range((len(plan['fins'])+3)//4):
  names=plan['fins'][page*4:page*4+4];sheet=Image.new('RGB',(1350,325*len(names)),(37,52,60));draw=ImageDraw.Draw(sheet)
  for row,name in enumerate(names):
   base=name.removesuffix('_mesh').removesuffix('_left').removesuffix('_right')
   matches=list(cutouts.glob(base+'-*.png'));assert len(matches)==1,(base,matches)
   for col,(label,p) in enumerate([('source native cutout',matches[0]),('cold isolated texture',review/f'fin-{name}-left-texture.png'),('cold isolated clay',review/f'fin-{name}-oblique-clay.png')]):
    image=load(p);image.thumbnail((440,290),Image.Resampling.NEAREST);x=col*450+(450-image.width)//2;y=row*325+30+(290-image.height)//2
    sheet.paste(image,(x,y),image);draw.text((col*450+8,row*325+8),name+' | '+label,fill='white')
  target=review/f'fin-source-comparison-{page}.jpg';assert not target.exists();sheet.save(target,quality=94);outputs[target.name]=sha(target)
 receipt={'ok':True,'kind':'actual_source_capture_composition','model_sha256':plan['model_sha256'],'inputs':inputs,'outputs':outputs,'source_scale_to_capture_pixels':scale,'scope':'Whole source and actual rest capture share fixed canvas/orthographic scale; no independent silhouette fit. Individual fin thumbnails have separate framing and are not area/size proof. Composition is not appearance/anatomy approval.'}
 target=review/'source-composition.validation.json';assert not target.exists();target.write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['plan','review','cutouts']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();fresh_output(a.review/'source-composition.validation.json');r=compose(a.plan,a.review.resolve(),a.cutouts.resolve());print(json.dumps({'ok':r['ok'],'outputs':list(r['outputs'])}))
