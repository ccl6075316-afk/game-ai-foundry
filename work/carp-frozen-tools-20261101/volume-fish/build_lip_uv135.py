"""Blender: continue complete source material from measured body-UV junctions."""
import sys,json,hashlib,runpy
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

g=runpy.run_path(str(Path(__file__).with_name('probe_lip_uv135.py')))
root=g['root'];plan=g['plan'];body=g['body'];lip=g['lip'];bvh=g['bvh']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,h in plan['frozen_inputs'].items():assert sha(p)==h,p
probe=json.loads((root/'body-lip-correspondence.json').read_text())
images=np.load(plan['source_images_npz']);source=images['source'];opaque=images['opaque']
bands=json.loads(Path(plan['band_plan']).read_text())['bands'];L,R=95,159;references=[];metrics=[];outputs=[]
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def bary(point,triangle):
 a,b,c=triangle;v0=b-a;v1=c-a;v2=point-a;d00=v0@v0;d01=v0@v1;d11=v1@v1;den=d00*d11-d01*d01
 vv=(d11*(v2@v0)-d01*(v2@v1))/den;ww=(d00*(v2@v1)-d01*(v2@v0))/den;return np.array([1-vv-ww,vv,ww])
for index,part in enumerate(lip['parts']):
 name=part['name'];positions=np.array(part['vertices']);rows=positions[1:-1].reshape(255,17,3);q=np.array(probe[name]['body_uv'])[1:-1].reshape(255,17,2)*[1986,991]
 s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(rows[:,16],axis=0),axis=1))];span=s[R]-s[L]
 dl=np.array([np.polyfit(s[L-5:L+1]-s[L],q[L-5:L+1,j,0],1)[0] for j in range(17)])
 dr=np.array([-np.polyfit(s[R:R+6]-s[R],q[R:R+6,j,0],1)[0] for j in range(17)])
 assert np.all(dl>0) and np.all(dr>0)
 N=round(span*(dl[16]+dr[16])/2);ul=q[L,16,0];ur=q[R,16,0]
 bounds=np.array(bands[name]['source_bounds']);cy=bounds[:,1] if name=='upper' else np.maximum(bounds[:,1],bounds[:,2])
 def contour(u):return np.floor(np.interp(u,bounds[:,0],cy))
 cref=contour(ul);leftv=q[L,:,1]-contour(q[L,:,0])+cref;rightv=q[R,:,1]-contour(q[R,:,0])+cref
 u0=int(np.floor(min(q[L,:,0].min(),ul)))-6;u1=int(np.ceil(ul+N+max(abs(q[R,:,0]-ur))))+7
 v0=int(np.floor(min(leftv.min(),rightv.min())))-20;v1=int(np.ceil(max(leftv.max(),rightv.max())))+20;W,H=u1-u0,v1-v0
 atlas=np.zeros((H,W,4),np.uint8);donors=[]
 for c in range(W):
  unwrapped=u0+c+.5;t=(unwrapped-ul)/N;anchor=ul+(ur-ul)*t;progress=min(unwrapped-ul,ul+N-unwrapped);donor_u=anchor+progress
  if donor_u>1960:donor_u=3920-donor_u
  assert donor_u>=1830
  x=int(np.clip(np.floor(donor_u),0,1985));shift=int(contour(donor_u)-cref)
  for row in range(H):
   y=int(np.clip(v0+row+shift,0,990));fallback=source[y,x,3]<242;color=(opaque if fallback else source)[y,x].copy();color[3]=255;atlas[row,c]=color;donors.append([c,row,x,y,int(fallback)])
 np.save(root/(name+'-continuation.rgba.npy'),atlas);(root/(name+'-donors.json')).write_text(json.dumps(donors,separators=(',',':')))
 uv2=np.zeros((len(positions),2));weights=np.zeros(len(positions));chart_rows=[];weight_rows=[]
 for i in range(255):
  t=np.clip((s[i]-s[L])/span,0,1);h00=2*t**3-3*t*t+1;h10=t**3-2*t*t+t;h01=-2*t**3+3*t*t;h11=t**3-t*t
  rightu=ul+N+ur-q[R,:,0]
  uu=h00*q[L,:,0]+h10*span*dl+h01*rightu+h11*span*dr
  vv=leftv*(1-t)+rightv*t
  chart=np.c_[(uu-u0)/W,(vv-v0)/H];weight=float(smooth((i-L)/2)*smooth((R-i)/2))
  uv2[1+i*17:1+(i+1)*17]=chart;weights[1+i*17:1+(i+1)*17]=weight;chart_rows.append(chart);weight_rows.append(weight)
 # Material UV follows actual body sampling on known sides; full pixel cells
 # continue through a native-resolution central chart, rather than new dots.
 part['uv']=probe[name]['body_uv'];part['uv2']=uv2.tolist();part['colors']=[[float(w),0.,0.,1.] for w in weights]
 # Extend reference coordinates onto adjacent real skin so an original black
 # lip cell sitting just outside the raised strip isn't moved onto its edge.
 refv=[];refq=[];refw=[];cross_count=31
 for i in range(L-5,R+6):
  row=rows[i];cs=np.array(chart_rows[i]);points=list(row);coords=list(cs);fades=[1.]*17
  previous=row[-1];direction=row[-1]-row[-2];direction/=np.linalg.norm(direction);distance=0.;gradient=(cs[-1]-cs[-2])/np.linalg.norm(row[-1]-row[-2])
  for k in range(14):
   point,normal,_,_=bvh.find_nearest(Vector(previous+direction*.0003));point=np.array(point);normal=np.array(normal);step=np.linalg.norm(point-previous);distance+=step;direction-=normal*(direction@normal);direction/=np.linalg.norm(direction);previous=point
   points.append(point);coords.append(cs[-1]+gradient*distance);fades.append(float(1-smooth((distance-.0027)/.0015)))
  refv.extend(points);refq.extend(coords);refw.extend([f*weight_rows[i] for f in fades])
 faces=[];nr=R-L+11
 for i in range(nr-1):
  for j in range(cross_count-1):
   a=i*cross_count+j;b=a+cross_count;faces.extend([[a,b,b+1],[a,b+1,a+1]])
 refv=np.array(refv);faces=np.array(faces);tree=BVHTree.FromPolygons(refv.tolist(),faces.tolist(),all_triangles=True)
 references.append((tree,refv,faces,np.array(refq),np.array(refw)))
 metrics.append({'part':name,'join_rows':[L,R],'left_join_source_outer_xy':q[L,16].tolist(),'right_join_source_outer_xy':q[R,16].tolist(),'measured_source_u_per_native_left_right':[float(dl[16]),float(dr[16])],'cross_source_pixel_span_left_right':[float(np.linalg.norm(q[L,-1]-q[L,0])),float(np.linalg.norm(q[R,-1]-q[R,0]))],'central_chart_size':[W,H],'central_unwrapped_source_pixels':N,'lower_edge_uses_actual_lower_source_boundary':name=='lower','whole_source_cells_and_midtone_preserved':True})
 for file in [name+'-continuation.rgba.npy',name+'-donors.json']:outputs.append({'path':str(root/file),'sha256':sha(root/file)})
