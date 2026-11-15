"""Rebake complete skin from coherent full-body projections in actual rest space.
Generated atlas attempt rejected: shifted islands are not source UV contracts.
"""
import bpy,json,hashlib,struct
import numpy as np
from pathlib import Path
W=Path(__file__).parent;O=W/'candidate'
exec((W/'apply_body_paint.py').read_text().split('bpy.ops.wm.open_mainfile')[0])
bpy.ops.wm.open_mainfile(filepath=str(W/'history/r2-before-edge-repair/fish.blend'))
exec(compile((W/'prepare_skin_r3.py').read_text(),str(W/'prepare_skin_r3.py'),'exec'))
ob=bpy.data.objects['Reference_head_body'];m=ob.data;m.calc_loop_triangles()
views=json.loads((W/'body-guide-r3.png.json').read_text())['views']
def read_image(path):
 im=bpy.data.images.load(str(path),check_existing=False);a=np.array(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],4)[::-1];return a
guide=read_image(W/'body-guide-r3.png');paint=read_image(W/'body-projections-r3.png')
def bounds(a):
 mask=a[:,:,:3].max(2)>.16;lo=np.full(a.shape[1],np.nan);hi=lo.copy()
 for x in range(a.shape[1]):
  ids=np.flatnonzero(mask[:,x])
  if len(ids):lo[x]=ids[0];hi[x]=ids[-1]
 valid=np.flatnonzero(np.isfinite(lo));return lo,hi,valid
panels=[]
for i in range(3):
 a=guide[round(i*guide.shape[0]/3):round((i+1)*guide.shape[0]/3)];b=paint[round(i*paint.shape[0]/3):round((i+1)*paint.shape[0]/3)];panels.append((a,b,bounds(a),bounds(b)))
sampling=[{'samples':0,'max_horizontal_edge_guard_px':0.,'max_outside_reference_column_fraction':0.}for i in range(3)]
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def sample(q,points):
 view=views[q];a,b,ba,bb=panels[q];p=points[:,[0,2,1]].copy();p[:,2]*=-1;p-=np.array(view['focus']);u=p@np.array(view['right'])/view['width']+.5;v=.5-p@np.array(view['up'])/view['height']
 ax=u*a.shape[1]-.5;ay=v*a.shape[0]-.5;lo,hi,valid=ba
 al=np.interp(ax,valid,lo[valid]);ah=np.interp(ax,valid,hi[valid]);fraction=(ay-al)/np.maximum(ah-al,1.)
 bx=u*b.shape[1]-.5;lo,hi,valid=bb;cx=np.clip(bx,valid[0],valid[-1]);bl=np.interp(cx,valid,lo[valid]);bh=np.interp(cx,valid,hi[valid])
 sampling[q]['max_horizontal_edge_guard_px']=max(sampling[q]['max_horizontal_edge_guard_px'],float(np.max(abs(cx-bx))))
 sampling[q]['max_outside_reference_column_fraction']=max(sampling[q]['max_outside_reference_column_fraction'],float(np.max(np.maximum(-fraction,fraction-1))))
 # Same whole-body column map; source is a continuous actual anatomical view,
 # never a repeated stripe or arbitrary texture patch. Edge guard stays bounded.
 cy=bl+np.clip(fraction,.025,.975)*(bh-bl);ix=np.rint(cx).astype(int);iy=np.rint(cy).astype(int)
 sampling[q]['samples']+=len(points);return b[iy,ix,:3]
coords=np.array([v.co[:]for v in m.vertices]);uv=np.array([l.uv[:]for l in m.uv_layers.active.data])
outer=np.array(sorted(set(i for f in m.polygons if f.material_index==2 for i in f.vertices)))
stations=np.linspace(coords[outer,0].min(),coords[outer,0].max(),90);top=[];bottom=[]
for x in stations:
 near=coords[outer][abs(coords[outer,0]-x)<.055]
 if not len(near):near=coords[outer[np.argsort(abs(coords[outer,0]-x))[:8]]]
 top.append(float(near[:,2].max()));bottom.append(float(near[:,2].min()))
