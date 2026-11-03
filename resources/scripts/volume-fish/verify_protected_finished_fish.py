"""Check unchanged prior finished fish after shared entry edits, without reauthoring."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';RELEASE=G/'plans/reviews/six-fish-release-20261104';sys.path.insert(0,str(Path(__file__).parent))
from check_frozen_fish_static import fingerprint
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p.resolve()),'sha256':sha(p)}
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main(a):
 five=read(ROOT/'resources/volume-fish/final-five-fish-20261104.json')['fish'];rows=[{'species':r['species'],'old':G/f'plans/reviews/five-fish-release-20261104/{r["species"]}','freeze':Path(r['static_freeze']['path'])}for r in five]
 rows.append({'species':'nile_tilapia','old':G/'plans/reviews/nile-tilapia-release-20261103','freeze':G/'assets/source/fish/nile_tilapia/frozen-static.json'})
 results=[]
 for row in rows:
  s=row['species'];dest=RELEASE/'protected'/s;dest.mkdir(parents=True,exist_ok=True);model=G/f'game/assets/models/fish/{s}.glb';frozen=read(row['freeze']);assert fingerprint(model)==frozen['static'],s+' static fingerprint changed'
  if s=='nile_tilapia':
   src=row['old']/'packed-parts.json';dst=dest/'packed-parts.json';shutil.copy2(src,dst);script=Path(__file__).parent/'verify_nile_final_entry.gd';args=[str(dest)]
  else:
   for name in ['entry.plan.json','parts-manifest.json']:shutil.copy2(row['old']/name,dest/name)
   script=Path(__file__).parent/'portable/verify_final_width_entry.gd';args=[str(dest).replace('\\','/'),s]
  log=ROOT/f'output/six-fish-release-20261104/protected/{s}.log';log.parent.mkdir(parents=True,exist_ok=True)
  with log.open('wb')as f:r=subprocess.run([str(a.godot),'--path',str(G/'game'),'--rendering-method','gl_compatibility','--audio-driver','Dummy','--position','-3000,-3000','--script',str(script),'--',*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=100)
  text=log.read_text(encoding='utf8',errors='replace');assert r.returncode==0 and not any(x in text for x in ['SCRIPT ERROR','Parse Error','Assertion failed','ERROR:']),text[-2200:]
  actual=read(dest/'canonical-load.validation.json');assert actual['ok']and actual['model_sha256']==sha(model)
  pairs=[];sheet=Image.new('RGB',(1200,880),(37,52,60));draw=ImageDraw.Draw(sheet)
  for i,action in enumerate(['Swim','Turn','Ascend','Dive']):
   x=dest/(action+'-canonical.png');y=dest/(action+'-approved.png');assert np.array_equal(np.array(Image.open(x)),np.array(Image.open(y))),s+':'+action
   pairs.append({'action':action,'changed_pixels':0,'canonical_sha256':sha(x),'direct_sha256':sha(y)});im=Image.open(x).convert('RGB');im.thumbnail((600,410),Image.Resampling.NEAREST);sheet.paste(im,((i%2)*600,(i//2)*440+25));draw.text(((i%2)*600+8,(i//2)*440+5),action,fill='white')
  sheet.save(dest/'canonical-actions.jpg',quality=94);record={'ok':True,'species':s,'model':ref(model),'static_freeze':ref(row['freeze']),'static_fingerprint_exact':True,'canonical':ref(dest/'canonical-load.validation.json'),'four_action_pairs':pairs,'scope':'Unchanged previously accepted static asset, new shared-entry applicability check only. Original physical reports and acceptance remain historical; no new biological/continuous-time claim.'};write(dest/'regression.validation.json',record);results.append(record);print(json.dumps({'ok':True,'protected':s,'static_and_actual_entry_equal':True}),flush=True)
 write(RELEASE/'protected-finished-fish.validation.json',{'ok':True,'species':results,'frozen_assets_changed':False,'shared_entry_regression_passed':True})
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--godot',required=True,type=Path);main(p.parse_args())
