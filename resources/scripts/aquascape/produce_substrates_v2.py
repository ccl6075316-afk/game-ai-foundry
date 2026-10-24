"""Deploy four reviewed source materials plus bounded source-derived gravel."""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
from PIL import Image
from catalog_workflows import call

IDS=['quartz_white','aquasoil_dark','river_gravel','slate_chips']
SCRIPTS=['EditableSubstrateBed.gd','SubstrateGravel.gd','SubstrateBlend.gdshader','SubstratePlacementLab.gd','SubstratePlacementReview.gd']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--godot',type=Path);a=p.parse_args();root=a.root.resolve();project=root/'projects/aquascape-substrates-v2';game=root/'projects/fishing-2d/game';out=game/'assets/aquascape-substrates-v2';review=root/'projects/fishing-2d/plans/reviews/aquascape-substrates-v2';out.mkdir(parents=True,exist_ok=True);review.mkdir(parents=True,exist_ok=True)
    status=call(root,['workflow','status','--manifest',str(project/'pipeline/manifest.json'),'--json'])
    if status['status']!='done' or status['next_action']!='human_review':raise ValueError('Source workflow not ready')
    manifest=read(project/'output/assets-manifest.json');rows=[]
    for id in IDS:
        asset=manifest['assets'][id]
        if asset.get('review',{}).get('status')!='accepted':raise ValueError('Unreviewed material: '+id)
        source=root/next(s['path_repo'] for s in asset['stages'] if s['stage']=='image.raw' and s['status']=='done');target=out/(id+'.png')
        if Image.open(source).size!=(1024,1024):raise ValueError('Unexpected source resolution')
        shutil.copyfile(source,target)
        config=target.with_suffix('.png.import')
        if not config.exists():
            uri='res://'+target.relative_to(game).as_posix();cache='res://.godot/imported/'+target.name+'-'+hashlib.md5(uri.encode()).hexdigest()+'.ctex'
            config.write_text('[remap]\nimporter="texture"\ntype="CompressedTexture2D"\npath="'+cache+'"\nmetadata={"vram_texture":false}\n[deps]\nsource_file="'+uri+'"\ndest_files=["'+cache+'"]\n[params]\ncompress/mode=0\nmipmaps/generate=false\nprocess/size_limit=0\ndetect_3d/compress_to=0\n',encoding='utf-8')
        rows.append({'id':id,'source':str(source),'source_sha256':sha(source),'output':str(target),'sha256':sha(target),'native_size':[1024,1024],'operator_source_review':'accepted','user_acceptance':'pending'})
    for name in SCRIPTS:shutil.copyfile(root/'resources/runtime/godot/aquascape'/name,game/'scripts/aquarium'/name)
    (out/'assets-manifest.json').write_text(json.dumps({'schema_version':1,'assets':rows,'reused_sand':'res://assets/aquascape-sand-v1/fine-sand.png','source_manifest':str(project/'output/assets-manifest.json'),'user_acceptance':'pending'},ensure_ascii=False,indent=2),encoding='utf-8')
    commands=[[root/'.venv/Scripts/python.exe',root/'resources/scripts/aquascape/build_gravel_proxies.py','--root',root,'--output',out],[root/'.venv/Scripts/python.exe',root/'resources/scripts/aquascape/validate_art_models.py','--input',out,'--output',out/'proxy-geometry.validation.json']]
    if a.godot:commands.extend([[a.godot,'--headless','--path',game,'--editor','--import','--quit'],[a.godot,'--path',game,'--windowed','--resolution','1440x900','--quit-after','3000','res://scenes/aquascape_substrates_review_v2.tscn','--','--capture-dir='+str(review/'godot')]])
    results=[]
    for i,cmd in enumerate(commands):
        log=review/f'step-{i+1:02d}.log';started=time.time_ns()
        with log.open('w',encoding='utf-8') as f:r=subprocess.run([str(v) for v in cmd],cwd=root,stdout=f,stderr=subprocess.STDOUT)
        okay=r.returncode==0 and 'ERROR:' not in log.read_text(encoding='utf-8')
        if 'res://scenes/aquascape_substrates_review_v2.tscn' in cmd:
            native=review/'godot/render.validation.json';okay=okay and native.exists() and native.stat().st_mtime_ns>=started and read(native)['ok']
        results.append({'step':i+1,'ok':okay,'exit_code':r.returncode,'log':str(log)})
        print(json.dumps(results[-1]),flush=True)
        if not okay:break
    okay=all(r['ok'] for r in results)
    handoff={'schema_version':1,'command':'aquascape.produce-substrates-v2','ok':okay,'status':'done' if okay else 'failed','next_action':'human_review' if okay else 'fix_input','outputs':{'materials':str(out/'assets-manifest.json'),'scene':'res://scenes/aquascape_substrates_v2.tscn','checks':results},'native_review_executed':bool(a.godot),'image_calls':0,'failures':[] if okay else ['Read last step log.'],'visual_review':'pending','user_acceptance':'pending'};(review/'production.handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf-8');return 0 if okay else 1

if __name__=='__main__':raise SystemExit(main())
