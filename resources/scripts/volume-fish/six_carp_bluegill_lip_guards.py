"""Measure current texture transport, without relabeling historical native-lip authoring."""
import sys,json,hashlib,io
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays
base=ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def image(d,b):
 q=d['bufferViews'][d['images'][0]['bufferView']];return np.array(Image.open(io.BytesIO(b[q.get('byteOffset',0):q.get('byteOffset',0)+q['byteLength']])).convert('RGBA'))
for s,old,new in [('carp',ROOT/'projects/fishing-2d/experiments/carp-lowpoly-sop-20261031/generated-underside-material-20261101/final/fish.glb',base/'carp/width-r4/fish.glb'),('bluegill',base/'bluegill/width-r3/fish.glb',base/'bluegill/width-r4/fish.glb')]:
 a,ab=read_glb(old);b,bb=read_glb(new);ap=a['meshes'][0]['primitives'][0];bp=b['meshes'][0]['primitives'][0];checks={key:np.array_equal(arrays(a,ab,ap['attributes'][key]),arrays(b,bb,bp['attributes'][key]))for key in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0']};checks['indices']=np.array_equal(arrays(a,ab,ap['indices']),arrays(b,bb,bp['indices']));checks['part_identity']=a['extras']['geometry_parts']==b['extras']['geometry_parts'];assert all(checks.values());aa=image(a,ab);ba=image(b,bb);assert aa.shape==ba.shape;changed=np.any(aa!=ba,axis=2)
 if s=='carp':
  assert not changed.any();extra={'all_actual_RGBA_exact':True,'native_lip_ownership_original_report':{'path':str(ROOT/'projects/fishing-2d/experiments/carp-lowpoly-sop-20261031/head-material-r5/authoring.validation.json'),'sha256':sha(ROOT/'projects/fishing-2d/experiments/carp-lowpoly-sop-20261031/head-material-r5/authoring.validation.json')},'scope':'Only preservation of previously baked complete native lip UV/pixels/part ownership is proven. Historical native chart retains original model SHA and author report; this does not assert current geometry unchanged. Current oral geometry is independently measured by mouth-opening-r4 and current visual review.'}
 else:
  bake=base/'bluegill/native-lips-r1/material.validation.json';r=json.loads(bake.read_text());allowed=np.zeros(changed.shape,bool)
  for q in r['actual_native_donors']:x,y=q['atlas_xy'];allowed[y,x]=True
  assert not np.any(changed&~allowed);assert np.array_equal(aa[:,:,3],ba[:,:,3]);extra={'changed_pixels':int(changed.sum()),'allowed_own_lip_texels':int(allowed.sum()),'changed_pixels_outside_declared_lip':0,'alpha_exact':True,'bake':{'path':str(bake),'sha256':sha(bake)},'scope':'Every changed RGBA pixel is inside the exact actually sampled own native lip band; body outside it, alpha and all static non-material arrays are unchanged from pectoral fit r3.'}
 report={'ok':True,'kind':'actual_native_lip_texture_transport_guard','species':s,'baseline_model':{'path':str(old),'sha256':sha(old)},'model_sha256':sha(new),'checks':checks,**extra};(base/s/'lip-transport.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(s,True)
