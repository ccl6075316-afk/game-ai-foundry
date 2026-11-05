"""Numeric source-bake mask for complete physical native lip domains.

No source RGB is edited. An auxiliary scalar atlas masks both auxiliary skin
colors only; original native lip transport remains the shader's base donor.
"""
import bpy,numpy as np
def nearest(points,segments):
 a=segments[:,0];v=segments[:,1]-a;t=np.clip(np.einsum('nsi,si->ns',points[:,None,:]-a[None,:,:],v)/np.einsum('si,si->s',v,v),0,1)
 return np.linalg.norm(points[:,None,:]-a[None,:,:]-t[:,:,None]*v[None,:,:],axis=2).min(1)
def build(mesh,grid,scale=186.9,upper_width=1.5,lower_width=2.,fade=1.):
 roles=[r.value for r in mesh.attributes['foundry_oral_surface'].data];edges={}
 for face in mesh.polygons:
  for a,b in zip(face.vertices,[*face.vertices[1:],face.vertices[0]]):edges.setdefault(tuple(sorted((a,b))),set()).add(roles[face.index])
 segments={role:np.array([[mesh.vertices[i].co[:]for i in edge]for edge,rs in edges.items()if 0 in rs and role in rs])for role in [1,2]};assert all(len(s)>0 for s in segments.values())
 size=grid*64;image=np.zeros((size,size,4),np.float32);image[:,:,3]=1
 proof={'protected_texels':0,'maximum_front_weight_inside_complete_lip':0.,'maximum_central_weight_inside_complete_lip':0.,'domain':{'upper_width_px':upper_width,'lower_width_px':lower_width,'outer_fade_px':fade},'upper_edges':len(segments[1]),'lower_edges':len(segments[2]),'maximum_conservative_texel_radius_source_px':0.}
 yy,xx=np.mgrid[:64,:64];u=(np.c_[xx.ravel()+.5,yy.ravel()+.5]-2.56)/58.88;raw=np.c_[1-u.sum(1),u];inside=(raw>=0).all(1);b=np.maximum(raw,0);b/=b.sum(1)[:,None]
 for k,face in enumerate(mesh.polygons):
  xyz=np.array([mesh.vertices[i].co[:]for i in face.vertices]);mask=np.zeros(4096)
  if xyz[:,0].max()*scale+934.5<1745:continue
  points=b@xyz;derivatives=np.array([xyz[1]-xyz[0],xyz[2]-xyz[0]])/58.88
  guard=.5*(np.linalg.norm(derivatives[0])+np.linalg.norm(derivatives[1]))*scale+1e-5
  proof['maximum_conservative_texel_radius_source_px']=max(proof['maximum_conservative_texel_radius_source_px'],float(guard))
  front=b@np.array([mesh.attributes['front_skin_mask'].data[i].value for i in face.loop_indices]);crown=b@np.array([mesh.attributes['crown_mask'].data[i].value for i in face.loop_indices])
  cores=np.zeros(4096,dtype=bool)
  for role,width in [(1,upper_width),(2,lower_width)]:
   distance=nearest(points,segments[role])*scale;core=(distance<=width)&inside;cores|=core
   t=np.clip((distance-width-guard)/fade,0,1);protection=1-t*t*(3-2*t);mask=np.maximum(mask,protection)
  proof['protected_texels']+=int(cores.sum())
  proof['maximum_front_weight_inside_complete_lip']=max(proof['maximum_front_weight_inside_complete_lip'],float((front*(1-mask))[cores].max(initial=0)))
  proof['maximum_central_weight_inside_complete_lip']=max(proof['maximum_central_weight_inside_complete_lip'],float((crown*(1-mask))[cores].max(initial=0)))
  tx=k%grid;ty=k//grid;image[ty*64:(ty+1)*64,tx*64:(tx+1)*64,:3]=mask.reshape(64,64,1)
 assert proof['protected_texels']>0 and proof['maximum_front_weight_inside_complete_lip']==0 and proof['maximum_central_weight_inside_complete_lip']==0
 out=bpy.data.images.new('Derived full native lip protection scalar atlas',size,size,alpha=False);out.colorspace_settings.name='Non-Color';out.pixels.foreach_set(image.ravel())
 return out,proof

