"""Build a read-only five-candidate viewer and a representative review sheet."""
import copy,hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf8'))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 root=ROOT/'projects/fishing-2d/experiments/five-fish-database-20261103';out=root/'review';assert not out.exists();out.mkdir();batch=read(ROOT/'projects/fishing-2d/plans/reviews/five-fish-width-detail-20261031/manifest.json')['database_revision_20261103'];assert len(batch['candidates_completed'])==5
 names={'rainbow_trout':'虹鳟','brown_trout':'褐鳟','atlantic_salmon':'大西洋鲑','sea_bass':'海鲈','red_emperor':'红皇帝鱼'};entries=[];inventory=[];sheet=Image.new('RGB',(1400,1900),(37,52,60));draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19);draw.text((26,14),'资料库调整 · 五鱼导出候选（待用户审阅）',font=font,fill='white');draw.text((26,55),'实际 Godot 侧面 / 俯视；各鱼独立取景，非跨物种尺寸比较。旧游戏成品保留。',font=small,fill='white')
 for i,s in enumerate(names):
  d=root/s;review=read(d/'production-review.json');assert read(d/'sop-postcleanup.validation.json')['ok'];model=Path(review['candidate_files']['model']['path']);assert sha(model)==review['candidate_files']['model']['sha256'];inv=read(d/'revision-invariants.validation.json');facts=read(d/'current-evidence.validation.json');capture=Path(facts['actual_capture']['path']);spec=read(Path(review['candidate_files']['final_spec']['path']));motion=ROOT/spec['motion']['profile']['path'];length=read(motion)['real_length_cm'];scale=spec['viewer']['model_scale']
  viewer={'kind':'fish_asset_finalization_spec','version':1,'species':s,'viewer':{'model_scale':scale,'native_clip':'Swim','focuses':{'head':{'mode':'bbox_relative','position':[.9,.48,.5]}},'captures':[{'name':label,'yaw_degrees':yaw,'pitch_degrees':pitch,'time_seconds':0}for label,yaw,pitch in [('side',0,0),('reverse',180,0),('front',90,0),('oblique',35,15),('top',0,85),('bottom',0,-85)]]},'motion':spec['motion'],'game':'projects/fishing-2d/game','model':{'path':str(model),'sha256':sha(model)},'scope':'Read-only reviewed exported candidate; not installed, user acceptance pending.'};vp=out/(s+'.viewer-spec.json');save(vp,viewer);entries.append({'id':s,'label':names[s]+' · 库后候选','length_cm':length,'spec':vp.relative_to(ROOT).as_posix(),'triangles':inv['triangles'],'status':'已完成操作者检查，待用户验收'});inventory.append({'species':s,'label':names[s],'model_sha256':sha(model),'body_axis_cm':inv['body_axis_cm'],'old_maximum_width_cm':inv['before_maximum']['before_width_cm'],'new_maximum_width_cm':inv['after_maximum']['after_width_cm'],'reference_maximum_width_cm':inv['reference_maximum_width_cm'],'reference_scope':'Same-name game-art reference'if s!='red_emperor'else'ShortTailRedSnapper named artistic proxy; not verified same species','sop':str(d/'sop-postcleanup.validation.json'),'installed':False,'user_acceptance':False})
  y=100+i*360;draw.text((24,y),f'{names[s]} · {inv["triangles"]} 三角面',font=font,fill='white')
  for column,label in enumerate(['whole-left-texture','whole-top-texture']):
   im=Image.open(capture.parent/(label+'.png')).convert('RGB');pixels=np.array(im).astype(int);mask=np.max(abs(pixels-pixels[0,0]),axis=2)>15;yy,xx=np.nonzero(mask);box=(max(0,int(xx.min())-8),max(0,int(yy.min())-8),min(im.width,int(xx.max())+9),min(im.height,int(yy.max())+9));im=im.crop(box);im.thumbnail((650,270),Image.Resampling.NEAREST);x=column*700+(700-im.width)//2;sheet.paste(im,(x,y+45+(270-im.height)//2))
 save(out/'recipe.json',{'entries':entries});sheet.save(out/'five-fish-overview.jpg',quality=95);save(out/'inventory.validation.json',{'ok':True,'kind':'five_reviewed_database_revision_candidates','species':inventory,'source':'Actual final direct-Godot captures, not generated pictures','user_acceptance':False,'installed':False})
 sys.path[:0]=[str(HERE/'portable')];from prepare_review_list import build
 build(out/'recipe.json',out/'viewer');print(json.dumps({'ok':True,'entries':len(entries),'review':str(out)}))
if __name__=='__main__':main()
