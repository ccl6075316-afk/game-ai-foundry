"""Native render contact sheet for operator inspection, never source artwork."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--category',required=True);p.add_argument('--review',type=Path);a=p.parse_args()
catalog=json.loads((a.root/'projects/fishing-2d/game/assets/aquascape-v5/catalog.json').read_text(encoding='utf-8'))['assets']
rows=[s for s in catalog if (s['category']=='plant')==(a.category=='plants')]
out=a.review or a.root/'projects/fishing-2d/plans/reviews/aquascape-catalog-v5'
for start in range(0,len(rows),2):
    views=['front','right','back','top','gray']
    sheet=Image.new('RGB',(2500,900),'#e6e6e6');draw=ImageDraw.Draw(sheet)
    for j,s in enumerate(rows[start:start+2]):
        for i,v in enumerate(views):
            file=out/f'godot/{s["id"]}-{v}.png'
            draw.text((i*500+12,j*450+8),s['id']+' / '+v,fill='black')
            image=Image.open(file).convert('RGB').crop((100,110,1100,795));image.thumbnail((490,410));sheet.paste(image,(i*500+(500-image.width)//2,j*450+28))
    sheet.save(out/f'render-{a.category}-{start//2+1}.jpg',quality=95)
