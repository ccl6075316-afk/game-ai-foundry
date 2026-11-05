"""Verify a fin-material edit preserves all actual geometry and body donors."""
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def image_hash(doc,blob,primitive):
 m=doc['materials'][primitive['material']];t=m.get('pbrMetallicRoughness',{}).get('baseColorTexture')
 if not t:return None
 i=doc['textures'][t['index']]['source'];v=doc['bufferViews'][doc['images'][i]['bufferView']];return hashlib.sha256(blob[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]).hexdigest()
def compare(previous,current):
 d,a=read_glb(previous);q,b=read_glb(current);rows=[];donors=[]
 for n in d['nodes']:
  if'mesh'not in n:continue
  o=next(x for x in q['nodes']if x.get('name')==n['name']);old=d['meshes'][n['mesh']]['primitives'];new=q['meshes'][o['mesh']]['primitives'];assert len(old)==len(new);protected=n['name']=='Reference_head_body'or n['name'].startswith('Eye_');normal_delta=0.
  for p,r in zip(old,new):
   ix=arrays(d,a,p['indices']).reshape(-1);iy=arrays(q,b,r['indices']).reshape(-1);assert len(ix)==len(iy)
   for key in ['POSITION','JOINTS_0','WEIGHTS_0']:
    assert np.array_equal(arrays(d,a,p['attributes'][key])[ix],arrays(q,b,r['attributes'][key])[iy]),(n['name'],key)
   nx=arrays(d,a,p['attributes']['NORMAL'])[ix];ny=arrays(q,b,r['attributes']['NORMAL'])[iy];normal_delta=max(normal_delta,float(abs(nx-ny).max()))
   if n['name']!='Caudal':assert np.array_equal(nx,ny),(n['name'],'normal changed outside tail')
   if protected:
    assert np.array_equal(arrays(d,a,p['attributes']['TEXCOORD_0'])[ix],arrays(q,b,r['attributes']['TEXCOORD_0'])[iy])
    assert image_hash(d,a,p)==image_hash(q,b,r);donors.append(dict(mesh=n['name'],sha256=image_hash(d,a,p)))
  rows.append(dict(mesh=n['name'],expanded_positions_skin_and_triangle_count_exact=True,body_eye_UV_and_image_exact=protected,maximum_exported_normal_component_change=normal_delta))
 return dict(ok=True,kind='fin_material_only_actual_export_scope',baseline_sha256=sha(previous),model_sha256=sha(current),all_mesh_positions_and_skin_exact=True,body_and_eye_UV_normal_and_donors_exact=True,body_eye_donors=donors,meshes=rows,checker_sha256=sha(Path(__file__)),scope='All actual expanded positions, triangle counts and skin bindings exact. Body/eye UV, normals and embedded donor payloads exact. Only fin UV/materials and declared caudal shading normals may change. Not whole-fish acceptance.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--current',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=compare(a.previous,a.current);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(ok=True,meshes=len(r['meshes']))))
