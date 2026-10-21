#!/usr/bin/env python3
"""Authorized post-failure readonly original-skin global diagnostic. No assets/CDT."""
import json,subprocess,sys,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from build_mouth_y_candidate_108 import map_faces
from validate_oral_cdt_108 import crossing

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 root=Path(__file__).resolve().parents[3];b=root/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108';out=b/'original-skin-readonly';out.mkdir(exist_ok=True);helper=Path(__file__).with_name('diagnostic_original_skin_ram_payload_108.py');payload=json.loads(subprocess.run([sys.executable,str(helper)],capture_output=True,text=True,check=True).stdout);pos=[np.array(s['POSITION'])for s in payload['surfaces']];faces=[np.array(s['indices']).reshape(-1,3)for s in payload['surfaces']];g,bin0=read_glb(Path(payload['original_source']));mi=next(n['mesh']for n in g['nodes']if n.get('name')=='Closed_body');pr=g['meshes'][mi]['primitives'];raw=[{k:accessor(g,bin0,v)for k,v in p['attributes'].items()}for p in pr];rawfaces=[accessor(g,bin0,p['indices']).reshape(-1,3)for p in pr];assert np.array_equal(faces[0],rawfaces[0]);sapi=json.loads((b/'cpu-upper-skin-cdt/cdt-api-result.validation.json').read_text());cfg=json.loads(Path(sapi['input']).read_text());actual=json.loads((b.parent/'eye-rollout-107/zander-mesh-rest.json').read_text());# Freeze actual/raw face mapping using the established factory's actual loader is unnecessary here: canonical raw keys identify every restored triangle.
 from collections import defaultdict
 from build_stage1_cdt_candidate_108 import face_key
 lookup=defaultdict(list)
 for i,f in enumerate(rawfaces[0]):lookup[face_key(raw[0]['POSITION'][f])].append(i)
 restored=[]
 for sh in cfg['sheets']:
  # old_local_faces points carry frozen actual origin positions.
  for f in sh['old_local_faces']:
   xyz=np.array([sh['points'][int(i)]['raw_POSITION']for i in f]);hits=lookup[face_key(xyz)];assert len(hits)==1;restored.extend(hits)
 assert len(restored)==209 and len(set(restored))==209
 changed=[np.any(pos[i][:len(raw[i]['POSITION'])]!=raw[i]['POSITION'],axis=1)for i in range(2)];changed[0][faces[0][restored].ravel()]=True;changed[1]=np.r_[changed[1],np.ones(len(pos[1])-len(raw[1]['POSITION']),bool)];n=len(pos[0]);vertices=np.r_[*pos];ff=np.r_[faces[0],faces[1]+n];cr=crossing(vertices,ff,np.r_[*changed]);tt=vertices[ff];area=np.linalg.norm(np.cross(tt[:,1]-tt[:,0],tt[:,2]-tt[:,0]),axis=1);_,iv=np.unique(vertices,axis=0,return_inverse=True);cf=iv[ff];ct=Counter(tuple(sorted((int(i),int(j))))for f in cf for i,j in zip(f,np.roll(f,-1)));direct=Counter((int(i),int(j))for f in cf for i,j in zip(f,np.roll(f,-1)));bound=[]
 for i in range(2):
  f=iv[faces[i]+(n if i else 0)];counts=Counter(tuple(sorted((int(i),int(j))))for t in f for i,j in zip(t,np.roll(t,-1)));bound.append({(int(i),int(j))for t in f for i,j in zip(t,np.roll(t,-1))if counts[tuple(sorted((int(i),int(j))))]==1})
 def detail(k):
  side=int(k>=len(faces[0]));idx=int(k-len(faces[0])if side else k);v=pos[side][faces[side][idx]];return dict(global_face=int(k),surface=side,local_face=idx,restored_original_upper_skin=side==0 and idx in restored,native_centroid_xy=[float((v[:,0].mean()+.5)*2024),float(371-v[:,1].mean()*2024)],actual_f32_xyz=v.tolist())
 result=dict(status='post_failure_readonly_NOT_Phase3pass',accepted=False,CPU_original_failed_unchanged=True,assets_written=False,field_changed=False,CDT_invoked=False,failedCPU_sha256=sha(b/'original-skin-cpu/completion.validation.json'),inputs={k:v for k,v in payload.items()if k not in ['surfaces','baseline_body_bounds_Blender']},surface_triangle_counts=[len(f)for f in faces],all_faces_included=len(ff),all_lower_cap_crossZ_oral_kept_included=True,restored209_selected=bool(changed[0][faces[0][restored]].any(1).all()),oral97_all_selected=bool(changed[1][faces[1][-97:]].any(1).all()),crossing=cr,zero_3D_area_faces=np.flatnonzero(area==0).tolist(),crossing_localizations=[[detail(i),detail(j)]for i,j in cr['pairs']],closure=dict(skin_boundary=len(bound[0]),oral_boundary=len(bound[1]),opposite397_exact=len(bound[0])==397 and bound[0]=={(j,i)for i,j in bound[1]},all_edges_incident2=all(c==2 for c in ct.values()),all_edges_opposite=all(direct[(i,j)]==direct[(j,i)]for i,j in ct)),comparison=dict(F2_connectivity_actual3Dcross=26,original_skin_actual3Dcross=cr['proper_crossings'],meaning='Connectivity-only diagnostic, source1.099px failure remains. No new point/field/epsilon/topology change.'))
 (out/'global-diagnostic.validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['status','surface_triangle_counts','all_faces_included','restored209_selected','oral97_all_selected','crossing','zero_3D_area_faces','closure']}))
if __name__=='__main__':main()
