"""Refine explicit fin patches from native source masks; preserve every other part.

This authors an isolated review reference, not an installed/accepted fish. Rig,
animations, body, mouth, eyes and retained fins are copied exactly. A small cage
supports source alpha detail; it never tessellates individual texture pixels.
"""
import argparse,copy,hashlib,io,json,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial import ConvexHull,Delaunay
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha
from patch_existing_fin_meshes import write
ROOT=HERE.parents[2]
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def line_distance(q,line):
 a=line[:-1];v=np.diff(line,axis=0);t=np.clip(((q-a)*v).sum(1)/np.maximum((v*v).sum(1),1e-12),0,1);r=a+t[:,None]*v;i=np.argmin(((r-q)**2).sum(1));return float(np.linalg.norm(r[i]-q))
def support_polygon(mask,n=14):
 yy,xx=np.nonzero(mask);pts=np.c_[xx+.5,yy+.5];angles=np.arange(n)*2*np.pi/n;norm=np.c_[np.cos(angles),np.sin(angles)];h=np.max(pts@norm.T,axis=0)+1.6
 return np.array([np.linalg.solve(np.array([norm[i],norm[(i+1)%n]]),[h[i],h[(i+1)%n]])for i in range(n)])
def sampler(uv,pos,joints,weights,tri):
 t=uv[tri];a=t[:,0];mat=np.stack([t[:,1]-a,t[:,2]-a],axis=2);det=np.linalg.det(mat);keep=np.abs(det)>1e-5
 tri=tri[keep];a=a[keep];mat=mat[keep];det=det[keep];inv=np.linalg.inv(mat)
 groups=[]
 for sign in [1,-1]:
  ids=np.where(det*sign>0)[0];assert len(ids)
  def sample(q,ids=ids):
   bc=np.einsum('nij,nj->ni',inv[ids],q-a[ids]);bary=np.c_[1-bc.sum(1),bc];cl=np.maximum(bary,0);cl/=cl.sum(1)[:,None];projected=np.einsum('ni,nij->nj',cl,uv[tri[ids]])
   inside=(bary>=-1e-6).all(1);dist=((projected-q)**2).sum(1);dist[inside]=0;k=int(np.argmin(dist));ids3=tri[ids[k]];w=bary[k]
   # Affine geometry may extend just beyond the old coarse cut. Skin weights
   # remain convex and normalized; no negative joint influence is introduced.
   p=w@pos[ids3];mix=np.zeros(18)
   for vertex,gain in zip(ids3,cl[k]):
    for j,value in zip(joints[vertex],weights[vertex]):mix[int(j)]+=gain*value
   mix[mix<1e-4]=0
   js=np.argsort(-mix)[:4];ws=mix[js];ws/=ws.sum();return p,js,ws
  groups.append(sample)
 return groups
