"""Author reference for explicit actual-body root skin fits and tiny fin offsets.

All fitting inputs are frozen; body/mouth/eyes/retained tail, native pixels,
topology, rig and clips stay unchanged. Source/cold authoring is the next step.
"""
import argparse,copy,json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent))
from glb_io import read_glb,arrays,sha
from patch_existing_fin_meshes import write
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fit',type=Path,required=True);p.add_argument('--offsets',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();fit=read(a.fit);source=Path(fit['model']);C=source.parent.parent;out=a.output.resolve();assert not out.exists()and out.is_relative_to(HERE.parents[3]/'projects/fishing-2d/experiments');out.mkdir(parents=True);assert sha(source)==fit['model_sha256']and sha(fit['source_blend'])==fit['source_blend_sha256'];d,b=read_glb(source);b=bytearray(b);pr=d['meshes'][0]['primitives'][0];v={k:arrays(d,b,x).copy()for k,x in pr['attributes'].items()};indices=arrays(d,b,pr['indices']).copy();parts=d['extras']['geometry_parts'];changed=[]
 for row in fit['changes']:
  i=row['vertex'];assert np.array_equal(v['JOINTS_0'][i],row['old_joints'])and np.max(abs(v['WEIGHTS_0'][i]-row['old_weights']))<1e-8;owner=next(p for p in parts if p['vertex_start']<=i<p['vertex_start']+p['vertex_count']);assert owner['role']=='fin'and owner['source_node']==row['fin']and row['fin']!='Caudal_mesh';v['JOINTS_0'][i]=row['new_joints'];v['WEIGHTS_0'][i]=row['new_weights'];assert (v['WEIGHTS_0'][i]>=0).all()and abs(v['WEIGHTS_0'][i].sum()-1)<1e-6;changed.append(i)
 offsets=read(a.offsets);scale=read(C/'source-run/final-spec.json')['viewer']['model_scale'];applied=[]
 for name,offset in offsets.items():
  part=next(p for p in parts if p['source_node']==name);assert part['role']=='fin'and name!='Caudal_mesh';delta=np.array(offset)/1000/scale;assert np.linalg.norm(offset)<=.2,'Review larger changes separately';lo=part['vertex_start'];hi=lo+part['vertex_count'];v['POSITION'][lo:hi]+=delta;applied.append({'name':name,'translation_mm':offset,'translation_native':delta.tolist()})
 def append(raw):
  b.extend(b'\0'*(-len(b)%4));o=len(b);b.extend(raw);i=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':o,'byteLength':len(raw)});return i
 for key in ['POSITION','JOINTS_0','WEIGHTS_0']:
  value=np.ascontiguousarray(v[key]);i=len(d['accessors']);row=copy.deepcopy(d['accessors'][pr['attributes'][key]]);row.update(bufferView=append(value.tobytes()),byteOffset=0,count=len(value))
  if key=='POSITION':row.update(min=value.min(0).tolist(),max=value.max(0).tolist())
  d['accessors'].append(row);pr['attributes'][key]=i
 dest=out/'author-reference.glb';write(dest,d,b);packing=read(C/'conformed/packing.validation.json');(out/'atlas.png').write_bytes((C/'conformed/atlas.png').read_bytes());(out/'parts.json').write_bytes((C/'conformed/parts.json').read_bytes());packing.update(atlas={**packing['atlas'],'path':str(out/'atlas.png'),'sha256':sha(out/'atlas.png')},candidates={'author-reference':{'path':str(dest),'sha256':sha(dest)}});save(out/'packing.validation.json',packing);auth=read(C/'conformed/author.validation.json')
 for row in auth['fins']:
  part=next(p for p in parts if p['source_node']==row['name']);row['root_band_rest_points_gltf']=v['POSITION'][np.array(row['root_band_ids'])+part['vertex_start']].tolist()
  if row['name']in fit['complete_fitted_fin_inventory']:row['root_strategy']='Complete original frozen root IDs retained; normalized <=4 actual body influences fitted to all490 finite-body trajectories, no amplitude/domain/collar changes.'
 auth.update(parent_candidate={'path':str(source),'sha256':sha(source)},root_skin_fit={'path':str(a.fit.resolve()),'sha256':sha(a.fit)},explicit_fin_offsets={'path':str(a.offsets.resolve()),'sha256':sha(a.offsets),'applied':applied},model=str(dest),model_sha256=sha(dest),static_finite_surface_check=False,physical_acceptance='Fresh current source/cold/static/full490 gates pending');save(out/'author.validation.json',auth);save(out/'skin-fit-application.validation.json',{'ok':True,'kind':'explicit_frozen_fin_root_skin_author_reference','source':str(source),'source_sha256':sha(source),'model':str(dest),'model_sha256':sha(dest),'fit_sha256':sha(a.fit),'changed_skin_vertices':changed,'offsets':applied,'topology_normals_UV_RGB_rig_animations_unchanged':True,'formal_acceptance':False});print(json.dumps({'ok':True,'skin_vertices':len(changed),'translated_fins':len(applied),'triangles':len(indices)//3}))
if __name__=='__main__':main()
