"""Deploy the accepted sand source and reusable interaction trial, optionally QA.

No image generation or language-model calls. Image creation/review stays in the
official Foundry workflow; existing artwork and model data are not rebuilt.
"""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
from catalog_workflows import call

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--godot',type=Path);p.add_argument('--dry-run',action='store_true');a=p.parse_args();root=a.root.resolve()
    project=root/'projects/aquascape-sand-trial-v1';game=root/'projects/fishing-2d/game';review=root/'projects/fishing-2d/plans/reviews/aquascape-sand-v1'
    scripts=['EditableSandBed','SandPlacementLab','SandPlacementReview']
    if a.dry_run:
        print(json.dumps({'ok':True,'status':'pending','next_action':'run','scripts':scripts,'source_project':str(project),'image_calls':0,'native_review':bool(a.godot)}));return 0
    workflow=call(root,['workflow','status','--manifest',str(project/'pipeline/manifest.json'),'--json'])
    if workflow['status']!='done' or workflow['next_action']!='human_review':raise ValueError('Source workflow not ready for use')
    row=read(project/'output/assets-manifest.json')['assets']['fine_sand']
    if row['review']['status']!='accepted':raise ValueError('Source artwork not reviewed')
    stage=next(s for s in row['stages'] if s['stage']=='image.raw' and s['status']=='done')
    source=root/stage['path_repo'];destination=game/'assets/aquascape-sand-v1/fine-sand.png'
    destination.parent.mkdir(parents=True,exist_ok=True);review.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,destination)
    for name in scripts:shutil.copyfile(root/f'resources/runtime/godot/aquascape/{name}.gd',game/f'scripts/aquarium/{name}.gd')
    assets=[{'id':'fine_sand','path':str(destination),'sha256':sha(destination),'source':str(source),'source_sha256':sha(source),'source_assets_manifest':str(project/'output/assets-manifest.json'),'operator_source_review':'accepted','user_acceptance':'pending'}]
    catalog=read(game/'assets/aquascape-v5/catalog.json')
    for id in ['rock','river_boulder']:
        spec=next(r for r in catalog['assets'] if r['id']==id);model=game/spec['model'].removeprefix('res://')
        assets.append({'id':id,'path':str(model),'sha256':sha(model),'source':'existing aquascape catalogue trial model, unchanged','user_acceptance':'pending'})
    (destination.parent/'assets-manifest.json').write_text(json.dumps({'schema_version':1,'assets':assets,'scope':'One sand source plus two reused illustrated rocks, isolated experiment.','user_acceptance':'pending'},ensure_ascii=False,indent=2),encoding='utf-8')
    results=[]
    if a.godot:
        commands=[[a.godot,'--headless','--path',game,'--editor','--import','--quit'],[a.godot,'--path',game,'--windowed','--resolution','1440x900','--quit-after','2200','res://scenes/aquascape_sand_review.tscn','--','--capture-dir='+str(review/'godot')]]
        for i,cmd in enumerate(commands):
            started=time.time_ns();log=review/('import-console.log' if i==0 else 'capture-console.log')
            with log.open('w',encoding='utf-8') as stream:r=subprocess.run([str(v) for v in cmd],cwd=root,stdout=stream,stderr=subprocess.STDOUT)
            okay=r.returncode==0 and 'ERROR:' not in log.read_text(encoding='utf-8')
            if i==1:
                report=review/'godot/render.validation.json'
                okay=okay and report.exists() and report.stat().st_mtime_ns>=started and read(report)['ok']
            results.append({'exit_code':r.returncode,'ok':okay,'log':str(log)})
            if not okay:break
    okay=not results or all(r['ok'] for r in results)
    handoff={'schema_version':1,'command':'aquascape.produce-sand-trial','ok':okay,'status':'done' if okay else 'failed','next_action':'human_review' if okay else 'fix_input','outputs':{'assets_manifest':str(destination.parent/'assets-manifest.json'),'scene':'res://scenes/aquascape_sand_lab.tscn','checks':results},'source_workflow_status':workflow['status'],'native_review_executed':bool(a.godot),'image_calls':0,'visual_review':'pending','user_acceptance':'pending','failures':[] if okay else ['See step log; do not continue.']}
    (review/'production.handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(handoff,ensure_ascii=False));return 0 if okay else 1

if __name__=='__main__':raise SystemExit(main())