def make_fin(old,tri,uvpx,maskrec,placement,atlas_size,settings):
 image=Image.open(maskrec['image']).convert('RGBA');mask=np.array(image)[:,:,3]>127;root=np.array(maskrec['root_px']);hull=support_polygon(mask,settings['support_sides'])
 unique=np.unique(np.round(uvpx,5),axis=0);near=np.array([q for q in unique if line_distance(q,root)<=5])
 cap=settings['basal_seed_limit']
 if len(near)>cap:near=near[np.linspace(0,len(near)-1,cap).round().astype(int)]
 if not len(near):near=unique[np.argsort([line_distance(q,root)for q in unique])[:4]]
 center=np.mean(np.argwhere(mask)[:,::-1],axis=0);bands=[]
 for base in root[np.linspace(0,len(root)-1,3).round().astype(int)]:
  direction=center-base;direction/=max(np.linalg.norm(direction),1e-12);bands.append(base+direction*8)
 seeds=np.r_[hull,near,root.mean(0)[None,:],center[None,:],bands];seeds=np.unique(np.round(seeds,5),axis=0)
 assert len(seeds)<=maskrec['max_layer_vertices'],(len(seeds),maskrec['max_layer_vertices'])
 dt=Delaunay(seeds);faces=dt.simplices.copy();boundary=ConvexHull(seeds).vertices
 sample=sampler(uvpx,old['POSITION'],old['JOINTS_0'],old['WEIGHTS_0'],tri)
 positions=[];joint=[];weight=[]
 for fn in sample:
  for q in seeds:
   p,j,w=fn(q);positions.append(p);joint.append(j);weight.append(w)
 positions=np.array(positions);n=len(seeds)
 # Orient the front cap toward the sampled layer separation, retaining old
 # thickness and root location instead of applying a guessed species spread.
 direction=np.mean(positions[:n]-positions[n:],axis=0)
 for i,f in enumerate(faces):
  a,b,c=positions[f]
  if np.dot(np.cross(b-a,c-a),direction)<0:faces[i]=f[::-1]
 outfaces=[*faces,*[f[::-1]+n for f in faces]];edges={}
 for f in faces:
  for a,b in zip(f,np.roll(f,-1)):
   key=tuple(sorted([int(a),int(b)]));edges.setdefault(key,[]).append((int(a),int(b)))
 for rows in edges.values():
  if len(rows)==1:
   a,b=rows[0];outfaces.extend([(b,a,a+n),(b,a+n,b+n)])
 outfaces=np.array(outfaces,dtype=np.uint32);normals=np.zeros_like(positions)
 for f in outfaces:
  a,b,c=positions[f];normal=np.cross(b-a,c-a)
  for v in f:normals[v]+=normal
 normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
 uv=(np.r_[seeds,seeds]+placement)/atlas_size
 result={'POSITION':positions.astype('<f4'),'NORMAL':normals.astype('<f4'),'TEXCOORD_0':uv.astype('<f4'),'JOINTS_0':np.array(joint,dtype='<u2'),'WEIGHTS_0':np.array(weight,dtype='<f4')}
 root_ids=[i for i,q in enumerate(seeds)if line_distance(q,root)<=17];root_ids+= [i+n for i in root_ids]
 return result,outfaces.reshape(-1),{'layer_vertices':n,'triangles':len(outfaces),'root_source_points':near.tolist(),'root_band_rest_points_gltf':positions[root_ids].tolist(),'root_band_ids':root_ids,'source_mask_pixels':int(mask.sum()),'support_contains_native_alpha':True,'root_strategy':'old UV-surface interpolation, original joint influences; finite source band, no body modification','physical_acceptance':'pending'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--masks',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();cfg=load(a.masks);audit=load(cfg['audit']);out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();out.mkdir(parents=True)
 settings_path=ROOT/'resources/volume-fish/fin-detail-cage-20261031.json';settings=load(settings_path)[cfg['species']]
 model=Path(cfg['model']);assert sha(model)==cfg['model_sha256'];baseline=load(model.parent/'deformation.plan.json');oldspec=load(Path(baseline['inputs']['model']['path']).parent/'final-spec.json');oldpack=load(ROOT/oldspec['inputs']['packing_report']['path'])
 d,b=read_glb(model);b=bytearray(b);pr=d['meshes'][0]['primitives'][0];values={k:arrays(d,b,v)for k,v in pr['attributes'].items()};indices=arrays(d,b,pr['indices']).reshape(-1);original_image_view=d['bufferViews'][d['images'][0]['bufferView']];iv=original_image_view;atlas=Image.open(io.BytesIO(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])).convert('RGBA');size=np.array(atlas.size)
 parts=d['extras']['geometry_parts'];repair={r['name']:r for r in cfg['fins']};fixed=[]
 for row,part in zip(oldpack['parts'],parts):
  if not any(part['source_node'].startswith(k+'_')for k in repair):
   x,y=row['atlas_placement'];w,h=row['virtual_crop_size'];fixed.append((x-3,y-3,x+w+3,y+h+3))
 def allocate(w,h):
  for y in sorted(set([3]+[max(3,r[3])for r in fixed])):
   for x in sorted(set([3]+[max(3,r[2])for r in fixed])):
    r=(x,y,x+w+6,y+h+6)
    if r[2]>size[0]or r[3]>size[1]:continue
    if any(r[0]<z[2]and z[0]<r[2]and r[1]<z[3]and z[1]<r[3]for z in fixed):continue
    fixed.append(r);return np.array([x+3,y+3])
  raise ValueError('No existing-atlas space for native fin cutouts')
 places={}
 for name,rec in sorted(repair.items(),key=lambda item:-np.prod(item[1]['size'])):
  image=Image.open(rec['image']).convert('RGBA');assert sha(rec['image'])==rec['image_sha256'];places[name]=allocate(*image.size);atlas.paste(image,tuple(places[name]))
 newvalues={k:[]for k in values};newindices=[];newparts=[];packrows=[];records=[];vo=ioff=0
 for ordinal,(part,oldrow)in enumerate(zip(parts,oldpack['parts'])):
  lo=part.get('vertex_start',part.get('source_vertex_start'));hi=lo+part['vertex_count'];i0=part['index_start'];i1=i0+part['index_count'];v={k:x[lo:hi].copy()for k,x in values.items()};tri=indices[i0:i1].astype('int64')-lo;name=next((k for k in repair if part['source_node'].startswith(k+'_')),None)
  row=copy.deepcopy(oldrow)
  if name:
   rec=repair[name];auditrow=next(r for r in audit['fins']if r['fin']==name);origin=np.array(oldrow['atlas_placement'])-oldrow['virtual_crop_origin'];oldcrop=np.array(auditrow['source_crop'][:2]);uvpx=v['TEXCOORD_0']*size-origin+oldcrop-np.array(rec['crop'][:2]);v,tri,proof=make_fin(v,tri.reshape(-1,3),uvpx,rec,places[name],size,settings);proof.update(name=part['source_node']);records.append(proof)
   row.update(atlas_placement=places[name].tolist(),virtual_crop_origin=[0,0],virtual_crop_size=rec['size'],source_size=rec['size'],source_RGBA_sha256=hashlib.sha256(np.array(Image.open(rec['image']).convert('RGBA')).tobytes()).hexdigest())
  else:
   assert all(np.array_equal(v[k],values[k][lo:hi])for k in values),'Protected part changed'
  for k in values:newvalues[k].append(v[k])
  newindices.extend((tri+vo).tolist());n=len(v['POSITION']);count=len(tri);np_=copy.deepcopy(part);np_.update(vertex_start=vo,source_vertex_start=vo,vertex_count=n,index_start=ioff,index_count=count);np_.pop('vertex_range',None);np_.pop('index_range',None);newparts.append(np_);row.update(new_vertex_range=[vo,vo+n],new_index_range=[ioff,ioff+count]);packrows.append(row);vo+=n;ioff+=count
 assert ioff//3<=2000,(ioff//3,'Whole-fish hard cap');d['extras']['geometry_parts']=newparts
 def append_bytes(raw):
  b.extend(b'\0'*(-len(b)%4));offset=len(b);b.extend(raw);v=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)});return v
 def accessor(data,kind,ctype):
  data=np.ascontiguousarray(data);idx=len(d['accessors']);ac={'bufferView':append_bytes(data.tobytes()),'componentType':ctype,'count':len(data),'type':kind}
  if kind=='VEC3':ac.update(min=data.min(0).tolist(),max=data.max(0).tolist())
  d['accessors'].append(ac);return idx
 for k in values:
  ar=np.concatenate(newvalues[k]).astype('<u2' if k=='JOINTS_0' else '<f4');pr['attributes'][k]=accessor(ar,{'POSITION':'VEC3','NORMAL':'VEC3','TEXCOORD_0':'VEC2','JOINTS_0':'VEC4','WEIGHTS_0':'VEC4'}[k],5123 if k=='JOINTS_0' else 5126)
 pr['indices']=accessor(np.array(newindices,dtype='<u4'),'SCALAR',5125);atlaspath=out/'atlas.png';atlas.save(atlaspath);d['images'][0]['bufferView']=append_bytes(atlaspath.read_bytes());dest=out/'author-reference.glb';write(dest,d,b)
 pack={'ok':True,'kind':'native_fin_detail_packing','candidates':{'author-reference':{'path':str(dest),'sha256':sha(dest)}},'parts':packrows,'atlas':{'path':str(atlaspath),'sha256':sha(atlaspath),'size':size.tolist()}};save(out/'packing.validation.json',pack)
 declared={k:oldspec[k]for k in ['parts','species','game','motion','viewer']if k in oldspec};save(out/'parts.json',declared)
 report={'ok':True,'kind':'native_fin_cage_refinement','species':cfg['species'],'baseline':{'path':str(model),'sha256':sha(model)},'input_masks':{'path':str(a.masks.resolve()),'sha256':sha(a.masks)},'triangles_before':len(indices)//3,'triangles_after':ioff//3,'vertices_after':vo,'bones':18,'rig_and_animation_bytes_unchanged':True,'protected_part_attributes_and_indices_exact':True,'protected_parts':[p['name']for p in parts if not any(p['source_node'].startswith(k+'_')for k in repair)],'fins':records,'model':str(dest),'model_sha256':sha(dest),'source_blend':audit['source_blend'],'formal_acceptance':False};save(out/'author.validation.json',report);print(json.dumps({'ok':True,'species':cfg['species'],'triangles':ioff//3,'vertices':vo,'report':str(out/'author.validation.json')}))
if __name__=='__main__':main()
