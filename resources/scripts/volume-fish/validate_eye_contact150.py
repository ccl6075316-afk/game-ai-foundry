"""Finite actual eye triangles versus current physical and composed surfaces."""
from pathlib import Path
import argparse,gzip,json,sys,hashlib
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from closed_body_index140 import build
ap=argparse.ArgumentParser(description=__doc__)
for key in ['parameters','profiles','motion','output']:ap.add_argument('--'+key,type=Path,required=True)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
params=json.loads(a.parameters.read_text())['species'];cfg=json.loads(a.profiles.read_text())['profiles'];motion=json.loads(a.motion.read_text())['profiles']
def frozen(ref):
 path=Path(ref['path']);path=path if path.is_absolute() else R/path
 assert hashlib.sha256(path.read_bytes()).hexdigest()==ref['sha256'],'Stale frozen eye input: '+str(path)
 return path
def raw(path):return gzip.decompress(path.read_bytes())if path.suffix=='.gz'else path.read_bytes()
def source_alpha(path):
 image=bpy.data.images.load(str(path),check_existing=False);width,height=image.size
 pixels=np.empty(width*height*4,dtype=np.float32);image.pixels.foreach_get(pixels)
 alpha=np.rint(pixels.reshape(height,width,4)[::-1,:,3]*255).astype(np.uint8)
 bpy.data.images.remove(image);return alpha

def arrays(path):
 d=json.loads(raw(path));vv=[];tt=[]
 for part in d['parts']:
  tt.extend((np.asarray(part['triangles']).reshape(-1,3)+len(vv)).tolist());vv.extend(part['vertices'])
 return np.asarray(vv),np.asarray(tt)
def tree(v,t):return BVHTree.FromPolygons(v.tolist(),t.tolist(),all_triangles=True)
rows=[]
for s,p in params.items():
 physical=frozen(p.get('physical_surface',p['native_surface']));v,t=arrays(physical);body=tree(v,t);inside=build(v,t)
 sv,st=arrays(frozen(p['native_surface']));support=tree(sv,st)
 span=float(v[:,0].max()-v[:,0].min());scale=float(motion[s]['real_length_cm'])/100/span
 # Frozen engineering limits in actual display units; art height is separate.
 penetration_mm=.075;rim_extra_mm=.025;numeric_native=max(1e-7,float(np.abs(v).max())*1e-7)
 caps=[]
 for cap in cfg[s]['caps']:
  points=np.asarray(cap['vertices']);base=np.asarray(cap['base_surface_points']);tri=np.asarray(cap['indices']).reshape(-1,3)
  probes=np.concatenate([points,points[tri].mean(1),points[tri[:,[0,1]]].mean(1),points[tri[:,[1,2]]].mean(1),points[tri[:,[2,0]]].mean(1)])
  distances=[]
  for q in probes:
   dist=body.find_nearest(Vector(q))[3];distances.append(-dist if inside(q)else dist)
  bvh_base_error=max(support.find_nearest(Vector(q))[3]for q in base)
  base_error=bvh_base_error
  if 'support_faces'in cap:
   face=np.asarray(cap['support_faces'],int);bw=np.asarray(cap['support_barycentric']);actual_faces={tuple(q)for q in st.tolist()}
   assert all(tuple(q)in actual_faces for q in face.tolist())and bw.min()>=0 and np.max(abs(bw.sum(1)-1))<1e-12
   base_error=float(np.linalg.norm((sv[face]*bw[:,:,None]).sum(1)-base,axis=1).max())
  sectors=p['sectors'];rim_dist=max(support.find_nearest(Vector(q))[3]for q in points[-sectors:])
  radius=min(p['native_xy']['radius'])*p['footprint'];peak=p['height_over_radius']*radius
  relief=np.linalg.norm(points-base,axis=1);area=np.linalg.norm(np.cross(points[tri[:,1]]-points[tri[:,0]],points[tri[:,2]]-points[tri[:,0]]),axis=1)/2
  joints=np.asarray(cap['joints']);weights=np.asarray(cap['weights']);bone_ok=bool(joints.min()>=0 and joints.max()<len(cfg[s]['bones'])and np.max(abs(weights.sum(1)-1))<1e-6 and weights.min()>=0)
  alpha=source_alpha(frozen(p['source_image']));uv=np.asarray(cap['uv']);uv_probes=np.concatenate([uv,uv[tri].mean(1)]);xy=np.floor(uv_probes*np.asarray(p['source_size'])).astype(int)
  source_opaque=bool(xy.min()>=0 and np.all(xy[:,0]<alpha.shape[1])and np.all(xy[:,1]<alpha.shape[0])and np.all(alpha[xy[:,1],xy[:,0]]==255))
  minimum_mm=min(distances)*scale*1000;rim_mm=rim_dist*scale*1000
  limit_mm=peak*.015*scale*1000+rim_extra_mm
  ok=bool(minimum_mm>=-penetration_mm and base_error<=numeric_native and rim_mm<=limit_mm and area.min()>1e-14 and bone_ok and source_opaque and np.max(relief)<=peak*1.016)
  caps.append(dict(ok=ok,side=cap['side'],finite_probes=len(probes),signed_min_mm=minimum_mm,base_support_error_native=base_error,bvh_nearest_base_roundoff_native=bvh_base_error,base_error_method='Actual finite support triangle and nonnegative normalized barycentric identity',base_error_limit=numeric_native,rim_distance_mm=rim_mm,rim_limit_mm=limit_mm,peak_mm=peak*scale*1000,bones_weights_valid=bone_ok,native_source_opaque=source_opaque,minimum_area_native=float(area.min())))
 row=dict(species=s,ok=all(c['ok']for c in caps),caps=caps,physical_body_sha256=hashlib.sha256(raw(physical)).hexdigest(),support_sha256=p['native_surface']['sha256'],limits='75 micrometre finite-body penetration bound; rim separates deliberate15/1000 peak offset from25 micrometre numeric margin. Base error scales only float precision. Art height not anatomy; static finite probes are not continuous-time proof.')
 rows.append(row);print(s,row['ok'],[(round(c['signed_min_mm'],4),round(c['rim_distance_mm'],4))for c in caps],flush=True)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(dict(ok=all(r['ok']for r in rows),rows=rows,checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parameters_sha256=hashlib.sha256(a.parameters.read_bytes()).hexdigest(),profiles_sha256=hashlib.sha256(a.profiles.read_bytes()).hexdigest()),indent=2)+'\n')
sys.exit(0 if all(r['ok']for r in rows)else 1)
