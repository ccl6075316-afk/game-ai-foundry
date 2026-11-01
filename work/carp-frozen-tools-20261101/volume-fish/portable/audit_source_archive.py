"""Verify an accepted source archive before generating auxiliary materials.

Does not recreate historical files or grant new model/visual acceptance.
"""
import argparse,json,sys
from pathlib import Path
from fish_asset_spec import ROOT,artifact_output
from parts import read,sha
sys.path.insert(0,str(ROOT/'cli'))
from volume_archive import archive_inputs

def audit(handoff,profile,source,output):
    handoff,profile,source=(Path(p).resolve()for p in [handoff,profile,source])
    out=artifact_output(output,[handoff,profile,source]);assert not out.exists();out.mkdir(parents=True)
    result={'ok':False,'kind':'accepted_source_archive_preflight','status':'blocked','next_action':'fix_input','inputs':{str(p):sha(p)if p.is_file()else None for p in [handoff,profile,source]},'failures':[],'scope':'Archive presence and historical hash binding only. No newly generated provenance, anatomy or current visual acceptance.'}
    try:
        missing=[str(p)for p in [handoff,profile,source]if not p.is_file()]
        if missing:raise ValueError('Missing primary archive inputs: '+', '.join(missing))
        old=read(handoff);p=read(profile);art=handoff.parent/(handoff.stem+'-artifacts')
        reference=(ROOT/p['style']['reference_image'].removeprefix('repo://')).resolve()
        names=old.get('style_review',{}).get('hashes',{}).get('review_images',{})
        assert all('/'not in n and '\\'not in n and n not in ['.','..']for n in names),'Invalid archive review name'
        spec={'accepted_handoff':str(handoff),'profile':str(profile),'source':str(source),'reference':str(reference),'blend':str(art/'fish.blend'),'glb':str(art/'fish.glb'),'review_images':{k:str(art/'review'/({'style_comparison':'style-comparison','master_comparison':'master-comparison'}.get(k,k)+'.png'))for k in names}}
        for key in ['front_source','top_source','bottom_source']:
            if old.get(key):spec[key]=old[key]['path']
        mapping=out/'archive-inputs.json';mapping.write_text(json.dumps(spec,indent=2)+'\n',encoding='utf8')
        files=[Path(v)for k,v in spec.items()if k!='review_images']+[Path(v)for v in spec['review_images'].values()]
        missing=[str(p)for p in files if not p.is_file()]
        if missing:raise ValueError('Missing actual accepted archive files: '+', '.join(missing))
        _,_,_,fingerprint=archive_inputs(mapping)
        result.update(ok=True,status='done',next_action='none',fingerprint=fingerprint,archive_inputs=str(mapping))
    except (ValueError,AssertionError,KeyError,OSError)as e:
        result['failures'].append({'kind':'validation','code':'accepted_archive_unavailable','message':str(e)})
    (out/'validation-report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['handoff','profile','source','output']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--json',action='store_true');a=parser.parse_args();result=audit(a.handoff,a.profile,a.source,a.output)
    print(json.dumps({'ok':result['ok'],'status':result['status'],'next_action':result['next_action'],'report':str(a.output/'validation-report.json'),'failures':result['failures']}));raise SystemExit(0 if result['ok']else 1)
