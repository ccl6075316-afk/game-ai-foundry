"""Fit body/caudal together on the frozen accepted side-art canvas."""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def normals(v,t):
 out=np.zeros_like(v);face=np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]])
 for j in range(3):np.add.at(out,t[:,j],face)
 return out/np.maximum(np.linalg.norm(out,axis=1)[:,None],1e-20)
def main():
 c=argparse.ArgumentParser();c.add_argument('--plan',type=Path,required=True);c.add_argument('--parameters',type=Path,required=True);c.add_argument('--output',type=Path,required=True);a=c.parse_args();root=Path(__file__).resolve().parents[3];params=json.loads(a.parameters.read_text(encoding='utf8'))['profiles'];plan=json.loads(a.plan.read_text(encoding='utf8'));result=[]
 for spec in plan['items']:
  sp=spec['species'];cfg=params[sp];source=Path(spec['model']);assert sha(source)==spec['model_sha256'];d,blob=read_glb(source);binary=bytearray(blob)
  profile=json.loads((root/'resources/volume-fish'/f'{sp.replace("_","-")}-121.profile.json').read_text(encoding='utf8'));image=root/f'projects/fishing-2d/experiments/blender-fish/hammer-pair-121/accepted/{sp}/inputs/char_{sp}_side121_nobg.png';im=np.array(Image.open(image));h,w=im.shape[:2];aspect=w/h
  def intervals(u):
   top=[];bottom=[]
   for x in np.atleast_1d(u):
    col=int(np.clip(round(x*w),0,w-1));ys=np.flatnonzero(im[:,col,3]>128);assert len(ys)>0
    top.append((ys[0]+.5)/h);bottom.append((ys[-1]-.5)/h)
   return np.asarray(top),np.asarray(bottom)
  def append(p,key,data):
   acc=copy.deepcopy(d['accessors'][p['attributes'][key]]);data=np.asarray(data,dtype='<f4');binary.extend(b'\0'*(-len(binary)%4));offset=len(binary);binary.extend(data.tobytes());acc.update(bufferView=len(d['bufferViews']),byteOffset=0,min=data.min(0).tolist(),max=data.max(0).tolist());d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':data.nbytes,'target':34962});d['accessors'].append(acc);p['attributes'][key]=len(d['accessors'])-1
  node=next(n for n in d['nodes'] if n.get('name')==spec['body'] and 'mesh'in n);ps=d['meshes'][node['mesh']]['primitives'];oldbody=np.concatenate([accessor(d,blob,p['attributes']['POSITION']) for p in ps]);rear=oldbody[:,0].min();assert abs(rear+.5-cfg['cap_u'])<1e-6
  xs=np.unique(np.round(oldbody[:,0],7));lows=[];highs=[]
  for x in xs:
   v=oldbody[np.abs(oldbody[:,0]-x)<1e-7];lows.append(v[:,1].min());highs.append(v[:,1].max())
  batches=[];allv=[];allt=[];base=0
  for si,p in enumerate(ps):
   v=accessor(d,blob,p['attributes']['POSITION']);old=v.copy();uv=accessor(d,blob,p['attributes']['TEXCOORD_0']);ns=accessor(d,blob,p['attributes']['NORMAL']);tri=accessor(d,blob,p['indices']).reshape(-1,3);u=v[:,0]+.5;selected=u<cfg['body_blend_end_u'];top,bot=intervals(u[selected]);oldlo=np.interp(v[selected,0],xs,lows);oldhi=np.interp(v[selected,0],xs,highs);f=(v[selected,1]-oldlo)/(oldhi-oldlo);target=(.5-bot)/aspect+f*(bot-top)/aspect;weight=1-smooth((u[selected]-cfg['body_match_end_u'])/(cfg['body_blend_end_u']-cfg['body_match_end_u']));v[selected,1]=old[selected,1]*(1-weight)+target*weight
   if si==0:uv[selected]=np.c_[u[selected],.5-v[selected,1]*aspect]
   batches.append((p,v,old,uv,ns,tri,selected));allv.append(v);allt.append(tri+base);base+=len(v)
  bv=np.concatenate(allv);bt=np.concatenate(allt);face=np.cross(bv[bt[:,1]]-bv[bt[:,0]],bv[bt[:,2]]-bv[bt[:,0]]);sums=np.zeros_like(bv)
  for j in range(3):np.add.at(sums,bt[:,j],face)
  _,inv=np.unique(np.round(bv,7),axis=0,return_inverse=True);group=np.zeros((inv.max()+1,3),np.float64);np.add.at(group,inv,sums);bn=group[inv];bn/=np.maximum(np.linalg.norm(bn,axis=1)[:,None],1e-20);base=0
  for p,v,old,uv,ns,tri,selected in batches:
   ns[selected]=bn[base:base+len(v)][selected];base+=len(v)
   for key,data in [('POSITION',v),('NORMAL',ns),('TEXCOORD_0',uv)]:append(p,key,data)
  tailnode=next(n for n in d['nodes'] if n.get('name')=='Caudal' and 'mesh'in n);p=d['meshes'][tailnode['mesh']]['primitives'][0];v=accessor(d,blob,p['attributes']['POSITION']);original=v.copy();uv=accessor(d,blob,p['attributes']['TEXCOORD_0']);tri=accessor(d,blob,p['indices']).reshape(-1,3);ids=np.array(spec['fins']['Caudal']['ids'])
  # Original UV is the accepted, unscaled source geometry before the rejected
  # 90% operation. Keep X fixed on that canvas; repair only the incorrect join.
  v[:,0]=uv[:,0]-.5;v[:,1]=(.5-uv[:,1])/aspect;u=uv[:,0].copy();selected=u>=cfg['tail_correct_start_u'];polygon=np.array(next(f for f in profile['fins'] if f['name']=='Caudal')['polygon'])
  lo=[];hi=[]
  for x in u[selected]:
   x=min(float(x),cfg['cap_u'])
   hits=[]
   for aa,bb in zip(polygon,np.roll(polygon,-1,axis=0)):
    if abs(bb[0]-aa[0])<1e-10:
     if abs(x-aa[0])<1e-6:hits.extend([aa[1],bb[1]])
    elif min(aa[0],bb[0])-1e-6<=x<=max(aa[0],bb[0])+1e-6:hits.append(aa[1]+(x-aa[0])/(bb[0]-aa[0])*(bb[1]-aa[1]))
   assert len(hits)>=2;lo.append(min(hits));hi.append(max(hits))
  lo=np.array(lo);hi=np.array(hi);top,bot=intervals(u[selected]);f=(uv[selected,1]-lo)/np.maximum(hi-lo,1e-10);target=top+f*(bot-top);weight=smooth((u[selected]-cfg['tail_correct_start_u'])/(cfg['cap_u']-cfg['tail_correct_start_u']));uv[selected,1]=uv[selected,1]*(1-weight)+target*weight;v[:,1]=(.5-uv[:,1])/aspect
  # Existing thick root cross-section stays; recompute root halfwidth from the
  # newly fitted actual cap, rather than keeping the old wrong root Y envelope.
  cap=bv[np.abs(bv[:,0]-rear)<1e-6];ys=np.unique(np.round(cap[:,1],7));width=np.array([np.abs(cap[np.abs(cap[:,1]-y)<1.1e-7,2]).max() for y in ys]);distance=np.maximum(0,rear-v[:,0]);mix=smooth(distance/.035);z=np.interp(v[:,1],ys,width,left=0,right=0);thin=.00006 if sp=='great_hammerhead' else .000075;side=np.where(original[:,2]>=0,1.,-1.);v[:,2]=side*(thin*mix+np.maximum(thin,z*.9998)*(1-mix))
  ns=normals(v,tri);cp=bv[(np.abs(bv[:,0]-rear)<1e-6)&(bv[:,2]>=-1e-8)];cn=bn[(np.abs(bv[:,0]-rear)<1e-6)&(bv[:,2]>=-1e-8)];order=np.argsort(cp[:,1]);cp=cp[order];cn=cn[order];join=np.stack([np.interp(v[:,1],cp[:,1],cn[:,j]) for j in range(3)],1);join[:,2]*=side;blend=smooth(distance/.012);ns=ns*blend[:,None]+join*(1-blend[:,None]);ns/=np.maximum(np.linalg.norm(ns,axis=1)[:,None],1e-20)
  for key,data in [('POSITION',v),('NORMAL',ns),('TEXCOORD_0',uv)]:append(p,key,data)
  assert binary[:len(blob)]==blob;folder=a.output/sp;folder.mkdir(parents=True,exist_ok=True);dest=folder/'fish.glb';write(dest,d,binary);out=copy.deepcopy(spec);out.update(model=str(dest.resolve()),model_sha256=sha(dest));out['fins']['Caudal']['rest_points_gltf']=v[ids].tolist();length=float(max(oldbody[:,0].max(),max(accessor(d,blob,pr['attributes']['POSITION'])[:,0].max() for n in d['nodes'] if 'mesh'in n and n['mesh']not in [node['mesh'],tailnode['mesh']] for pr in d['meshes'][n['mesh']]['primitives']))-v[:,0].min());out['scale_cm']*=out['length_native']/length;out['length_native']=length;result.append(out)
  report={'ok':True,'species':sp,'source_model_sha256':sha(source),'model_sha256':sha(dest),'source_image_sha256':sha(image),'parameters':cfg,'root_count':len(ids),'root_ids_preserved':True,'changed_meshes':['Closed_body','Caudal'],'other_meshes_rig_animation_source_binary_preserved':True,'method':'Unscaled fixed source canvas; jointly fit actual body-end and caudal-root Y to accepted alpha sections. Actual cap controls transverse root fit. Original weights unchanged.','limits':'Hidden width inferred; mandatory actual dynamic and body/material gates required.'};(folder/'fit.validation.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
 (a.output/'candidate.plan.json').write_text(json.dumps({'items':result},indent=2),encoding='utf8')
if __name__=='__main__':main()
