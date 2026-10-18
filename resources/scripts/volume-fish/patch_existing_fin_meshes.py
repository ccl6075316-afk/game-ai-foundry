"""Transplant repaired fin primitives while preserving original rig/animation/BIN prefix.

No mesh-node, skin, body, jaw, source image or animation stream is re-exported.
Joint indices are remapped explicitly by skeleton node name.
"""
import copy,hashlib,json,struct,sys
from pathlib import Path
def read(path):
 raw=Path(path).read_bytes();size=struct.unpack_from('<I',raw,12)[0];return json.loads(raw[20:20+size]),bytearray(raw[28+size:])
def write(path,doc,binary):
 doc['buffers'][0]['byteLength']=len(binary);binary+=b'\0'*(-len(binary)%4);encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*(-len(encoded)%4);Path(path).write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
def main():
 old=json.loads(Path(sys.argv[1]).read_text());new=json.loads(Path(sys.argv[2]).read_text());results=[]
 for base,row in zip(old['items'],new['items']):
  assert base['species']==row['species'];a,bin_a=read(base['model']);b,bin_b=read(row['model']);original=bytes(bin_a);accessor_map={};view_map={};patched=[]
  def accessor(idx):
   if idx in accessor_map:return accessor_map[idx]
   value=copy.deepcopy(b['accessors'][idx]);assert 'sparse' not in value;view=value['bufferView']
   if view not in view_map:
    bv=copy.deepcopy(b['bufferViews'][view]);start=bv.get('byteOffset',0);data=bin_b[start:start+bv['byteLength']];bin_a.extend(b'\0'*(-len(bin_a)%4));bv['byteOffset']=len(bin_a);bv['buffer']=0;bin_a.extend(data);view_map[view]=len(a['bufferViews']);a['bufferViews'].append(bv)
   value['bufferView']=view_map[view];accessor_map[idx]=len(a['accessors']);a['accessors'].append(value);return accessor_map[idx]
  for name in row['changes']:
   na=next(n for n in a['nodes'] if n.get('name')==name and 'mesh' in n);nb=next(n for n in b['nodes'] if n.get('name')==name and 'mesh' in n)
   assert not any(k in na or k in nb for k in ['matrix','translation','rotation','scale']),'Nonidentity fin node needs explicit space conversion'
   sa=a['skins'][na['skin']];sb=b['skins'][nb['skin']];names_a=[a['nodes'][i]['name'] for i in sa['joints']];names_b=[b['nodes'][i]['name'] for i in sb['joints']];joint_map={i:names_a.index(name) for i,name in enumerate(names_b)}
   mesh=copy.deepcopy(b['meshes'][nb['mesh']]);old_mesh=a['meshes'][na['mesh']];old_materials={a['materials'][p['material']]['name']:p['material'] for p in old_mesh['primitives']}
   for prim in mesh['primitives']:
    prim['material']=old_materials[b['materials'][prim['material']]['name']];prim['indices']=accessor(prim['indices']);prim['attributes']={key:accessor(idx) for key,idx in prim['attributes'].items()}
    for key,idx in prim['attributes'].items():
     if not key.startswith('JOINTS_'):continue
     acc=a['accessors'][idx];view=a['bufferViews'][acc['bufferView']];fmt={5121:'B',5123:'H'}[acc['componentType']];size=struct.calcsize(fmt);stride=view.get('byteStride',4*size);start=view['byteOffset']+acc.get('byteOffset',0)
     for i in range(acc['count']):
      off=start+i*stride;values=struct.unpack_from('<'+fmt*4,bin_a,off);struct.pack_into('<'+fmt*4,bin_a,off,*[joint_map[j] for j in values])
   a['meshes'][na['mesh']]=mesh;patched.append(name)
  assert bytes(bin_a[:len(original)])==original,'Original BIN prefix modified'
  dest=Path(row['model']).parent.parent/'candidate-c';dest.mkdir(exist_ok=True);path=dest/'fish.glb';write(path,a,bin_a);row['model']=str(path);row['model_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();row['preservation']={'original_bin_prefix_sha256':hashlib.sha256(original).hexdigest(),'original_bin_bytes':len(original),'body_skin_nodes_animations_images_unchanged':True,'replaced_fin_meshes':patched};results.append(row);(dest/'patch.validation.json').write_text(json.dumps({'ok':True,'species':row['species'],**row['preservation']},indent=2));print('PATCHED',row['species'],len(patched))
 Path(sys.argv[3]).write_text(json.dumps({'kind':'existing_fin_mesh_repair','items':results},indent=2))
if __name__=='__main__':main()
