"""Prune reproducible passing pose/frame caches, keeping extrema and review phases.

No model, source, report, still or video is removed. Dry-run by default.
"""
import argparse,json
from pathlib import Path
from fish_asset_spec import ROOT
from parts import read,sha

def plan(delivery):
    delivery=delivery.resolve()
    assert delivery.is_relative_to(ROOT/'projects') and 'experiments' in delivery.parts
    manifest=read(delivery/'manifest.json')
    assert manifest['ok'] and manifest['status']=='done'
    assert sha(Path(manifest['model']))==manifest['model_sha256']
    for stage in manifest['stages']:
        assert stage['ok'] and stage['status']=='done'
        assert sha(Path(stage['report']))==stage['report_sha256']
    removed=[];retained=[]
    for export in delivery.glob('fin490/*/export.validation.json'):
        folder=export.parent;roots=read(folder/'roots.validation.json');membrane=read(folder/'membranes.validation.json')
        assert roots['ok'] and membrane['ok']
        samples=read(export)['samples'];assert len(samples)==len(roots['samples'])==len(membrane['samples'])==490
        keep={0}
        for fin in roots['summary']:
            for key in ['min_signed_distance_cm','max_signed_distance_cm']:
                values=[r['fins'][fin][key] for r in roots['samples']]
                keep.add(min(range(len(values)),key=values.__getitem__))
                keep.add(max(range(len(values)),key=values.__getitem__))
            values=[r['fins'][fin]['min_signed_distance_mm'] for r in membrane['samples']]
            keep.add(min(range(len(values)),key=values.__getitem__))
        for index,row in enumerate(samples):
            p=Path(row['posed_mesh_json']).resolve()
            assert p.parent==folder.resolve() and p.name.startswith('sample-')
            if not p.exists():continue
            assert sha(p)==row['sha256']
            (retained if index in keep else removed).append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
    phases={0,16,32,48,64,80,96,112,128,144,160,176,192,208,224,240,251,263,275,287}
    for p in sorted((delivery/'review/frames').glob('frame-*.jpg')):
        row={'path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size}
        (retained if int(p.stem.split('-')[1]) in phases else removed).append(row)
    return {'ok':True,'kind':'reproducible_delivery_cache_cleanup','delivery':str(delivery),'model_sha256':manifest['model_sha256'],'removed':removed,'retained_samples_and_frames':retained,'removed_bytes':sum(r['bytes']for r in removed),'scope':'Full numeric reports, input hashes, static/extreme actual poses, twenty motion phases, all stills/video/models/editable source retained. Dense passing caches reproducible from saved commands.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--delivery',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--json',action='store_true');a=p.parse_args()
    receipt=plan(a.delivery);receipt['status']='planned'
    target=a.delivery/'cache-cleanup.validation.json'
    assert not target.exists(),'Existing receipt must be retained; do not overwrite cleanup history'
    if a.execute:
        # Validate the complete set before any unlink, then save the exact list.
        for row in receipt['removed']:assert sha(Path(row['path']))==row['sha256']
        target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
        for row in receipt['removed']:Path(row['path']).unlink()
        receipt['status']='done';receipt['remaining_bytes']=sum(p.stat().st_size for p in a.delivery.rglob('*')if p.is_file())
        target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in receipt.items()if not isinstance(v,list)}))
