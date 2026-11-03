"""Evaluate actual packed wall/cap atlas alpha at four barycentric probes."""
import sys,json,hashlib,io
from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'resources/scripts/volume-fish/portable'));from glb_io import read_glb
S=sys.argv[1];assert S in['red_seabream','black_seabream'];D=R/'projects/fishing-2d/plans/reviews/six-fish-release-20261104'/S;p=D/'wall-source-probes.json';d=json.loads(p.read_text());model=R/f'projects/fishing-2d/game/assets/models/fish/{S}.glb';g,b=read_glb(model);v=g['bufferViews'][g['images'][0]['bufferView']];im=np.array(Image.open(io.BytesIO(b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']])).convert('RGBA'));h,w=im.shape[:2];weights=np.array([[1/3]*3,[.6,.2,.2],[.2,.6,.2],[.2,.2,.6]]);rows=[]
for f in d['fins']:
 mismatch=[];maxdelta=0;ambiguous=0
 for wall in f['walls']:
  au=weights@np.array(wall['actual_uv']);cu=weights@np.array(wall['cap_uv']);maxdelta=max(maxdelta,float(abs(au-cu).max()));a=np.clip(np.floor(au*[w,h]).astype(int),[0,0],[w-1,h-1]);c=np.clip(np.floor(cu*[w,h]).astype(int),[0,0],[w-1,h-1]);aa=im[a[:,1],a[:,0],3];ca=im[c[:,1],c[:,0],3]
  # Preserve exact-alpha discrepancies rather than claiming equality at a texel
  # boundary. One source FLOAT32 ULP can straddle floor() while sharing the same
  # native edge; count those explicitly apart from an opaque inset wall.
  corner_rounding=bool(np.all(abs(np.array(wall['actual_uv'])-np.array(wall['cap_uv']))<=np.abs(np.spacing(np.array(wall['cap_uv'],dtype=np.float32))).astype(float)))
  for i in np.where((aa>=128)&(ca<128))[0]:
   edge=corner_rounding and bool(np.all(abs(a[i]-c[i])<=1));ambiguous+=int(edge);mismatch.append({'triangle':wall['polygon'],'actual_xy':a[i].tolist(),'cap_xy':c[i].tolist(),'actual_alpha':int(aa[i]),'cap_alpha':int(ca[i]),'within_one_FLOAT32_ULP_corner_and_one_pixel_boundary':edge})
 rows.append({'name':f['name'],'wall_triangles':f['closing_wall_triangles'],'probes':4*f['closing_wall_triangles'],'maximum_wall_vs_native_cap_UV_delta':maxdelta,'opaque_wall_over_transparent_native_cap_count':len(mismatch),'FLOAT32_boundary_ambiguous_count':ambiguous,'non_boundary_inset_mismatch_count':len(mismatch)-ambiguous,'examples':mismatch[:3]})
out={'ok':all(x['non_boundary_inset_mismatch_count']==0 for x in rows),'kind':'seven_fin_source_domain_wall_alpha_audit','model':str(model),'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'anatomical_domain_report':str(p),'anatomical_domain_report_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fins':rows,'scope':'Four barycentric probes per source-u/v-zero-area wall triangle, actual unchanged embedded atlas alpha. All exact alpha discrepancies remain counted; machine-precision texel-boundary ambiguity is separately explicit, not alpha equality or continuous certification. No texture/alpha threshold is modified. Actual isolated-fin review determines visible wire removal.'};(D/'wall-alpha-current.validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'ok':out['ok'],'species':S,'fins':len(rows),'probes':sum(x['probes']for x in rows),'mismatches':sum(x['opaque_wall_over_transparent_native_cap_count']for x in rows),'boundary_ambiguous':sum(x['FLOAT32_boundary_ambiguous_count']for x in rows)}))
