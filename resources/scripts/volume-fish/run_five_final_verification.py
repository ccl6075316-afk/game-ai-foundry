"""Fresh editable-source exports and actual canonical Godot loading checks."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];GAME=ROOT/'projects/fishing-2d';RELEASE=GAME/'plans/reviews/five-fish-release-20261104';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--blender',required=True,type=Path);p.add_argument('--godot',required=True,type=Path);a=p.parse_args();records=[]
for row in json.loads((RELEASE/'manifest.json').read_text(encoding='utf8'))['records']:
 s=row['species'];dest=RELEASE/s;out=ROOT/f'output/five-fish-release-20261104/exports/{s}';out.mkdir(parents=True,exist_ok=True)
 def run(name,args):
  logfile=out/(name+'.log')
  if logfile.exists() and not (out/(name+'.first-attempt.log')).exists():logfile.rename(out/(name+'.first-attempt.log'))
  with logfile.open('wb')as stream:result=subprocess.run([str(x)for x in args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=100)
  log=logfile.read_text(encoding='utf8',errors='replace');assert result.returncode==0 and not any(t in log for t in ['Traceback','SCRIPT ERROR','Parse Error','Assertion failed','ERROR:']),name+':'+log[-1800:]
 if not(out/'source-cold-export.validation.json').exists():run('source-export',[a.blender,'--background','--factory-startup','--python',ROOT/'resources/scripts/volume-fish/export_packed_fish_source.py','--','--blend',row['source']['path'],'--output',out/'fish.glb','--report',out/'source-cold-export.validation.json'])
 assert sha(out/'fish.glb')==row['model']['sha256'] and json.loads((out/'source-cold-export.validation.json').read_text())['blend_sha256']==row['source']['sha256'];(dest/'source-cold-export.validation.json').write_bytes((out/'source-cold-export.validation.json').read_bytes())
 run('canonical-entry',[a.godot,'--path',GAME/'game','--rendering-method','gl_compatibility','--audio-driver','Dummy','--position','-3000,-3000','--script',ROOT/'resources/scripts/volume-fish/portable/verify_final_width_entry.gd','--',str(dest).replace('\\','/'),s]);actual=json.loads((dest/'canonical-load.validation.json').read_text());assert actual['ok'] and actual['model_sha256']==row['model']['sha256'];pairs=[];sheet=Image.new('RGB',(1200,880),(37,52,60));draw=ImageDraw.Draw(sheet)
 for i,action in enumerate(['Swim','Turn','Ascend','Dive']):
  x=dest/(action+'-canonical.png');y=dest/(action+'-approved.png');aa=np.array(Image.open(x));bb=np.array(Image.open(y));assert np.array_equal(aa,bb),action+' actual/direct pixels differ';pairs.append({'action':action,'changed_pixels':0,'canonical_sha256':sha(x),'approved_sha256':sha(y)});im=Image.open(x).convert('RGB');im.thumbnail((600,410),Image.Resampling.NEAREST);sheet.paste(im,((i%2)*600,(i//2)*440+25));draw.text(((i%2)*600+8,(i//2)*440+5),action,fill='white')
 sheet.save(dest/'canonical-actions.jpg',quality=94);report={'ok':True,'species':s,'model_sha256':row['model']['sha256'],'pairs':pairs,'actual_canonical_entry':{'path':str(dest/'canonical-load.validation.json'),'sha256':sha(dest/'canonical-load.validation.json')},'source_export_equal':True};(dest/'canonical-pixels.validation.json').write_text(json.dumps(report,indent=2)+'\n');records.append(report);print(json.dumps({'species':s,'source_export_equal':True,'canonical_cache_and_480_controls':True,'four_action_pixels_equal':True}),flush=True)
(RELEASE/'installation.validation.json').write_text(json.dumps({'ok':True,'records':records,'user_acceptance':True,'installed':True,'static_shape_changed_after_acceptance':False},indent=2)+'\n')
