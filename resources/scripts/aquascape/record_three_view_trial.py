"""Bind actual viewed GPU evidence to this experiment, without user acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--note',required=True);a=p.parse_args()
    root=a.root;review=a.input;models=root/'projects/fishing-2d/game/assets/aquascape-v3'
    build=read(models/'build.validation.json');geometry=read(models/'geometry.validation.json');render=read(review/'render.validation.json')
    if not all(r.get('ok') for r in [build,geometry,render]):raise SystemExit('Current technical report failed; fix inputs first.')
    sources={};evidence={}
    for kind in ['rock','wood']:
        folder=root/f'projects/aquascape-{kind}-materials-v3'
        manifest=read(folder/'pipeline/manifest.json')
        if any(t['status'] not in ['done','skipped'] for t in manifest['tasks']):raise SystemExit('Material workflow not done.')
        asset=read(folder/'output/assets-manifest.json')['assets'][f'{kind}_material_views']
        if asset.get('review',{}).get('status')!='accepted':raise SystemExit('Material artwork not reviewed.')
        for f in [folder/f'output/{kind}_material_views_raw.png',folder/f'plans/{kind}_material_views.json',folder/'brief.json']:
            sources[str(f.relative_to(root))]=digest(f)
    for row in build['outputs']:
        path=root/row['output']
        if digest(path)!=row['sha256']:raise SystemExit('Stale model report.')
        for item in geometry['outputs']:
            if Path(item['path']).name==path.name and item['sha256']!=digest(path):raise SystemExit('Stale topology report.')
    for row in render['outputs']:
        f=Path(row['path']);evidence[f.name]=digest(f)
    for f in [root/'resources/aquascape/three-views-v3.json',root/'resources/scripts/aquascape/build_from_three_views.py',root/'projects/fishing-2d/game/scripts/aquarium/AquascapeThreeViewLab.gd',root/'projects/fishing-2d/game/scripts/aquarium/ThreeViewArtwork.gdshader']:
        sources[str(f.relative_to(root))]=digest(f)
    result={'schema_version':1,'command':'aquascape.record-three-view-material-trial','stage':'validate','ok':True,'status':'done','next_action':'human_review','failures':[],'scope':'Generated pixel materials and actual Godot review-only prototype. Technical completion is not geometric or user acceptance.','source_hashes':sources,'capture_hashes':evidence,'model_hashes':{r['id']:r['sha256'] for r in build['outputs']},'operator_visual_review':{'status':'reviewed_trial_with_known_defects','at':datetime.now(timezone.utc).isoformat(),'note':a.note},'user_acceptance':'pending','production_ready':False,'limitations':['Rock uses three silhouette constraints but internal terrace relief is incomplete; painted TOP reintroduced some oblique plane shading and is only a color donor.','Wood front/top medial form uses inferred depth guides. Original RIGHT silhouette conflicts with main branch elevation; used for global depth, not a solved hard shape constraint.','Wood end grain, branch junctions and projection seams remain imperfect; no final geometric acceptance.','Hidden back/left surfaces reuse donor artwork; independent back/left design is not complete.','Native donor crops are unresampled; alpha masks donor availability only and never cuts holes in the opaque surface.','Plants reuse V2 generated artwork models and species; no whole-plant three-view reconstruction completed.','High triangle count is for visual trial, not production optimization.']}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'status':'done','next_action':'human_review','output':str(a.output),'production_ready':False}))


if __name__=='__main__':main()
