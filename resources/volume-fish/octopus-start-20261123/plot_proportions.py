"""Scientific diagram of exported-skin measurements, not an image edit."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'r2';m=json.loads((OUT/'proportions.validation.json').read_text())
font='/System/Library/Fonts/STHeiti Medium.ttc'
def f(s):return ImageFont.truetype(font,s)
im=Image.new('RGB',(1600,1080),'#f4f6f8');d=ImageDraw.Draw(im)
ink='#24384a';arm='#377fb0';web='#d27829'
d.text((54,30),'灰模 R2 · 导出网格比例复核',font=f(36),fill=ink)
d.text((54,84),'北太平洋巨型章鱼  Enteroctopus dofleini',font=f(22),fill=ink)
def xy(p):return (490+p[0]*112,580-p[1]*112)
for a in m['arms']:
 pts=[xy(p) for p in a['path_for_annotation']];d.line(pts,fill=arm,width=5)
 x,y=pts[-1];d.text((x+8,y-12),a['arm'].replace('_',' '),font=f(20),fill=ink)
for w in m['webs']:
 p=xy(w['actual_mid_edge']);d.line([xy(m['mouth']),p],fill=web,width=3)
 d.ellipse((p[0]-5,p[1]-5,p[0]+5,p[1]+5),fill=web)
 if w['sector']=='C_L':d.text((p[0]-95,p[1]+15),'蹼深 WD',font=f(20),fill=web)
p=xy(m['mouth']);d.ellipse((p[0]-6,p[1]-6,p[0]+6,p[1]+6),fill=ink)
d.text((p[0]-25,p[1]+14),'口部',font=f(19),fill=ink)
d.line([(995,145),(995,965)],fill='#ccd5dc',width=2)
x=1040;y=150
for text,size,color in [
 ('长度口径',28,ink),('ML：眼中线至外套膜后端',22,ink),('AL：口部沿腕腹面至腕尖',22,arm),('WD：口部至蹼凹缘中点',22,web),
 ('',12,ink),('参考范围 / 本模复量',28,ink),('腕长：3–5 ML / 3.80–4.02 ML',22,ink),('最深蹼：18–28% / 22.96%',22,ink),('百分比以最长腕为分母',20,ink),
 ('',12,ink),('建模取值依据',28,ink),('长腕取范围中值 4 ML；',22,ink),('III、IV 腕按资料顺序略缩短。',22,ink),('最深蹼取范围中值 23%；',22,ink),('背侧 A、腹侧 E 取较浅值。',22,ink),
 ('',12,ink),('精确档差为已记录的造型插值，',21,ink),('并非某只标本的实测尺寸。',21,ink)]:
 d.text((x,y),text,font=f(size),fill=color);y+=size+13
# A unit scale applies to the XY projection, not the 3D arc-length readout.
d.line([(65,930),(177,930)],fill=ink,width=4)
for xx in [65,177]:d.line([(xx,922),(xx,938)],fill=ink,width=3)
d.text((65,945),'1 ML',font=f(20),fill=ink)
d.text((260,930),'蓝线：实际表面测线的俯视投影',font=f(22),fill=arm)
d.text((260,964),'标注数值由三维测线计算，不是平面投影长度。',font=f(20),fill=ink)
d.text((54,1025),'来源：FAO《Cephalopods of the World》Vol.3 p.124；测位定义见约束记录。',font=f(20),fill=ink)
im.save(OUT/'proportion-measurements.png')
