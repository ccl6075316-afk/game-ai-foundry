"""Prove an upper-side edit preserves XY, donors and every non-body part."""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def images(doc,blob):
 return[hashlib.sha256(blob[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]).hexdigest()for i in doc['images']for v in[doc['bufferViews'][i['bufferView']]]]
def compare(previous,current,body):
 d,a=read_glb(previous);q,b=read_glb(current);assert images(d,a)==images(q,b)and d['materials']==q['materials'];parts=[]
 for node in d['nodes']:
  if'mesh'not in node:continue
  other=next(n for n in q['nodes']if n.get('name')==node['name']);old=d['meshes'][node['mesh']]['primitives'];new=q['meshes'][other['mesh']]['primitives'];assert len(old)==len(new)
  for x,y in zip(old,new):
   # SCALAR accessor readers may retain the singleton component dimension.
   ix=arrays(d,a,x['indices']).reshape(-1);iy=arrays(q,b,y['indices']).reshape(-1);assert len(ix)==len(iy)
   if node['name']==body:
    P=arrays(d,a,x['attributes']['POSITION'])[ix];Q=arrays(q,b,y['attributes']['POSITION'])[iy]
    assert np.array_equal(P[:,[0,2]],Q[:,[0,2]]),'Body longitudinal/transverse coordinates changed'
    for key in ['TEXCOORD_0','JOINTS_0','WEIGHTS_0']:assert np.array_equal(arrays(d,a,x['attributes'][key])[ix],arrays(q,b,y['attributes'][key])[iy]),key
   else:
    assert x['attributes'].keys()==y['attributes'].keys()
    for key in x['attributes']:assert np.array_equal(arrays(d,a,x['attributes'][key]),arrays(q,b,y['attributes'][key])),(node['name'],key)
    assert np.array_equal(ix,iy)
  if node['name']!=body:parts.append(node['name'])
 return dict(ok=True,kind='side_only_static_scope_preservation',baseline_sha256=sha(previous),model_sha256=sha(current),all_body_expanded_triangle_XY_exact=True,body_expanded_UV_weights_joints_exact=True,all_embedded_image_payloads_exact=True,all_material_bindings_exact=True,all_non_body_attributes_and_indices_exact=parts,checker_sha256=sha(Path(__file__)),scope='Body vertical positions and associated normals may change. Every longitudinal/transverse coordinate, expanded UV/skin binding, embedded donor and complete non-body part is compared on actual exports. Mouth/source rig protection has separate actual author/probe evidence. Not user acceptance.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--current',type=Path,required=True);p.add_argument('--body',default='Reference_head_body');p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=compare(a.previous,a.current,a.body);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=True,unchanged_parts=len(r['all_non_body_attributes_and_indices_exact']))))
