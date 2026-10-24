"""Capture isolated, hash-frozen original/candidate fish; never installs them."""
import argparse,json,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True,type=Path);ap.add_argument('--game',required=True,type=Path);ap.add_argument('--godot',required=True,type=Path);a=ap.parse_args();results=[]
for row in json.loads(a.plan.read_text())['items']:
 out=Path(row['output']);out.mkdir(parents=True,exist_ok=True);receipt=out/'preview.validation.json'
 assert not receipt.exists(),'Use a new output directory for each frozen preview'
 cmd=[str(a.godot),'--path',str(a.game),'--rendering-method','gl_compatibility','--quit-after','1200','--script',str(Path(__file__).with_name('preview_species_mouth136.gd').resolve()),'--',row['plan'],row['output']]
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180)
  (out/'render.log').write_text(p.stdout+p.stderr,encoding='utf8')
  assert p.returncode==0 and 'ERROR:' not in p.stdout+p.stderr and 'Broken external resource' not in p.stdout+p.stderr
  assert receipt.exists() and json.loads(receipt.read_text())['ok'],'Missing/failed visual capture'
  result={'species':row['species'],'ok':True,'output':str(out),'production_installed':False}
 except Exception as e:result={'species':row['species'],'ok':False,'error':str(e),'production_installed':False}
 results.append(result);print('MOUTH_RENDER',json.dumps(result),flush=True)
Path(a.plan).with_suffix('.validation.json').write_text(json.dumps({'ok':all(r['ok'] for r in results),'records':results},indent=2));sys.exit(0 if all(r['ok'] for r in results) else 1)
