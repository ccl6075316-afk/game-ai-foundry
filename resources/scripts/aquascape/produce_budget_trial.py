"""Reproduce budgeted scenery and an isolated native GPU plant trial."""
import argparse,json,shutil,subprocess,time
from pathlib import Path
from optimize_scenery import load,save,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--godot',type=Path,required=True);p.add_argument('--reuse-build',action='store_true');p.add_argument('--json',action='store_true');a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d/game';out=game/'assets/aquascape-v9';review=root/'projects/fishing-2d/plans/reviews/aquascape-budget-v9';review.mkdir(parents=True,exist_ok=True);scripts=root/'resources/scripts/aquascape';python=root/'.venv/Scripts/python.exe'
    steps=[]
    def run(argv,label,report=None):
        log=review/(label+'.log');start=time.time_ns()
        with log.open('w',encoding='utf-8') as f:r=subprocess.run(list(map(str,argv)),cwd=root,stdout=f,stderr=subprocess.STDOUT)
        okay=r.returncode==0 and 'ERROR:' not in log.read_text(encoding='utf-8')
        if report:okay=okay and report.exists() and report.stat().st_mtime_ns>=start and load(report).get('ok',False)
        steps.append({'label':label,'argv':list(map(str,argv)),'exit_code':r.returncode,'ok':okay,'log':str(log)})
        if not okay:raise RuntimeError('Read '+str(log))
    if not a.reuse_build:
        run([python,scripts/'optimize_scenery.py','--root',root,'--output',out,'--report',review/'build.validation.json'],'build',review/'build.validation.json')
        natural=game/'assets/aquascape-v10';normal_report=root/'projects/fishing-2d/plans/reviews/aquascape-natural-v10/build.validation.json'
        run([python,scripts/'normalize_plant_leaves.py','--root',root,'--input',out/'aquascape-v5-catalog.json','--output',natural,'--report',normal_report,'--deploy'],'normal-leaves',normal_report)
        run([python,scripts/'build_shader_plants.py','--input',natural/'plants','--output',natural/'shader-plants'],'shader-build',natural/'shader-plants/shader-plants.validation.json')
        shutil.copyfile(natural/'catalog.json',game/'assets/aquascape-v5/catalog.json')
    live_catalog=game/'assets/aquascape-v5/catalog.json';live_decor=game/'assets/aquascape-decor-v1/catalog.json'
    active=load(live_catalog)['assets'];shader_uri=next(row['shader_metadata'] for row in active if row.get('animated'));shader_folder=(game/shader_uri.removeprefix('res://')).parent
    run([python,scripts/'validate_scenery_budget.py','--root',root,'--input',live_catalog,live_decor,'--output',review/'budget.validation.json','--json'],'budget',review/'budget.validation.json')
    for name in ['PlantSway.gdshader','SceneryBudgetReview.gd']:shutil.copyfile(root/'resources/runtime/godot/aquascape'/name,game/'scripts/aquarium'/name)
    run([a.godot,'--headless','--path',game,'--editor','--import','--quit'],'import')
    run([a.godot,'--path',game,'--windowed','--resolution','1280x720','--quit-after','15000','res://scenes/aquascape_budget_review.tscn','--','--capture-dir='+str(review/'native')],'native',review/'native/render.validation.json')
    run([python,scripts/'validate_shader_plants.py','--input',shader_folder,'--native',review/'native','--output',review/'shader.validation.json'],'shader-validation',review/'shader.validation.json')
    run([a.godot,'--path',game,'--windowed','--resolution','1440x900','res://scenes/shader_plant_tank.tscn','--','--motion-check-dir='+str(review/'live-motion')],'live-motion',review/'live-motion/motion.validation.json')
    run([python,scripts/'validate_live_plant_motion.py','--root',root,'--input',review/'live-motion'],'live-motion-validation',review/'live-motion/motion.validation.json')
    run(['ffmpeg','-y','-framerate','12','-i',review/'native/motion-frames/%04d.png','-c:v','libx264','-pix_fmt','yuv420p','-crf','19',review/'shader-sway.mp4'],'encode')
    # Capture only the explicit trial frames under this review directory.
    # Preserve hashes before removing reconstructible intermediate images.
    frames=list((review/'native/motion-frames').glob('*.png'));cleanup=[]
    for frame in frames:
        resolved=frame.resolve()
        if not resolved.is_relative_to((review/'native/motion-frames').resolve()):raise ValueError('Unsafe frame cleanup path')
        cleanup.append({'path':str(resolved),'sha256':sha(resolved),'bytes':resolved.stat().st_size})
    save(review/'frame-cleanup.validation.json',{'command':'aquascape.trial-frame-cleanup','status':'done','outputs':{'retained_video':str(review/'shader-sway.mp4'),'sha256':sha(review/'shader-sway.mp4')},'deleted':cleanup})
    for frame in frames:frame.unlink()
    if (review/'native/motion-frames').exists() and not any((review/'native/motion-frames').iterdir()):(review/'native/motion-frames').rmdir()
    active_models=[game/row['model'].removeprefix('res://') for row in active+load(live_decor)['assets']]
    inputs=[root/'resources/aquascape/geometry-budgets.json',*[(root/'resources/runtime/godot/aquascape'/n) for n in ['PlantSway.gdshader','SceneryBudgetReview.gd','ShaderPlantTank.gd']],*active_models,*shader_folder.glob('*.glb')]
    save(review/'production.handoff.json',{'schema_version':1,'command':'aquascape.produce-budget-trial','ok':True,'status':'done','next_action':'human_review','inputs':{str(p):sha(p) for p in inputs},'outputs':{'steps':steps,'build':str(review/'build.validation.json'),'budget':str(review/'budget.validation.json'),'native':str(review/'native/render.validation.json'),'shader':str(review/'shader.validation.json'),'video':str(review/'shader-sway.mp4'),'frame_cleanup':str(review/'frame-cleanup.validation.json')},'failures':[],'visual_review':'pending','user_acceptance':'pending'})
    print(json.dumps({'ok':True,'status':'done','next_action':'human_review','handoff':str(review/'production.handoff.json')}))
if __name__=='__main__':main()
