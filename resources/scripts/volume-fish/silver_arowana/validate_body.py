"""Explicit ordinary closed mixed-eye/barbel adapter around unchanged077 body/GPU.

Only inventory projection removes auxiliary mesh-node tags for the original
body inspection kernel. Every original accessor/buffer/material stays exact;
GPU validation always reads the real complete candidate and full inventory.
"""
import io,json,hashlib,sys,importlib.util,copy
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[4];PORT=ROOT/'resources/scripts/volume-fish/portable';sys.path[:0]=[str(PORT),str(PORT.parent)]
import validate_standalone_body as base
from patch_existing_fin_meshes import read,write
from freeze_surface_ownership import accessor
def inspect_aux(plan):
 doc,blob=read(Path(plan['model']));nodes=[n for n in doc['nodes']if 'mesh'in n];aux=plan['decorative_overlays'];assert set(n['name']for n in nodes)=={plan['body'],*plan['fins'],*aux}
 proofs=[];aux_triangles=0
 for name,definition in aux.items():
  assert definition['kind']in ['closed_body_supported_eye_lens','closed_skinned_mandibular_barbel']and definition['underlying_body']==plan['body']
  node=next(n for n in nodes if n['name']==name);skin=doc['skins'][node['skin']];joint_names=[doc['nodes'][i]['name']for i in skin['joints']];edges=Counter();directions=Counter();triangles=0;positions=[]
  allowed=set(definition['allowed_body_bones']);assert allowed and allowed<=set(plan['body_bones'])
  for primitive in doc['meshes'][node['mesh']]['primitives']:
   attrs=primitive['attributes'];pos=accessor(doc,blob,attrs['POSITION']);tri=accessor(doc,blob,primitive['indices']).reshape(-1,3);ws=accessor(doc,blob,attrs['WEIGHTS_0']);js=accessor(doc,blob,attrs['JOINTS_0']);assert np.isfinite(pos).all()and np.isfinite(ws).all()and ws.shape==js.shape==(len(pos),4);assert np.all(ws>=0)and np.all(abs(ws.sum(1)-1)<1e-5)
   for joints,weights in zip(js,ws):assert all(joint_names[int(j)]in allowed for j,w in zip(joints,weights)if w>1e-7),'Auxiliary uses undeclared support bone'
   assert np.all(np.linalg.norm(np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]]),axis=1)>0),'Degenerate auxiliary face'
   for face in tri:
    q=[tuple(round(float(x),7)for x in pos[i])for i in face];assert len(set(q))==3
    for a,b in zip(q,q[1:]+q[:1]):key=tuple(sorted([a,b]));edges[key]+=1;directions[key]+=1 if a<b else-1
   mat=doc['materials'][primitive['material']];assert mat.get('alphaMode','OPAQUE')=='OPAQUE'and mat.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1])[3]==1
   texture=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture')
   if texture:
    image=doc['images'][doc['textures'][texture['index']]['source']];assert 'bufferView'in image and'uri'not in image;view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0);rgba=np.array(Image.open(io.BytesIO(blob[start:start+view['byteLength']])).convert('RGBA'));assert np.all(rgba[:,:,3]==255),'Auxiliary donor is not wholly opaque'
   triangles+=len(tri);positions.extend(pos.tolist())
  assert edges and all(n==2 for n in edges.values())and all(n==0 for n in directions.values()),'Auxiliary is not oriented closed'
  aux_triangles+=triangles;proofs.append({'name':name,'kind':definition['kind'],'triangles':triangles,'closed_oriented':True,'normalized_body_bone_skin':True,'opaque_full_donor':True,'allowed_body_bones':sorted(allowed)})
 return doc,blob,aux_triangles,proofs
ORIGINAL=base.inspect_model
def inspect_model(plan):
 doc,blob,aux_triangles,proofs=inspect_aux(plan);projected=copy.deepcopy(doc)
 for node in projected['nodes']:
  if node.get('name')in plan['decorative_overlays']:node.pop('mesh',None)
 directory=Path(plan['aux_projection_output']).resolve();assert directory.is_relative_to(ROOT/'projects/fishing-2d/experiments');directory.mkdir(parents=True,exist_ok=True);target=directory/'body-inventory-projection.glb';write(target,projected,blob)
 p=copy.deepcopy(plan);p['model']=str(target);p['model_sha256']=base.sha(target);p['expected_triangles']-=aux_triangles;p['decorative_overlays']={};geometry=ORIGINAL(p)
 # No array, image or material projection: exact complete original document
 # changes only four auxiliary node mesh tags. Body kernel is unchanged.
 restored=copy.deepcopy(projected)
 for original,node in zip(doc['nodes'],restored['nodes']):
  if original.get('name')in plan['decorative_overlays']:node['mesh']=original['mesh']
 assert restored==doc and read(target)[1]==blob
 geometry.update(triangles=plan['expected_triangles'],decorative_overlay_proofs=proofs,analysis_projection_only=True,projection_proof={'original_model_sha256':plan['model_sha256'],'projection_sha256':base.sha(target),'all_accessors_buffers_materials_images_exact':True,'only_auxiliary_mesh_node_tags_removed':True,'gpu_reads_original_model':True})
 return geometry
def main():
 import argparse
 p=argparse.ArgumentParser();[p.add_argument('--'+k,type=Path,required=True)for k in ['game','godot','plan','output']];a=p.parse_args();base.inspect_model=inspect_model
 result=base.validate(a.game.resolve(),a.godot.resolve(),a.plan.resolve(),a.output.resolve());result['aux_adapter_sha256']=base.sha(__file__);result['body_gpu_kernel_unchanged_sha256']=base.sha(PORT/'validate_standalone_body.py');(a.output/'completion.validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':result['ok'],'error':result.get('error')}));raise SystemExit(0 if result['ok']else 1)
if __name__=='__main__':main()
