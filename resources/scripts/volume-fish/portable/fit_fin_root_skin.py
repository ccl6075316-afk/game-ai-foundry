"""Fit only explicit complete fin-root skin against actual finite-body poses.

Geometry, UV, normals, RGB, skeleton and native actions are immutable. No test
threshold or motion amplitude changes. Fresh source/cold and full posed gates
are still required. The compact exporter is diagnostic, not a completion gate.
"""
import argparse,itertools,json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.spatial import cKDTree
from glb_io import read_glb,arrays,sha
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def skin(row,mat):
 p=np.c_[row['vertices_native'],np.ones(len(row['vertices_native']))];js=np.array(row['joints'],int).reshape(-1,4);ws=np.array(row['weights']).reshape(-1,4);return(np.einsum('pnsij,nj->pnsi',mat[:,js],p)*ws[None,:,:,None]).sum(2)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['candidate','compact','bindings','output']:p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--full-export',type=Path,help='Actual complete export when it is outside candidate/delivery')
 a=p.parse_args();C=a.candidate.resolve();out=a.output.resolve();assert not out.exists();rest=read(a.compact/'rest-skin.json');bindings=read(a.bindings);assert sha(a.compact/'rest-skin.json')==bindings['compact_rest_sha256'];report=read(a.compact/'export.validation.json');rows=report['samples'];mat=np.array([read(r['posed_mesh_json'])['joint_matrices_m_per_native']for r in rows]);assert len(rows)==490;body=np.concatenate([skin(r,mat)for r in rest['surfaces']if r['body']],axis=1);source=C/'source-run/fish.glb';doc,blob=read_glb(source);pr=doc['meshes'][0]['primitives'][0];values={k:arrays(doc,blob,v)for k,v in pr['attributes'].items()};j_names=[doc['nodes'][j]['name']for j in doc['skins'][0]['joints']];j_map={i:j_names.index(n)for i,n in enumerate(rest['joint_names'])if n in j_names};changes=[];metrics=[];equivalence=[]
 # Verify compact actual skin against representative full Godot exports,
 # including each original failure; no pose schedule is synthesized here.
 old=read(a.full_export or C/'delivery/fin490'/doc.get('extras',{}).get('species',read(C/'source-run/final-spec.json')['species'])/'export.validation.json')
 assert rest['model_sha256']==old['model_sha256']==sha(source),'Compact/full/model identities differ'
 sample_ids=sorted(set([0,len(rows)-1,*np.linspace(0,len(rows)-1,17).round().astype(int).tolist()]))
 for i in sample_ids:
  assert rows[i]['action']==old['samples'][i]['action']and abs(rows[i]['seconds']-old['samples'][i]['seconds'])<1e-6;actual=read(old['samples'][i]['posed_mesh_json']);error=float(np.max(abs(np.array(actual['body_vertices_m'])-body[i])));assert error<5e-7,(i,error);equivalence.append({'sample':i,'body_max_position_error_m':error})
 for fin in bindings['fins']:
  row=next(r for r in rest['surfaces']if r['name']==fin['name']);pos=np.array(row['vertices_native']);js=np.array(row['joints'],int).reshape(-1,4);ws=np.array(row['weights']).reshape(-1,4);part=next(r for r in doc['extras']['geometry_parts']if r['source_node']==fin['name']);lo=part['vertex_start'];local=values['POSITION'][lo:lo+part['vertex_count']];tree=cKDTree(local)
  for root in fin['roots']:
   i=root['vertex'];tri=np.array(root['body_triangle']);beta=np.array(root['barycentric']);q=np.einsum('i,pij->pj',beta,body[:,tri]);normal=np.cross(body[:,tri[1]]-body[:,tri[0]],body[:,tri[2]]-body[:,tri[0]]);normal/=np.linalg.norm(normal,axis=1)[:,None];target=q+normal*root['static_signed_offset_m'];p4=np.r_[pos[i],1.];candidates=set()
   offset=0
   for br in rest['surfaces']:
    if not br['body']:continue
    count=len(br['vertices_native']);rj=np.array(br['joints'],int).reshape(-1,4);rw=np.array(br['weights']).reshape(-1,4)
    for vertex in tri:
     if offset<=vertex<offset+count:candidates.update(int(j)for j,w in zip(rj[vertex-offset],rw[vertex-offset])if w>1e-5)
    offset+=count
   old_weights={int(j):float(w)for j,w in zip(js[i],ws[i])if w>0};candidates.update(old_weights);candidates=sorted(candidates);assert all(j in j_map for j in candidates),'Unmapped actual body joint';all_features=np.einsum('pkij,j->pki',mat[:,candidates],p4);errors=(all_features-target[:,None,:])*1000;w0=np.array([old_weights.get(j,0)for j in candidates]);old_delta=np.einsum('pkj,k->pj',errors,w0);bound=max(float(abs(old_delta).max()),.01)+.001;best=None
   for size in range(1,min(4,len(candidates))+1):
    for subset in itertools.combinations(range(len(candidates)),size):
     ef=errors[:,subset,:];fn=np.einsum('pkj,pj->pk',ef,normal);a3=ef.transpose(0,2,1).reshape(-1,size);A=np.r_[np.c_[fn,-np.ones(len(fn))],np.c_[-fn,-np.ones(len(fn))],np.c_[a3,np.zeros(len(a3))],np.c_[-a3,np.zeros(len(a3))]];b=np.r_[np.zeros(2*len(fn)),np.full(2*len(a3),bound)];solution=linprog(np.r_[np.zeros(size),1.],A_ub=A,b_ub=b,A_eq=[np.r_[np.ones(size),0]],b_eq=[1.],bounds=[(0,1)]*size+[(0,None)],method='highs')
     if not solution.success:continue
     w=solution.x[:size];w[w<1e-4]=0;w/=w.sum();delta=np.einsum('pkj,k->pj',ef,w);score=float(abs(np.einsum('pj,pj->p',delta,normal)).max())
     if best is None or score<best[0]:best=(score,subset,w,delta)
   assert best;score,subset,w,delta=best;old_normal=float(abs(np.einsum('pj,pj->p',old_delta,normal)).max());distance,native=tree.query(pos[i]);assert distance<2e-6;native=int(native)+lo;new_js=[j_map[candidates[k]]for k in subset];new_ws=w.tolist();metrics.append({'fin':fin['name'],'compact_vertex':i,'native_vertex':native,'old_max_normal_error_mm':old_normal,'fitted_max_normal_error_mm':score,'old_max_component_error_mm':float(abs(old_delta).max()),'fitted_max_component_error_mm':float(abs(delta).max()),'candidate_bones':[rest['joint_names'][j]for j in candidates]})
   if score+1e-5<old_normal:
    new_js+= [0]*(4-len(new_js));new_ws+=[0.]*(4-len(new_ws));changes.append({'vertex':native,'fin':fin['name'],'old_joints':values['JOINTS_0'][native].tolist(),'old_weights':values['WEIGHTS_0'][native].tolist(),'new_joints':new_js,'new_weights':new_ws})
 result={'ok':True,'kind':'actual_pose_complete_root_skin_fit_plan','model':str(source),'model_sha256':sha(source),'source_blend':str(C/'source-run/source/fish.blend'),'source_blend_sha256':sha(C/'source-run/source/fish.blend'),'compact_rest':str(a.compact/'rest-skin.json'),'compact_rest_sha256':sha(a.compact/'rest-skin.json'),'binding_report':str(a.bindings.resolve()),'binding_report_sha256':sha(a.bindings),'pose_count':len(rows),'full_export_equivalence_samples':equivalence,'complete_fitted_fin_inventory':[r['name']for r in bindings['fins']],'metrics':metrics,'changes':changes,'geometry_UV_normals_RGB_rig_actions_unchanged':True,'formal_acceptance':False,'scope':'Only complete explicit root banks fitted to actual body finite-face trajectories; nonnegative normalized <=4 influences. Normal-error minimax subject to no worsening of original worst 3D component error. No amplitudes, root IDs, collar or tolerance edits. Fresh cold/volume/source/490 remain mandatory.'};out.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({'ok':True,'changes':len(changes),'max_old_normal_mm':max(r['old_max_normal_error_mm']for r in metrics),'max_fitted_normal_mm':max(r['fitted_max_normal_error_mm']for r in metrics)}))
if __name__=='__main__':main()
