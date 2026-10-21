#!/usr/bin/env python3
"""Validate the actual emitted float32 Stage1 GLB, not CPU double geometry."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from validate_oral_cdt_108 import crossing
from probe_mouth_slit_stage1_108 import canvas

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def key(p):return tuple(np.asarray(p,dtype=np.float32).astype(float))
def boundary(v,f):
 ct=Counter();directed=defaultdict(list)
 for tri in f:
  for i,j in zip(tri,np.roll(tri,-1)):
   e=(key(v[i]),key(v[j]));k=tuple(sorted(e));ct[k]+=1;directed[k].append(e)
 return {k:directed[k][0]for k,n in ct.items()if n==1},sum(n>2 for n in ct.values()),ct

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();build=json.loads(a.input.with_name('build.validation.json').read_text());source=Path(build['source']);d,b=read_glb(a.input);od,ob=read_glb(source);mi=next(n['mesh']for n in d['nodes']if n.get('name')=='Closed_body');p=d['meshes'][mi]['primitives'];op=od['meshes'][mi]['primitives'];vs=[accessor(d,b,t['attributes']['POSITION']).astype(float)for t in p];fs=[accessor(d,b,t['indices']).reshape(-1,3)for t in p];ovs=[accessor(od,ob,t['attributes']['POSITION']).astype(float)for t in op];ofs=[accessor(od,ob,t['indices']).reshape(-1,3)for t in op];changed=[np.any(v[:len(o)]!=o,axis=1)for o,v in zip(ovs,vs)];changed[1]=np.r_[changed[1],np.ones(len(vs[1])-len(ovs[1]),bool)];verts=np.concatenate(vs);faces=np.concatenate([fs[0],fs[1]+len(vs[0])]);selection=np.concatenate(changed);cross=crossing(verts,faces,selection)
 bounds=[boundary(v,f)for v,f in zip(vs,fs)];same=set(bounds[0][0])==set(bounds[1][0]);opposed=all(bounds[0][0][k]==bounds[1][0][k][::-1]for k in bounds[0][0])if same else False;combined=bounds[0][2]+bounds[1][2];non2=sum(n!=2 for n in combined.values())
 oldboundary=[boundary(v,f)[0]for v,f in zip(ovs,ofs)];new397=set(bounds[1][0]);expected=set()
 # Boundary identity follows exact raw source vertex identity then actual output
 # mapping, not nearest points nor a tolerance weld.
 posmap={key(o):key(v)for o,v in zip(ovs[0],vs[0])}
 for o,v in zip(ovs[1],vs[1][:len(ovs[1])]):
  if key(o)in posmap:assert posmap[key(o)]==key(v)
  else:posmap[key(o)]=key(v)
 for edge in oldboundary[1]:expected.add(tuple(sorted(posmap[x]for x in edge)))
 source_alignment=a.input.parent.parent/'source-mouth-alignment.validation.json';alignment=json.loads(source_alignment.read_text());actual_skin=json.loads((a.input.parent.parent.parent/'eye-rollout-107/zander-mesh-rest.json').read_text());actualpos=np.asarray(actual_skin['rest_xyz'],dtype=np.float32);raw_lookup=defaultdict(list)
 for i,v in enumerate(ovs[0]):raw_lookup[key(v)].append(i)
 tips={}
 for name in ['upper','lower']:
  ids=sorted(set(i for aid in alignment['actual_tips'][name]['vertex_ids']for i in raw_lookup[key(actualpos[aid])]))
  assert ids;q=canvas(vs[0][ids]);tips[name]=dict(raw_vertex_ids=ids,source_x_minmax=[float(q[:,0].min()),float(q[:,0].max())],source_y_minmax=[float(q[:,1].min()),float(q[:,1].max())])
 deg=[]
 for i,(v,f)in enumerate(zip(vs,fs)):
  t=v[f];area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1);deg.append(dict(surface=i,triangles=len(f),area2_min=float(area.min()),area2_lte1e14=int((area<=1e-14).sum())))
 report=dict(ok=bool(cross['proper_crossings']==0 and cross['coplanar_positive_area_overlap_pairs']==0 and same and opposed and len(bounds[1][0])==397 and new397==expected and not bounds[0][1]and not bounds[1][1]and not non2 and all(x['area2_lte1e14']==0 for x in deg)),source_sha256=sha(source),model_sha256=sha(a.input),checker_sha256=sha(Path(__file__).with_name('validate_oral_cdt_108.py')),selection='all actual moved raw vertices plus all291 newupper attributevertices (all97faces)',all97_new_faces_selected=bool(selection[fs[1][-97:]+len(vs[0])].any(1).all()),actual_float32_base_crossing=cross,interface397=dict(count=len(bounds[1][0]),skin_oral_undirected_exact=same,skin_oral_directed_opposed_exact=opposed,old397_correspondence_exact=new397==expected,skin_nonmanifold_edges=bounds[0][1],oral_nonmanifold_edges=bounds[1][1],combined_edge_multiplicity_not2=non2),triangles=deg,tips=tips,stage2_chin_front_lip_y_uv_done=False,limits=['Actual emitted float32 GLB base only; not importedLOD or animation/fin/body delivery acceptance.','Old sourceUV preserved despite Stage1 geometry movement; cannot claim aligned material or completed lower chin.'])
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(ok=report['ok'],interface397=report['interface397'],crossings=cross['proper_crossings'],overlap=cross['coplanar_positive_area_overlap_pairs'],tips=tips)));raise SystemExit(0 if report['ok']else 1)
if __name__=='__main__':main()
