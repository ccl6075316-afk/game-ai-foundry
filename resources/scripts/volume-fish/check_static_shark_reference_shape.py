"""Measure the cold finite trial mesh against frozen same-species image values."""
import argparse,json,sys,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'portable'))
from glb_io import read_glb,arrays,sha

def check(model,reference,out):
 cfg=json.loads(reference.read_text());doc,blob=read_glb(model);vertices=[];faces=[];whole_triangles=sum(int(doc['accessors'][p['indices']]['count'])//3 for m in doc['meshes']for p in m['primitives'])
 for node in doc['nodes']:
  if 'mesh'not in node or node.get('name')!='Reference_head_body':continue
  assert node.get('translation',[0,0,0])==[0,0,0] and node.get('scale',[1,1,1])==[1,1,1]
  for prim in doc['meshes'][node['mesh']]['primitives']:
   v=arrays(doc,blob,prim['attributes']['POSITION']);v=v[:,[0,2,1]];v[:,1]*=-1;tri=arrays(doc,blob,prim['indices']).reshape(-1,3);off=len(vertices);vertices.extend(v.tolist());faces.extend((tri+off).tolist())
 assert vertices and faces,'Explicit actual body mesh missing; fins cannot stand in for body width'
 v=np.array(vertices);tri=np.array(faces);edges=np.unique(np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1),axis=0);a,b=v[edges[:,0]],v[edges[:,1]];axis=cfg['reference_body_axis_m'];rows=[]
 for t in np.linspace(.15,.999,401):
  x=axis*(.5-t);m=(a[:,0]-x)*(b[:,0]-x)<0;p,q=a[m],b[m];hits=p+(q-p)*((x-p[:,0])/(q[:,0]-p[:,0]))[:,None];assert len(hits);rows.append(dict(t=float(t),width_m=float(hits[:,1].max()-hits[:,1].min())))
 peak=max(rows,key=lambda r:r['width_m']);target=cfg['body_axis_max_width_m'];head=float(v[:,1].max()-v[:,1].min());error=abs(peak['width_m']/target-1);he=abs(head/cfg['head_span_m']-1);pe=abs(peak['t']-cfg['body_width_peak_t']);r=dict(ok=error<=.02 and he<=.02 and pe<=.02,kind='actual_finite_static_shark_reference_width_trial',model_sha256=sha(model),reference_sha256=sha(reference),body_axis_m=axis,body_expected_width_m=target,body_actual_width_m=peak['width_m'],body_maximum_width_relative_error=error,body_reference_peak_t=cfg['body_width_peak_t'],body_actual_peak_t=peak['t'],body_peak_t_error=pe,head_expected_span_m=cfg['head_span_m'],head_actual_span_m=head,head_span_relative_error=he,actual_sections=rows,triangles=len(tri),checker_sha256=sha(__file__),formal_acceptance=False,limits='Finite static GLB,400-body-section samples excluding cephalofoil domain; global width/head span and peak consistency only.2% gates are trial representation criteria, not biological population uncertainty. Does not verify all local contours, tissue thickness, adult proportions, full fins, native lip materials, rig or motions. No complete-fish acceptance.')
 assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=check(a.model,a.reference,a.output);print(json.dumps({k:v for k,v in r.items()if k!='actual_sections'}));sys.exit(0 if r['ok']else 1)