def color(points):
 view=views[0];a=panels[0][0];lo,hi,valid=panels[0][2]
 ax=(points[:,0]/view['width']+.5)*a.shape[1]-.5
 ay=(.5-(points[:,2]-view['focus'][1])/view['height'])*a.shape[0]-.5
 al=np.interp(ax,valid,lo[valid]);ah=np.interp(ax,valid,hi[valid]);h=np.clip(1-(ay-al)/np.maximum(ah-al,1),0,1)
 up=smooth(.55,.96,h);down=1-smooth(.04,.45,h)
 # Central ventral jaws have no dark painted outline. Their real geometry
 # supplies the boundary. Head transition is a continuous spatial field.
 ventral=smooth(.82,1.02,points[:,0])*(1-smooth(-.235,-.17,points[:,2]));down=np.maximum(down,ventral);up*=1-ventral;side=np.maximum(0,1-up-down);total=up+down+side
 colors=[sample(i,points)for i in range(3)]
 return (colors[0]*side[:,None]+colors[1]*up[:,None]+colors[2]*down[:,None])/total[:,None]
N=2048;atlas=np.empty((N,N,4),np.float32);atlas[:]=(.43,.49,.50,1);owned=np.zeros((N,N),bool);painted=0
for tri in m.loop_triangles:
 if tri.material_index!=2:continue
 lis=list(tri.loops);ids=list(tri.vertices);q=uv[lis]*N-.5;A=np.column_stack((q[1]-q[0],q[2]-q[0]))
 if abs(np.linalg.det(A))<1e-10:continue
 lo=np.maximum(np.floor(q.min(0)-2).astype(int),0);hi=np.minimum(np.ceil(q.max(0)+2).astype(int),N-1)
 xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));pix=np.c_[xx.ravel(),yy.ravel()];ab=(pix-q[0])@np.linalg.inv(A).T;beta=np.c_[1-ab.sum(1),ab];inside=beta.min(1)>=-1e-8
 dist=np.full(len(pix),1e9)
 for a,b in zip(q,np.roll(q,-1,axis=0)):
  e=b-a;t=np.clip(((pix-a)*e).sum(1)/max(e@e,1e-20),0,1);dist=np.minimum(dist,np.linalg.norm(pix-(a+t[:,None]*e),axis=1))
 take=inside|((dist<2)&(~owned[pix[:,1],pix[:,0]]));pix=pix[take];beta=np.maximum(beta[take],0);beta/=beta.sum(1)[:,None];inside=inside[take]
 if not len(pix):continue
 rgb=color(beta@coords[ids]);atlas[pix[:,1],pix[:,0],:3]=rgb;owned[pix[inside,1],pix[inside,0]]=True;painted+=len(pix)
assert all(r['max_horizontal_edge_guard_px']<18 for r in sampling),sampling
image=bpy.data.images.new('Great hammerhead coherent entire skin R3',width=N,height=N,alpha=True)
image.pixels.foreach_set(atlas.ravel());image.filepath_raw=str(W/'body-baked-r3.png');image.file_format='PNG';image.save();image.pack()
nodes=[n for n in m.materials[2].node_tree.nodes if n.type=='TEX_IMAGE'];assert len(nodes)==1;nodes[0].image=image;nodes[0].interpolation='Closest'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(O/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
before=accessors(W/'history/r2-before-edge-repair/fish.glb');after=accessors(O/'fish.glb')
report={'ok':True,'model_sha256':sha(O/'fish.glb'),'source_sha256':sha(O/'fish.blend'),'projection_sha256':sha(W/'body-projections-r3.png'),'guide_sha256':sha(W/'body-guide-r3.png'),'baked_sha256':sha(W/'body-baked-r3.png'),'owned_body_texels':int(owned.sum()),'sampling':sampling,'method':'Complete body rebake in continuous3D rest coordinates using side/dorsal/ventral body-only color sources. Full skin UV unwrap to remove old overlapping mapping; local rim geometry smoothed. No local RGB patch. Other fins and eyes unchanged. Current visual review required.'}
(W/'body-bake-r3.validation.json').write_text(json.dumps(report,indent=2));print(report)
