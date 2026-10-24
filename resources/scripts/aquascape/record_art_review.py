"""Bind an explicit operator review note and current files to the GPU report.

This records the supplied note; it cannot supply or infer user acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--note',required=True)
    a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d'
    report=json.loads(a.input.read_text(encoding='utf-8'))
    models=json.loads((a.input.parent/'model.validation.json').read_text(encoding='utf-8'))
    log=root/'projects/aquascape-source-v2/output/runtime.log'
    errors=[line for line in log.read_text(encoding='utf-8').splitlines() if 'ERROR' in line or 'WARNING' in line]
    report['gpu_log_errors']=errors
    report['model_checks_report']='model.validation.json'
    report['ok']=bool(report['ok'] and models['ok'] and not errors and all(r['error']==0 for r in report['outputs']))
    report['visual_review']={'reviewer':'agent/operator, not user','status':'reviewed_experiment','note':a.note,'reviewed_images':[r['path'] for r in report['outputs']],'source_review':'Complete master artworks and six-leaf part sheets actually inspected; operator accepted for an experiment only. Unreliable auxiliary top/right images rejected as orthographic constraints.'}
    report['limitations'] += ['Front/back projection seams and side stretching remain visible; gray views show approximate inflated mass, not the exact painted geological or wood planes.','Plant placement/contact and source-clump layout are approximate; no measured contact proof.','Current generated reconstruction is about 408k triangles and has not been optimized for production.','Plant aggregate meshes have coincident/nonmanifold edge statistics; no claim of a fused manifold plant.','Only scenery review controls are reused from V1; V1 procedural scenery remains rejected.','Scenery uses unshaded painted materials for this style trial; dynamic underwater illumination is unfinished.']
    report['source_visual_rejections']=json.loads((root/'resources/aquascape/source-v2.json').read_text(encoding='utf-8'))['rejected_auxiliary_views']
    report['input_hashes']={}
    paths=list((game/'game/assets/aquascape-v2').glob('*.glb'))
    paths+=list(a.input.parent.glob('*.png'))+list((a.input.parent/'sources').glob('*.png'))
    paths+=[root/'resources/aquascape/source-v2.json',root/'resources/scripts/aquascape/build_from_art.py',root/'resources/scripts/aquascape/validate_art_models.py',game/'game/scripts/aquarium/AquascapeArtLab.gd',game/'game/scenes/aquascape_art_lab.tscn',a.input.parent/'model.validation.json',log]
    for path in paths:report['input_hashes'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    report['status']='done' if report['ok'] else 'failed'
    report['next_action']='human_review' if report['ok'] else 'fix_input'
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'command':'aquascape.record-art-review','ok':report['ok'],'status':report['status'],'next_action':report['next_action'],'outputs':[str(a.output)],'failures':errors},ensure_ascii=False))
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
