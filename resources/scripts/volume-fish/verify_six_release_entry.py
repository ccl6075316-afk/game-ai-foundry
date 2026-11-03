"""Run one accepted fish through fresh canonical/cache/direct entry and pixels."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';RELEASE=G/'plans/reviews/six-fish-release-20261104'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(a):
 s=a.species;assert s in ['red_seabream','black_seabream','crucian','grass_carp','carp','bluegill'];dest=RELEASE/s;plan=json.loads((dest/'entry.plan.json').read_text(encoding='utf8'));model=G/f'game/assets/models/fish/{s}.glb';assert sha(model)==plan['model_sha256']
 out=ROOT/'output/six-fish-release-20261104/canonical'/s;out.mkdir(parents=True,exist_ok=True);log=out/'canonical-entry.log'
 command=[str(a.godot),'--path',str(G/'game'),'--rendering-method','gl_compatibility','--audio-driver','Dummy','--position','-3000,-3000','--script',str(Path(__file__).parent/'portable/verify_six_final_entry.gd'),'--',str(dest).replace('\\','/'),s]
 with log.open('wb')as f:r=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=100)
 text=log.read_text(encoding='utf8',errors='replace');assert r.returncode==0 and not any(t in text for t in ['Traceback','SCRIPT ERROR','Parse Error','Assertion failed','ERROR:']),text[-2500:]
 actual=json.loads((dest/'canonical-load.validation.json').read_text(encoding='utf8'));assert actual['ok']and actual['model_sha256']==sha(model)
 pairs=[];sheet=Image.new('RGB',(1200,880),(37,52,60));draw=ImageDraw.Draw(sheet)
 for i,action in enumerate(['Swim','Turn','Ascend','Dive']):
  x=dest/(action+'-canonical.png');y=dest/(action+'-approved.png');aa=np.array(Image.open(x));bb=np.array(Image.open(y));assert np.array_equal(aa,bb),action+' canonical/direct pixels differ'
  pairs.append({'action':action,'changed_pixels':0,'canonical_sha256':sha(x),'approved_sha256':sha(y)});im=Image.open(x).convert('RGB');im.thumbnail((600,410),Image.Resampling.NEAREST);sheet.paste(im,((i%2)*600,(i//2)*440+25));draw.text(((i%2)*600+8,(i//2)*440+5),action,fill='white')
 sheet.save(dest/'canonical-actions.jpg',quality=94)
 report={'ok':True,'species':s,'model_sha256':sha(model),'pairs':pairs,'actual_canonical_entry':{'path':str(dest/'canonical-load.validation.json'),'sha256':sha(dest/'canonical-load.validation.json')},'scope':'Actual canonical first/cache and independent GLB use each species exact reviewed controller; four action RGBA pairs identical. No new user-acceptance inference.'};(dest/'canonical-pixels.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'ok':True,'species':s,'actual_canonical_cache_direct_equal':True,'four_action_pixels_equal':True}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True);p.add_argument('--godot',required=True,type=Path);main(p.parse_args())
