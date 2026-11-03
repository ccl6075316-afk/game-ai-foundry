"""Reproduce accepted packed colors using only canonical retained source inputs.

No retired experiment paths, new donor choice, geometry or static game edits.
This preserves the actual accepted native-texel transport and chin quilt map.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--species',choices=['crucian','grass_carp'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();source=G/f'assets/source/fish/{a.species}';out=a.output.resolve();assert out.is_relative_to(ROOT/'output')and not out.exists();out.mkdir(parents=True);raw=json.loads((source/'native-lips/material.validation.json').read_text(encoding='utf8'));original=np.asarray(Image.open(source/'source.png').convert('RGBA'));image=np.array(Image.open(source/'source-atlas-before-native.png').convert('RGBA'));before=image.copy();protect=[]
for r in raw['actual_native_donors']:
 x,y=r['atlas_xy'];sx,sy=r['source_xy'];w=r['native_weight'];image[y,x,:3]=np.rint(before[y,x,:3]*(1-w)+original[sy,sx,:3]*w).astype('uint8');protect.append((x,y))
native=image.copy();c='chin-bake-r3'if a.species=='crucian'else'chin-bake-r1';sk='chin-skin-r3'if a.species=='crucian'else'chin-skin-r1';mapping=np.load(source/f'chin-material/{c}/actual-chin-donors.npz');skin=np.asarray(Image.open(source/f'chin-material/{sk}/skin.png').convert('RGBA'));assert len(mapping['atlas_xy'])==len(mapping['donor_xy_weight'])
for (x,y),(tx,ty,w)in zip(mapping['atlas_xy'],mapping['donor_xy_weight']):
 x,y,tx,ty=map(int,[x,y,tx,ty]);image[y,x,:3]=np.rint(native[y,x,:3]*(1-w)+skin[ty,tx,:3]*w).astype('uint8')
expected=np.asarray(Image.open(source/'atlas.png').convert('RGBA'));error=int(np.abs(image.astype(int)-expected.astype(int)).max());assert error==0;assert all(np.array_equal(image[y,x],native[y,x])for x,y in protect);Image.fromarray(image).save(out/'atlas.png');report={'ok':True,'kind':'canonical_input_material_reproduction','species':a.species,'retired_experiment_inputs_used':False,'maximum_RGBA_error_against_accepted':error,'complete_lip_and_fade_texels_protected':len(protect),'native_donor_texels':len(raw['actual_native_donors']),'chin_target_texels':len(mapping['atlas_xy']),'actual_inputs':{str(p):sha(p)for p in [source/'source.png',source/'source-atlas-before-native.png',source/'native-lips/material.validation.json',source/f'chin-material/{c}/actual-chin-donors.npz',source/f'chin-material/{sk}/skin.png',source/'atlas.png']},'scope':'Deterministic exact accepted RGB/alpha reconstruction from actual original source donor coordinates and native-density chin quilt/map. Canonical source/model not modified; not a new artistic variant.'};(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'species':a.species,'maximum_RGBA_error':error}))
