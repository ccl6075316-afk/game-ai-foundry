"""Native cutout/geometry coverage and manifoldness, before costly posed gates."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from audit_fin_source141 import raster
from validate_mouth_body139 import closed
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--source',type=Path,required=True);a=p.parse_args();plan=json.loads(a.plan.read_text());out=Path(plan['output']);rows=[]
 try:
  data=json.loads((out/'fins.bound.json').read_text());roots=json.loads((out/'root-selection.json').read_text());source=np.asarray(Image.open(a.source).convert('RGBA'));h,w=source.shape[:2];assert [w,h]==plan['source_size'];defs={x['name']:x for x in plan['fins']}
  for f in data['fins']:
   name=f['name'];spec=defs[name];texture=Path(spec['texture']);assert sha(texture)==spec['texture_sha256'];image=np.asarray(Image.open(texture).convert('RGBA'));mask=np.asarray(Image.open(spec['source_mask']))>0;assert np.array_equal(image[:,:,:3],source[:,:,:3]),'Native source RGB changed';assert np.array_equal(image[:,:,3],np.where(mask,source[:,:,3],0)),'Cutout alpha differs from frozen source mask';shell=closed(f['parts']);coverage=np.zeros((h,w),bool)
   for part in f['parts']:
    uv=np.asarray(part['uv']);tri=np.asarray(part['triangles']).reshape(-1,3);coverage|=raster(uv*[w,h],tri,w,h);v=np.asarray(part['vertices']);ww=np.asarray(part['weights']);assert np.isfinite(v).all() and np.isfinite(ww).all() and ww.min()>=0 and max(abs(ww.sum(1)-1))<1e-6
   missing=int((mask&~coverage).sum());assert missing/max(mask.sum(),1)<.005,('Native fin cut off by geometry',name,missing);assert len(roots[name]['ids'])>1
   rows.append({'name':name,'ok':True,'closed_shell':shell,'native_source_pixels':int(mask.sum()),'pixels_not_covered_by_uv_geometry':missing,'geometry_only_padding_px':spec['geometry_only_padding_px'],'source_rgb_identical':True,'source_alpha_cut_only':True})
  result={'ok':len(rows)==len(defs),'plan_sha256':sha(a.plan),'geometry_sha256':sha(out/'fins.bound.json'),'source_sha256':sha(a.source),'records':rows,'scope':'Closed finite fin shells and original-RGB cutout geometry coverage. Annotation semantics, actual posed contact, body occlusion, spread and user judgment remain separate.'}
 except Exception as e:result={'ok':False,'error':str(e),'records':rows}
 (out/'source-build.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps({'ok':result['ok'],'fins':len(rows),'error':result.get('error')}));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
