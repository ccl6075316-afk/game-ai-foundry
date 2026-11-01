"""Restore byte-identical reviewed PNGs embedded in the existing source GLBs.

No new generation/approval is created. Historical source-review and exact image
hash must both match; derived texture atlases are labelled separately.
"""
import argparse,hashlib,io,json
from pathlib import Path
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['plan','game','models-root','output']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);rows=[]
    for item in json.loads(a.plan.read_text())['items']:
        s=item['species'];model=a.game/f'assets/models/fish/{s}.glb';assert sha(model)==item['profile']['source_model_sha256']
        d,b=read_glb(model);images=[]
        for im in d.get('images',[]):
            v=d['bufferViews'][im['bufferView']];raw=b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
            images.append({'name':im.get('name',''),'raw':raw,'sha256':hashlib.sha256(raw).hexdigest()})
        assert images
        matches=[]
        for handoff in (a.models_root/s).glob('*handoff.json'):
            h=json.loads(handoff.read_text())
            if h.get('source_review',{}).get('status')=='accepted' and h.get('source',{}).get('sha256')==images[0]['sha256']:matches.append((handoff,h))
        assert matches,'No exact historical reviewed-source binding: '+s
        handoff,h=matches[-1];out=a.output/s;out.mkdir(parents=True,exist_ok=True);retained=[]
        for i,im in enumerate(images):
            role='source-original' if i==0 else 'front-original' if h.get('front_source',{}).get('sha256')==im['sha256'] and h.get('front_source_review',{}).get('status')=='accepted' else f'derived-baseline-{i}'
            target=out/(role+'.png');target.write_bytes(im['raw']);assert sha(target)==im['sha256']
            size=Image.open(io.BytesIO(im['raw'])).size
            retained.append({'role':role,'path':str(target),'sha256':im['sha256'],'native_size':size,'image_name':im['name']})
        row={'species':s,'ok':True,'source_model_sha256':sha(model),'historical_handoff':str(handoff),'historical_handoff_sha256':sha(handoff),'historical_source_review':h['source_review'],'source_png_restored_byte_identically':True,'images':retained,'scope':'Existing reviewed source PNG restored from unchanged embedded bytes; no regeneration, no new source or whole-fish acceptance.'}
        (out/'provenance.validation.json').write_text(json.dumps(row,ensure_ascii=False,indent=2));rows.append(row)
    result={'ok':len(rows)==len(json.loads(a.plan.read_text())['items']),'records':rows,'checker_sha256':sha(__file__)};(a.output/'completion.validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'ok':result['ok'],'fish':len(rows)}))
if __name__=='__main__':main()