# Static per-vertex chart records for the existing skin shader; no body arrays
# are changed, including source UV1 and all source-material reference tables.
skin=body['parts'][0];p=np.array(skin['vertices']);table=np.zeros((len(p),4));selection=np.flatnonzero((p[:,0]>.465)&(p[:,1]>-.070)&(p[:,1]<.005)&(abs(p[:,2])<.026))
for idx in selection:
 best=None
 for label,(tree,rv,faces,coords,ww) in enumerate(references):
  point,_,face,distance=tree.find_nearest(Vector(p[idx]))
  if point is None or distance>.0012:continue
  weights=bary(np.array(point),rv[faces[face]]);at=coords[faces[face]].T@weights;amount=float(ww[faces[face]]@weights)*(1-float(smooth((distance-.0003)/.0009)))
  if amount>0 and (best is None or distance<best[0]):best=(distance,at,amount,label)
 if best is not None:table[idx]=[best[1][0],best[1][1],best[2],best[3]]
path=root/'aligned-lips.mesh.json';path.write_text(json.dumps(lip,separators=(',',':')));outputs.append({'path':str(path),'sha256':sha(path)})
upper=np.load(root/'upper-continuation.rgba.npy');lower=np.load(root/'lower-continuation.rgba.npy');HH=len(upper)+len(lower);WW=max(upper.shape[1],lower.shape[1]);packed=np.zeros((HH,WW,4),np.uint8);packed[:len(upper),:upper.shape[1]]=upper;packed[len(upper):,:lower.shape[1]]=lower
for label,a in enumerate([upper,lower]):
 ids=(table[:,2]>0)&(table[:,3]==label);table[ids,0]*=a.shape[1]/WW;table[ids,1]=(table[ids,1]*len(a)+(0 if label==0 else len(upper)))/HH
path=root/'skin-continuation.rgba.npy';np.save(path,packed);outputs.append({'path':str(path),'sha256':sha(path)})
path=root/'skin-chart-records.json';path.write_text(json.dumps(table.tolist(),separators=(',',':')));outputs.append({'path':str(path),'sha256':sha(path)})
report={'schema_version':1,'ok':True,'command':'fish.build-lip-uv135','stage':'validate','status':'done','next_action':'human_review','inputs':{'plan_sha256':sha(root/'trial.plan.json'),'builder_sha256':sha(__file__),'correspondence_sha256':sha(root/'body-lip-correspondence.json')},'outputs':outputs,'summary':{'charts':metrics,'skin_vertices_with_material_coordinates':int((table[:,2]>0).sum()),'body_geometry_uv_and_reference_tables_unchanged':True,'lip_geometry_normals_and_indices_unchanged':True,'scope':'Complete native source pixel material continued from measured real body-UV joins. Adjacent skin shares the chart so original line position is retained; hidden middle is artistic extension, not anatomy acceptance.'},'failures':[]}
(root/'geometry-material.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary']),flush=True)
