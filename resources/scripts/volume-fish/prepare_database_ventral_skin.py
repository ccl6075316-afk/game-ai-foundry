"""Prepare inspected, own-fish ventral tissue and geometric protection parameters."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main(a):
    out=a.directory.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments/five-fish-database-20261103');assert out.name==a.species
    old=json.loads((ROOT/f'output/five-fish-database-20261103/restored/{a.species}/frozen/spec-sop-review.json').read_text(encoding='utf8'));source=Path(old['candidate_files']['source_image']['path']);W,H=Image.open(source).size;author=Path(old['evidence']['mouth.complete_native_lip_domain_and_front_exclusion']['path']);domain=json.loads(author.read_text())['complete_native_lip_ownership']['domain'];plan=json.loads((out/'width-r1/deformation.plan.json').read_text());gain=plan['gain_range'][1]
    generated=a.source.resolve();im=Image.open(generated).convert('RGBA');roi=im.crop(tuple(a.roi));pixels=np.array(roi);assert pixels[:,:,3].min()>=.95*255;target=out/'ventral-native-roi.png';assert not target.exists();roi.convert('RGB').save(target);palette=pixels[:,:,:3].mean((0,1)).round().astype(int).tolist()
    quilt={'native_material':{'source':target.relative_to(ROOT).as_posix(),'source_sha256':sha(target),'roi_px':[0,0,roi.width,roi.height]},'plain_RGB':palette,'original_source':{'path':generated.relative_to(ROOT).as_posix(),'sha256':sha(generated),'roi_px':a.roi,'source_kind':'Previously generated same-fish body-skin RGB; not the original side-art RGB or a biological hidden-skin observation.','source_alpha_range':[int(pixels[:,:,3].min()),int(pixels[:,:,3].max())],'RGB_exact_crop':True,'opacity_scope':'Interior alpha >=.95; only RGB is adopted for an opaque-body donor.'}}
    (out/'ventral-quilt.config.json').write_text(json.dumps(quilt,indent=2)+'\n')
    protection=(max(domain['upper_width_px'],domain['lower_width_px'])+domain['outer_fade_px']+6)*gain/W
    (out/'ventral-protection.parameters.json').write_text(json.dumps({'species':a.species,'source_width':W,'original_lip_domain':domain,'maximum_transverse_gain':gain,'mouth_protection_native':protection,'formula':'(max(upper/lower native lip widths)+outer fade+6 source px)*maximum field gain/source width','window':a.window,'underside_fade':a.underside,'native_source_width':im.width,'source_image_size':[W,H]},indent=2)+'\n');print(json.dumps({'ok':True,'palette':palette,'mouth_protection_native':protection}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--species',required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--roi',type=int,nargs=4,required=True);p.add_argument('--window',type=float,nargs=4,required=True);p.add_argument('--underside',type=float,nargs=2,required=True);main(p.parse_args())
