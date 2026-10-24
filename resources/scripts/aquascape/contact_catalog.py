"""Read-only artwork contact sheets for visual review; never production donors."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--category',required=True);a=p.parse_args()
catalog=json.loads((a.root/'resources/aquascape/catalog-20-v5.json').read_text(encoding='utf-8'))
rows=catalog[a.category]
out=a.root/'projects/fishing-2d/plans/reviews/aquascape-catalog-v5';out.mkdir(parents=True,exist_ok=True)
for start in range(0,len(rows),2):
    views=['front','right','top','leaves'] if a.category=='plants' else ['front','right','top']
    sheet=Image.new('RGB',(len(views)*600,2*720),'#e6e6e6');draw=ImageDraw.Draw(sheet)
    for j,s in enumerate(rows[start:start+2]):
        for i,v in enumerate(views):
            folder=a.root/(f'projects/aquascape-{a.category}-fronts-v5' if v=='front' else f'projects/aquascape-{s["id"]}-views-v5')
            file=folder/f'output/{s["id"]}_{v}_raw.png'
            draw.text((i*600+12,j*720+8),s['id']+' / '+v,fill='black')
            if not file.exists():continue
            image=Image.open(file).convert('RGB');image.thumbnail((588,680));sheet.paste(image,(i*600+(600-image.width)//2,j*720+32+(680-image.height)//2))
    sheet.save(out/f'source-{a.category}-{start//2+1}.jpg',quality=95)
