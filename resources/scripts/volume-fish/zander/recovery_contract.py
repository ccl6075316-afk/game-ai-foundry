from pathlib import Path
import hashlib,json,sys,numpy as np
sys.path.insert(0,str(Path(__file__).parent.parent/'portable'));from glb_io import read_glb,arrays

def contract(path):
 d,b=read_glb(path);used=set()
 for m in d.get('meshes',[]):
  for p in m['primitives']:used.update(p['attributes'].values());used.add(p['indices'])
 for s in d.get('skins',[]):used.add(s['inverseBindMatrices'])
 for a in d.get('animations',[]):
  for s in a['samplers']:used.add(s['input']);used.add(s['output'])
 dig=lambda a:hashlib.sha256(np.asarray(a).tobytes()).hexdigest();images=[]
 for im in d.get('images',[]):
  v=d['bufferViews'][im['bufferView']];o=v.get('byteOffset',0);images.append(hashlib.sha256(b[o:o+v['byteLength']]).hexdigest())
 return {'full_JSON_structure_sha256':hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'every_referenced_accessor':{str(i):dig(arrays(d,b,i))for i in sorted(used)},'all_embedded_PNG_payloads':images,'unused_accessors':sorted(set(range(len(d['accessors'])))-used)}
