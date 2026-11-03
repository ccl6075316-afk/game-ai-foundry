"""Recheck raw packed lip bake against actual source, authored and final GLBs."""
import sys,json,hashlib,io,argparse
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE/'portable')]
from glb_io import read_glb,arrays
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mesh(p):
 d,b=read_glb(p);pr=d['meshes'][0]['primitives'][0]
 a={k:arrays(d,b,v) for k,v in pr['attributes'].items()};a['indices']=arrays(d,b,pr['indices'])
 view=d['bufferViews'][d['images'][0]['bufferView']];im=np.array(Image.open(io.BytesIO(b[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])).convert('RGBA'))
 return a,im
p=argparse.ArgumentParser();p.add_argument('--species',required=True);p.add_argument('--author',required=True);p.add_argument('--final',required=True);p.add_argument('--raw',required=True);p.add_argument('--output',required=True);a=p.parse_args()
rawpath=Path(a.raw).resolve();raw=json.loads(rawpath.read_text());source=Path(raw['source']['path']);assert sha(source)==raw['source']['sha256'];sourceim=np.array(Image.open(source).convert('RGBA'))
before=rawpath.parent.parent/'width-r1/fish.glb';old,oldim=mesh(before);author,im=mesh(a.author);final,fi=mesh(a.final)
guard={k:bool(np.array_equal(old[k],author[k])) for k in old};assert all(guard.values());final_guard={k:bool(np.array_equal(author[k],final[k]))for k in author};assert all(v for k,v in final_guard.items()if k!='POSITION');doc,_=read_glb(a.final);finids={i for q in doc['extras']['geometry_parts']if q['role']=='fin'for i in range(q['vertex_start'],q['vertex_start']+q['vertex_count'])};changed=np.flatnonzero(np.any(author['POSITION']!=final['POSITION'],axis=1));assert set(changed.tolist())<=finids
rows=raw['actual_native_donors'];core=[r for r in rows if r['distance_px']<=raw['complete_native_lip_ownership']['domain']['upper_width_px']]
errors=[];alphas=[];preserved=[];core_errors=[]
for r in rows:
 x,y=r['atlas_xy'];sx,sy=r['source_xy'];w=r['native_weight'];expect=np.rint(oldim[y,x,:3]*(1-w)+sourceim[sy,sx,:3]*w).astype('uint8')
 errors.append(int(abs(im[y,x,:3].astype(int)-expect).max()));alphas.append(int(sourceim[sy,sx,3]));preserved.append(bool(np.array_equal(im[y,x],fi[y,x])))
 if r in core:core_errors.append(int(abs(im[y,x,:3].astype(int)-sourceim[sy,sx,:3]).max()))
assert max(errors)==0 and min(alphas)>=243 and all(preserved) and max(core_errors)==0
assert np.array_equal(oldim[:,:,3],im[:,:,3]) and np.array_equal(im[:,:,3],fi[:,:,3])
binding=lambda p:{'path':str(Path(p).resolve()),'sha256':sha(p)}
out={'ok':True,'kind':'complete_anterior_semantic_color_chart','species':a.species,'source_sha256':sha(source),'model_sha256':sha(a.author),'source':binding(source),'material_author_model':binding(a.author),'current_model':binding(a.final),'raw_bake_report':binding(rawpath),'actual_3d_rim_transport':{k+'_edges':int(v['segments'])for k,v in raw['actual_3d_rim_transport'].items()},'geometry_weights_triangles_unchanged':all(guard.values()),'actual_array_equality':guard,'following_fin_geometry_exception':{'changed_vertices':changed.tolist(),'all_changed_positions_are_fin_only':True,'body_mouth_positions_UV_skin_indices_exact':True,'all_other_arrays_equal':final_guard},'actual_source_donor_alpha_minimum':min(alphas),'actual_baked_RGB_maximum_error':max(errors),'actual_core_original_RGB_maximum_error':max(core_errors),'complete_native_lip_ownership':{'protected_texels':len(core),'maximum_front_weight_inside_complete_lip':max(1-r['native_weight'] for r in core),'maximum_central_weight_inside_complete_lip':max(1-r['native_weight'] for r in core),'domain':raw['complete_native_lip_ownership']['domain']},'following_head_bottom_protection':{'measured_RGBA_identical_texels':sum(preserved),'total_native_core_and_fade_texels':len(rows),'maximum_RGBA_error':0},'alpha_exact':True,'scope':'Independently sampled every actual raw donor texel from the original source and actual embedded images. Complete core equals original source RGB. Author input/output/current geometry arrays equal. Current head-bottom baking preserves every lip core+fade RGBA. This numerical ownership evidence does not replace rendered mouth review.'}
Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['ok','actual_3d_rim_transport','complete_native_lip_ownership','following_head_bottom_protection']}))
