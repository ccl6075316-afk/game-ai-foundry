from pathlib import Path
import sys,json,numpy as np
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parents[5];sys.path.insert(0,str(R/'resources/scripts/volume-fish'))
import rebind_repaired_upper_lip as m
I=Path(__file__).resolve().parent;C=I.parent
recipe=json.loads((I/'baseline-mouth-anchor.json').read_text());old,ob=m.read_glb(I/'baseline.glb');new,nb=m.read_glb(C/'cold-fish.glb')
assert recipe['model_sha256']==m.sha(I/'baseline.glb')
on,op=m.node_primitive(old,recipe['mesh'],recipe['surface']);ov=m.arrays(old,ob,op['attributes']['POSITION'])[recipe['vertex_index']];uv=m.arrays(old,ob,op['attributes']['TEXCOORD_0'])[recipe['vertex_index']];skin,*_=m.named_skin(old,ob,on,op,recipe['vertex_index'])
assert np.max(abs(ov-recipe['position_native']))<1e-7 and np.max(abs(uv-recipe['texcoord0']))<1e-7
nn,np_=m.node_primitive(new,recipe['mesh'],recipe['surface']);pos=m.arrays(new,nb,np_['attributes']['POSITION']);uvs=m.arrays(new,nb,np_['attributes']['TEXCOORD_0']);ids=np.flatnonzero(np.max(abs(uvs-uv),axis=1)<1e-7);matches=[]
for i in ids:
 sk,j,w=m.named_skin(new,nb,nn,np_,int(i))
 if m.skin_equal(sk,skin):matches.append((int(i),sk,j,w))
assert len(matches)==1,matches
idx,sk,j,w=matches[0];p=pos[idx];delta=float(np.linalg.norm(p-ov));assert delta<.002,delta
oral_names={'Recessed actual mouth cavity R5'};sf,of,_=m.owner_faces(new,nb,nn,oral_names);tree=cKDTree(sf.reshape(-1,3));shared=tree.query(of.reshape(-1,3))[0].reshape(-1,3)<1e-7;norm=np.cross(of[:,1]-of[:,0],of[:,2]-of[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-30);witness=[]
for fi in np.flatnonzero(norm[:,1]<-.1):
 for a,b in [(0,1),(1,2),(2,0)]:
  if shared[fi,a] and shared[fi,b] and min(np.linalg.norm(of[fi,a]-p),np.linalg.norm(of[fi,b]-p))<1e-7:witness.append({'oral_triangle':int(fi),'edge':of[fi,[a,b]].tolist(),'actual_oral_face_normal':norm[fi].tolist()})
assert witness
out=recipe|{'model_sha256':m.sha(C/'cold-fish.glb'),'vertex_index':idx,'position_native':p.tolist(),'texcoord0':uvs[idx].tolist(),'raw_joint_indices':j,'raw_weights':w,'weighted_bones':sk,'body_vertex_ranges':[[0,len(pos)]],'scope':'Accepted R5 actual shared upper oral roof vertex; fresh canonical import/hook validation follows install.','identity_evidence':{'method':'Unique unchanged native UV and named skin weights from explicit previous canonical upper-lip vertex. Physical repair permits measured local displacement <.002 native units. Independently require actual downward-facing oral roof edge shared with skin.','superseded_recipe':{'path':str(I/'baseline-mouth-anchor.json'),'sha256':m.sha(I/'baseline-mouth-anchor.json')},'canonical_baseline_model_sha256':m.sha(I/'baseline.glb'),'oral_materials':sorted(oral_names),'position_delta_native':delta,'shared_upper_roof_edge_witnesses':witness,'checker_sha256':m.sha(__file__)}}
(I/'current-mouth-anchor.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'vertex':idx,'position':p.tolist(),'delta_native':delta,'roof_witnesses':len(witness)}))
