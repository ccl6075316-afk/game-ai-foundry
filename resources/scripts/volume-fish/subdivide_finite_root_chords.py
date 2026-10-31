"""Subdivide actual failing basal chords, preserving every original root point.

Input is an actual 490-pose export. This authors a new candidate, never a pass.
Only all-root triangles are considered; frozen root collars are unchanged.
"""
import argparse,copy,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays,sha
from patch_existing_fin_meshes import write
from fin_vertex_identity import native_to_actual
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
def tree_for(sample):
 vs=np.array(sample['body_vertices_m']);tr=np.array(sample['body_triangles'],int);vol=np.einsum('ij,ij->i',vs[tr[:,0]],np.cross(vs[tr[:,1]],vs[tr[:,2]])).sum()
 if vol<0:tr=tr[:,::-1]
 return BVHTree.FromPolygons(vs.tolist(),tr.tolist(),all_triangles=True),vs,tr
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['candidate','compact','export','output']:p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--fin',required=True);p.add_argument('--trigger-mm',type=float,default=.40);p.add_argument('--support-offset-mm',type=float,default=.30);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);assert .02<a.trigger_mm<.5 and 0<a.support_offset_mm<.5;C=a.candidate.resolve();out=a.output.resolve();assert not out.exists()and out.is_relative_to(HERE.parents[2]/'projects/fishing-2d/experiments');ex=read(a.export);model=C/'source-run/fish.glb';assert sha(model)==ex['model_sha256'];d,b=read_glb(model);b=bytearray(b);pr=d['meshes'][0]['primitives'][0];values={k:arrays(d,b,v).copy()for k,v in pr['attributes'].items()};idx=arrays(d,b,pr['indices']).reshape(-1,3);parts=d['extras']['geometry_parts'];part=next(x for x in parts if x['source_node']==a.fin);lo=part['vertex_start'];n=part['vertex_count'];auth=read(C/'conformed/author.validation.json');row=next(r for r in auth['fins']if r['name']==a.fin);roots=set(row['root_band_ids']);tri=idx[part['index_start']//3:(part['index_start']+part['index_count'])//3]-lo;selected={};direction=Vector((.231,.371,.899)).normalized()
 # Packed logical parts are reindexed by first triangle occurrence in Godot.
 # Prove a bijection from native vertices; never apply native face IDs to the
 # differently ordered posed array (even when both arrays have equal length).
 scale=read(C/'source-run/final-spec.json')['viewer']['model_scale'];static_pose=read(ex['samples'][0]['posed_mesh_json']);actual_rest=np.array(static_pose['membranes'][a.fin]['vertices_m']);mapping=native_to_actual(values['POSITION'][lo:lo+n],actual_rest,scale)
 # Inspect exact finite root-face probes against actual posed body surfaces.
 for si,sample in enumerate(ex['samples']):
  assert sha(sample['posed_mesh_json'])==sample['sha256'];pose=read(sample['posed_mesh_json']);tree,body,body_tri=tree_for(pose);v=np.array(pose['membranes'][a.fin]['vertices_m'])[mapping];assert len(v)==n
  lower=body.min(0);upper=body.max(0)
  for ids in tri:
   if not all(int(j)in roots for j in ids):continue
   q=v[ids];probes=[q.mean(0),*[q[i]*.6+q[(i+1)%3]*.2+q[(i+2)%3]*.2 for i in range(3)]]
   for i in range(3):probes.extend(q[i]*(1-t)+q[(i+1)%3]*t for t in [.25,.5,.75])
   bad=False
   for pt in probes:
    if np.any(pt<lower-1e-8)or np.any(pt>upper+1e-8):continue
    _,_,_,dist=tree.find_nearest(Vector(pt))
    if dist<a.trigger_mm/1000:continue
    hit,normal,_,_=tree.ray_cast(Vector(pt),direction)
    if hit is not None and normal.dot(direction)>0:bad=True;break
   if bad:
    edges=[tuple(sorted((int(ids[i]),int(ids[(i+1)%3]))))for i in range(3)];edge=max(edges,key=lambda e:np.linalg.norm(v[e[0]]-v[e[1]]));selected.setdefault(edge,[]).append(si)
 assert selected,'No actual failing basal chords';assert len(idx)+2*len(selected)<=2000,(len(idx),len(selected));out.mkdir(parents=True)
 static=read(ex['samples'][0]['posed_mesh_json']);assert ex['samples'][0]['action']=='Static';tree,body,body_tri=tree_for(static);scale=read(C/'source-run/final-spec.json')['viewer']['model_scale'];rest=read(a.compact/'rest-skin.json');joint_names=[d['nodes'][j]['name']for j in d['skins'][0]['joints']];remap={i:joint_names.index(n)for i,n in enumerate(rest['joint_names'])if n in joint_names};body_skin=[]
 for r in rest['surfaces']:
  if r['body']:body_skin.extend(zip(np.array(r['joints']).reshape(-1,4),np.array(r['weights']).reshape(-1,4)))
 assert len(body_skin)==len(body)
 bpy.ops.wm.open_mainfile(filepath=str(C/'volume-source/fish.blend'));ob=bpy.data.objects[a.fin];ts=np.array([r.value for r in ob.data.attributes['foundry_fin_source_t'].data]);assert len(ts)==n
 local={k:list(v[lo:lo+n])for k,v in values.items()};new_ts=ts.tolist();faces=tri.tolist();added=[]
 for (aa,bb),samples in sorted(selected.items()):
  midpoint=(np.array(local['POSITION'][aa])+local['POSITION'][bb])/2;hit,normal,fi,dist=tree.find_nearest(Vector(midpoint*scale));beta=np.maximum(np.array(barycentric_transform(hit,*[Vector(body[j])for j in body_tri[fi]],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))),0);beta/=beta.sum();weights={}
  for j,gain in zip(body_tri[fi],beta):
   js,ws=body_skin[j]
   for bone,w in zip(js,ws):
    if w>0:weights[remap[int(bone)]]=weights.get(remap[int(bone)],0)+gain*w
  ordered=sorted(weights,key=weights.get,reverse=True)[:4];ws=np.array([weights[j]for j in ordered]);ws/=ws.sum();i=len(local['POSITION']);point=(np.array(hit)+np.array(normal)*a.support_offset_mm/1000)/scale
  for k in local:
   value=(np.array(local[k][aa])+np.array(local[k][bb]))/2
   if k=='POSITION':value=point
   elif k=='NORMAL':value/=max(np.linalg.norm(value),1e-12)
   elif k=='JOINTS_0':value=np.array(ordered+[0]*(4-len(ordered)))
   elif k=='WEIGHTS_0':value=np.r_[ws,np.zeros(4-len(ws))]
   local[k].append(value)
  new_ts.append(float((ts[aa]+ts[bb])/2));new_faces=[]
  for f in faces:
   if aa in f and bb in f:
    k=next(k for k in range(3)if set([f[k],f[(k+1)%3]])==set([aa,bb]));x,y,z=f[k],f[(k+1)%3],f[(k+2)%3];new_faces.extend([[x,i,z],[i,y,z]])
   else:new_faces.append(f)
  faces=new_faces;added.append({'edge':[aa,bb],'vertex':i,'actual_pose_ids':sorted(set(samples)),'static_projection_distance_mm':dist*1000})
 # Preserve all original vertices/UVs, add finite-body support midpoints only.
 vals={k:[]for k in values};new_idx=[];new_parts=[];packing=read(C/'conformed/packing.validation.json');vo=io=0
 for old,packed in zip(parts,packing['parts']):
  start=old['vertex_start'];end=start+old['vertex_count'];arr={k:(np.array(local[k],dtype=values[k].dtype)if old is part else v[start:end])for k,v in values.items()};tr=np.array(faces)if old is part else idx[old['index_start']//3:(old['index_start']+old['index_count'])//3]-start
  for k in vals:vals[k].append(arr[k])
  nr=copy.deepcopy(old);nr.update(vertex_start=vo,source_vertex_start=vo,vertex_count=len(arr['POSITION']),index_start=io,index_count=tr.size);new_parts.append(nr);packed.update(new_vertex_range=[vo,vo+nr['vertex_count']],new_index_range=[io,io+tr.size]);new_idx.extend((tr+vo).reshape(-1));vo+=nr['vertex_count'];io+=tr.size
 d['extras']['geometry_parts']=new_parts
 def put(ar,old_accessor):
  ar=np.ascontiguousarray(ar);b.extend(b'\0'*(-len(b)%4));offset=len(b);b.extend(ar.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':ar.nbytes});r=copy.deepcopy(d['accessors'][old_accessor]);r.update(bufferView=vi,byteOffset=0,count=len(ar))
  if r['type']=='VEC3':r.update(min=ar.min(0).tolist(),max=ar.max(0).tolist())
  ai=len(d['accessors']);d['accessors'].append(r);return ai
 for k in vals:pr['attributes'][k]=put(np.concatenate(vals[k]),pr['attributes'][k])
 pr['indices']=put(np.array(new_idx,dtype=np.uint32),pr['indices']);d['accessors'][pr['indices']].update(componentType=5125,min=[int(min(new_idx))],max=[int(max(new_idx))]);dest=out/'author-reference.glb';write(dest,d,b)
 for name in ['atlas.png','parts.json']:(out/name).write_bytes((C/'conformed'/name).read_bytes())
 packing.update(candidates={'author-reference':{'path':str(dest),'sha256':sha(dest)}},atlas={**packing['atlas'],'path':str(out/'atlas.png'),'sha256':sha(out/'atlas.png')});save(out/'packing.validation.json',packing)
 row.update(root_band_ids=sorted(roots|set(range(n,len(local['POSITION'])))),source_parameter_explicit=new_ts,triangles=len(faces),root_strategy='Every original root retained; actual failing finite basal chords subdivided with body-surface midpoint support; no root collar/domain reduction.')
 for r in auth['fins']:
  part2=next(p for p in new_parts if p['source_node']==r['name']);v2=np.concatenate(vals['POSITION'])[part2['vertex_start']:part2['vertex_start']+part2['vertex_count']];r['root_band_rest_points_gltf']=v2[r['root_band_ids']].tolist()
 auth.update(model=str(dest),model_sha256=sha(dest),triangles_after=len(new_idx)//3,parent_model=str(model),parent_model_sha256=sha(model),finite_chord_subdivision={'export':str(a.export.resolve()),'export_sha256':sha(a.export),'added':added},formal_acceptance=False);save(out/'author.validation.json',auth);print(json.dumps({'ok':True,'edges':len(added),'triangles':len(new_idx)//3}))
if __name__=='__main__':main()
