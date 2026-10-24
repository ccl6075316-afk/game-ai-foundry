"""Record material-only repair evidence against unchanged validated native rigs."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from rig_plant_current import read_glb

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--note',required=True);a=p.parse_args();root=a.root.resolve()
    folder=root/'projects/fishing-2d/plans/reviews/aquascape-leaf-edges-v6';assets=root/'projects/fishing-2d/game/assets/aquascape-v6'
    cleanup=read(assets/'edge-cleanup.validation.json');native=read(folder/'godot/render.validation.json');comparison=read(folder/'screen-comparison.validation.json');hashes={}
    def add(path):
        path=Path(path);path=path if path.is_absolute() else root/path
        hashes[str(path.relative_to(root)).replace('\\','/')]=sha(path)
        return path
    if not cleanup['ok'] or not native['ok'] or native['counts']!={'all':20,'animated_plants':10}:raise ValueError('Current native checks failed')
    cpu_files=[root/'projects/fishing-2d/game/assets/aquascape-v5/plants/motion.validation.json',root/'projects/fishing-2d/game/assets/aquascape-v4/motion.validation.json']
    cpu_rows=[r for path in cpu_files for r in read(path)['outputs']]
    for row in cleanup['outputs']:
        source=add(row['source']);output=add(row['output']);add(row['source_parts'])
        if sha(source)!=row['source_sha256'] or sha(output)!=row['sha256']:raise ValueError('Stale material validation')
        if next(r for r in cpu_rows if r['id']==row['id'])['sha256']!=sha(source):raise ValueError('Stale original motion evidence')
        doc,binary=read_glb(source);new,newbin=read_glb(output)
        if newbin[:len(binary)]!=binary or any(doc.get(k)!=new.get(k) for k in ['meshes','accessors','nodes','skins','animations','samplers']):raise ValueError('Unexpected non-image change')
    catalog=root/'projects/fishing-2d/game/assets/aquascape-v5/catalog.json'
    for row in read(catalog)['assets']:add(root/'projects/fishing-2d/game'/row['model'].removeprefix('res://'))
    for path in native['outputs']:add(path)
    for path in [catalog,assets/'edge-cleanup.validation.json',folder/'godot/render.validation.json',folder/'screen-comparison.validation.json',folder/'before-after.png',*cpu_files,root/'resources/scripts/aquascape/clean_plant_material_edges.py',root/'resources/scripts/aquascape/produce_catalog.py',root/'resources/scripts/aquascape/compare_leaf_edge_renders.py',root/'projects/fishing-2d/game/scripts/aquarium/AquascapeCatalogLab.gd',root/'projects/fishing-2d/docs/AQUASCAPE-CATALOG-V5.md']:
        add(path)
    for name in ['plants-overview.mp4','vallisneria-current.mp4','vallisneria-current.gif']:add(folder/'godot'/name)
    data={'schema_version':1,'command':'aquascape.record-leaf-edge-review','ok':True,'status':'done','next_action':'human_review','outputs':{'preview':'res://scenes/aquascape_catalog_lab.tscn','comparison':str(folder/'before-after.png'),'material_models':str(assets/'plants')},'summary':{'plant_species':10,'source_leaf_images':60,'leaf_edge_pixels_corrected':sum(l['white_matte_pixels_before'] for r in cleanup['outputs'] for l in r['leaves']),'root_background_pixels_corrected':sum(l['white_background_pixels_corrected'] for r in cleanup['outputs'] for l in r['roots']),'original_geometry_uv_skin_animation_identical':True,'native_poses':native['sampled_poses'],'native_probes':native['native_probe_count'],'native_max_root_motion_m':native['max_native_root_motion_m'],'pause_resume_passed':native['pause_passed'] and native['resume_passed']},'screen_comparison':comparison['outputs'],'operator_visual_review':{'status':'reviewed_repair','at':datetime.now(timezone.utc).isoformat(),'note':a.note},'user_feedback_before_repair':'User praised overall appearance and requested removal of visible white material fringes. This is not acceptance of the repaired revision.','user_acceptance':'pending','scope':'Material-only repair across ten plants. Reference artwork and meshes are preserved; original CPU motion reports remain applicable by byte-exact non-image data comparison, with fresh native Godot checks.','limitations':['Legitimate interior pale veins/spots and pink leaf color are retained. No global white-color deletion or silhouette erosion.','Prior approximate reconstruction and separate-shell collision limitations remain.','This report supersedes V5 as current catalog material evidence. V5 captures remain historical before-repair evidence.'],'hashes':hashes,'failures':[]}
    (folder/'validation-report.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'status':'done','next_action':'human_review','hash_bound_files':len(hashes),'summary':data['summary']}))

if __name__=='__main__':main()
