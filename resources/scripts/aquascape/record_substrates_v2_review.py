"""Bind five-material source lineage, tiny gravel geometry and native evidence."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--note',required=True);a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d/game';out=game/'assets/aquascape-substrates-v2';review=root/'projects/fishing-2d/plans/reviews/aquascape-substrates-v2';project=root/'projects/aquascape-substrates-v2'
    native=read(review/'godot/render.validation.json');handoff=read(review/'production.handoff.json');geometry=read(out/'proxy-geometry.validation.json');proxies=read(out/'proxy-build.validation.json');assets=read(out/'assets-manifest.json');source_manifest=read(project/'output/assets-manifest.json')
    if not all(x['ok'] for x in [native,handoff,geometry,proxies]) or not handoff['native_review_executed']:raise ValueError('Incomplete/failed technical evidence')
    if 'ERROR:' in (review/'step-04.log').read_text(encoding='utf-8') or not all(native['checks'].values()):raise ValueError('Native errors or failed check')
    hashes={}
    def add(path):
        path=Path(path);path=path if path.is_absolute() else root/path;hashes[path.relative_to(root).as_posix()]=sha(path);return path
    for row in assets['assets']:
        source=add(row['source']);output=add(row['output'])
        if sha(source)!=row['source_sha256'] or sha(output)!=row['sha256'] or sha(source)!=sha(output):raise ValueError('Changed/resampled source art')
        if source_manifest['assets'][row['id']]['review']['status']!='accepted':raise ValueError('Unreviewed source')
        config=add(output.with_suffix('.png.import')).read_text(encoding='utf-8')
        if 'process/size_limit=0' not in config or 'compress/mode=0' not in config:raise ValueError('Import lost native clarity')
        add(project/'plans'/(row['id']+'.json'))
    for row in proxies['outputs']:
        model=add(row['output']);source=add(row['source']);art=add(row['source_art'])
        if sha(model)!=row['sha256'] or sha(source)!=row['source_sha256'] or sha(art)!=row['source_art_sha256']:raise ValueError('Stale proxy lineage')
        if row['triangles']>84:raise ValueError('Proxy triangle budget exceeded')
        if next(r for r in geometry['outputs'] if Path(r['path']).resolve()==model.resolve())['sha256']!=sha(model):raise ValueError('Stale proxy geometry check')
    names=['EditableSubstrateBed.gd','SubstrateGravel.gd','SubstrateBlend.gdshader','SubstratePlacementLab.gd','SubstratePlacementReview.gd']
    for name in names:
        source=add(root/'resources/runtime/godot/aquascape'/name);output=add(game/'scripts/aquarium'/name)
        if sha(source)!=sha(output):raise ValueError('Stale runtime deployment')
    for name in ['EditableSandBed.gd','SandPlacementLab.gd','ThreeViewArtwork.gdshader']:add(game/'scripts/aquarium'/name)
    # V1 runtime remains the accepted baseline; verify its report bindings for
    # all inherited source files without pretending its other files are current.
    old=read(root/'projects/fishing-2d/plans/reviews/aquascape-sand-v1/validation-report.json')
    for name in ['EditableSandBed.gd','SandPlacementLab.gd']:
        path=game/'scripts/aquarium'/name
        if old['hashes'][path.relative_to(root).as_posix()]!=sha(path):raise ValueError('Inherited V1 implementation changed')
    for path in [*project.glob('*.json'),project/'pipeline/manifest.json',project/'output/assets-manifest.json',*out.glob('*.json'),game/'assets/aquascape-v5/catalog.json',game/'assets/aquascape-sand-v1/fine-sand.png',game/'scenes/aquascape_substrates_v2.tscn',game/'scenes/aquascape_substrates_review_v2.tscn',root/'projects/fishing-2d/open-aquascape-substrates-v2.cmd',root/'projects/fishing-2d/docs/AQUASCAPE-SUBSTRATES-V2.md',root/'projects/fishing-2d/plans/changes/aquascape-substrates-v2.production-delta.json',root/'resources/scripts/aquascape/build_gravel_proxies.py',root/'resources/scripts/aquascape/produce_substrates_v2.py',Path(__file__).resolve(),review/'production.handoff.json',review/'godot/render.validation.json',review/'godot/mixed-save.json',review/'godot/legacy-save.json']:
        add(path)
    for row in proxies['outputs']:
        for view in ['front','right','top']:add(game/row['material_dir'].removeprefix('res://')/(row['id']+'-'+view+'.png'))
    for path in review.glob('step-*.log'):add(path)
    for path in project.glob('reviews/*/*'):add(path)
    for path in native['outputs']:add(path)
    board=Image.new('RGB',(1440,540),'#10272d');draw=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
    labels=['浅米细沙','白色石英砂','深色水草泥','自然混合砾砂','灰色小碎石']
    for i,label in enumerate(labels):
        im=Image.open(review/f'godot/material-{i}.png').crop((100,240,1100,680));im.thumbnail((460,220),Image.Resampling.LANCZOS);at=(i%3*480+10,i//3*270+42);board.paste(im,at);draw.text((at[0],at[1]-34),label,font=font,fill='#e7e2cc')
    board.save(review/'five-substrates-native-contact.png');add(review/'five-substrates-native-contact.png')
    report={'schema_version':1,'command':'aquascape.record-substrates-v2-review','ok':True,'status':'done','next_action':'human_review','outputs':{'scene':'res://scenes/aquascape_substrates_v2.tscn','launcher':str(root/'projects/fishing-2d/open-aquascape-substrates-v2.cmd'),'comparison':str(review/'five-substrates-native-contact.png'),'mixed':str(review/'godot/mixed-overview.png')},'summary':native['summary'],'native_checks_passed':len(native['checks']),'proxy_triangles':{r['id']:r['triangles'] for r in proxies['outputs']},'source_art':{'new_materials':4,'retained_materials':1,'native_size':[1024,1024],'pixel_bytes_preserved':True,'source_review':'operator accepted after actual viewing','generation':'Foundry workflow configured openai/gpt-image-2; existing sand illustration used for style reference','rejected_trials':['dark soil first trial below unchanged variance gate','river gravel first trial too photographic']},'operator_visual_review':{'status':'reviewed_trial','at':datetime.now(timezone.utc).isoformat(),'note':a.note},'user_acceptance':'pending','scope':'Five locally paintable surface materials, two source-derived tiny gravel proxies, bounded batching, inherited sand/large-rock interactions, isolated versioned saves.','limitations':native['limitations']+['Only the visible surface material is stored; excavation does not expose historical material layers.','Gravel instances are visual approximations, without per-grain selection, collision, rolling or physical mixture.','Tiny proxies approximate convex stone envelopes and retain source proportions; larger hidden concavities are not preserved.','Material tiling, near/far aliasing, boundary sampling, and gravel-to-underlay visual scale remain finite-resolution approximations.','Native CPU/frame samples apply to the recorded RTX 5080 machine and workload; they are not minimum-device guarantees.'],'hashes':hashes,'failures':[]};(review/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'next_action':'human_review','native_checks_passed':len(native['checks']),'hash_bound_files':len(hashes),'summary':native['summary']}))

if __name__=='__main__':main()
