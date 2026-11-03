"""Bake own original lip colors on the actual packed skin/oral rim, across both sides."""
import sys,json,hashlib,io,argparse
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays
from rim_material_transport import ordered_boundary,nearest_arc,side_curve_donor,native_lip_ownership
from check_native_lip_donor import check
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--species',required=True);a=p.parse_args();s=a.species;root=ROOT/f'projects/fishing-2d/experiments/six-fish-database-20261104/{s}';cfg=json.loads((ROOT/f'resources/volume-fish/{s.replace("_","-")}-central-material-20261031.json').read_text(encoding='utf8'));geometry_trace={k:cfg[k]for k in ['upper_inner_edge_px','lower_inner_edge_px']};donor_end=1885 if s=='crucian'else cfg['upper_inner_edge_px'][-1][0];cfg['geometry_trace_unmodified']=geometry_trace
for key in ['upper_inner_edge_px','lower_inner_edge_px']:
 curve=np.array(cfg[key],float);cfg[key]=curve[curve[:,0]<donor_end].tolist()+[[donor_end,float(np.interp(donor_end,curve[:,0],curve[:,1]))]]
cfg['lip_source_transport']={'source_start_x':cfg['upper_inner_edge_px'][0][0],'source_end_x':cfg['upper_inner_edge_px'][-1][0],'complete_native_lip':{'upper_width_px':6,'lower_width_px':6,'outer_fade_px':2},'inner_lip_return_px':0,'inner_lip_fade_px':0};out=root/'native-lips-r3';out.mkdir(exist_ok=True);pre=check(cfg);(out/'donor-preflight.validation.json').write_text(json.dumps(pre,indent=2)+'\n');assert pre['ok'],'Own 2D full outward donor footprint failed; do not bake';model=root/'width-r1/fish.glb';d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];v=arrays(d,b,pr['attributes']['POSITION']);xyz=v[:,[0,2,1]]*np.array([1,-1,1]);uv=arrays(d,b,pr['attributes']['TEXCOORD_0']);inds=arrays(d,b,pr['indices']);parts=d['extras']['geometry_parts'];body=[q for q in parts if q['role']=='body_skin'];oral=[q for q in parts if q['role']=='mouth'];_,weld=np.unique(np.round(xyz,6),axis=0,return_inverse=True);_,representative=np.unique(weld,return_index=True);coords=xyz[representative];edges={}
for role,ps in [('skin',body),('oral',oral)]:
 for part in ps:
  fs=inds[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3)
  for tri in fs:
   no=np.cross(xyz[tri[1]]-xyz[tri[0]],xyz[tri[2]]-xyz[tri[0]]);no/=max(np.linalg.norm(no),1e-30)
   for x,y in zip(tri,np.roll(tri,-1)):
    key=tuple(sorted([int(weld[x]),int(weld[y])]))
    if key[0]!=key[1]:edges.setdefault(key,[]).append((role,no[2]))
chains={}
for name,sign in [('upper',-1),('lower',1)]:
 selected=[]
 for k,vs in edges.items():
  if not(any(r=='skin'for r,z in vs)and any(r=='oral'for r,z in vs)):continue
  point=coords[list(k)].mean(0);px=(point[0]+.5)*cfg['source_size'][0];mid=sum(np.interp(px,np.array(geometry_trace[n])[:,0],np.array(geometry_trace[n])[:,1])for n in ['upper_inner_edge_px','lower_inner_edge_px'])/2;above=point[2]>(.5-mid/cfg['source_size'][1])*cfg['source_size'][1]/cfg['source_size'][0]
  if above==(name=='upper'):selected.append(k)
 print(name,'seam_edges',len(selected));chains[name]=ordered_boundary(coords,selected)
