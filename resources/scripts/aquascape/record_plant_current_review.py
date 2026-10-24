"""Bind source, actual native skeleton checks, rendered loop and visual review."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--note',required=True);a=p.parse_args()
    root=a.root;models=root/'projects/fishing-2d/game/assets/aquascape-v4';config=root/'resources/aquascape/plant-current-v4.json'
    handoff=read(models/'rig.handoff.json');cpu=read(models/'motion.validation.json');gpu=read(a.input/'render.validation.json')
    if not all(r['ok'] for r in [handoff,cpu,gpu]):raise SystemExit('A current motion report failed.')
    if digest(config)!=handoff['config_sha256']:raise SystemExit('Stale rig configuration.')
    hashes={}
    def add(path):
        path=path.resolve();hashes[str(path.relative_to(root))]=digest(path)
    for row in handoff['outputs']:
        model=root/row['output'];source=Path(row['source'])
        if digest(model)!=row['sha256'] or digest(source)!=row['source_sha256']:raise SystemExit('Stale model/source.')
        validated=next(r for r in cpu['outputs'] if r['id']==row['id'])
        if validated['sha256']!=digest(model):raise SystemExit('Stale CPU skin report.')
        add(model);add(source)
    for project,asset in [('aquascape-anubias-v2-leaves','anubias_leaves'),('aquascape-fern-v2-leaves','fern_leaves')]:
        folder=root/'projects'/project;manifest=read(folder/'pipeline/manifest.json');assets=read(folder/'output/assets-manifest.json')
        if any(t['status'] not in ['done','skipped'] for t in manifest['tasks']):raise SystemExit('Source artwork workflow not done.')
        if assets['assets'][asset]['review']['status']!='accepted':raise SystemExit('Source artwork not reviewed.')
        add(folder/'output/assets-manifest.json');add(folder/f'output/{asset}_nobg.png')
    for row in gpu['outputs']:add(Path(row['path']))
    for name in ['plant-current.mp4','plant-current.gif']:add(a.input/name)
    for path in [config,root/'resources/aquascape/source-v2.json',root/'resources/scripts/aquascape/rig_plant_current.py',root/'resources/scripts/aquascape/validate_plant_current.py',root/'projects/fishing-2d/game/scripts/aquarium/PlantCurrent.gd',root/'projects/fishing-2d/game/scripts/aquarium/AquascapePlantCurrentLab.gd',root/'projects/fishing-2d/game/scripts/aquarium/AquascapeThreeViewLab.gd',models/'rig.handoff.json',models/'motion.validation.json',a.input/'render.validation.json']:
        add(path)
    report={'schema_version':1,'command':'aquascape.record-plant-current-review','stage':'validate','ok':True,'status':'done','next_action':'human_review','failures':[],'scope':'Existing two plant species now have native skeletal micro-current in an independent Godot preview.','hashes':hashes,'summary':{'native_bones':gpu['native_rigs'],'cpu_all_pinned_vertices_sampled_poses':81,'godot_native_sampled_poses':gpu['sampled_native_poses'],'godot_pinned_probe_motion_m':gpu['max_native_anchor_motion_m'],'godot_tip_motion_from_phase_zero_m':gpu['max_native_tip_motion_from_phase_zero_m'],'static_scenery_unchanged':gpu['static_scenery_unchanged'],'pause_resume_passed':gpu['pause_control_passed'] and gpu['resume_control_passed'],'loop_duration_s':10,'native_clip_fps':30,'evidence_video_fps':12},'operator_visual_review':{'status':'reviewed_trial','at':datetime.now(timezone.utc).isoformat(),'note':a.note},'user_acceptance':'pending','limitations':['No continuous self/rock collision proof; current poses and contact inherit the existing V2 plant geometry.','Whole-plant multi-view reconstruction and previously documented static material/shape issues remain separate.','No anemone or coral asset created; those require species-specific construction and motion profiles.']}
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'status':'done','next_action':'human_review','output':str(a.output)}))


if __name__=='__main__':main()
