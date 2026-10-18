"""Derive opaque body texel donors and audit full body shells. No source/mesh edits."""
import sys,json,hashlib,io,argparse
from pathlib import Path
from collections import Counter
import numpy as np,cv2
from PIL import Image
parser=argparse.ArgumentParser(description="Freeze derived opaque body donors and audit welded body shells; preserve source and GLB bytes.")
parser.add_argument('--models',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--topology-report',type=Path,required=True);args=parser.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parent));from freeze_surface_ownership import read_glb,accessor
head_parameters=json.loads((Path(__file__).resolve().parents[2]/"volume-fish/head-surfaces-080.json").read_text())["profiles"]
models=args.models.resolve();out=args.output.parent/'opaque-skin';out.mkdir(parents=True,exist_ok=True);ownership=json.loads((models/'motion/surface-ownership.json').read_text());records={};topology=[];generated=set()
for path in models.glob('*.glb'):
 head=head_parameters.get(path.stem,{})
 if head:assert head['model_sha256']==hashlib.sha256(path.read_bytes()).hexdigest(),'Stale head surface contract'
 d,b=read_glb(path);fin=ownership['profiles'][path.stem]['fins'];surfaces={};suppressed=[]
 for node in d['nodes']:
  if 'mesh' not in node or node['name'] in fin:continue
  if node['name'] in head.get('decorative_overlays',{}):continue
  primitives=d['meshes'][node['mesh']]['primitives']
  if node['name'].startswith('Textured_eye') and all(d['materials'][p['material']].get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1])[3]==0 for p in primitives):
   suppressed.append(node['name']);continue
  edges=Counter()
  for si,prim in enumerate(d['meshes'][node['mesh']]['primitives']):
   pos=accessor(d,b,prim['attributes']['POSITION']);tri=accessor(d,b,prim['indices']).reshape(-1,3);weld=[tuple(round(float(x),7) for x in p) for p in pos]
   for face in tri:
    p=[weld[x] for x in face]
    for a,z in zip(p,p[1:]+p[:1]):edges[tuple(sorted([a,z]))]+=1
   mat=d['materials'][prim['material']];tex=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture')
   if tex is None:continue
   img=d['images'][d['textures'][tex['index']]['source']];v=d['bufferViews'][img['bufferView']];raw=b[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']];key=hashlib.sha256(raw).hexdigest();fn=out/(key+'.png')
   a=np.array(Image.open(io.BytesIO(raw)).convert('RGBA'));missing=a[:,:,3]<243
   if key not in generated:
    assert np.any(~missing),'No opaque texel donor'
    if missing.any():
     _,labels=cv2.distanceTransformWithLabels(missing.astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL);palette=a[~missing];a[missing]=palette[labels[missing]-1]
    a[:,:,3]=255;Image.fromarray(a).save(fn)
    generated.add(key)
   surfaces.setdefault(node['name'],{})[str(si)]={'texture':'res://assets/models/fish/motion/opaque-skin/'+fn.name,'source_image_sha256':key,'texture_sha256':hashlib.sha256(fn.read_bytes()).hexdigest(),'source_alpha_missing_pixels':int(missing.sum())}
  topology.append({'species':path.stem,'mesh':node['name'],'boundary_edges':sum(v==1 for v in edges.values()),'nonmanifold_edges':sum(v>2 for v in edges.values()),'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 records[path.stem]={'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'surfaces':surfaces,'suppressed_auxiliary':suppressed,'decorative_overlays':head.get('decorative_overlays',{}),'head_projection':head.get('head_projection',{})}
args.output.write_text(json.dumps({'schema_version':1,'method':'Nearest opaque source texel extension only where original alpha is below243/255; body uses opaque render pipeline. Source pixels and models unchanged.','profiles':records},indent=2))
args.topology_report.parent.mkdir(parents=True,exist_ok=True);args.topology_report.write_text(json.dumps({'ok':bool(topology) and all(not x['boundary_edges'] and not x['nonmanifold_edges'] for x in topology),'meshes':topology},indent=2));print(json.dumps([t for t in topology if t['boundary_edges'] or t['nonmanifold_edges']],indent=2));print('BODY_TEXTURES',len(list(out.glob('*.png'))));sys.exit(0 if topology and all(not x['boundary_edges'] and not x['nonmanifold_edges'] for x in topology) else 1)
