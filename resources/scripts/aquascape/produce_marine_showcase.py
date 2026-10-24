"""Assemble the existing generated art into a reproducible marine exhibit."""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from catalog_workflows import call

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--godot',type=Path);p.add_argument('--record-note');a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d/game';review=root/'projects/fishing-2d/plans/reviews/aquascape-marine-v1';review.mkdir(parents=True,exist_ok=True);out=game/'assets/aquascape-marine-v1';out.mkdir(parents=True,exist_ok=True);source=root/'resources/runtime/godot/aquascape';layout=read(root/'resources/aquascape/marine-showcase-v1.json');status=call(root,['workflow','status','--manifest',str(root/'projects/aquascape-decor-fronts-v1/pipeline/manifest.json'),'--json'])
    if status['status']!='done' or status['next_action']!='human_review':raise ValueError('Source workflow is not complete')
    hashes={}
    def add(path):
        path=Path(path);path=path if path.is_absolute() else root/path;hashes[path.relative_to(root).as_posix()]=sha(path);return path
    # Preserve the actual selected fish binaries, the current helper chain and
    # all prop donors. This task does not re-export or rewrite any fish asset.
    baseline={}
    for species in layout['fish_species']:
        path=game/'assets/models/fish'/(species['id']+'.glb');baseline[path.relative_to(root).as_posix()]=sha(path)
    for path in (game/'scripts/aquarium').rglob('*'):
        if path.suffix in ['.gd','.gdshader'] and not path.name.startswith('Marine'):baseline[path.relative_to(root).as_posix()]=sha(path)
    for path in (game/'assets/models/fish/motion').glob('*.json'):baseline[path.relative_to(root).as_posix()]=sha(path)
    if a.record_note:
        handoff=read(review/'production.handoff.json');native=read(review/'godot/render.validation.json')
        if not handoff['ok'] or not native['ok'] or not all(native['checks'].values()):raise ValueError('Failed technical evidence')
        for rel,digest in handoff['baseline_hashes'].items():
            if sha(root/rel)!=digest:raise ValueError('An inherited input changed during this task: '+rel)
            add(rel)
        for row in layout['fish_species']:
            path='res://assets/models/fish/'+row['id']+'.glb'
            if native['unchanged_fish_model_hashes'][path]!=sha(game/path.removeprefix('res://')):raise ValueError('Stale native fish evidence')
        catalog={}
        for path in ['assets/aquascape-v5/catalog.json','assets/aquascape-decor-v1/catalog.json']:
            add(game/path)
            for row in read(game/path)['assets']:catalog[row['id']]=row
        for row in layout['props']:
            spec=catalog[row['id']];add(game/spec['model'].removeprefix('res://'))
            for view in ['front','right','top']:add(game/spec['material_dir'].removeprefix('res://')/(row['id']+'-'+view+'.png'))
        for name in ['MarineShowcase.gd','MarineBackdrop.gdshader','MarineSubstrateBlend.gdshader']:
            if sha(add(source/name))!=sha(add(game/'scripts/aquarium'/name)):raise ValueError('Stale deployment')
        for directory in ['assets/aquascape-substrates-v2','assets/aquascape-sand-v1']:
            for path in (game/directory).iterdir():
                if path.suffix in ['.png','.glb']:add(path)
        for path in [root/'resources/aquascape/marine-showcase-v1.json',out/'layout.json',game/'scenes/aquascape_marine_showcase_v1.tscn',root/'projects/fishing-2d/open-aquascape-marine-v1.cmd',root/'projects/fishing-2d/docs/AQUASCAPE-MARINE-V1.md',root/'projects/fishing-2d/plans/changes/aquascape-marine-showcase-v1.production-delta.json',Path(__file__).resolve(),review/'production.handoff.json',review/'godot/render.validation.json',*review.glob('*.log'),*review.glob('godot/*.png')]:add(path)
        report={'schema_version':1,'command':'aquascape.marine-showcase-review','ok':True,'status':'done','next_action':'human_review','summary':native['summary'],'native_checks_passed':len(native['checks']),'outputs':{'scene':'res://scenes/aquascape_marine_showcase_v1.tscn','hero':str(review/'godot/hero.png'),'launcher':str(root/'projects/fishing-2d/open-aquascape-marine-v1.cmd')},'visual_review':{'status':'operator_reviewed_trial','at':datetime.now(timezone.utc).isoformat(),'note':a.record_note},'user_acceptance':'pending','source_art':'Existing generated art only; no new image calls or code-painted replacement prop textures.','limitations':native['limitations']+['Local native preview only: inherited fish source-ink helpers warn that raw image loads need export packaging work. No standalone export is claimed.','Existing GLB fallback texture UID warnings use valid text paths; visible ornament materials use the original three-view donors.','Existing fish motion/appearance gates are inherited, not re-certified as new fish deliveries.'],'hashes':hashes,'failures':[]};(review/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'checks':len(native['checks']),'hashes':len(hashes)}));return
    if not a.godot:raise ValueError('--godot required for production/capture')
    shutil.copyfile(root/'resources/aquascape/marine-showcase-v1.json',out/'layout.json')
    for name in ['MarineShowcase.gd','MarineBackdrop.gdshader','MarineSubstrateBlend.gdshader']:shutil.copyfile(source/name,game/'scripts/aquarium'/name)
    results=[]
    commands=[('import',[a.godot,'--headless','--path',game,'--editor','--import','--quit']),('native',[a.godot,'--path',game,'--windowed','--resolution','1920x1080','--quit-after','1800','res://scenes/aquascape_marine_showcase_v1.tscn','--','--capture-dir='+str(review/'godot')])]
    for label,cmd in commands:
        log=review/(label+'.log');start=time.time_ns()
        with log.open('w',encoding='utf-8') as f:r=subprocess.run([str(x) for x in cmd],cwd=root,stdout=f,stderr=subprocess.STDOUT)
        okay=r.returncode==0 and 'ERROR:' not in log.read_text(encoding='utf-8')
        if label=='native':
            report=review/'godot/render.validation.json';okay=okay and report.exists() and report.stat().st_mtime_ns>=start and read(report)['ok']
        results.append({'step':label,'ok':okay,'exit_code':r.returncode,'log':str(log)});print(json.dumps(results[-1]),flush=True)
        if not okay:break
    unchanged=all(sha(root/rel)==digest for rel,digest in baseline.items());okay=all(r['ok'] for r in results) and len(results)==2 and unchanged
    handoff={'schema_version':1,'command':'aquascape.produce-marine-showcase','ok':okay,'status':'done' if okay else 'failed','next_action':'human_review' if okay else 'fix_input','outputs':{'scene':'res://scenes/aquascape_marine_showcase_v1.tscn','checks':results},'baseline_hashes':baseline,'inherited_inputs_unchanged':unchanged,'visual_review':'pending','user_acceptance':'pending','failures':[] if okay else ['Read logs; no failed step is accepted.']};(review/'production.handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf-8');return 0 if okay else 1

if __name__=='__main__':raise SystemExit(main())
