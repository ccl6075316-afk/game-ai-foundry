"""Prepare a hash-bound list from explicit viewer-only existing final specs."""
import argparse,json
from pathlib import Path
from view import prepare,sha256
from fish_asset_spec import ROOT,artifact_output

def build(recipe,output):
    data=json.loads(recipe.read_text(encoding='utf8'));out=artifact_output(output,[recipe]);assert not out.exists();out.mkdir(parents=True)
    entries=[];bindings={str(recipe.resolve()):sha256(recipe)}
    for entry in data['entries']:
        spec=(ROOT/entry['spec']).resolve();config=prepare(spec)
        if config['controller']:
            motion=json.loads(Path(config['controller']['profile']).read_text(encoding='utf8'))
            assert float(entry['length_cm'])==float(motion['real_length_cm']),'Displayed length must match this actual motion/source profile'
        entries.append({**entry,'viewer':config})
        for path in config['input_paths']:bindings[path]=sha256(path)
    for filename in ['FishListViewer.gd','FishAssetViewer.gd']:
        path=Path(__file__).with_name(filename).resolve();bindings[str(path)]=sha256(path)
    catalog={'kind':'existing_fish_review_list','entries':entries,'bindings':bindings,'mode':'smoke','output':str(out/'smoke')}
    (out/'catalog-smoke.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    catalog.update(mode='interactive',output=str(out/'interactive'));(out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'manifest.json').write_text(json.dumps({'ok':True,'status':'pending','next_action':'run','scope':'Read-only review list; existing models/specs/motion remain unchanged.','models':{entry['id']:entry['viewer']['model_sha256']for entry in entries}},indent=2)+'\n',encoding='utf8')
    return len(entries)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps({'ok':True,'entries':build(a.recipe,a.output)}))
