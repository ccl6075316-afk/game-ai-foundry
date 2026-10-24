"""Hash-bind the twenty-asset trial after explicit operator visual inspection."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--note',required=True);a=p.parse_args();root=a.root.resolve()
    review=root/'projects/fishing-2d/plans/reviews/aquascape-catalog-v5';assets=root/'projects/fishing-2d/game/assets/aquascape-v5'
    registry=read(assets/'catalog.json');native=read(review/'godot/render.validation.json');cpu=read(assets/'plants/motion.validation.json');extracted=read(review/'source-extraction.validation.json');production=read(review/'production.handoff.json')
    for data in [native,cpu,production,read(assets/'plants/geometry.validation.json'),read(assets/'solids/geometry.validation.json')]:
        if not data['ok']:raise ValueError('A current production/validation report failed.')
    if len(registry['assets'])!=20 or native['counts']!={'all':20,'animated_plants':10}:raise ValueError('Catalog count mismatch')
    hashes={}
    def add(path):
        path=Path(path).resolve();hashes[str(path.relative_to(root)).replace('\\','/')]=digest(path)
    for kind,report in [('plants','rig.handoff.json'),('solids','build.validation.json')]:
        for row in read(assets/kind/report)['outputs']:
            path=Path(row['output'])
            if digest(path)!=row['sha256']:raise ValueError('Stale built model: '+row['id'])
            if kind=='plants' and next(r for r in cpu['outputs'] if r['id']==row['id'])['sha256']!=digest(path):raise ValueError('Stale motion validation: '+row['id'])
            add(path)
    for row in registry['assets']:
        path=root/'projects/fishing-2d/game'/row['model'].removeprefix('res://');add(path)
        if not row['animated']:
            for view in ['front','right','top']:add(root/'projects/fishing-2d/game'/row['material_dir'].removeprefix('res://')/(row['id']+'-'+view+'.png'))
    for row in extracted['outputs']:
        if digest(Path(row['source']))!=row['sha256']:raise ValueError('Stale source crop')
        add(row['source']);add(row['output'])
        project=Path(row['source']).parents[1]
        add(project/'output/assets-manifest.json');add(project/'pipeline/manifest.json')
    for path in native['outputs']:add(path)
    for path in [*assets.rglob('*.json'),review/'source-extraction.validation.json',review/'production.handoff.json',review/'godot/render.validation.json',root/'resources/aquascape/catalog-20-v5.json',*root.glob('resources/scripts/aquascape/*.py'),root/'projects/fishing-2d/game/scripts/aquarium/AquascapeCatalogLab.gd',root/'projects/fishing-2d/game/scripts/aquarium/PlantCurrent.gd',root/'projects/fishing-2d/game/scripts/aquarium/ThreeViewArtwork.gdshader']:
        add(path)
    for name in ['plants-overview.mp4','vallisneria-current.mp4','vallisneria-current.gif']:add(review/'godot'/name)
    add(root/'projects/fishing-2d/game/scenes/aquascape_catalog_lab.tscn')
    add(root/'projects/fishing-2d/docs/AQUASCAPE-CATALOG-V5.md')
    limits=['Generated camera drawings retain some perspective and internal landmark drift; silhouette overlap is not proof of accurate 3D reconstruction. Basalt top retry remains oblique and is accepted only for this material/shape trial.','Opposite sides of solids reuse front/right/top donors. Projection seams and branch-depth ambiguity remain visible at some angles.','Plant top/right drawings guide growth form; individually painted leaf parts supply geometry and UV. This is not dense multi-view correspondence or photogrammetry.','Plants consist of separate closed leaf shells and roots; positional welding reports nonmanifold contacts. No single watertight union or continuous leaf-collision guarantee.','Gallery is an independent native scene in the game project. Interactive placement, collision, shop inventory and aquarium persistence are outside this trial.','Ten species include two existing approved trial assets. Eight new species and eight new solids were made. No coral or anemone is included.']
    report={'schema_version':1,'command':'aquascape.record-catalog-review','stage':'validate','ok':True,'status':'done','next_action':'human_review','outputs':{'catalog':str(assets/'catalog.json'),'scene':'res://scenes/aquascape_catalog_lab.tscn','launch':str(root/'projects/fishing-2d/open-aquascape-catalog-v5.cmd')},'summary':{'plants':10,'rocks':5,'wood':5,'new_models':16,'reused_models':4,'native_rigs':native['native_rigs'],'cpu_poses_per_new_species':81,'native_poses':41,'native_probes':native['native_probe_count'],'native_max_root_motion_m':native['max_native_root_motion_m'],'native_tip_motion_m':native['native_tip_motion_m'],'pause_resume':native['pause_passed'] and native['resume_passed']},'automation':{'artwork':'Independent full-resolution front/right/top; plants additionally have a six-leaf part sheet. No final packed-view texture.','three_d':'Source crops, traced shells, visual-hull construction, source UV/projection, native skinning, motion, technical checks and registry are deterministic scripts.','one_command':'resources/scripts/aquascape/produce_catalog.py','network_calls_during_3d':0,'codex_token_reduction':'Fewer repeated per-asset code-writing and analysis steps; no quantitative token saving is claimed.','manual_gates':['Source style/species/camera review','Cross-angle native model review','Individual growth and depth corrections','Rendered motion inspection']},'operator_visual_review':{'status':'reviewed_trial','at':datetime.now(timezone.utc).isoformat(),'note':a.note},'user_acceptance':'pending','limitations':limits,'hashes':hashes,'failures':[]}
    (review/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'status':'done','next_action':'human_review','hash_bound_files':len(hashes),'models':20}))

if __name__=='__main__':main()