iv=d['bufferViews'][d['images'][0]['bufferView']];img=np.array(Image.open(io.BytesIO(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']])).convert('RGBA'));before=img.copy();H,A=img.shape[:2];raw=np.array(Image.open(ROOT/cfg['source']).convert('RGBA'));W,SH=cfg['source_size'];mapping={};invalid=[];maximum=0;corecount=0;records=[]
for part in body:
 for tri in inds[part['index_start']:part['index_start']+part['index_count']].reshape(-1,3):
  q=uv[tri]*[A,H];lo=np.maximum(np.ceil(q.min(0)-.5).astype(int),0);hi=np.minimum(np.floor(q.max(0)-.5).astype(int),[A-1,H-1]);matrix=np.stack([q[1]-q[0],q[2]-q[0]],axis=1)
  if np.prod(hi-lo+1)<=0 or abs(np.linalg.det(matrix))<1e-9:continue
  yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];cells=np.c_[xx.ravel(),yy.ravel()];ab=(cells+.5-q[0])@np.linalg.inv(matrix).T;bw=np.c_[1-ab.sum(1),ab];inside=(bw>=-1e-6).all(1);cells=cells[inside];bw=bw[inside];points=bw@xyz[tri];near={k:nearest_arc(points,z)for k,z in chains.items()};upper=near['upper'][0]<=near['lower'][0];distance=np.where(upper,near['upper'][0],near['lower'][0])*W;weight=native_lip_ownership(distance,6,2);take=weight>0
  if not take.any():continue
  cells=cells[take];points=points[take];upper=upper[take];distance=distance[take];weight=weight[take];donor=np.empty((len(points),2))
  for name,isupper in [('upper',True),('lower',False)]:
   chosen=upper==isupper;curve=np.asarray(cfg[name+'_inner_edge_px'],float);donor[chosen]=side_curve_donor(near[name][1][take][chosen],chains[name][1][-1],distance[chosen],curve,isupper)
  source=np.rint(donor).astype(int);valid=(source[:,0]>=0)&(source[:,0]<W)&(source[:,1]>=0)&(source[:,1]<SH);assert valid.all(),source[~valid][:5];assert np.all(raw[source[:,1],source[:,0],3]>=243),'Actual lip donor alpha failed'
  for cell,xy,w,dist in zip(cells,source,weight,distance):
   x,y=map(int,cell);rgb=raw[xy[1],xy[0],:3];old=before[y,x,:3];img[y,x,:3]=np.rint(old*(1-w)+rgb*w).astype('uint8');mapping[(x,y)]=[int(xy[0]),int(xy[1]),float(w),float(dist)]
assert mapping;assert np.array_equal(img[:,:,3],before[:,:,3]);Image.fromarray(img).save(out/'atlas.png');(out/'config.json').write_text(json.dumps(cfg,indent=2)+'\n');records=[{'atlas_xy':list(k),'source_xy':v[:2],'native_weight':v[2],'distance_px':v[3]}for k,v in sorted(mapping.items())];core=[r for r in records if r['distance_px']<=6];assert core and all(r['native_weight']==1 for r in core);report={'ok':True,'kind':'actual_packed_complete_native_lip_domain_bake','species':s,'input_model_sha256':sha(model),'source':{'path':str(ROOT/cfg['source']),'sha256':sha(ROOT/cfg['source'])},'atlas_sha256':sha(out/'atlas.png'),'config_sha256':sha(out/'config.json'),'actual_3d_rim_transport':{k:{'segments':len(z[0])-1,'arc_native':float(z[1][-1])}for k,z in chains.items()},'complete_native_lip_ownership':{'protected_texels':len(core),'maximum_front_weight_inside_complete_lip':0,'maximum_central_weight_inside_complete_lip':0,'domain':cfg['lip_source_transport']['complete_native_lip']},'actual_native_donors':records,'changed_pixels':int(np.any(img!=before,axis=2).sum()),'alpha_exact':True,'scope':'Actual finite skin/oral seam chain with own source curves and conservative donor preflight. Geometry/UV/eyes/fins untouched; only measured body lip band RGB changed. Visual review and all affected gates remain due.'};(out/'material.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'mapped_texels':len(records),'protected':len(core),'changed':report['changed_pixels']}))
