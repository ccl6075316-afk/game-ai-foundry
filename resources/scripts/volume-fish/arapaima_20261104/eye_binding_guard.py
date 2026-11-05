"""Verify closed nonrigid eye support from actual exported body triangles/skin."""
import json,hashlib
from pathlib import Path
import numpy as np
from glb_io import arrays

def verify(doc,blob,plan,node,definition):
 path=Path(definition['binding_report']);assert hashlib.sha256(path.read_bytes()).hexdigest()==definition['binding_report_sha256'];report=json.loads(path.read_text());assert report['ok']and report['kind']=='restored_body_supported_lowpoly_eye_lenses'and report['species']=='arapaima';source=next(e for e in report['eyes']if e['name']==node['name']);bindings=source['bindings'];assert len(bindings)==50 and source['vertices']==50 and source['triangles']==96
 body=next(n for n in doc['nodes']if n.get('name')==plan['body']and'mesh'in n);body_names=[doc['nodes'][j]['name']for j in doc['skins'][body['skin']]['joints']];by_position={};triangles=set()
 key=lambda p:tuple(np.rint(np.asarray(p,dtype=np.float64)*1e7).astype(np.int64))
 for pr in doc['meshes'][body['mesh']]['primitives']:
  p=arrays(doc,blob,pr['attributes']['POSITION']);p=np.column_stack([p[:,0],-p[:,2],p[:,1]]);js=arrays(doc,blob,pr['attributes']['JOINTS_0']);ws=arrays(doc,blob,pr['attributes']['WEIGHTS_0'])
  for co,j,w in zip(p,js,ws):
   weights={body_names[int(i)]:float(v)for i,v in zip(j,w)if v>1e-7};k=key(co)
   if k in by_position:assert set(weights)==set(by_position[k])and max(abs(weights[n]-by_position[k][n])for n in weights)<2e-5
   by_position[k]=weights
  for t in arrays(doc,blob,pr['indices']).reshape(-1,3):triangles.add(tuple(sorted(key(q)for q in p[t])))
 expected=[]
 for binding in bindings:
  tri=np.asarray(binding['body_triangle_positions_native']);bc=np.asarray(binding['barycentric']);assert tuple(sorted(key(q)for q in tri))in triangles,'Eye support triangle absent from actual exported body';assert bc.min()>-1e-5 and abs(bc.sum()-1)<1e-4
  # Blender's float32 barycentric_transform is renormalized exactly as the saved skin weights.
  bc=np.maximum(bc,0);bc/=bc.sum();support=bc@tri;assert np.linalg.norm(support-binding['support_native'])<2e-6;normal=np.asarray(binding['source_normal']);assert abs(np.linalg.norm(normal)-1)<1e-5;offset=binding['normal_offset_native'];assert -.00004<=offset<=source['old_peak_relief_native']+1e-7
  weights={}
  for q,gain in zip(tri,bc):
   for n,w in by_position[key(q)].items():weights[n]=weights.get(n,0)+max(0,gain)*w
  total=sum(weights.values());weights={n:w/total for n,w in weights.items()if w/total>1e-7};assert len(weights)<=4
  declared=binding['expected_named_weights'];assert set(weights)==set(declared)and max(abs(weights[n]-declared[n])for n in weights)<2e-5,'Authored eye weights do not equal actual body barycentric skin'
  expected.append((support+normal*offset,weights))
 eye_names=[doc['nodes'][j]['name']for j in doc['skins'][node['skin']]['joints']];seen=set();max_error=0
 for pr in doc['meshes'][node['mesh']]['primitives']:
  p=arrays(doc,blob,pr['attributes']['POSITION']);p=np.column_stack([p[:,0],-p[:,2],p[:,1]]);js=arrays(doc,blob,pr['attributes']['JOINTS_0']);ws=arrays(doc,blob,pr['attributes']['WEIGHTS_0'])
  for co,j,w in zip(p,js,ws):
   errors=[np.linalg.norm(co-q)for q,weights in expected];i=int(np.argmin(errors));assert errors[i]<2e-6;seen.add(i);max_error=max(max_error,float(errors[i]));actual={eye_names[int(k)]:float(v)for k,v in zip(j,w)if v>1e-7};weights=expected[i][1];assert set(actual)==set(weights)and max(abs(actual[n]-weights[n])for n in actual)<2e-5,'Exported eye weights differ from actual finite-body support'
 assert len(seen)==len(expected),'Incomplete actual eye binding inventory'
 return {'ok':True,'binding_vertices':len(seen),'maximum_position_error_native':max_error,'actual_body_barycentric_named_weights':True,'binding_report_sha256':definition['binding_report_sha256']}
