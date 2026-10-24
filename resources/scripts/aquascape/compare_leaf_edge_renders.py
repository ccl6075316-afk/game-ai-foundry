"""Same-camera native before/after evidence and an independent screen-pixel check."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root
before=root/'projects/fishing-2d/plans/reviews/aquascape-catalog-v5/godot';after=root/'projects/fishing-2d/plans/reviews/aquascape-leaf-edges-v6/godot'
registry=json.loads((root/'projects/fishing-2d/game/assets/aquascape-v5/catalog.json').read_text(encoding='utf-8'))
results=[]
for row in registry['assets']:
    if not row['animated']:continue
    old=np.array(Image.open(before/(row['id']+'-front.png')).convert('RGB'))[130:790,220:1100]
    new=np.array(Image.open(after/(row['id']+'-front.png')).convert('RGB'))[130:790,220:1100]
    # Separate screen-space criterion, independent of the source-matte detector.
    def whites(rgb):return int(((rgb.min(2)>=190)&(np.ptp(rgb.astype(float),axis=2)<=40)).sum())
    results.append({'id':row['id'],'native_neutral_bright_pixels_before':whites(old),'native_neutral_bright_pixels_after':whites(new),'changed_render_pixels':int(np.any(old!=new,axis=2).sum())})
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
sheet=Image.new('RGB',(1260,700),'#102d32');draw=ImageDraw.Draw(sheet)
for i,(folder,label) in enumerate([(before,'修复前'),(after,'修复后：同一相机与姿态')]):
    draw.text((i*630+18,12),label,font=font,fill='#e7e0c8')
    im=Image.open(folder/'crypt_wendtii-front.png').convert('RGB').crop((350,140,980,790));sheet.paste(im,(i*630,50))
sheet.save(after.parent/'before-after.png')
report={'command':'aquascape.compare-native-leaf-edges','status':'done','next_action':'human_review','outputs':results,'scope':'Neutral bright pixels in identical native close-up ROIs. Legitimate pink leaves/highlights can remain bright; this is not an automatic art approval.'}
(after.parent/'screen-comparison.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results))
