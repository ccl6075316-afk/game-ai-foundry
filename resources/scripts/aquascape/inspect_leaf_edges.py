"""Read-only inspection of source silhouettes and actual embedded leaf paint."""
import sys,io,json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from build_from_art import split_leaves,foreground
from rig_plant_current import read_glb
root=Path(__file__).resolve().parents[3]
catalog=json.loads((root/'projects/fishing-2d/game/assets/aquascape-v5/catalog.json').read_text(encoding='utf-8'))
for row in catalog['assets']:
    if not row['animated']:continue
    id=row['id']
    src=(root/'projects/aquascape-anubias-v2-leaves/output/anubias_leaves_nobg.png' if id=='anubias' else root/'projects/aquascape-fern-v2-leaves/output/fern_leaves_nobg.png' if id=='java_fern' else root/f'projects/fishing-2d/plans/reviews/aquascape-catalog-v5/sources/{id}/{id}-leaves.png')
    leaves=split_leaves(src);doc,binary=read_glb(root/'projects/fishing-2d/game'/row['model'].removeprefix('res://'))
    results=[]
    for i,leaf in enumerate(leaves):
        im=doc['images'][i];v=doc['bufferViews'][im['bufferView']];a=np.array(Image.open(io.BytesIO(binary[v['byteOffset']:v['byteOffset']+v['byteLength']])).convert('RGB'))
        mask=foreground(leaf);distance=ndi.distance_transform_edt(np.pad(mask,1))[1:-1,1:-1]
        band=mask&(distance<=3)
        white=(a.min(2)>=175)&(np.ptp(a.astype(float),axis=2)<70)
        results.append({'leaf':i+1,'edge_white':int((band&white).sum()),'interior_white':int((white&(distance>3)).sum()),'edge_pixels':int(band.sum())})
    print(json.dumps({'id':id,'leaves':results}))
