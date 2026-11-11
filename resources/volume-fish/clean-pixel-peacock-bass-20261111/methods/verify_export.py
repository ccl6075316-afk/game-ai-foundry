"""Assert all source-cold active streams and material bindings match the baseline."""
from pathlib import Path
import json,sys
import numpy as np
from bake import ROOT,W,BASE,read_glb,arrays,sha,png,save
def verify(first,second):
    a,ab=read_glb(first);b,bb=read_glb(second)
    for key in ['asset','extensionsUsed','nodes','materials','textures','samplers','scene','scenes']:
        assert a.get(key)==b.get(key),key
    refs=set()
    def same(label,i,j):
        x=arrays(a,ab,i);y=arrays(b,bb,j)
        assert x.dtype==y.dtype and x.shape==y.shape and x.tobytes()==y.tobytes(),label
        refs.add((i,j))
    parts=[]
    for x,y in zip(a['meshes'],b['meshes'],strict=True):
        assert x['name']==y['name']
        for k,(p,q) in enumerate(zip(x['primitives'],y['primitives'],strict=True)):
            name=(x['name'],k)
            assert p.keys()==q.keys() and p['material']==q['material']
            assert set(p['attributes'])==set(q['attributes'])
            for key in p['attributes']:
                same((name,key),p['attributes'][key],q['attributes'][key])
            same((name,'indices'),p['indices'],q['indices'])
            parts.append({'part':name,'triangles':a['accessors'][p['indices']]['count']//3})
    for x,y in zip(a['skins'],b['skins'],strict=True):
        assert {k:v for k,v in x.items() if k!='inverseBindMatrices'}=={k:v for k,v in y.items() if k!='inverseBindMatrices'}
        same('skin inverse binds',x['inverseBindMatrices'],y['inverseBindMatrices'])
    for x,y in zip(a['animations'],b['animations'],strict=True):
        assert x['name']==y['name'] and x['channels']==y['channels']
        for p,q in zip(x['samplers'],y['samplers'],strict=True):
            assert p['interpolation']==q['interpolation']
            for k in ['input','output']:
                same(('native animation',k),p[k],q[k])
    images=[]
    for i,_ in enumerate(zip(a['images'],b['images'],strict=True)):
        im=png(a,ab,i);candidate=png(b,bb,i)
        assert im.shape==candidate.shape and np.array_equal(im[:,:,3],candidate[:,:,3]),i
        images.append({'index':i,'size':list(im.shape[:2][::-1]),'changed_RGB':int(np.any(im[:,:,:3]!=candidate[:,:,:3],axis=2).sum()),'RGBA_equal':np.array_equal(im,candidate)})
    return dict(ok=True,first_model_sha256=sha(first),second_model_sha256=sha(second),active_exact_accessors=len(refs),all_nonimage_active_streams_exact=True,part_and_surface_order_exact=True,triangles=sum(p['triangles'] for p in parts),bones=len(b['skins'][0]['joints']),parts=parts,images=images)
if __name__=='__main__':
    out=Path(sys.argv[1])
    assert sha(out/'fish.glb')==sha(out/'cold-fish.glb')
    final=out/'cold-fish.glb'
    receipt=verify(BASE,final)
    preview=verify(W/'fins-r2/fish.glb',final)
    assert all(row['RGBA_equal'] for row in preview['images'])
    save(out/'preservation.validation.json',receipt|{'warm_and_fresh_cold_file_exact':True,'image_only_bake_RGBA_exact':True,'scope':'Unchanged actual nonimage primitive streams, indices, rest/binds, materials, sampling, animations and image alpha. All new baked RGB embedded through source; no mesh packing or runtime construction.'})
