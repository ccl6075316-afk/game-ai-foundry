"""Fit only the posterior ventral fin-base neighborhood to inspected source art.

Anterior half, topology, UV, skin and original material reference arrays stay exact.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from audit_fin_source141 import raster
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root;s='nile_tilapia';root=r.parents[4];old=json.loads((r.parent/'mouth-rollout-140/install140.plan.json').read_text());item=next(x for x in old['items'] if x['species']==s);bodyfile=Path(item['geometry']['path']);data=json.loads(bodyfile.read_text());ann=root/'resources/volume-fish/fin-source-141.json';base=np.asarray(json.loads(ann.read_text())['species'][s]['Anal']['baseline_px'],float);w,h=json.loads((r/'nile141.plan.json').read_text())['source_size'];aspect=w/h
 original=[np.asarray(part['vertices'],float).copy() for part in data['parts']];silhouette=np.zeros((h,w),bool)
 for part,v in zip(data['parts'],original):silhouette|=raster(np.c_[(v[:,0]+.5)*w,(.5-v[:,1]*aspect)*h],np.asarray(part['triangles']).reshape(-1,3),w,h)
 yy,xx=np.where(silhouette);floor=np.full(w,-1);roof=np.full(w,h);np.maximum.at(floor,xx,yy);np.minimum.at(roof,xx,yy);valid=floor>=0;xs=np.arange(w)[valid]/w-.5;bottom=(.5-floor[valid]/h)/aspect;top=(.5-roof[valid]/h)/aspect;source_x=base[:,0]/w-.5;source_y=(.5-base[:,1]/h)/aspect;support=[base[0,0]-45,base[-1,0]+45];changed=[]
 for pi,(part,v0) in enumerate(zip(data['parts'],original)):
  v=v0.copy();x=v[:,0];px=(x+.5)*w;lo=np.interp(x,xs,bottom);hi=np.interp(x,xs,top);cy=(lo+hi)/2;target=np.interp(x,source_x,source_y);delta=np.minimum(0,target-lo);envelope=smooth((px-support[0])/45)*smooth((support[1]-px)/45);vertical=np.clip((cy-v[:,1])/np.maximum(cy-lo,1e-6),0,1)**6;v[:,1]+=delta*envelope*vertical
  assert np.array_equal(v[x>=0],v0[x>=0]),'Protected anterior half changed';assert np.max(abs(v-v0))<.025,{'surface':pi,'max_delta':float(np.max(abs(v-v0))),'worst_source_px':float(px[np.argmax(abs(v[:,1]-v0[:,1]))]),'original_native':v0[np.argmax(abs(v[:,1]-v0[:,1]))].tolist(),'target_bottom':float(target[np.argmax(abs(v[:,1]-v0[:,1]))]),'current_bottom':float(lo[np.argmax(abs(v[:,1]-v0[:,1]))])}
  part['vertices']=v.tolist();ids=np.where(abs(v[:,1]-v0[:,1])>1e-12)[0];changed.append({'surface':pi,'vertices_changed':len(ids),'max_displacement_native':float(np.max(abs(v[:,1]-v0[:,1]))),'protected_anterior_half_equal':True,'unchanged_uv_topology_skin_normals_material_references':True})
 out=r/s/'body-fit-v8';out.mkdir(parents=True,exist_ok=True);path=out/'body.bound.json';path.write_text(json.dumps(data));plan={'species':s,'source_body_geometry':str(bodyfile),'source_body_sha256':sha(bodyfile),'source_resource':item['profile']['body'],'body':str(path.resolve()),'body_sha256':sha(path),'source_annotations_sha256':sha(ann),'posterior_source_x_support_px':support,'skin_joint_names':json.loads(Path(item['skinning_report']['path']).read_text())['summary']['skin_joint_names'],'output':str((out/'body.res').resolve()),'scope':'Local posterior ventral fit to the inspected anal source base. Anterior half/head/eyes/mouth, UV/topology/skin and material reference arrays are unchanged; normals deliberately retained with source shading.'};(out/'body.plan.json').write_text(json.dumps(plan,indent=2));(out/'fit.validation.json').write_text(json.dumps({'ok':True,'records':changed,'geometry_sha256':sha(path),'plan_sha256':sha(out/'body.plan.json'),'head_unchanged':True,'scope':plan['scope']},indent=2));print(json.dumps(changed))
if __name__=='__main__':main()
