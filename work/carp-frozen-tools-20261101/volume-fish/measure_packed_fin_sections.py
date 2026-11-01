"""Blender: actual packed fin normal-ray sections and complete tail end profile.

Reads exported finite triangles, source-owned UVs and explicit full basal bands.
No whole-fish or anatomical acceptance is granted by this measurement alone.
"""
import sys,json,io
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE/'portable')]
from glb_io import read_glb,arrays,sha
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def line_distance(q,line):
 a=line[:-1];v=np.diff(line,axis=0);t=np.clip(((q-a)*v).sum(1)/np.maximum((v*v).sum(1),1e-12),0,1);return float(np.min(np.linalg.norm(a+t[:,None]*v-q,axis=1)))
def measure(model,packing,audit,scale,basal,scratch):
 d,b=read_glb(model);pr=d['meshes'][0]['primitives'][0];pos=arrays(d,b,pr['attributes']['POSITION']);uv=arrays(d,b,pr['attributes']['TEXCOORD_0']);idx=arrays(d,b,pr['indices']).reshape(-1,3);parts=d['extras']['geometry_parts'];size=np.array(packing['atlas']['size']);iv=d['bufferViews'][d['images'][0]['bufferView']]
 temporary=scratch/('measurement-embedded-'+sha(model)[:12]+'.png');assert not temporary.exists()
 try:
  temporary.write_bytes(b[iv.get('byteOffset',0):iv.get('byteOffset',0)+iv['byteLength']]);image=bpy.data.images.load(str(temporary),check_existing=False);assert list(image.size)==size.tolist();pixels=np.empty(int(np.prod(size))*4,dtype=np.float32);image.pixels.foreach_get(pixels);alpha=np.rint(pixels.reshape(size[1],size[0],4)[::-1,:,3]*255).astype('uint8');bpy.data.images.remove(image);del pixels
 finally:temporary.unlink(missing_ok=True)
 bodyfaces=np.concatenate([idx[p['index_start']//3:(p['index_start']+p['index_count'])//3]for p in parts if p['role']=='body_skin']);bodytree=BVHTree.FromPolygons([Vector(x)for x in pos],bodyfaces.tolist(),all_triangles=True);bodyids=np.unique(bodyfaces);rear=pos[bodyids,0].min();capids=bodyids[np.abs(pos[bodyids,0]-rear)<1e-6];cap=pos[capids];records=[]
 for part,row in zip(parts,packing['parts']):
  if part['role']!='fin':continue
  name=part['source_node'];fin=next(k for k in ['Dorsal','Anal','Caudal','Pectoral','Pelvic']if name.startswith(k));info=next(r for r in audit['fins']if r['fin']==fin);lo=part['vertex_start'];hi=lo+part['vertex_count'];p=pos[lo:hi];u=uv[lo:hi];t=idx[part['index_start']//3:(part['index_start']+part['index_count'])//3]-lo;vertices=[Vector(v)for v in p];signed_volume=sum(vertices[a].dot(vertices[b].cross(vertices[c]))for a,b,c in t)/6.;assert abs(signed_volume)>1e-14,(name,'Collapsed finite volume');tris=t if signed_volume>0 else t[:,::-1];tree=BVHTree.FromPolygons(vertices,tris.tolist(),all_triangles=True);origin=np.array(row['atlas_placement'])-row['virtual_crop_origin'];mask=audit.get('native_masks',{}).get(fin);source_origin=np.array(mask['crop'][:2]if mask else info['source_crop'][:2]);pixel=u*size-origin+source_origin;root=np.array(mask['root_px'])+source_origin if mask else np.array(info['source_baseline_px']);distance=np.maximum(0,p[:,0].max()-p[:,0])if fin=='Caudal'else np.array([line_distance(q,root)for q in pixel]);maxd=max(distance.max(),1e-9);probes=[];missing=[];buried=0
  transparent=0
  for face,tv in enumerate(tris):
   uvtri=u[tv]*size;det=np.linalg.det(np.array([uvtri[1]-uvtri[0],uvtri[2]-uvtri[0]]));longest=max(np.linalg.norm(uvtri[1]-uvtri[0]),np.linalg.norm(uvtri[2]-uvtri[0]),np.linalg.norm(uvtri[2]-uvtri[1]))
   # Float32 packed UVs can leave a closing rim nominally nonzero by a few
   # atlas-coordinate ULPs. Classify source-space height, not raw determinant.
   if abs(det)<=max(longest,1e-9)*.0015:continue
   xyz=[vertices[int(i)]for i in tv];no=(xyz[1]-xyz[0]).cross(xyz[2]-xyz[0]).normalized()
   for bw in [(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]:
    texel=np.clip(np.floor(np.array(bw)@uvtri).astype(int),[0,0],size-1)
    if alpha[texel[1],texel[0]]<128:transparent+=1;continue
    point=sum((v*w for v,w in zip(xyz,bw)),Vector());source_t=float(np.array(bw)@distance[tv]/maxd);bodydist=bodytree.find_nearest(point)[3]*scale*1000
    if source_t<.025 or bodydist<.5:buried+=1;continue
    hit,_,_,dist=tree.ray_cast(point-no*1e-7,-no,.3)
    if hit is None:missing.append({'face':int(face),'source_t':source_t});continue
    probes.append({'source_t':source_t,'local_normal_thickness_mm':float((dist+1e-7)*scale*1000)})
  zones={}
  for zone,a,z in [('proximal',.025,.4),('middle',.4,.75),('distal',.75,1.001)]:
   values=[q['local_normal_thickness_mm']for q in probes if a<=q['source_t']<z];zones[zone]={'samples':len(values),'min_median_max_mm':np.percentile(values,[0,50,100]).tolist()if values else None}
  complete=all(z['samples']for z in zones.values());ratio=zones['proximal']['min_median_max_mm'][1]/zones['distal']['min_median_max_mm'][1]if complete else 0;records.append({'name':name,'zones':zones,'proximal_to_distal_median_ratio':ratio,'missing_opposing_ray_count':len(missing),'missing_opposing_rays':missing,'basal_or_body_contact_probes_separate':buried,'transparent_source_probes_separate':transparent,'signed_volume_native':signed_volume,'actual_probes':probes,'ok':complete and ratio>=1.5 and not missing})
 caudal=next(p for p in parts if p['source_node']=='Caudal_mesh');tp=pos[caudal['vertex_start']:caudal['vertex_start']+caudal['vertex_count']];rootpts=tp[np.abs(tp[:,0]-tp[:,0].max())<1e-6];ys=np.unique(np.round(rootpts[:,1],7));widths=[2*np.max(np.abs(rootpts[np.abs(rootpts[:,1]-y)<1e-6,2]))for y in ys];sections=[]
 for y in np.unique(np.round(cap[:,1],7)):
  bodywidth=2*np.max(np.abs(cap[np.abs(cap[:,1]-y)<1e-6,2]));tailwidth=float(np.interp(y,ys,widths));sections.append({'height_native':float(y),'body_width_mm':float(bodywidth*scale*1000),'tail_root_width_mm':tailwidth*scale*1000,'difference_mm':abs(bodywidth-tailwidth)*scale*1000})
 error=float(max(s['difference_mm']for s in sections));return {'ok':all(r['ok']for r in records)and error<=.4,'fins':records,'fin_inventory':[r['name']for r in records],'tail_cross_section':{'ok':error<=.4,'maximum_width_error_mm':error,'tolerance_mm':.4,'sections':sections},'model_sha256':sha(model)}
def main():
 args=sys.argv[sys.argv.index('--')+1:];candidate=Path(args[0]).resolve();out=Path(args[1]).resolve()
 report=load(candidate/'author/tail-donors.validation.json');base=Path(report['baseline']).parent.parent
 audit=load(base.parent/'audit/audit.validation.json');author=load(base/'author/author.validation.json')
 audit['native_masks']={r['name']:r for r in load(author['input_masks']['path'])['fins']}
 scale=load(candidate/'fin-review.plan.json')['model_scale'];packing=load(candidate/'author/packing.validation.json')
 current=measure(candidate/'source-run/fish.glb',packing,audit,scale,load(candidate/'fin.plan.json')['items'][0],out.parent)
 negative=measure(Path(report['baseline']),load(base/'author/packing.validation.json'),audit,scale,load(base/'fin.plan.json')['items'][0],out.parent)
 result={'ok':current['ok']and not negative['ok'],'kind':'actual_packed_fin_normal_rays_and_tail_section','species':report['species'],'model_sha256':current['model_sha256'],'current':current,'rejected_original':negative,'scope':'Actual exported triangles: exposed face normal rays, native source distance zones and complete finite tail-end width knots. Basal source/contact bands excluded from exposed membrane metric. Source profile/biological evidence, current posed gates and visual review remain separate.'}
 assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'ok':result['ok'],'current':[{k:r[k]for k in ['name','proximal_to_distal_median_ratio','missing_opposing_ray_count','ok']}for r in current['fins']],'tail_error_mm':current['tail_cross_section']['maximum_width_error_mm']}))
if __name__=='__main__':main()
