"""Compose diagnostic contact sheets/video from hash-bound actual captures.

No model or source texture edits, and no visual acceptance is inferred.
"""
import argparse,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from parts import read,sha
from fish_asset_spec import ROOT

def build(plan_path,review,ffmpeg):
    plan=read(plan_path);capture=read(review/'review-capture.validation.json');movie=read(review/'movie-frames.validation.json')
    assert capture['ok']and capture['model_sha256']==movie['model_sha256']==plan['model_sha256']==sha(plan['model'])
    for row in capture['captures']:assert sha(row['path'])==row['sha256']
    for row in movie['frames']:assert sha(review/row['path'])==row['sha256']
    views=['left','right','front','rear','top','bottom','oblique','reverse-oblique'];fins=plan['fins']
    groups={
      'whole-contact.jpg':['whole-'+v+'-texture.png'for v in views]+['water-natural-freshwater-left.png','water-natural-freshwater-oblique.png'],
      'head-contact.jpg':[part+'-'+v+'-'+kind+'.png'for part in ['head','mouth']for v in ['left','front','top','bottom','oblique']for kind in ['texture','clay']],
      'body-fin-contact.jpg':['body-without-fins-'+v+'-texture.png'for v in ['left','right','oblique','bottom']]+['fin-'+fin+'-oblique-texture.png'for fin in fins],
      'fin-clay-contact.jpg':['fin-'+fin+'-'+v+'-clay.png'for fin in fins for v in ['left','right','oblique']],
      'body-other-contact.jpg':['body-without-fins-'+v+'-'+kind+'.png'for v in views for kind in ['texture','clay']],
      'motion-contact.jpg':[movie['frames'][i]['path']for i in [0,16,32,48,64,80,96,112,128,144,160,176,192,208,224,240,251,263,275,287]]}
    outputs={}
    for name,names in groups.items():
        target=review/name;assert not target.exists()
        cols=4;cw,ch=450,375;sheet=Image.new('RGB',(cols*cw,((len(names)+cols-1)//cols)*ch),(32,47,54));draw=ImageDraw.Draw(sheet)
        for i,n in enumerate(names):
            image=Image.open(review/n).convert('RGB');image.thumbnail((cw,ch-24),Image.Resampling.NEAREST);x=(i%cols)*cw;y=(i//cols)*ch;sheet.paste(image,(x+(cw-image.width)//2,y+24));draw.text((x+5,y+5),n,fill='white')
        sheet.save(target,quality=92);outputs[name]=sha(target)
    canvas=Image.new('RGB',(1800,650),(37,52,60));draw=ImageDraw.Draw(canvas);src=Image.open(plan['review_sources'][0]['path']).convert('RGBA');src.thumbnail((850,560),Image.Resampling.NEAREST);canvas.paste(src,(25,55),src);canvas.paste(Image.open(review/'whole-left-texture.png').convert('RGB'),(900,30));draw.text((25,15),'Original accepted source',fill='white');draw.text((925,15),'Current cold GLB | source-owned completed body and finite jaw skin',fill='white');target=review/'source-final-comparison.png';assert not target.exists();canvas.save(target);outputs[target.name]=sha(target)
    target=review/'review.mp4';assert not target.exists();proc=subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-framerate',str(movie['fps']),'-i',str(review/'frames/frame-%04d.jpg'),'-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],capture_output=True,timeout=120);assert proc.returncode==0,proc.stderr.decode(errors='replace')[-1000:];outputs[target.name]=sha(target)
    receipt={'ok':True,'kind':'actual_review_contact_composition','model_sha256':plan['model_sha256'],'plan_sha256':sha(plan_path),'capture_sha256':sha(review/'review-capture.validation.json'),'frame_manifest_sha256':sha(review/'movie-frames.validation.json'),'duration_seconds':movie['duration_seconds'],'outputs':outputs,'scope':'Contact composition from actual unchanged captured pixels. No source texture/model edit or visual approval.'};(review/'contact-composition.validation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--ffmpeg',type=Path,required=True);a=p.parse_args();a.review=a.review.resolve();assert a.review.is_relative_to(ROOT/'projects/fishing-2d/experiments');r=build(a.plan,a.review,a.ffmpeg);print(json.dumps({'ok':r['ok'],'outputs':list(r['outputs'])}))
