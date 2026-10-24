"""Deploy reviewed three-view ornaments and run native placement evidence."""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
from catalog_workflows import call

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--godot',type=Path,required=True);p.add_argument('--reuse-build',action='store_true');a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d/game';out=game/'assets/aquascape-decor-v1';review=root/'projects/fishing-2d/plans/reviews/aquascape-decor-v1';out.mkdir(parents=True,exist_ok=True);review.mkdir(parents=True,exist_ok=True)
    specs=read(root/'resources/aquascape/decor-10-v1.json')['assets']
    for name in ['fronts',*[s['id']+'-views' for s in specs]]:
        project=root/f'projects/aquascape-decor-{name}-v1';status=call(root,['workflow','status','--manifest',str(project/'pipeline/manifest.json'),'--json'])
        if status['status']!='done' or status['next_action']!='human_review':raise ValueError('Source workflow not ready: '+name)
        if any(v.get('review',{}).get('status')!='accepted' for v in read(project/'output/assets-manifest.json')['assets'].values()):raise ValueError('Source review incomplete: '+name)
    results=[]
    def run(cmd,label,native=False):
        log=review/(label+'.log');started=time.time_ns()
        with log.open('w',encoding='utf-8') as f:r=subprocess.run([str(v) for v in cmd],cwd=root,stdout=f,stderr=subprocess.STDOUT)
        okay=r.returncode==0 and 'ERROR:' not in log.read_text(encoding='utf-8')
        if native:
            report=review/'godot/render.validation.json';okay=okay and report.exists() and report.stat().st_mtime_ns>=started and read(report)['ok']
        row={'step':label,'ok':okay,'exit_code':r.returncode,'log':str(log)};results.append(row);print(json.dumps(row),flush=True)
        if not okay:raise RuntimeError('Read '+str(log))
    if not a.reuse_build:run([root/'.venv/Scripts/python.exe',root/'resources/scripts/aquascape/build_decor_ten.py','--root',root,'--output',out],'build')
    build=read(out/'build.validation.json')
    if not build['ok']:raise ValueError('Failed model build')
    rows=[]
    for row in build['outputs']:
        if hashlib.sha256(Path(row['output']).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Stale model build')
        rows.append({'id':row['id'],'name_zh':row['name_zh'],'model':'res://assets/aquascape-decor-v1/'+row['id']+'.glb','material_dir':'res://assets/aquascape-decor-v1','projection_bounds':row['projection_bounds']})
    (out/'catalog.json').write_text(json.dumps({'schema_version':1,'assets':rows,'user_acceptance':'pending'},ensure_ascii=False,indent=2),encoding='utf-8')
    for target in out.glob('*.png'):
        if target.with_suffix('.png.import').exists():continue
        uri='res://'+target.relative_to(game).as_posix();cache='res://.godot/imported/'+target.name+'-'+hashlib.md5(uri.encode()).hexdigest()+'.ctex';target.with_suffix('.png.import').write_text('[remap]\nimporter="texture"\ntype="CompressedTexture2D"\npath="'+cache+'"\nmetadata={"vram_texture":false}\n[deps]\nsource_file="'+uri+'"\ndest_files=["'+cache+'"]\n[params]\ncompress/mode=0\nmipmaps/generate=false\nprocess/size_limit=0\ndetect_3d/compress_to=0\n',encoding='utf-8')
    for name in ['DecorPlacementLab.gd','DecorPlacementReview.gd','DecorThreeViewArtwork.gdshader']:shutil.copyfile(root/'resources/runtime/godot/aquascape'/name,game/'scripts/aquarium'/name)
    run([root/'.venv/Scripts/python.exe',root/'resources/scripts/aquascape/validate_art_models.py','--input',out,'--output',out/'geometry.validation.json'],'geometry')
    run([a.godot,'--headless','--path',game,'--editor','--import','--quit'],'import')
    run([a.godot,'--path',game,'--windowed','--resolution','1440x900','--quit-after','6000','res://scenes/aquascape_decor_review_v1.tscn','--','--capture-dir='+str(review/'godot')],'native',True)
    handoff={'schema_version':1,'command':'aquascape.produce-decor-ten','ok':True,'status':'done','next_action':'human_review','outputs':{'catalog':str(out/'catalog.json'),'scene':'res://scenes/aquascape_decor_v1.tscn','checks':results},'native_review_executed':True,'visual_review':'pending','user_acceptance':'pending','failures':[]};(review/'production.handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
