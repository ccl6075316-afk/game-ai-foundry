import sys,json,argparse,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from probe_mouth_slit_stage1_108 import field,canvas
ap=argparse.ArgumentParser(description='Read-only108Stage1 finite triangle failure localization');ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args();b=args.input.resolve();data=[json.load(open(b.parent/'eye-rollout-107/zander-mesh-rest.json')),json.load(open(b/'zander-oral-rest.json'))];old=[];new=[];faces=[];offset=0
for d in data:
 v=np.array(d['rest_xyz']);q=canvas(v);m,J=field(q);o=v.copy();s=q[:,0]>1988;o[s,0]=m[s,0]/2024-.5;o[s,1]=(371-m[s,1])/2024;old.extend(v);new.extend(o);faces.extend(np.array(d['indices']).reshape(-1,3)+offset);offset+=len(v)
old=np.array(old);new=np.array(new);faces=np.array(faces);report=[]
for i,j in [(23280,23625),(23626,23936)]:
 A=new[faces[i]];B=new[faces[j]];entry={'combined_triangles':[i,j],'oral_triangles':[i-22941,j-22941],'old_xyz':[old[faces[i]].tolist(),old[faces[j]].tolist()],'new_xyz':[A.tolist(),B.tolist()],'old_source_canvas':[canvas(old[faces[i]]).tolist(),canvas(old[faces[j]]).tolist()],'new_source_canvas':[canvas(A).tolist(),canvas(B).tolist()],'minimum_pair_vertex_distance_rest':float(np.linalg.norm(A[:,None,:]-B[None,:,:],axis=2).min()),'hits':[]}
 for target,segment in [(A,B),(B,A)]:
  e1=target[1]-target[0];e2=target[2]-target[0]
  for k in range(3):
   O=segment[k];D=segment[(k+1)%3]-O;H=np.cross(D,e2);det=np.dot(e1,H)
   if abs(det)<=1e-14:continue
   s=O-target[0];u=np.dot(s,H)/det;Q=np.cross(s,e1);v=np.dot(D,Q)/det;t=np.dot(e2,Q)/det
   if u>1e-8 and v>1e-8 and u+v<1-1e-8 and 1e-8<t<1-1e-8:entry['hits'].append({'edge':k,'det':float(det),'u':float(u),'v':float(v),'segment_t':float(t),'point_rest':(O+t*D).tolist(),'distance_from_edge_ends_rest':float(min(t,1-t)*np.linalg.norm(D))})
 report.append(entry)
# Compare actual emitted geometric normal with transported original geometric normal, not mere old-normal dot.
metrics=[]
for surface,d in enumerate(data):
 v=np.array(d['rest_xyz']);q=canvas(v);mq,J=field(q);o=v.copy();s=q[:,0]>1988;o[s,0]=mq[s,0]/2024-.5;o[s,1]=(371-mq[s,1])/2024
 for name,indices in [('base',d['indices'])]+[(f'LOD{k}',x['indices']) for k,x in enumerate(d['lods'])]:
  ids=np.array(indices).reshape(-1,3);ta=v[ids];tb=o[ids];an=np.cross(ta[:,1]-ta[:,0],ta[:,2]-ta[:,0]);bn=np.cross(tb[:,1]-tb[:,0],tb[:,2]-tb[:,0]);cent=canvas(ta.mean(1));_,J=field(cent);J[:,0,1]*=-1;J[:,1,0]*=-1;J3=np.tile(np.eye(3),(len(ids),1,1));J3[:,:2,:2]=J;expected=np.einsum('nij,nj->ni',np.linalg.inv(J3).transpose(0,2,1),an);aa=np.linalg.norm(expected,axis=1);ba=np.linalg.norm(bn,axis=1);valid=(aa>1e-14)&(ba>1e-14);cos=np.einsum('ij,ij->i',expected,bn)/np.maximum(aa*ba,1e-30);oldcos=np.einsum('ij,ij->i',an,bn);bad=(cos<=0)&valid;metrics.append({'surface':surface,'level':name,'opposite_emitted_vs_transported_geometric_normal_count':int(bad.sum()),'minimum_cosine':float(cos[valid].min()),'opposite_ids':np.flatnonzero(bad)[:24].tolist(),'oldnormal_dot_negative_ids':np.flatnonzero(oldcos<=0)[:24].tolist()})
out={'status':'stage1_additional_read_only_failure_localization','field_parameters_unchanged':True,'crossing_pairs':report,'normal_transport_comparison':metrics};args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'pairs':[{'triangles':x['oral_triangles'],'min_vertex_distance':x['minimum_pair_vertex_distance_rest'],'hits':x['hits']} for x in report],'normal_comparison':metrics},indent=2))
