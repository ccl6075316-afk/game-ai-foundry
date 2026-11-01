"""Versioned transverse head field and rigid paired-fin neutral-pose revision.

Keep texture/UV/topology. Rotate the complete pectoral primitive AND its joint
rest/animation frame; update inverse binds, never move only the visible fin tip.
Finite contact re-projection and actual runtime validation remain separate.
"""
from pathlib import Path
import json,copy,hashlib,sys,argparse
import numpy as np
from scipy.spatial.transform import Rotation
from freeze_surface_ownership import read_glb,accessor
from patch_existing_fin_meshes import write

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(x):return np.clip(x,0,1)**2*(3-2*np.clip(x,0,1))
def field(v,p):
 v=np.asarray(v,dtype=float);o=v.copy();x=v[:,0];z=v[:,2];g=np.ones(len(v))
 if p.get('width_interpolation')=='pchip':
  from scipy.interpolate import PchipInterpolator
  stations=np.asarray(p['width_stations'],float)
  g=PchipInterpolator(stations[:,0],stations[:,1],extrapolate=False)(np.clip(x,stations[0,0],stations[-1,0]))
 else:
  for a,b in zip(p['width_stations'],p['width_stations'][1:]):
   amount=smooth((x-a[0])/(b[0]-a[0]));g=np.where(x>=a[0],a[1]+(b[1]-a[1])*amount,g)
 o[:,2]=z*g
 front=p['round_front'];amount=smooth((x-front['start_x'])/(front['end_x']-front['start_x']))
 o[:,0]-=front['corner_retreat']*(z/front['reference_half_width'])**2*amount
 return o
def jacobian(v,p):
 v=np.asarray(v,float);result=np.empty((len(v),3,3));eps=1e-6
 for i in range(3):
  delta=np.zeros_like(v);delta[:,i]=eps;result[:,:,i]=(field(v+delta,p)-field(v-delta,p))/(2*eps)
 return result