def lower_native_transport(mesh,grid,curve,stations,native_pixels,scale=186.9):
 """Curve-aligned original lower-lip/lower-jaw donor across hidden front.

 This is native tissue UV transport, not either auxiliary skin color. Upper
 nose and oral faces are excluded. True lateral source ownership is retained.
 """
 def smooth(a,b,x):
  t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
 table=[]
 for x in stations:
  native_x=(x-934.5)/scale;width=max(abs(v.co.y)for v in mesh.vertices if abs(v.co.x-native_x)<1e-5);table.append((native_x,width))
 table=np.array(table);roles=[r.value for r in mesh.attributes['foundry_oral_surface'].data]
 size=grid*64;data=np.zeros((size,size,4),np.float32);data[:,:,3]=1
 yy,xx=np.mgrid[:64,:64];q=(np.c_[xx.ravel()+.5,yy.ravel()+.5]-2.56)/58.88;b=np.maximum(np.c_[1-q.sum(1),q],0);b/=b.sum(1)[:,None]
 cx,cy=np.array(curve).T;proof={'samples':0,'source_min_px':[1e10,1e10],'source_max_px':[-1e10,-1e10],'minimum_source_alpha':1.,'upper_nose_samples':0,'oral_face_samples':0,'actual_ventral_faces_excluded_from_front_chart':0,'method':'Original lower-lip curve aligned2D native coordinates over hidden frontal lowerjaw; no modulo. Continuous actual width/normal mask keeps true lateral source pixels. SourceX=min(actualX,1846+.75*abs(transverse)*186.9), sourceY=lowerLip(donorX)+actualY-lowerLip(actualX). Same native image; no generic frontskin or generated color.'}
 for k,face in enumerate(mesh.polygons):
  xyz=np.array([mesh.vertices[i].co[:]for i in face.vertices]);source_x=xyz[:,0]*scale+934.5
  if roles[k]!=0 or source_x.max()<1830:continue
  points=b@xyz;x=points[:,0]*scale+934.5;y=89.5-points[:,2]*scale;nx=b@np.array([mesh.vertices[i].normal.x for i in face.vertices]);width=np.interp(points[:,0],table[:,0],table[:,1]);branch=y>=np.interp(x,cx,cy)-2
  weight=smooth(1830,1855,x)*smooth(.05,.6,nx)*(1-smooth(.55,.85,np.abs(points[:,1])/np.maximum(width,1e-8)))*branch
  if face.normal.z<-.7 and abs(face.normal.x)<.15:
   weight[:]=0.;proof['actual_ventral_faces_excluded_from_front_chart']+=1
  dx=np.minimum(x,1846+np.abs(points[:,1])*scale*.75);dy=np.interp(dx,cx,cy)+y-np.interp(x,cx,cy)
  ix=np.clip(dx.astype(int),0,1868)
  for column in np.unique(ix):
   valid=np.flatnonzero(native_pixels[:,column,3]>.95);assert len(valid);take=ix==column;dy[take]=np.clip(dy[take],valid[0]+.5,valid[-1]+.5)
  iy=np.clip(dy.astype(int),0,178);take=weight>1e-8
  if take.any():
   assert (native_pixels[iy[take],ix[take],3]>.95).all(),'Native lower lip donor left real opaque tissue'
   coordinates=np.c_[dx[take],dy[take]];proof['samples']+=int(take.sum());proof['source_min_px']=np.minimum(proof['source_min_px'],coordinates.min(0)).tolist();proof['source_max_px']=np.maximum(proof['source_max_px'],coordinates.max(0)).tolist();proof['minimum_source_alpha']=min(proof['minimum_source_alpha'],float(native_pixels[iy[take],ix[take],3].min()))
  tile=np.c_[dx/1869,1-dy/179,weight,np.ones(4096)].reshape(64,64,4);tx=k%grid;ty=k//grid;data[ty*64:(ty+1)*64,tx*64:(tx+1)*64]=tile
 assert proof['samples']>0
 out=bpy.data.images.new('Native lower lip continuous UV and ownership field',size,size,alpha=True,float_buffer=True);out.colorspace_settings.name='Non-Color';out.pixels.foreach_set(data.ravel());return out,proof
