import bpy,json,hashlib,struct,numpy as np
from pathlib import Path
W=Path(__file__).parent;O=W/'candidate'
exec((W/'apply_body_paint.py').read_text().split('bpy.ops.wm.open_mainfile')[0])
bpy.ops.wm.open_mainfile(filepath=str(W/'history/r3-before-tail-action-review/fish.blend'))
ob=bpy.data.objects['Reference_head_body'];m=ob.data;m.calc_loop_triangles()
src=(W/'bake_body_r3.py').read_text();exec(src[src.index('views=json.loads'):src.index('N=2048;')])
original_color=color
def color(points):
 p=points.copy();p[:,0]=np.maximum(p[:,0],-1.515)
 return original_color(p)
# The generated body donor's very first column includes its dark silhouette edge.
# Re-evaluate the complete body atlas with an explicit inward tail-end sample.
# Both adjoining surfaces now use the same actual interior source column.
exec(src[src.index('N=2048;'):src.index("image=bpy.data.images.new")])
bodyim=bpy.data.images.new('Whole body R4 corrected tail-end sampling',width=N,height=N,alpha=True);bodyim.pixels.foreach_set(atlas.ravel());bodyim.filepath_raw=str(W/'body-baked-r4.png');bodyim.file_format='PNG';bodyim.save();bodyim.pack()
for n in m.materials[2].node_tree.nodes:
 if n.type=='TEX_IMAGE':n.image=bodyim
body_image=m.materials[2].node_tree.nodes.get('Image Texture')
ob=bpy.data.objects['Caudal'];m=ob.data;m.calc_loop_triangles();coords=np.array([v.co[:]for v in m.vertices]);uv=np.array([l.uv[:]for l in m.uv_layers.active.data])
oldim=next(n.image for n in m.materials[0].node_tree.nodes if n.type=='TEX_IMAGE');N=oldim.size[0];old=np.array(oldim.pixels[:],dtype=np.float32).reshape(N,N,4);atlas=old.copy();owned=np.zeros((N,N),bool)
for tri in m.loop_triangles:
 ids=list(tri.vertices);q=uv[list(tri.loops)]*N-.5;A=np.column_stack((q[1]-q[0],q[2]-q[0]))
 if abs(np.linalg.det(A))<1e-10:continue
 lo=np.maximum(np.floor(q.min(0)-2).astype(int),0);hi=np.minimum(np.ceil(q.max(0)+2).astype(int),N-1)
 xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));pix=np.c_[xx.ravel(),yy.ravel()];ab=(pix-q[0])@np.linalg.inv(A).T;beta=np.c_[1-ab.sum(1),ab];inside=beta.min(1)>=-1e-8
 dist=np.full(len(pix),1e9)
 for a,b in zip(q,np.roll(q,-1,axis=0)):
  e=b-a;t=np.clip(((pix-a)*e).sum(1)/max(e@e,1e-20),0,1);dist=np.minimum(dist,np.linalg.norm(pix-(a+t[:,None]*e),axis=1))
 take=inside|((dist<2)&(~owned[pix[:,1],pix[:,0]]));pix=pix[take];inside=inside[take];beta=np.maximum(beta[take],0);beta/=beta.sum(1)[:,None]
 if not len(pix):continue
 p=beta@coords[ids];distance=-1.53-p[:,0]
 # Anatomical tail-root continuation in the same 3D field as entire body.
 # No geometric changes or extra surface. Entire caudal atlas rebaked.
 samplep=p.copy();samplep[:,0]=-1.515
 rgb=color(samplep)
 oldrgb=old[pix[:,1],pix[:,0],:3]
 # Preserve distal fin pigment/texture progressively; root has no legacy ink.
 fade=smooth(.025,.48,distance);rgb=rgb*(1-fade[:,None])+oldrgb*fade[:,None]
 atlas[pix[:,1],pix[:,0],:3]=rgb;owned[pix[inside,1],pix[inside,0]]=True
im=bpy.data.images.new('Complete caudal body-continuity R4',width=N,height=N,alpha=True);im.pixels.foreach_set(atlas.ravel());im.filepath_raw=str(W/'caudal-baked-r4.png');im.file_format='PNG';im.save();im.pack()
for mat in m.materials:
 for n in mat.node_tree.nodes:
  if n.type=='TEX_IMAGE':n.image=im;n.interpolation='Closest'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(O/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
assert accessors(W/'history/r3-before-tail-action-review/fish.glb')==accessors(O/'fish.glb')
r={'ok':True,'source_sha256':sha(O/'fish.blend'),'model_sha256':sha(O/'fish.glb'),'base_source_sha256':sha(W/'history/r3-before-tail-action-review/fish.blend'),'all_non_image_accessors_exact':True,'scope':'Whole body and caudal atlas RGB rebaked with common interior tail-end column x=-1.515 to exclude generated silhouette ink. Other fin/eye images unchanged. Distal caudal original color retained by continuous25-480mm root-distance transition. No lip geometry, UV, weights, bones or native clip edits.','owned_texels':int(owned.sum()),'atlas_sha256':sha(W/'caudal-baked-r4.png')}
(W/'tail-r4.validation.json').write_text(json.dumps(r,indent=2));print(r)

