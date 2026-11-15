import bpy,json,numpy as np,hashlib
from pathlib import Path
W=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(W/'candidate/fish.blend'))
ob=bpy.data.objects['Reference_head_body'];m=ob.data;m.calc_loop_triangles();uv=np.array([l.uv[:]for l in m.uv_layers.active.data]);N=2048;mask=np.zeros((N,N),bool)
for tri in m.loop_triangles:
 if tri.material_index!=2 or max(m.vertices[i].co.x for i in tri.vertices)<.8:continue
 q=uv[list(tri.loops)]*N-.5;A=np.column_stack((q[1]-q[0],q[2]-q[0]))
 if abs(np.linalg.det(A))<1e-10:continue
 lo=np.maximum(np.floor(q.min(0)).astype(int),0);hi=np.minimum(np.ceil(q.max(0)).astype(int),N-1)
 xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));p=np.c_[xx.ravel(),yy.ravel()];ab=(p-q[0])@np.linalg.inv(A).T;b=np.c_[1-ab.sum(1),ab];p=p[b.min(1)>=0];mask[p[:,1],p[:,0]]=True
def pixels(name):
 im=bpy.data.images.load(str(W/name),check_existing=False);return np.array(im.pixels[:]).reshape(N,N,4)
a=pixels('body-baked-r3.png');b=pixels('body-baked-r4.png');different=np.any(a!=b,axis=2)
r={'ok':not bool(different[mask].any()),'head_mouth_texels_protected':int(mask.sum()),'changed_protected_texels':int(different[mask].sum()),'model_sha256':hashlib.sha256((W/'candidate/fish.glb').read_bytes()).hexdigest(),'scope':'Every interior UV texel of body skin triangles reaching x>.8m compared against R3 body atlas, RGBA exact. No claim tail RGB unchanged.'}
(W/'mouth-preservation-r4.validation.json').write_text(json.dumps(r,indent=2));assert r['ok'];print(r)
