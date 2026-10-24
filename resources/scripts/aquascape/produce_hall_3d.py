"""Deploy, exercise and bind the editable aquarium hall without altering fish."""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from catalog_workflows import call

NAMES=['AquariumHall3D.gd','AquariumHall3DReview.gd','HallTank3D.gd','HallTankEditor.gd','HallFloor3D.gdshader','HallFootprint.gd','HallBuildReview.gd','HallStyleReview.gd']
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--godot',type=Path);p.add_argument('--record-note');p.add_argument('--build-tools',action='store_true');p.add_argument('--pixel-style',action='store_true');a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d/game';review=root/('projects/fishing-2d/plans/reviews/aquarium-hall-style-v3' if a.pixel_style else 'projects/fishing-2d/plans/reviews/aquarium-hall-build-v2' if a.build_tools else 'projects/fishing-2d/plans/reviews/aquarium-hall-3d-v1');review.mkdir(parents=True,exist_ok=True);source=root/'resources/runtime/godot/aquascape'
    status=call(root,['workflow','status','--manifest',str(root/'projects/aquascape-decor-fronts-v1/pipeline/manifest.json'),'--json'])
    if status['status']!='done' or status['next_action']!='human_review':raise ValueError('Asset workflow not complete')
    art_source=root/'projects/aquarium-hall-materials-v3'
    art_target=game/'assets/aquarium-hall-style-v3'
    # Every hall deployment now depends on these reviewed generated materials.
    art_status=call(root,['workflow','status','--manifest',str(art_source/'pipeline/manifest.json'),'--json'])
    if art_status['status']!='done' or art_status['next_action']!='human_review':raise ValueError('Hall artwork workflow not complete')
    rows=json.loads(subprocess.check_output([str(root/'.venv/Scripts/python.exe'),str(root/'cli/gamefactory.py'),'assets','review','list','--manifest',str(art_source/'output/assets-manifest.json'),'--json'],cwd=root,encoding='utf-8'))
    if len(rows)!=3 or any(r['review']['status']!='accepted' for r in rows):raise ValueError('Hall artwork needs visual review')
    if not a.record_note:
        art_target.mkdir(parents=True,exist_ok=True)
        lineage=[]
        for name in ['hall_floor','hall_wall','hall_wood']:
            donor=art_source/'output'/(name+'_raw.png');target=art_target/(name+'.png');shutil.copyfile(donor,target)
            lineage.append({'asset':name,'source':donor.relative_to(root).as_posix(),'runtime':target.relative_to(root).as_posix(),'sha256':sha(donor)})
        (art_target/'lineage.json').write_text(json.dumps({'workflow':str(art_source/'pipeline/manifest.json'),'prompt_set':str(art_source/'plans'),'native_copy':True,'assets':lineage},indent=2),encoding='utf-8')
    if a.record_note:
        handoff=read(review/'production.handoff.json');native=read(review/'godot/render.validation.json');router=read(review/'router.validation.json')
        if not all(r['ok'] for r in [handoff,native,router]) or not all(native['checks'].values()) or not all(router['checks'].values()):raise ValueError('Incomplete or failed evidence')
        hashes={}
        def add(path):
            path=Path(path);path=path if path.is_absolute() else root/path;hashes[path.relative_to(root).as_posix()]=sha(path);return path
        for rel,digest in handoff['inherited_hashes'].items():
            if sha(root/rel)!=digest:raise ValueError('Inherited file changed: '+rel)
            add(rel)
        for name in NAMES:
            if sha(add(source/name))!=sha(add(game/'scripts/aquarium'/name)):raise ValueError('Stale runtime deployment')
        if a.pixel_style:
            for path in [art_target/'lineage.json',art_source/'brief.json',art_source/'pipeline/manifest.json',art_source/'output/assets-manifest.json',game/'scenes/aquarium_hall_style_review.tscn',root/'projects/fishing-2d/plans/changes/aquarium-hall-style-v3.production-delta.json',root/'resources/scripts/aquascape/prepare_hall_materials.py']:add(path)
            for name in ['hall_floor','hall_wall','hall_wood']:
                if sha(add(art_source/'output'/(name+'_raw.png')))!=sha(add(art_target/(name+'.png'))):raise ValueError('Artwork was modified')
                add(art_source/'plans'/(name+'.json'))
        for path in [game/'scripts/Main.cs',game/'scripts/Main.Screens.cs',game/'scripts/AquariumHall3DRouteReview.cs',game/'scripts/GameSave.cs',game/'scripts/GameSaveStore.cs',game/'scenes/aquarium_hall.tscn',game/'scenes/aquarium_hall_3d.tscn',game/'scenes/aquarium_hall_3d_review.tscn',game/'scenes/aquarium_hall_3d_route_review.tscn',root/'projects/fishing-2d/open-aquarium-hall-3d.cmd',root/'projects/fishing-2d/docs/AQUARIUM-HALL-3D-V1.md',root/'projects/fishing-2d/plans/changes/aquarium-hall-3d-v1.production-delta.json',Path(__file__).resolve(),review/'production.handoff.json',review/'router.validation.json',review/'godot/render.validation.json',review/'godot/hall-save.json',*review.glob('godot/*.png')]:add(path)
        # Bind the current asset catalogue and actual selected scenery donors.
        for catalog_path in ['aquascape-v5','aquascape-decor-v1']:
            catalog=add(game/'assets'/catalog_path/'catalog.json')
            for row in read(catalog)['assets']:
                if row.get('animated',False):continue
                add(game/row['model'].removeprefix('res://'))
                for view in ['front','right','top']:add(game/row['material_dir'].removeprefix('res://')/(row['id']+'-'+view+'.png'))
        for path in review.glob('*.log'):
            if path.name.startswith('interactive'):continue
            add(path)
            if 'ERROR:' in path.read_text(encoding='utf-8'):raise ValueError('Errors in '+str(path))
        if a.build_tools:
            for path in [game/'scenes/aquarium_hall_build_review.tscn',root/'projects/fishing-2d/plans/changes/aquarium-hall-build-v2.production-delta.json',review/'godot/build-layout.json',review/'godot/legacy-layout.json']:add(path)
        report={'schema_version':1,'command':'aquarium.hall-3d-review','ok':True,'status':'done','next_action':'human_review','outputs':{'launcher':str(root/'projects/fishing-2d/open-aquarium-hall-3d.cmd'),'hall':str(review/('godot/08-expanded-hall-build.png' if a.build_tools else 'godot/01-hall-editor.png')),'walk':str(review/'godot/02-first-person.png'),'tank_editor':str(review/'godot/03-in-tank-editor.png')},'summary':native['summary'],'native_checks_passed':len(native['checks']),'router_checks_passed':len(router['checks']),'visual_review':{'status':'operator_reviewed_trial','at':datetime.now(timezone.utc).isoformat(),'note':a.record_note},'user_acceptance':'pending','limitations':native['limitations']+['Legacy 2D source classes remain for data compatibility and historical tooling; the normal aquarium/tank routes do not mount them.','Native preview only; existing fish source-ink export and GLB fallback UID warnings are inherited.'],'hashes':hashes,'failures':[]};(review/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'native_checks':len(native['checks']),'router_checks':len(router['checks']),'hashes':len(hashes)}));return 0
    if not a.godot:raise ValueError('--godot required')
    for name in NAMES:shutil.copyfile(source/name,game/'scripts/aquarium'/name)
    inherited={}
    for name in ['EditableSandBed.gd','EditableSubstrateBed.gd','SubstrateGravel.gd','SandPlacementLab.gd','SubstratePlacementLab.gd','DecorPlacementLab.gd','MarineShowcase.gd','VolumeFishExhibit.gd','FishSurfaceOwnership.gd']:
        path=game/'scripts/aquarium'/name;inherited[path.relative_to(root).as_posix()]=sha(path)
    for species in ['red_emperor','red_seabream','black_seabream','yellow_croaker']:
        path=game/'assets/models/fish'/(species+'.glb');inherited[path.relative_to(root).as_posix()]=sha(path)
    for path in (game/'scripts/aquarium').rglob('*'):
        if path.suffix in ['.gd','.gdshader'] and path.name not in NAMES:inherited[path.relative_to(root).as_posix()]=sha(path)
    scene='res://scenes/aquarium_hall_style_review.tscn' if a.pixel_style else 'res://scenes/aquarium_hall_build_review.tscn' if a.build_tools else 'res://scenes/aquarium_hall_3d_review.tscn'
    commands=[('build',['dotnet','build',game/'GameFactoryDemo.csproj','--no-restore','--nologo','-v','quiet']),('import',[a.godot,'--headless','--path',game,'--editor','--import','--quit']),('native',[a.godot,'--path',game,'--windowed','--resolution','1920x1080','--quit-after','3600',scene,'--','--capture-dir='+str(review/'godot')]),('router',[a.godot,'--headless','--path',game,'--quit-after','1200','res://scenes/aquarium_hall_3d_route_review.tscn','--','--hall-review-dir='+str(review)])]
    steps=[]
    for name,cmd in commands:
        log=review/(name+'.log');started=time.time_ns()
        with log.open('w',encoding='utf-8') as f:r=subprocess.run([str(x) for x in cmd],cwd=root,stdout=f,stderr=subprocess.STDOUT)
        okay=r.returncode==0 and 'ERROR:' not in log.read_text(encoding='utf-8')
        if name in ['native','router']:
            path=review/('godot/render.validation.json' if name=='native' else 'router.validation.json');okay=okay and path.exists() and path.stat().st_mtime_ns>=started and read(path)['ok']
        steps.append({'step':name,'ok':okay,'exit_code':r.returncode,'log':str(log)});print(json.dumps(steps[-1]),flush=True)
        if not okay:break
    unchanged=all(sha(root/rel)==h for rel,h in inherited.items());okay=len(steps)==4 and all(s['ok'] for s in steps) and unchanged
    handoff={'schema_version':1,'command':'aquarium.produce-hall-3d','ok':okay,'status':'done' if okay else 'failed','next_action':'human_review' if okay else 'fix_input','outputs':{'scene':'res://scenes/aquarium_hall.tscn','checks':steps},'inherited_hashes':inherited,'inherited_inputs_unchanged':unchanged,'visual_review':'pending','user_acceptance':'pending','failures':[] if okay else ['Read failed step log or changed inherited input.']};(review/'production.handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2),encoding='utf-8');return 0 if okay else 1

if __name__=='__main__':raise SystemExit(main())
