"""Extend local native fin tissue into an explicitly bounded free-edge ink band.

This is a material donor operation. Alpha, silhouettes, UVs and geometry stay
unchanged. Root domains and every pixel outside the declared band are protected.
"""
import argparse, hashlib, io, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from glb_io import read_glb

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf8'))
def ref(p): return (ROOT / p).resolve()

def line_distance(x, y, line):
    result = np.full(x.shape, np.inf)
    for a, b in zip(line[:-1], line[1:]):
        a, b = np.asarray(a), np.asarray(b)
        v = b-a
        t = np.clip(((x-a[0])*v[0]+(y-a[1])*v[1])/max(float(v@v), 1e-9), 0, 1)
        result = np.minimum(result, np.hypot(x-a[0]-t*v[0], y-a[1]-t*v[1]))
    return result

def run(config, output):
    c = read(config); output = output.resolve()
    assert output.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not output.exists()
    model, packing, domains = [ref(c[k]) for k in ('model','packing','domains')]
    for k,p in [('model',model),('packing',packing),('domains',domains)]: assert sha(p)==c[k+'_sha256']
    d,b = read_glb(model); bv = d['bufferViews'][d['images'][0]['bufferView']]
    atlas = np.array(Image.open(io.BytesIO(b[bv.get('byteOffset',0):bv.get('byteOffset',0)+bv['byteLength']])).convert('RGBA'))
    original = atlas.copy(); changed = np.zeros(atlas.shape[:2],bool)
    rows = read(domains)['fins']; layout = read(packing)['parts']; output.mkdir(parents=True)
    records=[]; all_donors={}
    for f in rows:
        image=Path(f['image']); assert sha(image)==f['image_sha256']
        rgba=np.array(Image.open(image).convert('RGBA')); h,w=rgba.shape[:2]
        solid=rgba[:,:,3]>=128
        depth=distance_transform_edt(np.pad(solid,1))[1:-1,1:-1]
        yy,xx=np.mgrid[:h,:w]; root=line_distance(xx,yy,f['root_px'])
        params=c['fins'][f['name']]
        protected=root<=f['root_band_px']+params['root_padding_px']
        band=(rgba[:,:,3]>0)&(depth<=params['edge_band_px'])&~protected
        safe=solid&(depth>=params['donor_depth_px'])&~protected
        assert band.any() and safe.any()
        _,near=distance_transform_edt(~safe,return_indices=True)
        sy,sx=near[:,band]; ty,tx=np.where(band)
        fixed=rgba.copy(); fixed[ty,tx,:3]=rgba[sy,sx,:3]
        assert np.array_equal(fixed[:,:,3],rgba[:,:,3]) and np.array_equal(fixed[~band],rgba[~band])
        Image.fromarray(rgba).save(output/(f['name']+'-before.png'))
        Image.fromarray(fixed).save(output/(f['name']+'-after.png'))
        mask=np.zeros((h,w,4),np.uint8); mask[band]=[255,70,100,255]; Image.fromarray(mask).save(output/(f['name']+'-modified-band.png'))
        all_donors[f['name']+'_target_xy']=np.c_[tx,ty]; all_donors[f['name']+'_donor_xy']=np.c_[sx,sy]
        placements=[]
        for p in layout:
            if p['node'].removesuffix('_mesh').removesuffix('_left').removesuffix('_right')!=f['name']: continue
            ax,ay=p['atlas_placement']; ox,oy=p['virtual_crop_origin']; tw,th=p['virtual_crop_size']
            xs=np.clip(np.arange(ox,ox+tw),0,w-1); ys=np.clip(np.arange(oy,oy+th),0,h-1)
            old=rgba[ys[:,None],xs[None,:]]; new=fixed[ys[:,None],xs[None,:]]
            assert np.array_equal(original[ay:ay+th,ax:ax+tw],old),(p['node'],'atlas/source mismatch')
            atlas[ay:ay+th,ax:ax+tw]=new; changed[ay:ay+th,ax:ax+tw]|=band[ys[:,None],xs[None,:]]
            placements.append(p['node'])
        assert placements
        records.append({'name':f['name'],'parameters':params,'protected_root_band_px':f['root_band_px'],'source_sha256':sha(image),'changed_RGB_pixels':int(np.any(fixed[:,:,:3]!=rgba[:,:,:3],axis=2).sum()),'bounded_band_pixels':len(tx),'alpha_exact':True,'root_pixels_exact':True,'interior_pixels_exact':True,'atlas_parts':placements,'maximum_donor_distance_px':float(np.hypot(sx-tx,sy-ty).max())})
    assert np.array_equal(atlas[:,:,3],original[:,:,3])
    assert np.array_equal(atlas[~changed],original[~changed])
    assert sum(len(r['atlas_parts'])for r in records)==c['expected_fin_count']
    Image.fromarray(atlas).save(output/'atlas.png'); np.savez_compressed(output/'native-donor-addresses.npz',**all_donors)
    report={'ok':True,'kind':'bounded_native_fin_edge_material_repair','species':c['species'],'config_sha256':sha(config),'baseline_model_sha256':sha(model),'original_atlas_RGBA_sha256':hashlib.sha256(original.tobytes()).hexdigest(),'atlas':str(output/'atlas.png'),'atlas_sha256':sha(output/'atlas.png'),'alpha_exact':True,'pixels_outside_declared_fin_edge_bands_exact':True,'body_mouth_eyes_barbels_pixels_exact':True,'fin_parts':c['expected_fin_count'],'fins':records,'scope':'Local same-fin native RGB donors replace the declared exterior ink/fringe band only. No synthesized anatomy, alpha erosion, global darkness filter or runtime repair. Visual review and frozen-source export remain required.'}
    (output/'edge-material.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'ok':True,'fins':len(records),'atlas_fin_parts':c['expected_fin_count'],'changed_RGB_pixels':sum(r['changed_RGB_pixels']for r in records)}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.config,a.output)
