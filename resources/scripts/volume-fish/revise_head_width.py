"""Versioned head-only rest-width revision; preserve original rig/UV/animation streams."""
import argparse,copy,hashlib,json,math,struct
from pathlib import Path
import numpy as np
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write

def gain_at(stations,u):
 if u<=stations[0][0]:return stations[0][1],0.
 for a,b in zip(stations,stations[1:]):
  if u<=b[0]:
   t=(u-a[0])/(b[0]-a[0]);return a[1]+(b[1]-a[1])*t*t*(3-2*t),(b[1]-a[1])*6*t*(1-t)/(b[0]-a[0])
 return stations[-1][1],0.

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--ownership',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();plan=json.loads(a.plan.read_text(encoding='utf8'));own=json.loads(a.ownership.read_text());records=[]
 for row in plan['items']:
  source=Path(row['source']);assert source.resolve()!=Path(row['target']).resolve();assert hashlib.sha256(source.read_bytes()).hexdigest()==row['source_sha256'];d,b=read_glb(source);original=bytes(b);binary=bytearray(b);old_doc=copy.deepcopy(d);stations=row['stations'];assert len(stations)>=2 and all(0<=x<=1 and 1<=y<=12 and math.isfinite(x+y) for x,y in stations);assert all(x[0]<y[0] for x,y in zip(stations,stations[1:]));changed=[]
  def add(values,template):
   data=np.asarray(values,dtype='<f4');binary.extend(b'\0'*(-len(binary)%4));start=len(binary);binary.extend(data.tobytes());vi=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':data.nbytes,'target':34962});ac=copy.deepcopy(template);ac.update(bufferView=vi,byteOffset=0,count=len(data),componentType=5126,min=data.min(axis=0).tolist(),max=data.max(axis=0).tolist());idx=len(d['accessors']);d['accessors'].append(ac);return idx
  allowlist=row.get('mesh_allowlist')
  if allowlist is not None:
   assert allowlist and len(set(allowlist))==len(allowlist)
   assert set(allowlist)<={n['name'] for n in d['nodes'] if 'mesh' in n},'Unknown allowed mesh'
   for node in d['nodes']:
    if 'mesh' in node and node['name'] in own['profiles'][row['species']]['fins']:
     for prim in d['meshes'][node['mesh']]['primitives']:
      assert np.all(accessor(old_doc,b,prim['attributes']['POSITION'])[:,0]+.5<=stations[0][0]),'Fin overlaps local head domain'
  for node in d['nodes']:
   if 'mesh' not in node:continue
   if allowlist is not None and node['name'] not in allowlist:continue
   assert not any(k in node for k in ['matrix','translation','rotation','scale']),'Nonidentity mesh space requires explicit transform'
   isfin=node['name'] in own['profiles'][row['species']]['fins']
   for prim in d['meshes'][node['mesh']]['primitives']:
    attrs=prim['attributes'];old=accessor(old_doc,b,attrs['POSITION']);u=old[:,0].astype(float)+.5;factors=np.array([gain_at(stations,float(x)) for x in u]);g=factors[:,0];derivative=factors[:,1];mask=g>1+1e-9
    if not mask.any():continue
    assert not isfin,'A fin overlaps head revision region'
    new=old.copy();new[:,2]=old[:,2]*g;assert np.array_equal(new[:,:2],old[:,:2]);assert np.array_equal(new[~mask],old[~mask]);attrs['POSITION']=add(new,d['accessors'][attrs['POSITION']])
    if 'NORMAL' in attrs:
     n=accessor(old_doc,b,attrs['NORMAL']);normal=n.copy().astype(float);normal[:,0]=n[:,0]-old[:,2]*derivative/g*n[:,2];normal[:,2]=n[:,2]/g;length=np.linalg.norm(normal,axis=1);normal/=np.maximum(length,1e-12)[:,None];normal[~mask]=n[~mask];attrs['NORMAL']=add(normal,d['accessors'][attrs['NORMAL']])
    if 'TANGENT' in attrs:
     t=accessor(old_doc,b,attrs['TANGENT']);nt=t.copy().astype(float);nt[:,2]=g*t[:,2]+old[:,2]*derivative*t[:,0];nt[:,:3]/=np.maximum(np.linalg.norm(nt[:,:3],axis=1),1e-12)[:,None];nt[~mask]=t[~mask];attrs['TANGENT']=add(nt,d['accessors'][attrs['TANGENT']])
    changed.append({'mesh':node['name'],'changed_vertices':int(mask.sum()),'u_range':[float(u[mask].min()),float(u[mask].max())]})
  assert changed;assert bytes(binary[:len(original)])==original
  for key in ['nodes','skins','animations','images','textures','materials']:assert d.get(key)==old_doc.get(key),'Unexpected '+key+' mutation'
  target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True);write(target,d,binary);records.append({'species':row['species'],'source_sha256':row['source_sha256'],'model_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'model':str(target),'changes':changed,'original_BIN_prefix_preserved':True,'rig_uv_fin_topology_animation_images_preserved':True,'side_XY_exactly_preserved':True})
 a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps({'ok':True,'plan_sha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'items':records},indent=2));print(json.dumps({'ok':True,'species':[x['species'] for x in records]}))
if __name__=='__main__':main()
