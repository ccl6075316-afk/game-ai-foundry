"""Bind intact-outline geometry checks, fresh motion and native placement proof."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--note',required=True);a=p.parse_args();root=a.root.resolve();assets=root/'projects/fishing-2d/game/assets/aquascape-v7';review=root/'projects/fishing-2d/plans/reviews/aquascape-leaf-contours-v7'
    build=read(assets/'build.validation.json');geometry=read(assets/'geometry.validation.json');motion=read(assets/'motion.validation.json');audit=read(review/'after/contour-audit.validation.json');native=read(review/'godot/render.validation.json')
    if not all(r['ok'] for r in [build,geometry,motion,audit,native]):raise ValueError('Current check failed')
    if len(build['outputs'])!=10 or native['counts']!={'all':20,'animated_plants':10}:raise ValueError('Asset count mismatch')
    hashes={}
    def add(path):
        path=Path(path);path=path if path.is_absolute() else root/path;hashes[str(path.relative_to(root)).replace('\\','/')]=sha(path);return path
    for row in build['outputs']:
        model=add(row['output']);source=add(row['source']);add(row['static']);add(row['source_parts'])
        if sha(model)!=row['sha256'] or sha(source)!=row['source_sha256']:raise ValueError('Stale source/model')
        if next(r for r in motion['outputs'] if r['id']==row['id'])['sha256']!=sha(model):raise ValueError('Stale motion report')
        if next(r for r in geometry['outputs'] if Path(r['path']).stem==row['id'])['sha256']!=sha(model):raise ValueError('Stale geometry report')
    for path in [*assets.glob('*.json'),review/'after/contour-audit.validation.json',review/'contour-audit.validation.json',review/'godot/render.validation.json',root/'projects/fishing-2d/game/assets/aquascape-v5/catalog.json',root/'projects/fishing-2d/docs/AQUASCAPE-CATALOG-V5.md',root/'resources/scripts/aquascape/leaf_polygon.py',root/'resources/scripts/aquascape/repair_plant_contours.py',root/'resources/scripts/aquascape/audit_leaf_contours.py',root/'resources/scripts/aquascape/produce_catalog.py',root/'projects/fishing-2d/game/scripts/aquarium/AquascapeCatalogLab.gd',root/'projects/fishing-2d/game/scripts/aquarium/PlantCurrent.gd']:
        add(path)
    for path in native['outputs']:add(path)
    for path in review.glob('*comparison.png'):add(path)
    for path in review.glob('*before-after.png'):add(path)
    for path in (review/'after').glob('*contour.png'):add(path)
    for name in ['plants-overview.mp4','vallisneria-current.mp4','vallisneria-current.gif']:add(review/'godot'/name)
    total=sum(len(r['leaves']) for r in build['outputs']);holes=sum(l['internal_uv_holes'] for r in audit['outputs'] for l in r['leaves'])
    report={'schema_version':1,'command':'aquascape.record-leaf-contour-review','ok':True,'status':'done','next_action':'human_review','outputs':{'scene':'res://scenes/aquascape_catalog_lab.tscn','models':str(assets/'plants'),'comparisons':[str(p) for p in review.glob('*before-after.png')]},'summary':{'plant_species':10,'rebuilt_leaf_shells':total,'audited_exported_leaf_shells':sum(len(r['leaves']) for r in audit['outputs']),'internal_uv_holes':holes,'geometry_open_edges':sum(r['open_edges'] for r in geometry['outputs']),'all_cpu_motion_checks_pass':True,'cpu_sampled_poses_per_plant':81,'native_sampled_poses':native['sampled_poses'],'native_probes':native['native_probe_count'],'native_root_motion_m':native['max_native_root_motion_m'],'player_placement_check':native['player_placement_check'],'native_pause_resume':native['pause_passed'] and native['resume_passed']},'changes':['Continuous outer source polygons with subpixel simplification replace background-rejected unconstrained triangles.','Polygon-constrained triangulation covers the complete leaf, with shared longitudinal slices for bone deformation.','UVs use original image texel centers; existing cleaned paint bytes, root meshes, bone graph and native animation clips are retained.','New geometry has freshly assigned pinned-root weights and fresh CPU/native checks.','Repeatable production command now applies edge cleanup, contour repair and exported silhouette checks.'],'operator_visual_review':{'status':'reviewed_trial','at':datetime.now(timezone.utc).isoformat(),'note':a.note},'user_acceptance':'pending','limitations':['Source artwork, growth arrangement and species-specific broad waves are retained; this is not a new botanical accuracy certification.','Subpixel contour simplification and raster comparison have finite tolerance; a few source-mask pixels can differ at the boundary.','Separate roots/leaves can overlap; aggregate nonmanifold contacts remain. No continuous self-collision or inter-prop collision proof.','Healthy whole leaf exteriors are assumed; fenestrated or damaged species need a separate hole-preserving profile.','Relocation and four rotations check asset transforms and pinned roots, not an implemented player placement interface.','Existing solid scenery reconstruction limitations remain.'],'hashes':hashes,'failures':[]}
    (review/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'status':'done','next_action':'human_review','hash_bound_files':len(hashes),'summary':report['summary']}))

if __name__=='__main__':main()
