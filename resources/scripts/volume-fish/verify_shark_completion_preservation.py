"""Bind the earlier mouth-author report to the final fish's actual anterior skin."""
import sys,json,hashlib,collections
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb,arrays,sha

def triangles(doc,blob,name,min_x=None):
 node=next(n for n in doc['nodes']if n.get('name')==name and 'mesh'in n);result=[]
 for p in doc['meshes'][node['mesh']]['primitives']:
  attrs={k:arrays(doc,blob,v)for k,v in p['attributes'].items() if k in ['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0']}
  for t in arrays(doc,blob,p['indices']).reshape(-1,3):
   if min_x is not None and attrs['POSITION'][t,0].min()<=min_x:continue
   # An ordered per-corner tuple preserves UV, normal and skin seam ownership.
   corners=[tuple(np.rint(np.concatenate([attrs[k][i]for k in sorted(attrs)])*1e5).astype('int64'))for i in t]
   result.append((doc['materials'][p['material']]['name'],tuple(sorted(corners))))
 return collections.Counter(result)

def animation(doc,blob):
 return [dict(name=a.get('name'),channels=[dict(node=doc['nodes'][ch['target']['node']]['name'],path=ch['target']['path'],interpolation=a['samplers'][ch['sampler']].get('interpolation','LINEAR'),time=arrays(doc,blob,a['samplers'][ch['sampler']]['input']).tolist(),value=arrays(doc,blob,a['samplers'][ch['sampler']]['output']).tolist())for ch in a['channels']])for a in doc['animations']]

def material_images(doc,blob,name):
 node=next(n for n in doc['nodes']if n.get('name')==name and'mesh'in n);out=[]
 for p in doc['meshes'][node['mesh']]['primitives']:
  m=doc['materials'][p['material']];entry={'name':m['name'],'pbr':m.get('pbrMetallicRoughness',{}).copy()}
  slot=entry['pbr'].pop('baseColorTexture',None)
  if slot:
   tex=doc['textures'][slot['index']];image=doc['images'][tex['source']];view=doc['bufferViews'][image['bufferView']];o=view.get('byteOffset',0);entry['embedded_image_sha256']=hashlib.sha256(blob[o:o+view['byteLength']]).hexdigest()
  out.append(entry)
 return out

if __name__=='__main__':
 before,after,out=map(Path,sys.argv[1:]);a,ab=read_glb(before);b,bb=read_glb(after)
 old=triangles(a,ab,'Closed_body',.30);new=triangles(b,bb,'Closed_body',.30)
 # Posterior body Boolean cap is intentionally rebuilt by the new whole tail.
 checks=dict(anterior_triangles_uv_normals_skin_unchanged=old==new,anterior_triangles=sum(new.values()),anterior_domain_min_x=.30,quantization_native=1e-5,body_materials_embedded_images_unchanged=material_images(a,ab,'Closed_body')==material_images(b,bb,'Closed_body'),native_animation_channels_exact=animation(a,ab)==animation(b,bb),bones=[b['nodes'][j]['name']for j in b['skins'][0]['joints']]==[a['nodes'][j]['name']for j in a['skins'][0]['joints']])
 names=['FirstDorsal','SecondDorsal','Pectoral_left','Pectoral_right','Pelvic_left','Pelvic_right','Anal'];checks['other_seven_fin_geometry_uv_normals_skin_unchanged']={n:triangles(a,ab,n)==triangles(b,bb,n)for n in names}
 result=dict(ok=all(checks[k]for k in ['anterior_triangles_uv_normals_skin_unchanged','body_materials_embedded_images_unchanged','native_animation_channels_exact','bones'])and all(checks['other_seven_fin_geometry_uv_normals_skin_unchanged'].values()),kind='mouth_material_author_to_final_anterior_preservation',material_author_model_sha256=sha(before),model_sha256=sha(after),checks=checks,scope='Actual decoded corner attributes, named material/image semantics and native animation; modified posterior body cap and complete new caudal excluded from the unchanged-geometry claim.')
 assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result));sys.exit(0 if result['ok']else 1)
