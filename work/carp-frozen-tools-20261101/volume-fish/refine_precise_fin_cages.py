"""Rebuild explicitly masked native fin support within the current whole-fish cap.

Uses each fish's existing finite-shell placement and thickness parameters. This
is an isolated authoring reference: root conformity, cold export, actual rays,
full posed checks and visual review are separate mandatory steps.
"""
import argparse,copy,io,json,sys,hashlib
from pathlib import Path
import numpy as np,cv2
from PIL import Image
from scipy.spatial import Delaunay
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha
from patch_existing_fin_meshes import write
from refine_native_fin_cages import support_polygon,line_distance
from native_fin_support import polygon as basal_support,triangulate as basal_triangulate,improve_interior_edges
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sampler(uv,pos,js,ws,tri,bones):
 t=uv[tri];a=t[:,0];mat=np.stack([t[:,1]-a,t[:,2]-a],2);det=np.linalg.det(mat);valid=abs(det)>1e-4;tri=tri[valid];a=a[valid];mat=mat[valid];det=det[valid];inv=np.linalg.inv(mat);functions=[]
 for sign in [1,-1]:
  ids=np.where(det*sign>0)[0];assert len(ids)
  def sample(q,ids=ids):
   bc=np.einsum('nij,nj->ni',inv[ids],q-a[ids]);bary=np.c_[1-bc.sum(1),bc];cl=np.maximum(bary,0);cl/=cl.sum(1)[:,None];proj=np.einsum('ni,nij->nj',cl,uv[tri[ids]]);dist=((proj-q)**2).sum(1);dist[(bary>=-1e-6).all(1)]=0;k=int(np.argmin(dist));vs=tri[ids[k]];p=bary[k]@pos[vs];mix=np.zeros(bones)
   for v,gain in zip(vs,cl[k]):
    for j,w in zip(js[v],ws[v]):mix[int(j)]+=gain*w
   mix[mix<1e-4]=0;j=np.argsort(-mix)[:4];w=mix[j];w/=w.sum();return p,j,w
  functions.append(sample)
 return functions
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['entry','output']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();entry=load(a.entry);out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True)
 baseline=Path(entry['output'])/'width-r1/fish.glb';masks_path=Path(entry['fin_cage'].get('masks',str(Path(entry['output'])/'masks-r4/masks.validation.json')));cfg=load(masks_path);uv_audit=load(Path(entry['output'])/'uv-mask-audit.validation.json');domain=load(Path(entry['output'])/'fin-mask-audit/source-domain.json');spec=load(entry['baseline_spec']['path']);pack=load(ROOT/spec['inputs']['packing_report']['path']);thickness=load(entry['fin_cage']['thickness_config']);support_sides=entry['fin_cage']['support_sides'];tile_origins={};tiles={}
 assert sha(entry['baseline_model']['path'])==entry['baseline_model']['sha256'];d,b=read_glb(baseline);b=bytearray(b);pr=d['meshes'][0]['primitives'][0];values={k:arrays(d,b,v)for k,v in pr['attributes'].items()};idx=arrays(d,b,pr['indices']).reshape(-1);bones=len(d['skins'][0]['joints']);iv=d['bufferViews'][d['images'][0]['bufferView']];atlas=Image.open(io.BytesIO(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])).convert('RGBA');size=np.array(atlas.size);repair={r['fin']:r for r in cfg['fins']};fixed=[];places={};scale=thickness['model_scale']
 for row,part in zip(pack['parts'],d['extras']['geometry_parts']):
  if not any(part['source_node'].startswith(k+'_')for k in repair):
   x,y=row['atlas_placement'];w,h=row['virtual_crop_size'];fixed.append((x-3,y-3,x+w+3,y+h+3))
 for name,rec in sorted(repair.items(),key=lambda x:-np.prod(Image.open(x[1]['image']).size)):
  original=Image.open(rec['image']).convert('RGBA');hull=basal_support(np.array(original)[:,:,3]>127,rec['source_root_local_px'],support_sides,rec['annotation']['root_side'],rec['annotation'].get('support_margin_px',2.5),entry['fin_cage'].get('support_simplify_px',{}).get(name,0));origin=np.minimum(np.floor(hull.min(0)).astype(int)-4,0);end=np.maximum(np.ceil(hull.max(0)).astype(int)+4,original.size);image=Image.new('RGBA',tuple(end-origin));image.paste(original,tuple(-origin));tile_origins[name]=origin;tiles[name]=image;w,h=image.size;chosen=None
  for y in sorted(set([3]+[max(3,r[3])for r in fixed])):
   for x in sorted(set([3]+[max(3,r[2])for r in fixed])):
    r=(x,y,x+w+6,y+h+6)
    if r[2]<=size[0]and r[3]<=size[1]and not any(r[0]<z[2]and z[0]<r[2]and r[1]<z[3]and z[1]<r[3]for z in fixed):chosen=r;break
   if chosen:break
  assert chosen,'Native atlas allocation failed';fixed.append(chosen);places[name]=np.array(chosen[:2])+3;atlas.paste(image,tuple(places[name]))
 vals={k:[]for k in values};indices=[];parts=[];rows=[];records=[];vo=ioff=0
 for part,packed in zip(d['extras']['geometry_parts'],pack['parts']):
  lo=part['vertex_start'];hi=lo+part['vertex_count'];i0=part['index_start'];ti=idx[i0:i0+part['index_count']].astype(int)-lo;v={k:x[lo:hi].copy()for k,x in values.items()};kind=next((k for k in repair if part['source_node'].startswith(k+'_')),None);row=copy.deepcopy(packed)
  if kind:
   mr=repair[kind];root=np.array(mr['source_root_local_px']);mask=np.array(Image.open(mr['image']))[:,:,3]>127;oldrec=next(r for r in uv_audit['fins']if r['fin']==kind);cx,cy,_,_=oldrec['old_crop_in_context'];uv=v['TEXCOORD_0']*size-(np.array(packed['atlas_placement'])-packed['virtual_crop_origin'])+[cx,cy]
   sample=sampler(uv,v['POSITION'],v['JOINTS_0'],v['WEIGHTS_0'],ti.reshape(-1,3),bones);seeds=basal_support(mask,root,support_sides,mr['annotation']['root_side'],mr['annotation'].get('support_margin_px',2.5),entry['fin_cage'].get('support_simplify_px',{}).get(kind,0));tri=basal_triangulate(seeds)
   painted=np.array(np.nonzero(mask)[::-1]).T[::3]+.5;aa=root[:-1];vv=np.diff(root,axis=0);tt=np.clip(((painted[:,None,:]-aa)*vv).sum(2)/np.maximum((vv*vv).sum(1),1e-12),0,1);dd=np.linalg.norm(painted[:,None,:]-aa-tt[:,:,None]*vv,axis=2).min(1);maximum=float(dd.max());oldroot=np.array(next(r for r in domain['fins']if r['fin']==kind)['source_baseline_px'])-mr['source_crop'][:2];oldfin=next(r for r in load(entry['profile']['path'])['fins']if r['name']==kind);oldmax=max(line_distance(q,oldroot)for q in uv);band_px=max(17.,oldfin['root_attachment']['root_band']*oldmax)
   controls=entry['fin_cage'].get('foil_controls',{}).get(kind,[.30]);row_fractions=entry['fin_cage'].get('proximal_row_fractions',{}).get(kind,[]);locations=[]
   if row_fractions:
    arclength=np.r_[0,np.cumsum(np.linalg.norm(np.diff(root,axis=0),axis=1))]
    for fraction in row_fractions:locations.append((max(.10,(band_px+4)/maximum),np.array([np.interp(fraction*arclength[-1],arclength,root[:,i])for i in [0,1]])))
    controls=controls[1:]
   locations.extend((t,painted.mean(0))for t in controls)
   for control_t,near in locations:
    target=max(control_t,(band_px+4)/maximum);band=abs(dd/maximum-target)<.025;choices=painted[band];assert len(choices);center=choices[np.argmin(((choices-near)**2).sum(1))];selected=None
    for j,f in enumerate(tri):
     xy=seeds[f];matrix=np.column_stack([xy[1]-xy[0],xy[2]-xy[0]]);bc=np.linalg.solve(matrix,center-xy[0])
     if min(*bc,1-bc.sum())>1e-6:selected=j;break
    assert selected is not None,'Proximal foil control must be strictly inside the native support';center_id=len(seeds);seeds=np.r_[seeds,center[None,:]];first=tri[selected];tri=np.r_[np.delete(tri,selected,axis=0),np.array([(first[0],first[1],center_id),(first[1],first[2],center_id),(first[2],first[0],center_id)])]
   tri=improve_interior_edges(seeds,tri);n=len(seeds);pos=[];js=[];ws=[]
   coverage=np.zeros(mask.shape,np.uint8)
   for t0 in tri:cv2.fillConvexPoly(coverage,np.rint(seeds[t0]).astype(np.int32),1)
   assert not (mask&(coverage==0)).any(),(kind,'Source alpha clipped by support')
   for fn in sample:
    for q in seeds:
     pp,j,w=fn(q);pos.append(pp);js.append(j);ws.append(w)
   pos=np.array(pos);direction=np.mean(pos[:n]-pos[n:],axis=0);direction/=np.linalg.norm(direction)
   # The previous accepted-to-continue per-fish taper remains the authoring
   # target; extrapolating old edge thickness could invert the shell.
   mid=(pos[:n]+pos[n:])/2;dist=np.array([line_distance(q,root)for q in seeds]);maxdist=max(line_distance(q,root)for q in np.array(np.nonzero(mask)[::-1]).T[::5]);t=np.clip(dist/maxdist,0,1);foil=thickness['fins'][kind]
   if kind in entry['fin_cage'].get('planar_foil_kinds',[]):
    valid=np.array([line_distance(q,oldroot)>band_px for q in uv]);assert valid.sum()>=6;coeff=np.linalg.lstsq(np.c_[uv[valid],np.ones(valid.sum())],v['POSITION'][valid],rcond=None)[0];mid=np.c_[seeds,np.ones(n)]@coeff;normal=np.cross(coeff[0],coeff[1]);normal/=np.linalg.norm(normal)
    if np.dot(normal,direction)<0:normal=-normal
    direction=normal
   mm=np.interp(t,[0,.5,1],[foil['root_mm'],foil['mid_mm'],foil['edge_mm']]);half=mm/1000/scale/2;pos=np.r_[mid+half[:,None]*direction,mid-half[:,None]*direction]
   for i,f in enumerate(tri):
    x,y,z=pos[f]
    if np.dot(np.cross(y-x,z-x),direction)<0:tri[i]=f[::-1]
   faces=[*tri,*[f[::-1]+n for f in tri]];edges={}
   for f in tri:
    for aa,bb in zip(f,np.roll(f,-1)):edges.setdefault(tuple(sorted([int(aa),int(bb)])),[]).append((int(aa),int(bb)))
   for edge in edges.values():
    if len(edge)==1:aa,bb=edge[0];faces.extend([(bb,aa,aa+n),(bb,aa+n,bb+n)])
   faces=np.array(faces,np.uint32);norm=np.zeros_like(pos)
   for f in faces:
    x,y,z=pos[f];normal=np.cross(y-x,z-x)
    for j in f:norm[j]+=normal
   norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-12);v={'POSITION':pos.astype('<f4'),'NORMAL':norm.astype('<f4'),'TEXCOORD_0':((np.r_[seeds,seeds]+places[kind]-tile_origins[kind])/size).astype('<f4'),'JOINTS_0':np.array(js,dtype='<u2'),'WEIGHTS_0':np.array(ws,dtype='<f4')};ti=faces.reshape(-1)
   oldroot=np.array(next(r for r in domain['fins']if r['fin']==kind)['source_baseline_px'])-mr['source_crop'][:2];oldfin=next(r for r in load(entry['profile']['path'])['fins']if r['name']==kind);oldmax=max(line_distance(q,oldroot)for q in uv);band_px=max(17.,oldfin['root_attachment']['root_band']*oldmax);rids=[i for i,q in enumerate(seeds)if line_distance(q,root)<=band_px];rids+= [i+n for i in rids]
   records.append({'name':part['source_node'],'kind':kind,'triangles':len(faces),'layer_vertices':n,'root_band_px':band_px,'root_px':root.tolist(),'root_band_ids':rids,'root_band_rest_points_gltf':pos[rids].tolist(),'foil_target_mm':foil,'source_t':np.r_[t,t].tolist(),'source_band_fraction':oldfin['root_attachment']['root_band'],'geometry_placement':'Existing own finite layers sampled independently; original rig and source-root width retained; root conformity pending.'})
   row.update(atlas_placement=places[kind].tolist(),virtual_crop_origin=tile_origins[kind].tolist(),virtual_crop_size=list(tiles[kind].size),source_size=list(Image.open(mr['image']).size),source_RGBA_sha256=hashlib.sha256(np.array(Image.open(mr['image']).convert('RGBA')).tobytes()).hexdigest())
  for k in vals:vals[k].append(v[k])
  count=len(v['POSITION']);indices.extend((ti+vo).tolist());np_=copy.deepcopy(part);np_.update(vertex_start=vo,source_vertex_start=vo,vertex_count=count,index_start=ioff,index_count=len(ti));parts.append(np_);row.update(new_vertex_range=[vo,vo+count],new_index_range=[ioff,ioff+len(ti)]);rows.append(row);vo+=count;ioff+=len(ti)
 assert ioff//3<=2000,(ioff//3,'Whole-fish hard cap');d['extras']['geometry_parts']=parts
 def append(raw):
  b.extend(b'\0'*(-len(b)%4));o=len(b);b.extend(raw);i=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':o,'byteLength':len(raw)});return i
 def put(ar,kind,ctype):
  ar=np.ascontiguousarray(ar);i=len(d['accessors']);row={'bufferView':append(ar.tobytes()),'componentType':ctype,'count':len(ar),'type':kind}
  if kind=='VEC3':row.update(min=ar.min(0).tolist(),max=ar.max(0).tolist())
  d['accessors'].append(row);return i
 for k in values:pr['attributes'][k]=put(np.concatenate(vals[k]).astype('<u2'if k=='JOINTS_0'else'<f4'),{'POSITION':'VEC3','NORMAL':'VEC3','TEXCOORD_0':'VEC2','JOINTS_0':'VEC4','WEIGHTS_0':'VEC4'}[k],5123 if k=='JOINTS_0'else 5126)
 pr['indices']=put(np.array(indices,dtype='<u4'),'SCALAR',5125);atlas.save(out/'atlas.png');d['images'][0]['bufferView']=append((out/'atlas.png').read_bytes());dest=out/'author-reference.glb';write(dest,d,b)
 save(out/'packing.validation.json',{'ok':True,'kind':'precise_native_fin_cage_packing','candidates':{'author-reference':{'path':str(dest),'sha256':sha(dest)}},'parts':rows,'atlas':{'path':str(out/'atlas.png'),'sha256':sha(out/'atlas.png'),'size':size.tolist()}});save(out/'parts.json',{k:spec[k]for k in ['parts','species','game','motion','viewer']if k in spec})
 save(out/'author.validation.json',{'ok':True,'kind':'precise_native_fin_support_reference','species':entry['species'],'baseline':{'path':str(baseline),'sha256':sha(baseline)},'input_masks':{'path':str(masks_path),'sha256':sha(masks_path)},'entry':str(a.entry.resolve()),'triangles_before':len(idx)//3,'triangles_after':ioff//3,'bones':bones,'fins':records,'model':str(dest),'model_sha256':sha(dest),'formal_acceptance':False,'root_conformity':'pending','scope':'Small native-alpha support cages; body/mouth/eyes/caudal and all rig/actions unchanged. Not a completed fish.'});print(json.dumps({'ok':True,'species':entry['species'],'triangles':ioff//3,'bones':bones}))
if __name__=='__main__':main()
