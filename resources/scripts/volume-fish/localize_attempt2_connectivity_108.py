#!/usr/bin/env python3
"""Readonly localization appendix; never changes failed CPU/model/field."""
import json,subprocess,sys,hashlib
from pathlib import Path
from collections import Counter
import numpy as np

def main():
 root=Path(__file__).resolve().parents[3];b=root/'projects/fishing-2d/experiments/blender-fish/mouth-alignment-108';out=b/'attempt2-connectivity-readonly';report=json.loads((out/'connectivity-attribution.validation.json').read_text());helper=Path(__file__).with_name('diagnostic_attempt2_ram_payload_108.py');payload=json.loads(subprocess.run([sys.executable,str(helper)],check=True,capture_output=True,text=True).stdout);surfaces=payload['surfaces'];pos=[np.array(x['POSITION'])for x in surfaces];faces=[np.array(x['indices']).reshape(-1,3)for x in surfaces];api=json.loads((b/'cpu-upper-skin-cdt/cdt-api-result.validation.json').read_text());cfg=json.loads(Path(api['input']).read_text());outside=[]
 for sh,g in zip(cfg['sheets'],report['graphs']):
  ids=np.array([p['raw_glb_vertex_ids'][0]for p in sh['points']]);pts=pos[0][ids];loop=g['boundary_loops'][0];edges=list(zip(loop,np.roll(loop,-1)))
  for k in g['interior_points_outside_boundary']:
   distances=[]
   for i,j in edges:
    a,c=pts[i,:2],pts[j,:2];d=c-a;t=float(np.clip((pts[k,:2]-a)@d/(d@d),0,1));dist=float(np.linalg.norm(pts[k,:2]-a-t*d));distances.append((dist,int(i),int(j),t))
   dist,i,j,t=min(distances);p=sh['points'][k];outside.append(dict(sheet=sh['sheet'],patch_point_id=k,actual_vertex_id=p['actual_vertex_id'],raw_vertex_ids=p['raw_glb_vertex_ids'],original_raw_xyz=p['raw_POSITION'],stage1_xyz=p['stage1_xyz'],attempt2_f32_xyz=pts[k].tolist(),attempt2_native_xy=[float((pts[k,0]+.5)*2024),float(371-pts[k,1]*2024)],nearest_boundary_patch_edge=[i,j],nearest_boundary_actual_edge=[sh['points'][v]['actual_vertex_id']for v in [i,j]],nearest_boundary_edge_f32_xyz=pts[[i,j]].tolist(),edge_interpolation_t=t,projected_distance_native_px=dist*2024))
 # Canonical exact actual-f32 positions, keeping every surface face.
 verts=np.r_[*pos];_,inverse=np.unique(verts,axis=0,return_inverse=True);allf=np.r_[faces[0],faces[1]+len(pos[0])];canonical=inverse[allf];counts=Counter(tuple(sorted((int(i),int(j))))for f in canonical for i,j in zip(f,np.roll(f,-1)));directions=Counter((int(i),int(j))for f in canonical for i,j in zip(f,np.roll(f,-1)));boundary=[]
 for surface in range(2):
  ff=inverse[faces[surface]+(len(pos[0])if surface else 0)];ct=Counter(tuple(sorted((int(i),int(j))))for f in ff for i,j in zip(f,np.roll(f,-1)));boundary.append({(int(i),int(j))for f in ff for i,j in zip(f,np.roll(f,-1))if ct[tuple(sorted((int(i),int(j))))]==1})
 skinlen=len(faces[0]);start=skinlen-209;left_end=start+103
 def label(face):
  surface=int(face>=skinlen);local=int(face-skinlen if surface else face)
  patch='oral-new97'if surface and local>=len(faces[1])-97 else 'oral-kept'if surface else 'skin-new-left103'if start<=local<left_end else 'skin-new-right106'if local>=left_end else 'skin-kept-lower-cap-crossZ-and-other'
  vv=pos[surface][faces[surface][local]];return dict(global_face=int(face),surface=surface,local_face=local,region=patch,native_centroid_xy=[float((vv[:,0].mean()+.5)*2024),float(371-vv[:,1].mean()*2024)],actual_f32_xyz=vv.tolist())
 pairs=[dict(faces=[label(i),label(j)])for i,j in report['global_full_actual_f32']['crossing']['pairs']];appendix=dict(status='read_only_localization_not_acceptance',assets_written=False,field_changed=False,CDT_invoked=False,source_report_sha256=hashlib.sha256((out/'connectivity-attribution.validation.json').read_bytes()).hexdigest(),outside_points=outside,global_crossing_localizations=pairs,exact_f32_closed_interface=dict(all_faces=len(allf),all_canonical_edge_incidence_two=all(v==2 for v in counts.values()),non_two_edge_count=sum(v!=2 for v in counts.values()),all_canonical_edges_opposite=all(directions[(i,j)]==directions[(j,i)]for i,j in counts),skin_boundary_edges=len(boundary[0]),oral_boundary_edges=len(boundary[1]),boundary397_opposite_exact=boundary[0]=={(j,i)for i,j in boundary[1]}and len(boundary[0])==397),conclusion='Old upper connectivity is illegal at frozen destination. Boundary loops are simple but contain outside old interior points; direct same-point destinationCDT is not proposed. Outside in projectedXY does not prove global field nonmonotonicity in3D. No automatic field/boundary/point modification authorized. Source5919to369 adjacentfaces also directly participate in actual3D crossings; shading57negativecorners is not the proof. Original failedCPU stays failed.')
 (out/'connectivity-localization.validation.json').write_text(json.dumps(appendix,indent=2)+'\n');print(json.dumps(dict(outside=outside,closure=appendix['exact_f32_closed_interface'])))
if __name__=='__main__':main()