def normals(v,n,p):
 j=jacobian(v,p);out=np.linalg.solve(j.transpose(0,2,1),np.asarray(n,float)[:,:,None])[:,:,0];return out/np.maximum(np.linalg.norm(out,axis=1)[:,None],1e-15)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);a=ap.parse_args();p=json.loads(a.plan.read_text());src=Path(p['source_model']['path']);assert sha(src)==p['source_model']['sha256']
 out=Path(p['output']);out.mkdir(parents=True,exist_ok=True);doc,blob=read_glb(src);old=copy.deepcopy(doc);binary=bytearray(blob);head=p['head'];finplan=json.loads(Path(p['fin_plan']).read_text());spec=finplan['items'][0]
 def put(source,rows):
  template=copy.deepcopy(doc['accessors'][source]);dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[template['componentType']];v=np.asarray(rows,dtype=dt)
  binary.extend(b'\0'*(-len(binary)%4));off=len(binary);binary.extend(v.tobytes());template.update(bufferView=len(doc['bufferViews']),byteOffset=0,count=len(v));template.pop('min',None);template.pop('max',None)
  if template['type']=='VEC3':template.update(min=v.min(0).tolist(),max=v.max(0).tolist())
  doc['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':v.nbytes});doc['accessors'].append(template);return len(doc['accessors'])-1
 parents={child:i for i,n in enumerate(old['nodes'])for child in n.get('children',[])};worlds={}
 def world(i):
  if i in worlds:return worlds[i]
  n=old['nodes'][i];m=np.eye(4)
  if 'matrix'in n:m=np.array(n['matrix']).reshape(4,4).T
  else:m[:3,:3]=Rotation.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0])
  worlds[i]=world(parents[i])@m if i in parents else m;return worlds[i]
 transformations={};joint_transforms={};rows=[]
 for name,config in p['pectoral'].items():
  roots=np.asarray(spec['fins'][name]['rest_points_gltf']);pivot=roots.mean(0);rot=Rotation.from_euler('x',config['rotation_x_degrees'],degrees=True).as_matrix();destination=field(pivot[None,:],head)[0]+np.array(config['translation'])
  h=np.eye(4);h[:3,:3]=rot;h[:3,3]=destination-rot@pivot;transformations[name]=h
  rootjoint=next(i for i,n in enumerate(old['nodes'])if n.get('name')==name and 'mesh'not in n)
  subtree=[]
  def descend(i):
   subtree.append(i)
   for c in old['nodes'][i].get('children',[]):descend(c)
  descend(rootjoint)
  for i in subtree:joint_transforms[i]=h
  parent=world(parents[rootjoint])if rootjoint in parents else np.eye(4);local=np.linalg.inv(parent)@h@world(rootjoint);n=doc['nodes'][rootjoint]
  n.pop('matrix',None);n['translation']=local[:3,3].tolist();n['rotation']=Rotation.from_matrix(local[:3,:3]).as_quat().tolist();n.pop('scale',None)
  correction=np.linalg.inv(parent)@h@parent
  for animation in doc.get('animations',[]):
   for channel in animation['channels']:
    if channel['target']['node']!=rootjoint:continue
    sampler=animation['samplers'][channel['sampler']];assert sampler.get('interpolation','LINEAR')in ['LINEAR','STEP'];idx=sampler['output'];v=accessor(old,blob,idx);kind=channel['target']['path']
    if kind=='rotation':v=(Rotation.from_matrix(correction[:3,:3])*Rotation.from_quat(v)).as_quat()
    elif kind=='translation':v=v@correction[:3,:3].T+correction[:3,3]
    elif kind=='scale':continue
    else:raise AssertionError(kind)
    sampler['output']=put(idx,v)
  spec['fins'][name]['rest_points_gltf']=(roots@rot.T+h[:3,3]).tolist()
  rows.append({'name':name,'old_root_centroid':pivot.tolist(),'new_root_centroid':destination.tolist(),'rotation_x_degrees':config['rotation_x_degrees'],'rigid_matrix':h.tolist(),'joint_rest_and_animation_frame_updated':True})
 for n in doc['nodes']:
  if 'mesh'not in n:continue
  name=n.get('name','')
  if name!='Closed_body'and name not in transformations:continue
  for primitive in doc['meshes'][n['mesh']]['primitives']:
   attrs=primitive['attributes'];v=accessor(old,blob,attrs['POSITION']);normal=accessor(old,blob,attrs['NORMAL'])
   if name=='Closed_body':new=field(v,head);nn=normals(v,normal,head)
   else:h=transformations[name];new=v@h[:3,:3].T+h[:3,3];nn=normal@h[:3,:3].T
   attrs['POSITION']=put(attrs['POSITION'],new);attrs['NORMAL']=put(attrs['NORMAL'],nn)
   if 'TANGENT'in attrs:
    t=accessor(old,blob,attrs['TANGENT']);tv=np.einsum('nij,nj->ni',jacobian(v,head),t[:,:3])if name=='Closed_body'else t[:,:3]@h[:3,:3].T;tv/=np.maximum(np.linalg.norm(tv,axis=1)[:,None],1e-15);t[:,:3]=tv;attrs['TANGENT']=put(attrs['TANGENT'],t)
 for si,skin in enumerate(doc['skins']):
  idx=skin.get('inverseBindMatrices')
  if idx is None:continue
  acc=old['accessors'][idx];view=old['bufferViews'][acc['bufferView']];matrices=np.ndarray((acc['count'],16),dtype='<f4',buffer=blob,offset=view.get('byteOffset',0)+acc.get('byteOffset',0)).copy();changed=False
  for ji,node_index in enumerate(skin['joints']):
   if node_index not in joint_transforms:continue
   matrix=matrices[ji].reshape(4,4).T;matrices[ji]=(matrix@np.linalg.inv(joint_transforms[node_index])).T.reshape(16);changed=True
  if changed:skin['inverseBindMatrices']=put(idx,matrices)
 for kind in ['body','lips']:
  source=Path(p[kind]['path']);assert sha(source)==p[kind]['sha256'];data=json.loads(source.read_text())
  for part in data['parts']:
   v=np.array(part['vertices']);part['vertices']=field(v,head).astype('<f4').tolist();part['normals']=normals(v,part['normals'],head).astype('<f4').tolist()
  (out/(kind+'.json')).write_text(json.dumps(data,separators=(',',':'))+'\n',encoding='utf8')
 # Art pixels and source UVs remain byte-identical; geometry support evidence is invalidated.
 for key in ['images','textures','materials','samplers']:assert doc.get(key)==old.get(key)
 assert bytes(binary[:len(blob)])==blob
 target=out/'fish.glb';write(target,doc,binary);spec.update(model=str(target.resolve()),model_sha256=sha(target));spec['membrane_clearance']['targets']=list(p['pectoral']);spec['membrane_clearance']['contact_edge_length_native']=.003
 (out/'fin-repair.plan.json').write_text(json.dumps(finplan,indent=2)+'\n');
 sample=np.array(json.loads((out/'body.json').read_text())['parts'][0]['vertices']);det=np.linalg.det(jacobian(sample,head));assert det.min()>.5
 report={'ok':True,'source_model_sha256':sha(src),'model_sha256':sha(target),'head_field':head,'minimum_jacobian_determinant':float(det.min()),'pectoral':rows,'source_pixels_uv_and_topology_retained':True,'scope':'Finite head and full pectoral neutral-pose candidate. Head body/lips transported together; paired joint rest/animation/inverse binds transformed consistently. Root re-projection, current support/caps/physical checks and actual gray/source review still required.'}
 (out/'form.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'ok':True,'min_jacobian':float(det.min()),'fins':rows}))
if __name__=='__main__':main()
