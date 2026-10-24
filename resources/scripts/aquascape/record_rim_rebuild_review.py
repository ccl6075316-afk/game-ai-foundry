"""Bind material-only reconstruction to its immutable baseline and native review."""
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--note',required=True);a=p.parse_args();root=a.root.resolve()
    assets=root/'projects/fishing-2d/game/assets/aquascape-v8';review=root/'projects/fishing-2d/plans/reviews/aquascape-edge-rebuild-v8'
    build=read(assets/'rim-rebuild.validation.json');geometry=read(assets/'geometry.validation.json');native=read(review/'godot/render.validation.json');baseline_motion=read(root/'projects/fishing-2d/game/assets/aquascape-v7/motion.validation.json')
    if not all(r['ok'] for r in [build,geometry,native,baseline_motion]):raise ValueError('Failed validation')
    if len(build['outputs'])!=10 or native['plant_count']!=10 or len(native['outputs'])!=100:raise ValueError('Incomplete native evidence')
    catalog_path=root/'projects/fishing-2d/game/assets/aquascape-v5/catalog.json';catalog=read(catalog_path)
    hashes={}
    def add(path):
        path=Path(path);path=path if path.is_absolute() else root/path
        hashes[path.relative_to(root).as_posix()]=sha(path);return path
    for row in build['outputs']:
        model=add(row['output']);source=add(row['source']);parts=add(row['source_parts'])
        if sha(model)!=row['sha256'] or sha(source)!=row['source_sha256'] or sha(parts)!=row['source_parts_sha256']:raise ValueError('Stale model/source')
        if not row['geometry_uv_skin_animation_binary_identical'] or not row['root_materials_identical']:raise ValueError('Scope changed beyond leaf paint')
        if next(r for r in baseline_motion['outputs'] if r['id']==row['id'])['sha256']!=sha(source):raise ValueError('Baseline motion evidence stale')
        if next(r for r in geometry['outputs'] if Path(r['path']).stem==row['id'])['sha256']!=sha(model):raise ValueError('Geometry evidence stale')
        registered=next(r for r in catalog['assets'] if r['id']==row['id'])
        if (root/'projects/fishing-2d/game'/registered['model'].removeprefix('res://')).resolve()!=model.resolve():raise ValueError('Catalog model mismatch')
    for path in [assets/'rim-rebuild.validation.json',assets/'geometry.validation.json',review/'godot/render.validation.json',root/'projects/fishing-2d/game/assets/aquascape-v7/motion.validation.json',catalog_path,root/'projects/fishing-2d/docs/AQUASCAPE-CATALOG-V5.md',review/'production-dry-run.json',root/'resources/scripts/aquascape/rebuild_plant_edge_colors.py',root/'resources/scripts/aquascape/produce_catalog.py',Path(__file__).resolve(),root/'resources/runtime/godot/aquascape/AquascapeCatalogLab.gd',root/'resources/runtime/godot/aquascape/AquascapeEdgeReview.gd',root/'projects/fishing-2d/game/scripts/aquarium/AquascapeCatalogLab.gd',root/'projects/fishing-2d/game/scripts/aquarium/AquascapeEdgeReview.gd',root/'projects/fishing-2d/game/scripts/aquarium/PlantCurrent.gd',root/'projects/fishing-2d/game/scenes/aquascape_edge_review.tscn']:
        add(path)
    for path in native['outputs']:add(path)
    for path in review.glob('*.png'):add(path)
    report={'schema_version':1,'command':'aquascape.record-rim-rebuild-review','ok':True,'status':'done','next_action':'human_review','outputs':{'scene':'res://scenes/aquascape_catalog_lab.tscn','comparison':str(review/'godot-4x-before-after.png'),'models':str(assets/'plants')},'summary':{'plants':10,'native_leaf_textures':60,'rebuilt_rim_pixels':sum(l['rebuilt_rim_pixels'] for r in build['outputs'] for l in r['leaves']),'geometry_uv_skin_animation_binary_identical':True,'baseline_cpu_motion_validation_hash_checked':True,'cpu_motion_rerun':False,'native_scale_phase_check':{'model_scales':native['model_scales'],'phases':native['native_phase_samples'],'max_root_error_m':native['max_scaled_root_error_m']},'paired_native_images':len(native['outputs']),'geometry_open_edges':sum(r['open_edges'] for r in geometry['outputs'])},'operator_visual_review':{'status':'reviewed_trial','at':datetime.now(timezone.utc).isoformat(),'note':a.note},'user_acceptance':'pending','changes':['Replaced the whole outer color band from inset leaf donors; colored pale fringes no longer escape a near-white threshold.','Kept native pixels, leaf silhouette, UVs, root materials and all rig/animation bytes.','Actual Godot old/new material overrides share the same model, camera and phase at four object scales.','Added review-only object scale controls and a closer camera zoom limit.','Repeatable production includes the new material pass and fresh final-model geometry validation.'],'limitations':['Outer painted highlights within the replaced band may also change; this is an explicit visual tradeoff.','Extreme enlargement reveals the original finite-resolution pixel art and geometry; no unlimited-scale quality claim.','Baseline CPU motion results are inherited only through verified unchanged geometry/rig bytes; they were not rerun for a texture-only edit.','Sampled native roots are not a continuous collision or full placement-system certification.','Existing botanical accuracy and solid prop reconstruction limitations remain.'],'hashes':hashes,'failures':[]}
    (review/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'next_action':'human_review','hash_bound_files':len(hashes),'summary':report['summary']}))

if __name__=='__main__':main()
