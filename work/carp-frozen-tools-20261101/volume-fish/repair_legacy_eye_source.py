"""Continue native two-dimensional skin cells beneath a preserved real eye.

This is a texture-coordinate operation, not new artwork. Original image/alpha
and the independent real eye remain intact. The donor rectangle excludes eye,
gill markings and outline; its full vertical gradient is kept without tiling Y.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);a=p.parse_args();cfg=json.loads(a.plan.read_text())
    for path,h in cfg['frozen_inputs'].items():assert sha(path)==h
    source=np.asarray(Image.open(cfg['source']).convert('RGBA'));opaque=np.asarray(Image.open(cfg['opaque']).convert('RGBA'));assert source.shape==opaque.shape
    yy,xx=np.indices(source.shape[:2]);cx,cy=cfg['center_px'];rx,ry=cfg['radius_px'];mask=((xx-cx)/rx)**2+((yy-cy)/ry)**2<=1
    x0,y0,x1,y1=cfg['donor_rect'];assert x1>x0 and y1>y0
    assert yy[mask].min()>=y0 and yy[mask].max()<y1,'Donor must cover complete original vertical gradient'
    donor_x=x0+np.minimum((xx-x0)%(2*(x1-x0)),2*(x1-x0)-1-(xx-x0)%(2*(x1-x0)))
    dy=yy[mask];dx=donor_x[mask];assert np.all(source[dy,dx,3]==255)
    # The mask and donor domain are separate: never copy the eye into itself.
    assert not mask[dy,dx].any()
    clean=source.copy();clean_opaque=opaque.copy();clean[mask,:3]=source[dy,dx,:3];clean_opaque[mask,:3]=source[dy,dx,:3]
    assert np.array_equal(clean[:,:,3],source[:,:,3]) and np.array_equal(clean[~mask],source[~mask]);assert np.all(clean_opaque[:,:,3]==255)
    out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=True)
    Image.fromarray(clean).save(out/'source.png');Image.fromarray(clean_opaque).save(out/'opaque.png')
    np.savez_compressed(out/'donors.npz',destination_y=yy[mask],destination_x=xx[mask],source_y=dy,source_x=dx)
    result={'ok':True,'plan_sha256':sha(a.plan),'mask_pixels':int(mask.sum()),'outside_mask_rgba_unchanged':True,'all_source_alpha_unchanged':True,'opaque_alpha_255':True,'vertical_gradient_preserved':True,'outputs':{name:sha(out/name) for name in ['source.png','opaque.png','donors.npz']},'scope':'Underlying source eye footprint only. Actual eye mesh/material is preserved. Native source cells and vertical gradient, not generic forehead fill; visual/body/runtime gates required.'}
    (out/'source.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
