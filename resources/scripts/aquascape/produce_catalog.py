"""One deterministic 3D production command, after independent artwork review.

No language-model or image-provider calls. A successful run still requires visual
inspection and never grants user acceptance. Logs and reports are authoritative.
"""
import argparse,json,subprocess,sys,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--catalog',type=Path,default=Path('resources/aquascape/catalog-20-v5.json'));p.add_argument('--output',type=Path,default=Path('projects/fishing-2d/game/assets/aquascape-v5'));p.add_argument('--review',type=Path,default=Path('projects/fishing-2d/plans/reviews/aquascape-catalog-v5'));p.add_argument('--godot',type=Path);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    root=a.root.resolve();out=root/a.output;review=root/a.review;scripts=root/'resources/scripts/aquascape';python=root/'.venv/Scripts/python.exe'
    commands=[]
    for stage in ['extract','plants','solids','registry']:
        commands.append([python,scripts/'build_catalog_models.py','--root',root,'--input',root/a.catalog,'--output',out,'--review',review,'--stage',stage])
    commands.append([python,scripts/'clean_plant_material_edges.py','--root',root,'--input',out/'catalog.json','--output',root/'projects/fishing-2d/game/assets/aquascape-v6'])
    repaired=root/'projects/fishing-2d/game/assets/aquascape-v7'
    commands.append([python,scripts/'repair_plant_contours.py','--root',root,'--input',out/'catalog.json','--output',repaired])
    rebuilt=root/'projects/fishing-2d/game/assets/aquascape-v8'
    commands.append([python,scripts/'rebuild_plant_edge_colors.py','--root',root,'--input',out/'catalog.json','--output',rebuilt,'--review',review/'rim-rebuild'])
    for kind in ['plants','solids']:
        commands.append([python,scripts/'validate_art_models.py','--input',out/kind,'--output',out/kind/'geometry.validation.json'])
    commands.append([python,scripts/'validate_plant_current.py','--root',root,'--input',out/'plants','--config',out/'plant-motion.json','--output',out/'plants/motion.validation.json'])
    commands.append([python,scripts/'validate_art_models.py','--input',repaired/'plants','--output',repaired/'geometry.validation.json'])
    commands.append([python,scripts/'validate_plant_current.py','--root',root,'--input',repaired/'plants','--config',repaired/'plant-motion.json','--output',repaired/'motion.validation.json'])
    commands.append([python,scripts/'audit_leaf_contours.py','--root',root,'--output',review/'contour-after'])
    commands.append([python,scripts/'validate_art_models.py','--input',rebuilt/'plants','--output',rebuilt/'geometry.validation.json'])
    if a.godot:
        commands.extend([[a.godot,'--headless','--path',root/'projects/fishing-2d/game','--editor','--import','--quit'],[a.godot,'--path',root/'projects/fishing-2d/game','--windowed','--resolution','1440x900','res://scenes/aquascape_catalog_lab.tscn','--','--capture-dir='+str(review/'godot')]])
        commands.append([a.godot,'--path',root/'projects/fishing-2d/game','--windowed','--resolution','1440x900','res://scenes/aquascape_edge_review.tscn','--','--capture-dir='+str(review/'rim-rebuild/godot')])
    if a.dry_run:
        print(json.dumps({'command':'aquascape.produce-catalog','ok':True,'status':'pending','next_action':'run','steps':[[str(v) for v in cmd] for cmd in commands],'network_calls':0,'image_calls':0,'visual_review':'required'},indent=2));return 0
    review.mkdir(parents=True,exist_ok=True)
    results=[]
    for i,command in enumerate(commands):
        started_ns=time.time_ns()
        log=review/f'production-step-{i+1:02d}.log'
        with log.open('w',encoding='utf-8') as stream:
            run=subprocess.run([str(v) for v in command],cwd=root,stdout=stream,stderr=subprocess.STDOUT)
        results.append({'step':i+1,'argv':[str(v) for v in command],'exit_code':run.returncode,'log':str(log)})
        capture_arg=next((str(v) for v in command if str(v).startswith('--capture-dir=')),None)
        if capture_arg and run.returncode==0:
            native=Path(capture_arg.removeprefix('--capture-dir='))/'render.validation.json'
            if not native.exists() or native.stat().st_mtime_ns<started_ns or not json.loads(native.read_text(encoding='utf-8')).get('ok'):
                results[-1]['exit_code']=1
                results[-1]['failure']='Native render report is missing, stale or failed.'
        print(json.dumps(results[-1]),flush=True)
        if results[-1]['exit_code']:break
    okay=bool(results) and all(r['exit_code']==0 for r in results)
    data={'command':'aquascape.produce-catalog','ok':okay,'status':'done' if okay else 'failed','next_action':'human_review' if okay else 'fix_input','outputs':results,'failures':[] if okay else ['See last step log. Do not continue after failed input or validation.'],'network_calls':0,'image_calls':0,'visual_review':'pending','user_acceptance':'pending'}
    (review/'production.handoff.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if okay else 1

if __name__=='__main__':raise SystemExit(main())
