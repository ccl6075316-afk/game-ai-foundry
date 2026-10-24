"""Native render and exact source-contour comparisons for the remeshed leaves."""
import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
old=root/'projects/fishing-2d/plans/reviews/aquascape-leaf-edges-v6/godot';review=root/'projects/fishing-2d/plans/reviews/aquascape-leaf-contours-v7';new=review/'godot';font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
for id in ['amazon_sword','crypt_wendtii','aponogeton']:
    sheet=Image.new('RGB',(1260,700),'#16353a');draw=ImageDraw.Draw(sheet)
    for i,(folder,label) in enumerate([(old,'原模型：残留细碎缺口'),(new,'修整后：完整叶缘，保留原画')]):
        draw.text((i*630+12,12),label,font=font,fill='#e7e1c9')
        im=Image.open(folder/(id+'-front.png')).convert('RGB').crop((350,140,980,790));sheet.paste(im,(i*630,50))
    sheet.save(review/(id+'-before-after.png'))
    sheet=Image.new('RGB',(1000,840),'#16353a');draw=ImageDraw.Draw(sheet)
    for i,(folder,label) in enumerate([(review,'原模型轮廓'),(review/'after','修整后轮廓')]):
        draw.text((i*500+12,12),label,font=font,fill='#e7e1c9')
        im=Image.open(folder/(id+'-contour.png')).crop((1000,60,1500,840));sheet.paste(im,(i*500,60))
    sheet.save(review/(id+'-mesh-comparison.png'))
print('Saved three native artwork pairs and three actual UV-contour pairs.')
