from pathlib import Path
import sys,json,numpy as np
from scipy.spatial import cKDTree
R=Path('/Users/czl/projects/game-ai-foundry');W=R/'work/arapaima-jaw-20261112';O=R/'work/arapaima-release-20261112'
sys.path.insert(0,str(R/'resources/scripts/volume-fish'));from rebind_repaired_upper_lip import *
model=Path(sys.argv[1]);output=Path(sys.argv[2]);d,b=read_glb(model);node,p=node_primitive(d,'Closed_body',0)
cage=json.loads((R/'resources/volume-fish/clean-pixel-arapaima-20261112/parameters/rebuilt-body.json').read_text());print(cage.keys())
position=np.array(cage['vertices'][31*24]);vertices=arrays(d,b,p['attributes']['POSITION']);ids=np.flatnonzero(np.linalg.norm(vertices-position,axis=1)<1e-7);assert len(ids)>0;index=int(ids[0]);position=vertices[index];skin,joints,weights=named_skin(d,b,node,p,index)
oral_name=d['materials'][d['meshes'][node['mesh']]['primitives'][1]['material']]['name'];sf,of,ranges=owner_faces(d,b,node,{oral_name});shared=cKDTree(sf.reshape(-1,3)).query(of.reshape(-1,3))[0].reshape(-1,3)<1e-7;normals=np.cross(of[:,1]-of[:,0],of[:,2]-of[:,0]);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-30);witness=[]
for fi in np.flatnonzero(normals[:,1]<-.1):
 for l,r in [(0,1),(1,2),(2,0)]:
  if shared[fi,l]and shared[fi,r]and min(np.linalg.norm(of[fi,l]-position),np.linalg.norm(of[fi,r]-position))<1e-7:witness.append({'oral_triangle':int(fi),'edge':of[fi,[l,r]].tolist(),'actual_oral_face_normal':normals[fi].tolist()})
assert witness
result={'kind':'existing_skinned_upper_lip_vertex_recipe','species':'arapaima','model_sha256':sha(model),'mesh':'Closed_body','surface':0,'vertex_index':index,'position_native':position.tolist(),'texcoord0':arrays(d,b,p['attributes']['TEXCOORD_0'])[index].tolist(),'raw_joint_indices':joints,'raw_weights':weights,'weighted_bones':skin,'body_vertex_ranges':[[0,len(vertices)]],'binding_space':'mesh_native','semantic':'Explicit upper center lip of the rebuilt mouth rim, shared by outer skin and oral roof.','identity_evidence':{'method':'Source cage ring31 theta0 vertex744 identifies upper center lip. Exact native position mapped to exported outer skin, then independently verified shared oral roof edges. Duplicate corner vertices have the same semantic point; first outer corner selected explicitly.','cage_sha256':sha(R/'resources/volume-fish/clean-pixel-arapaima-20261112/parameters/rebuilt-body.json'),'source_vertex':744,'oral_materials':[oral_name],'shared_upper_roof_edge_witnesses':witness,'checker_sha256':sha(Path(__file__))},'scope':'Godot imported identity and hook placement require the canonical verification report.'}
output.write_text(json.dumps(result,indent=2)+'\n');print({'upper_lip':index,'witnesses':len(witness)})
