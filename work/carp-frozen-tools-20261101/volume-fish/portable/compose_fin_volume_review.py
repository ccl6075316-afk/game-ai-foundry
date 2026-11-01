"""Arrange unaltered cold fin captures for end/top volume review; no approval."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
from parts import read,sha

def compose(directory):
    capture=directory/'fin-volume-capture.validation.json';report=read(capture)
    assert report['ok'];inputs={str(capture.resolve()):sha(capture)};outputs={}
    views=['front-clay','top-clay','oblique-clay']
    for page in range((len(report['fin_inventory'])+3)//4):
        names=report['fin_inventory'][page*4:page*4+4]
        sheet=Image.new('RGB',(1800,440*len(names)),(37,52,60));draw=ImageDraw.Draw(sheet)
        for row,name in enumerate(names):
            for col,view in enumerate(views):
                source=directory/f'fin-{name}-{view}.png';inputs[str(source.resolve())]=sha(source)
                im=Image.open(source).convert('RGB');im.thumbnail((600,410),Image.Resampling.NEAREST)
                sheet.paste(im,(col*600+(600-im.width)//2,row*440+30))
                draw.text((col*600+8,row*440+8),name+' | '+view,fill='white')
        output=directory/f'fin-volume-review-{page}.jpg';assert not output.exists();sheet.save(output,quality=96);outputs[str(output.resolve())]=sha(output)
    result={'ok':True,'kind':'cold_fin_volume_contact_sheets','model_sha256':report['model_sha256'],'inputs':inputs,'outputs':outputs,'formal_acceptance':False,'scope':'Actual end/top/oblique clay captures, uniformly scaled in both axes with no thickness exaggeration. Separate fin framing is not scale comparison or acceptance.'}
    output=directory/'fin-volume-sheets.validation.json';assert not output.exists();output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',required=True,type=Path)
    a=p.parse_args();print(json.dumps(compose(a.review)))
