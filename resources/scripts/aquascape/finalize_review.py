"""Bind a reviewed static scenery pilot report to its current source and output hashes.

Does not approve user visual acceptance. It validates crop provenance and GPU logs,
then records the operator's explicit review notes alongside the technical report.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--foundry', type=Path, required=True)
    p.add_argument('--game-project', type=Path, required=True)
    args = p.parse_args()
    root, project = args.foundry.resolve(), args.game_project.resolve()
    source = root / 'projects/aquascape-pilot'
    review = project / 'plans/reviews/aquascape-pilot'
    target = review / 'validation-report.json'
    data = json.loads(target.read_text(encoding='utf-8'))
    if data.get('user_acceptance') == 'rejected':
        raise SystemExit('This prototype was rejected by the user. Preserve the rejection; create and review replacement artwork instead of re-finalizing this report.')
    atlas = source / 'output/aquascape_atlas_raw.png'
    image = Image.open(atlas).convert('RGB')
    w, h = image.size
    checks = []
    for name, xy in [('rock',(0,0)), ('wood',(1,0)), ('anubias',(0,1)), ('fern',(1,1))]:
        tile = project / f'game/assets/aquascape/{name}.png'
        crop = image.crop((xy[0]*w//2,xy[1]*h//2,(xy[0]+1)*w//2,(xy[1]+1)*h//2))
        actual = Image.open(tile).convert('RGB')
        checks.append({'name':name,'source_size':[w,h],'tile_size':list(actual.size),'exact_native_crop':actual.size==crop.size and actual.tobytes()==crop.tobytes(),'sha256':sha(tile)})
    log = source / 'output/runtime.log'
    errors = [line for line in log.read_text(encoding='utf-8').splitlines() if 'ERROR' in line or 'WARNING' in line]
    data['source_checks']=checks
    data['gpu_log_errors']=errors
    data['ok']=bool(data['ok'] and all(c['exact_native_crop'] for c in checks) and not errors)
    data['visual_review']={
        'reviewer':'agent/operator, not user',
        'status':'reviewed_prototype',
        'compared':['original silver arowana style reference','Foundry concept','Foundry 2x2 atlas','eight actual GPU captures'],
        'observations':[
            'Stone has continuous textured coverage from front, rear and top; its model remains more rounded than the concept slate.',
            'Wood grain follows the trunk and branches, separate cut-end rings remove the previous radial texture smear.',
            'Broad Anubias and lanceolate Microsorum leaf silhouettes differ; back and side views show geometry and visible petioles/rhizomes.',
            'Nearest native-resolution textures and quantized leaf sampling are used; fish is loaded unchanged for same-light style comparison.',
            'Gray and checker views inspected. Geometric tips and thin petioles compress UVs; this is not a distortion-free UV unwrap certification.'
        ],
        'remaining_limits':[
            'Wood forks are intersecting closed branch meshes, not a sculpted watertight union; junctions need further art direction.',
            'Leaf surfaces remain grainy at some viewing distances; style is a review candidate, not user approved.',
            'Static sample, no water-current motion, LOD or batching; 179 mesh instances are not a production performance target.',
            'Native Godot shader materials; no claim of portable baked GLB textures.',
            'Plant attachment has been visually inspected, not measured with a signed-distance contact proof.',
            'Isolated aquarium-floor diorama, not yet wired into the aquarium placement/save/collision system.'
        ]
    }
    data['user_acceptance']='pending'
    data['input_hashes']={}
    paths=[atlas,source/'brief.json',source/'production.json',root/'resources/aquascape/pilot.json',root/'resources/runtime/godot/aquascape/AquascapeKit.gd',project/'game/scripts/aquarium/AquascapeLab.gd',project/'game/scripts/aquarium/AquascapeKit.gd',project/'game/scenes/aquascape_lab.tscn']
    paths+=list((project/'game/assets/aquascape').glob('*.tscn'))
    paths+=list(review.glob('*.png'))
    for path in paths:
        data['input_hashes'][str(path)]=sha(path)
    data['status']='done' if data['ok'] else 'failed'
    data['next_action']='human_review' if data['ok'] else 'fix_input'
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'command':'aquascape.finalize-review','ok':data['ok'],'status':data['status'],'next_action':data['next_action'],'outputs':[str(target)],'failures':errors},ensure_ascii=False))
    return 0 if data['ok'] else 1


if __name__=='__main__':
    raise SystemExit(main())
