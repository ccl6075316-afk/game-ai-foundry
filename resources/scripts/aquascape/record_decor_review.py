"""Bind source review, exported geometry and actual native visual evidence."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--note',required=True);a=p.parse_args();root=a.root.resolve();game=root/'projects/fishing-2d/game';out=game/'assets/aquascape-decor-v1';review=root/'projects/fishing-2d/plans/reviews/aquascape-decor-v1'
    build=read(out/'build.validation.json');geometry=read(out/'geometry.validation.json');native=read(review/'godot/render.validation.json');handoff=read(review/'production.handoff.json')
    if not all(r['ok'] for r in [build,geometry,native,handoff]) or not all(native['checks'].values()) or len(build['outputs'])!=10:raise ValueError('Missing or failed evidence')
    hashes={}
    def add(path):
        path=Path(path);path=path if path.is_absolute() else root/path;hashes[path.relative_to(root).as_posix()]=sha(path);return path
    for row in build['outputs']:
        model=add(row['output'])
        if sha(model)!=row['sha256'] or row['triangles']>18000 or row['connected_components']!=1 or not all(t['ok'] for t in row['semantic_checks']):raise ValueError('Stale or out-of-budget model')
        checked=next(x for x in geometry['outputs'] if Path(x['path']).resolve()==model.resolve())
        if checked['sha256']!=sha(model) or checked['open_edges'] or checked['nonmanifold_edges']:raise ValueError('Unclosed/nonmanifold/stale mesh')
        for view,donor in row['materials'].items():
            source=add(donor['source']);target=add(donor['output'])
            if sha(source)!=donor['source_sha256'] or sha(target)!=donor['sha256'] or list(Image.open(target).size)!=donor['native_crop']:raise ValueError('Stale or resampled donor')
            project=source.parent.parent
            if read(project/'output/assets-manifest.json')['assets'][row['id']+'_'+view]['review']['status']!='accepted':raise ValueError('Unreviewed source')
            for path in [project/'plans'/(row['id']+'_'+view+'.json'),project/'brief.json',project/'pipeline/manifest.json',project/'output/assets-manifest.json']:add(path)
            config=add(target.with_suffix('.png.import')).read_text(encoding='utf-8')
            if 'process/size_limit=0' not in config or 'compress/mode=0' not in config:raise ValueError('Native import changed')
        for view in ['front','right','back','top','gray']:add(review/f'godot/{row["id"]}-{view}.png')
    for name in ['DecorPlacementLab.gd','DecorPlacementReview.gd','DecorThreeViewArtwork.gdshader']:
        if sha(add(root/'resources/runtime/godot/aquascape'/name))!=sha(add(game/'scripts/aquarium'/name)):raise ValueError('Runtime deployment mismatch')
    old=read(root/'projects/fishing-2d/plans/reviews/aquascape-substrates-v2/validation-report.json')
    for name in ['EditableSandBed.gd','SandPlacementLab.gd','EditableSubstrateBed.gd','SubstrateGravel.gd','SubstrateBlend.gdshader','SubstratePlacementLab.gd','ThreeViewArtwork.gdshader']:
        path=add(game/'scripts/aquarium'/name)
        if old['hashes'][path.relative_to(root).as_posix()]!=sha(path):raise ValueError('Inherited baseline changed')
    for path in review.glob('*.log'):
        add(path)
        if 'ERROR:' in path.read_text(encoding='utf-8'):raise ValueError('Godot errors: '+str(path))
    for path in [*out.glob('*.json'),*review.glob('godot/*.json'),*review.glob('godot/*.png'),review/'production.handoff.json',root/'resources/aquascape/decor-10-v1.json',game/'scenes/aquascape_decor_v1.tscn',game/'scenes/aquascape_decor_review_v1.tscn',root/'projects/fishing-2d/open-aquascape-decor-v1.cmd',root/'projects/fishing-2d/docs/AQUASCAPE-DECOR-V1.md',root/'projects/fishing-2d/plans/changes/aquascape-decor-v1.production-delta.json',*[(root/'resources/scripts/aquascape'/name) for name in ['prepare_decor_ten.py','build_decor_ten.py','produce_decor_ten.py','record_decor_review.py','run_decor_aux_sources.py','requirements-decor.txt']]]:add(path)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24);board=Image.new('RGB',(1500,720),'#10272d');draw=ImageDraw.Draw(board)
    for i,row in enumerate(build['outputs']):
        image=Image.open(review/f'godot/{row["id"]}-front.png').crop((375,320,825,790));image.thumbnail((285,285),Image.Resampling.LANCZOS);at=(i%5*300+5,i//5*360+50);board.paste(image,at);draw.text((at[0]+8,at[1]-35),row['name_zh'],font=font,fill='#e7e2cc')
    board.save(review/'ten-decor-native-contact.png');add(review/'ten-decor-native-contact.png')
    for name in ['source-contact.jpg','native-all-views-contact.jpg']:
        if (review/name).exists():add(review/name)
    report={'schema_version':1,'command':'aquascape.record-decor-review','ok':True,'status':'done','next_action':'human_review','outputs':{'scene':'res://scenes/aquascape_decor_v1.tscn','launcher':str(root/'projects/fishing-2d/open-aquascape-decor-v1.cmd'),'comparison':str(review/'ten-decor-native-contact.png'),'overview':str(review/'godot/decor-overview.png')},'native_checks_passed':len(native['checks']),'summary':native['summary'],'triangles':{r['id']:r['triangles'] for r in build['outputs']},'source_art':{'generation':'Foundry workflow configured openai/gpt-image-2','independent_views':30,'source_review':'operator accepted after actual viewing','donors':'native unresampled crops with three-pixel edge color reconstruction; nearest lossless import'},'operator_visual_review':{'status':'reviewed_trial','at':datetime.now(timezone.utc).isoformat(),'note':a.note},'user_acceptance':'pending','limitations':build['outputs'][0]['limitations']+['Ornaments are visual decor with selection bounds; this trial does not add fish pathfinding, per-prop rigid bodies or fish traversal guarantees.','The placement cap remains 80; 18k triangles per ornament is a bounded trial mesh budget, not a minimum-device performance certification.'],'hashes':hashes,'failures':[]};(review/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'ok':True,'native_checks_passed':len(native['checks']),'hash_bound_files':len(hashes)}))

if __name__=='__main__':main()
