"""Assemble native Godot crops with identical crop and scale before/after."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=Path(__file__).resolve().parent/'motion-r5';out=Image.new('RGB',(1600,840),(29,36,43));draw=ImageDraw.Draw(out);font=ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',26)
for col,prefix in enumerate(['baseline-','']):
 draw.text((col*800+24,16),'修改前（R4）' if col==0 else '修改后（R5）：腕足加粗，末段缩短',font=font,fill='white')
 im=Image.open(p/(prefix+'tight-coil-close.png')).crop((280,180,940,620));out.paste(im,(col*800+70,60))
 im=Image.open(p/(prefix+'tip-straight-close.png')).crop((200,300,850,500)).resize((780,240));out.paste(im,(col*800+10,545))
 draw.text((col*800+24,505),'同机位紧卷 / 展开腕尖',font=font,fill=(183,199,209))
out.save(p/'thickness-before-after.jpg',quality=93)
