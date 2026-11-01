"""Prepare the frozen three-fish tail/fin review, without installing assets."""
import copy, hashlib, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
from prepare_native_fin_delivery import load, save, sheet
from portable.glb_io import sha

def main():
 root=ROOT/'projects/fishing-2d/experiments/three-fish-fin-detail-20261031'
 original=load(ROOT/'projects/fishing-2d/experiments/four-fish-width-trial-20261031/viewer/catalog.json')
 entries=[]; records=[]
 for sp,rev,label in [('bluegill','tail-donors-r14','蓝鳃太阳鱼'),('crucian','tail-donors-r13','鲫鱼'),('grass_carp','tail-donors-r13','草鱼')]:
  out=root/sp/rev; spec=out/'source-run/final-spec.json'; d=load(spec); model=out/'source-run/fish.glb'
  auth=load(out/'author/tail-donors.validation.json'); settings=out/'species-parameters.json'; save(settings,{'species':sp,'settings':auth['settings'],'evidence_grade':'engineering fit, not new biological measurements'})
  base=next(e for e in original['entries'] if e['id']==sp+'-trial')
  before=copy.deepcopy(base); before.update(id=sp+'-width-baseline',label=label+' · 返修前',status='已认可宽度基线 · 鳍尾待修旧版')
  after=copy.deepcopy(base); after.update(id=sp+'-tail-fin-revised',label=label+' · 尾部与鳍返修',status='尾部/鳍专项复核 · 整鱼验收未完成',triangles=d['expected']['triangles'],spec=str(spec.relative_to(ROOT)))
  v=after['viewer']; v.update(spec=str(spec),spec_sha256=sha(spec),model=str(model),model_sha256=sha(model),model_role='final_model',input_paths=[str(spec),str(model),v['controller']['runtime'],v['controller']['profile']]); entries.extend([after,before])
  review=out/'review'
  sheet(review,[(review/('before-'+n+'.png'),review/('after-'+n+'.png')) for n in ['whole-left-texture','whole-oblique-texture','whole-top-texture']], 'tail-fin-before-after.png',label+'：上一轮鳍版（左） / 本次尾部与鳍返修（右）')
  sheet(review,[(review/('before-'+n+'.png'),review/('after-'+n+'.png')) for n in ['head-left-texture','head-front-texture','head-oblique-texture']], 'mouth-preservation.png',label+'：头嘴眼保留，同相机实际成品')
  folder=out/'fin-volume'; names=load(out/'fin-review.plan.json')['fins']
  sheet(folder,[(folder/('fin-'+n+'-left-texture.png'),folder/('fin-'+n+'-oblique-clay.png')) for n in names], 'all-fins-overview.png',label+'：所有鳍原画与有限厚度灰模')
  body=load(out/'body077/completion.validation.json'); proofs={}
  for key,rel in [('source','source-run/validation-report.json'),('sections','fin-sections.validation.json'),('preservation','preservation.validation.json'),('roots','fin-root-gate/completion.validation.json'),('membranes','fin490/completion.validation.json'),('motion','motion.validation.json'),('body077','body077/completion.validation.json')]:
   p=out/rel; proof=load(p); proofs[key]={'path':str(p),'sha256':sha(p),'ok':proof['ok']}
  assert all(proofs[k]['ok'] for k in proofs if k!='body077')
  records.append({'species':sp,'label':label,'candidate':str(out),'model':str(model),'model_sha256':sha(model),'editable_blend':str(out/'source-run/source/fish.blend'),'editable_blend_sha256':sha(out/'source-run/source/fish.blend'),'width_triangles':base['triangles'],'fin_triangles':d['expected']['triangles'],'vertices':d['expected']['vertices'],'bones':d['expected']['bones'],'full490':True,'body077':body['ok'],'body077_error':body.get('error'),'installed':False,'user_fin_appearance_accepted':False,'specific_settings':auth['settings'],'specific_settings_sha256':sha(settings),'proofs':proofs})
 nile=copy.deepcopy(next(e for e in original['entries'] if e['id']=='nile_tilapia-trial')); nile.update(label='罗非鱼 · 保留参考',status='本轮未改'); entries.append(nile)
 bindings={p:sha(p) for e in entries for p in e['viewer']['input_paths']}
 for p in [HERE/'portable/FishListViewer.gd',HERE/'portable/FishAssetViewer.gd',root/'TailFinReviewViewer.gd',ROOT/'projects/fishing-2d/experiments/four-fish-width-trial-20261031/WidthReviewViewer.gd']: bindings[str(p)]=sha(p)
 catalog={'kind':'existing_fish_review_list','entries':entries,'bindings':bindings,'mode':'interactive','output':str(root/'viewer/tail-interactive')}; save(root/'viewer/tail-catalog.json',catalog)
 smoke=copy.deepcopy(catalog); smoke.update(mode='smoke',output=str(root/'viewer/tail-smoke')); save(root/'viewer/tail-smoke.catalog.json',smoke)
 result={'ok':True,'kind':'three_fish_tail_fin_donor_candidates','width_user_accepted':True,'fin_repair_scope_verified':True,'formal_whole_fish_acceptance':False,'records':records}
 save(root/'current-candidates.validation.json',result)
 manifest=load(root/'manifest.json'); manifest.update(status='awaiting_review',next_action='human_review',scope='Current tail narrowing, finite fin taper and native donor correction frozen for review. Whole-fish gates remain incomplete; no formal installation.',species=records,formal_whole_fish_acceptance=False,interactive_catalog=str(root/'viewer/tail-catalog.json')); save(root/'manifest.json',manifest)
 print(json.dumps({'ok':True,'entries':len(entries),'models':[{k:r[k] for k in ['species','model_sha256','fin_triangles','bones','body077']} for r in records]}))
if __name__=='__main__':main()
