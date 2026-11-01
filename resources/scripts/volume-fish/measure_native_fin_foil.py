"""Actual free fin-face inward normal rays; engineering thickness, not biology."""
import sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from glb_io import read_glb,arrays,sha
args=sys.argv[sys.argv.index('--')+1:];plan=Path(args[0]).resolve();p=json.loads(plan.read_text(encoding='utf8'));assert sha(p['model'])==p['model_sha256'];out=Path(args[1]);assert not out.exists();doc,blob=read_glb(p['model']);records=[]
for name,root in p['fins'].items():
 node=next(n for n in doc['nodes']if n.get('name')==name and'mesh'in n);pr=doc['meshes'][node['mesh']]['primitives'][0];v=arrays(doc,blob,pr['attributes']['POSITION']);uv=arrays(doc,blob,pr['attributes']['TEXCOORD_0']);tri=arrays(doc,blob,pr['indices']).reshape(-1,3);volume=np.einsum('ij,ij->i',v[tri[:,0]],np.cross(v[tri[:,1]],v[tri[:,2]])).sum()
 if volume<0:tri=tri[:,[0,2,1]]
 tree=BVHTree.FromPolygons(v.tolist(),tri.tolist(),all_triangles=True);roots=np.array(root['rest_points_gltf']);rid=np.min(np.linalg.norm(v[:,None,:]-roots[None,:,:],axis=2),axis=1)<1e-6;distances=[];missed=0;missing=[];epsilon=1e-7
 for t in tri:
  if rid[t].all():continue
  a,b,c=uv[t];cross=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
  if abs(cross)<1e-10:continue
  a,b,c=[Vector(x)for x in v[t]];n=(b-a).cross(c-a)
  if n.length<1e-12:continue
  n.normalize();center=(a+b+c)/3;hit,_,_,dist=tree.ray_cast(center-n*epsilon,-n)
  if hit is None:missed+=1;missing.append({'triangle':t.tolist(),'root_flags':rid[t].tolist(),'source_uv':uv[t].tolist(),'positions':v[t].tolist()})
  else:distances.append(float((dist+epsilon)*p['model_scale']*1000))
 assert distances and min(distances)>0,name;records.append({'name':name,'rays':len(distances),'missing_rays':missed,'missing_faces':missing,'normal_ray_mm_percentiles':np.percentile(distances,[0,10,50,90,100]).tolist(),'percentile_order':[0,10,50,90,100]})
r={'ok':all(x['missing_rays']==0 for x in records),'kind':'actual_native_closed_fin_foil_rays','model_sha256':p['model_sha256'],'plan_sha256':sha(plan),'records':records,'formal_acceptance':False,'scope':'Rest-pose rays from actual non-basal finite surface triangle centroids, along their inward geometric normal, excluding UV-degenerate side walls. Describes current engineered mesh; no target-species tissue measurement or continuous-motion proof.'};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'ok':r['ok'],'fins':len(records)}))
