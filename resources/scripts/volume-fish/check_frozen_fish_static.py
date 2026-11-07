"""Hash static mesh/material/rig data independently of changeable animation clips."""
import argparse,json,hashlib
from pathlib import Path
from portable.glb_io import read_glb,arrays

def fingerprint(model):
 d,b=read_glb(Path(model));geometry=hashlib.sha256();material=hashlib.sha256()
 for mesh in d['meshes']:
  for p in mesh['primitives']:
   for k in ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']:
    geometry.update(k.encode())
    # Constant oral/eye materials can legitimately omit UVs. Hash absence
    # explicitly; all geometric and skin attributes remain mandatory.
    if k=='TEXCOORD_0' and k not in p['attributes']:geometry.update(b'absent')
    else:geometry.update(arrays(d,b,p['attributes'][k]).tobytes())
   geometry.update(arrays(d,b,p['indices']).tobytes())
 material.update(json.dumps(d['materials'],sort_keys=True).encode())
 for im in d['images']:
  iv=d['bufferViews'][im['bufferView']];material.update(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])
 rig=hashlib.sha256(json.dumps(d['nodes'],sort_keys=True).encode())
 for skin in d['skins']:
  rig.update(json.dumps(skin['joints']).encode());rig.update(arrays(d,b,skin['inverseBindMatrices']).tobytes())
 return {'geometry_uv_skin_sha256':geometry.hexdigest(),'material_pixels_sha256':material.hexdigest(),'skeleton_rest_bind_sha256':rig.hexdigest(),'triangles':sum(d['accessors'][p['indices']]['count']//3 for m in d['meshes']for p in m['primitives']),'bones':len(d['skins'][0]['joints'])}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--create',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();actual=fingerprint(a.model)
 if a.create:
  assert not a.freeze.exists(),'Never silently replace an accepted static freeze';a.freeze.parent.mkdir(parents=True,exist_ok=True);a.freeze.write_text(json.dumps({'kind':'accepted_fish_static_freeze','static':actual,'future_scope':'Animation/controller motion only by default; changing any static data requires explicit user reopening and relevant production verification.'},indent=2)+'\n',encoding='utf8')
 expected=json.loads(a.freeze.read_text(encoding='utf8'))['static'];result={'ok':actual==expected,'kind':'frozen_fish_static_check','actual':actual,'expected':expected,'animation_data_excluded':True}
 if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(result));return 0 if result['ok']else 1
if __name__=='__main__':raise SystemExit(main())
