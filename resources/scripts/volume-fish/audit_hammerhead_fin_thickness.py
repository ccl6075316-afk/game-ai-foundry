"""Protect accepted head/body and original complete fin source domains."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from portable.glb_io import read_glb,arrays

def main():
 p=argparse.ArgumentParser()
 for key in ['baseline','model','output']:p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();od,ob=read_glb(a.baseline);nd,nb=read_glb(a.model);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();parts=lambda d:{n['name']:d['meshes'][n['mesh']]['primitives']for n in d['nodes']if'mesh'in n};old,new=parts(od),parts(nd);assert old.keys()==new.keys();assert od['nodes']==nd['nodes'] and od['materials']==nd['materials'] and od['samplers']==nd['samplers'];checked=[]
 for name in old:
  assert len(old[name])==len(new[name])
  for u,v in zip(old[name],new[name]):
   assert np.array_equal(arrays(od,ob,u['indices']),arrays(nd,nb,v['indices']))
   for key in u['attributes']:
    x,y=arrays(od,ob,u['attributes'][key]),arrays(nd,nb,v['attributes'][key]);assert x.shape==y.shape
    if name=='Reference_head_body'or key not in ['POSITION','NORMAL']:assert np.array_equal(x,y),(name,key)
  checked.append(name)
 original=json.loads(a.baseline.with_name('fin-authoring.json').read_text());current=json.loads(a.model.with_name('fin-authoring.json').read_text());assert len(original['fins'])==len(current['fins'])==8;count=0
 for u,v in zip(original['fins'],current['fins']):
  assert u['name']==v['name'] and u['root_ids']==v['root_ids'] and u['triangles']==v['triangles'];count+=len(v['root_ids'])
 assert count==328
 result=dict(ok=True,kind='accepted_whole_body_and_full_fin_domain_preservation',model_sha256=sha(a.model),baseline_sha256=sha(a.baseline),checker_sha256=sha(__file__),accepted_R36_all_body_arrays_exact=True,body_mouth_eyes_normals_UV_weights_indices_exact=True,node_rig_material_sampler_bindings_exact=True,all_fin_topology_UV_weights_exact=True,complete_original_root_ids=count,fins=8,checked_meshes=checked,scope='Fin positions and normals intentionally change; roots constrained to original finite body support. No claim that fin silhouette pixels are unchanged. Original source/camber control domains and complete basal IDs retained; current fin-body motion gates separate.',formal_acceptance=False);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
