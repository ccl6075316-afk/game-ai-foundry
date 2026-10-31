"""Prepare per-fish cold model catalogue and human review evidence; no install."""
import copy,json,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import sha
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def sheet(out,names,filename,title):
 canvas=Image.new('RGB',(1440,60+len(names)*500),'#25343c');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22);draw.text((12,12),title,font=font,fill='white')
 for i,(left,right)in enumerate(names):
  for j,p in enumerate([left,right]):
   im=Image.open(p).convert('RGB');im.thumbnail((710,460));canvas.paste(im,(j*720,60+i*500));draw.text((j*720+12,60+i*500+463),p.stem,font=font,fill='white')
 canvas.save(out/filename)
def main():
 root=ROOT/'projects/fishing-2d/experiments/three-fish-fin-detail-20261031';old=load(ROOT/'projects/fishing-2d/experiments/four-fish-width-trial-20261031/viewer/catalog.json');entries=[];records=[]
 for sp,rev,label in [('bluegill','candidate-r7','蓝鳃太阳鱼'),('crucian','candidate-r4','鲫鱼'),('grass_carp','candidate-r5','草鱼')]:
  out=root/sp/rev;spec=out/'source-run/final-spec.json';d=load(spec);model=ROOT/d['model']['path'];base=next(e for e in old['entries']if e['id']==sp+'-trial');before=copy.deepcopy(base);before.update(id=sp+'-width-baseline',label=label+' · 修鳍前',status='已认可宽度基线');after=copy.deepcopy(base);after.update(id=sp+'-fin-refined',label=label+' · 鳍精修',status='鳍490通过 · 外观待看 · 独立候选',triangles=d['expected']['triangles'],spec=str(spec.relative_to(ROOT)));v=after['viewer'];v.update(spec=str(spec),spec_sha256=sha(spec),model=str(model),model_sha256=sha(model),model_role='final_model',input_paths=[str(spec),str(model),v['controller']['runtime'],v['controller']['profile']]);entries.extend([after,before])
  review=out/'review';sheet(review,[(review/('before-'+n+'.png'),review/('after-'+n+'.png'))for n in ['whole-left-texture','whole-oblique-texture','whole-top-texture']], 'fin-before-after.png',label+'：修鳍前（左） / 精修候选（右），同相机、同宽度')
  sheet(review,[(review/('before-'+n+'.png'),review/('after-'+n+'.png'))for n in ['head-left-texture','head-front-texture','head-oblique-texture']], 'mouth-preservation.png',label+'：嘴、头、眼与身体不变；实际成品对照')
  names=load(out/'fin-review.plan.json')['fins'];folder=out/'fin-volume';sheet(folder,[(folder/('fin-'+n+'-left-texture.png'),folder/('fin-'+n+'-oblique-clay.png'))for n in names],'all-fins-overview.png',label+'：全部适用鳍，原像素和斜视灰模')
  body=load(out/'body077/completion.validation.json');records.append({'species':sp,'label':label,'candidate':str(out),'model':str(model),'model_sha256':sha(model),'editable_blend':str(out/'source-run/source/fish.blend'),'editable_blend_sha256':sha(out/'source-run/source/fish.blend'),'width_triangles':base['triangles'],'fin_triangles':d['expected']['triangles'],'vertices':d['expected']['vertices'],'bones':d['expected']['bones'],'full490':load(out/'fin490/completion.validation.json')['ok'],'body077':body['ok'],'body077_error':body.get('error'),'installed':False,'user_fin_appearance_accepted':False})
 # Retain the accepted Nile as a quality/style reference, without editing it.
 nile=copy.deepcopy(next(e for e in old['entries']if e['id']=='nile_tilapia-trial'));nile.update(label='罗非鱼 · 保留参考',status='本轮未改');entries.append(nile)
 bindings={}
 for e in entries:
  for p in e['viewer']['input_paths']:bindings[p]=sha(p)
 for p in [HERE/'portable/FishListViewer.gd',HERE/'portable/FishAssetViewer.gd',root/'FinReviewViewer.gd',ROOT/'projects/fishing-2d/experiments/four-fish-width-trial-20261031/WidthReviewViewer.gd']:bindings[str(p)]=sha(p)
 catalog={'kind':'existing_fish_review_list','entries':entries,'bindings':bindings,'mode':'interactive','output':str(root/'viewer/interactive')};save(root/'viewer/catalog.json',catalog);smoke=copy.deepcopy(catalog);smoke.update(mode='smoke',output=str(root/'viewer/smoke'));save(root/'viewer/smoke.catalog.json',smoke)
 save(root/'current-candidates.validation.json',{'ok':True,'kind':'three_fish_fin_detail_candidates','width_user_accepted':True,'fin_repair_scope_verified':True,'formal_whole_fish_acceptance':False,'records':records});print(json.dumps({'ok':True,'entries':len(entries),'candidates':records},ensure_ascii=False))
if __name__=='__main__':main()
