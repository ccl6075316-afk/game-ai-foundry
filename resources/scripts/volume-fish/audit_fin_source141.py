"""Compare source UV footprint with actual rest projection; no source fabrication.

Profile polygons are labelled legacy priors, never independent silhouette truth.
Explicit native source annotations supersede those priors after image inspection.
"""
import argparse,json,hashlib,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
from source_fin_mask141 import source_mask
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def raster(points,tri,w,h):
 m=np.zeros((h,w),np.uint8);p=np.rint(points).astype(np.int32)
 for ids in tri:
  q=p[ids]
  e=q[1]-q[0];f=q[2]-q[0]
  if abs(int(e[0])*int(f[1])-int(e[1])*int(f[0]))>.5:cv2.fillConvexPoly(m,q,255)
 return m>0
def bounds(mask,pad=12):
 y,x=np.where(mask);assert len(x);return max(0,int(x.min())-pad),max(0,int(y.min())-pad),min(mask.shape[1],int(x.max())+pad+1),min(mask.shape[0],int(y.max())+pad+1)
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--annotations',type=Path);p.add_argument('--species',nargs='*',default=[]);a=p.parse_args();r=a.root;scope=read(r/'scope.validation.json');annotations=read(a.annotations)['species'] if a.annotations else {};rows=[]
 for spec in scope['records']:
  s=spec['species']
  if a.species and s not in a.species:continue
  meshfile=r/scope.get('baseline_dir','baseline')/f'{s}.mesh.json'
  if not meshfile.exists():continue
  mesh=read(meshfile);source=Image.open(spec['source']).convert('RGBA');rgba=np.asarray(source);w,h=source.size;aspect=w/h;profile=read(spec['profile']) if spec.get('profile') else {};defs={f['name']:f for f in profile.get('fins',[])};out=r/'audit'/s;out.mkdir(parents=True,exist_ok=True)
  fins=[]
  for f in mesh['fins']:
   name=f['name'];base=name.removesuffix('_left').removesuffix('_right');label=annotations.get(s,{}).get(base);prior=defs.get(base);uvmask=np.zeros((h,w),bool);geom=np.zeros_like(uvmask);maxuv=[];area3=0
   for part in f['parts']:
    v=np.asarray(part['rest_vertices']);uv=np.asarray(part['uv']);tri=np.asarray(part['triangles']).reshape(-1,3)
    if len(uv)!=len(v):continue
    image=Image.open(part['texture']['path']);same_size=image.size==source.size
    if not same_size:continue
    mapping=spec.get('pixel_mapping');projected=np.c_[v[:,0]*mapping['pixels_per_unit']+mapping['center_x'],mapping['center_y']-v[:,1]*mapping['pixels_per_unit']] if mapping else np.c_[(v[:,0]+.5)*w,(.5-v[:,1]*aspect)*h]
    uvmask|=raster(uv*[w,h],tri,w,h);geom|=raster(projected,tri,w,h)
    maxuv.append(float(np.max(np.linalg.norm(projected-uv*[w,h],axis=1))))
    area3+=float(np.sum(np.linalg.norm(np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]]),axis=1)/2))
   if not uvmask.any():fins.append({'name':name,'status':'different_fin_material_chart_requires_explicit_source_mapping'});continue
   prior_mask=np.zeros_like(uvmask,dtype=np.uint8)
   poly=label['polygon_px'] if label else (np.asarray(prior['polygon'])*[w,h]).tolist() if prior else None
   if poly:cv2.fillPoly(prior_mask,[np.rint(poly).astype(np.int32)],1)
   target=source_mask(rgba,label) if label else prior_mask.astype(bool)&(rgba[:,:,3]>32)
   Image.fromarray(target.astype('uint8')*255).save(out/f'{name}-source-mask.png')
   bx=bounds(uvmask|geom|target);x0,y0,x1,y1=bx;cut=rgba.copy();cut[:,:,3]=np.where(target,cut[:,:,3],0);Image.fromarray(cut).save(out/f'{name}-source-native.png');cutim=Image.fromarray(cut).crop(bx);cutim.save(out/f'{name}-source-cutout.png');proof=Image.new('RGBA',cutim.size,(25,49,63,255));proof.alpha_composite(cutim);proof.convert('RGB').save(out/f'{name}-source-cutout-proof.png')
   native=rgba.copy();native[:,:,3]=np.where(uvmask,native[:,:,3],0);Image.fromarray(native).crop(bx).save(out/f'{name}-old-uv-cutout.png')
   context=source.crop((max(0,x0-35),max(0,y0-35),min(w,x1+35),min(h,y1+35)));context.save(out/f'{name}-source-context.png')
   overlay=source.convert('RGB');ar=np.asarray(overlay).copy()
   for mask,color in [(target,(255,203,67)),(uvmask,(76,222,249)),(geom,(255,77,109))]:
    contours,_=cv2.findContours(mask.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(ar,contours,-1,color,max(1,w//900))
   Image.fromarray(ar).crop(bx).save(out/f'{name}-overlay.png')
   union=np.count_nonzero(target|uvmask);ref_pixels=int(target.sum());miss=int((target&~uvmask).sum());excess=int((uvmask&~target&(rgba[:,:,3]>32)).sum())
   record={'name':name,'reference_status':'operator_inspected_original_source_annotation' if label else 'legacy_profile_prior_not_independent_truth' if prior else 'source_unknown','bbox_px':bx,'source_pixels':ref_pixels,'missing_source_pixels':miss,'extra_opaque_source_pixels':excess,'uv_iou':float(np.count_nonzero(target&uvmask)/max(union,1)),'projected_vs_uv_iou':float(np.count_nonzero(geom&uvmask)/max(np.count_nonzero(geom|uvmask),1)),'max_vertex_projection_vs_uv_px_upper_bound':max(maxuv,default=0),'rest_surface_area_both_sides_native':area3,'source_polygon_px':poly,'basal_polyline_px':label.get('baseline_px') if label else (np.asarray(prior['source_baseline'])*[w,h]).tolist() if prior and prior.get('source_baseline') else None,'cutout_sha256':sha(out/f'{name}-source-cutout.png'),'scope':'UV/raster diagnostics; 3D orientation, occlusion and source-designed visible fin are separate. Legacy profile masks cannot prove source match.'};fins.append(record)
  row={'species':s,'ok':True,'source_sha256':spec['source_sha256'],'actual_runtime_mesh_sha256':sha(meshfile),'fins':fins,'whole_fish_acceptance':False};(out/'audit.validation.json').write_text(json.dumps(row,indent=2));rows.append(row)
 (r/'source-audit141.validation.json').write_text(json.dumps({'ok':len(rows)==len(a.species or scope['records']),'records':rows,'scope':'Source cutouts plus actual UV/rest projections. Independent annotations distinguished from old authored priors. Diagnostic only, no geometric or user acceptance.'},indent=2));print(json.dumps({'ok':True,'fish':len(rows),'fins':sum(len(x['fins']) for x in rows)}))
if __name__=='__main__':main()
