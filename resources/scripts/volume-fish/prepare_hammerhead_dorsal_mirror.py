"""Map only upper left skin texels to the existing right skin, head facing up.

Readonly mesh mapping, native Blender Y<0 donor and Y>0 receiver. This is an
asset texture bake; no model geometry or source image is generated/altered.
"""
import bpy,json,hashlib,sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
args=sys.argv[sys.argv.index('--')+1:];src,out=map(lambda p:Path(p).resolve(),args);assert not(out/'mapping.npz').exists();out.mkdir(exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST';body=bpy.data.objects['Reference_head_body'];me=body.data;me.calc_loop_triangles();uv=me.uv_layers.active;verts=np.array([v.co[:]for v in me.vertices]);skin={i for i,m in enumerate(me.materials)if m.name.startswith(('Project-native','Own native body pixels'))};faces=list(me.loop_triangles);donors=[t for t in faces if t.material_index in skin and max(verts[list(t.vertices),1])<=1e-6];tree=BVHTree.FromPolygons([Vector(v)for v in verts],[tuple(t.vertices)for t in donors],all_triangles=True);sizes={};maps=[];protected=np.load(src.parent/'skin-author-r7/native-lip-pixel-map.npz')['map'];protected_xy=set((int(x),int(y))for x,y,*_ in protected);normal=np.array([n.vector[:]for n in me.corner_normals])
for slot in sorted(skin):
 image=next(n.image for n in me.materials[slot].node_tree.nodes if n.type=='TEX_IMAGE');sizes[slot]=list(image.size)
for t in faces:
 slot=t.material_index
 if slot not in skin:continue
 xyz=verts[list(t.vertices)]
 if xyz[:,1].max()<=1e-6:continue
 W,H=sizes[slot];uvs=np.array([uv.data[k].uv[:]for k in t.loops]);q=np.stack([uvs[:,0]*W-.5,(1-uvs[:,1])*H-.5],axis=1);a,b,c=q;den=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 if abs(den)<1e-9:continue
 lo=np.maximum(np.floor(q.min(0)).astype(int),0);hi=np.minimum(np.ceil(q.max(0)).astype(int),[W-1,H-1]);xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));p=np.stack([xx.ravel(),yy.ravel()],1);bb=((p[:,0]-a[0])*(c[1]-a[1])-(p[:,1]-a[1])*(c[0]-a[0]))/den;cc=((b[0]-a[0])*(p[:,1]-a[1])-(b[1]-a[1])*(p[:,0]-a[0]))/den;beta=np.stack([1-bb-cc,bb,cc],1);good=beta.min(1)>=-1e-7;beta=beta[good];p=p[good];points=beta@xyz;ns=beta@normal[list(t.loops)];ns/=np.maximum(np.linalg.norm(ns,axis=1)[:,None],1e-12);gain=np.clip((ns[:,2]-.10)/.45,0,1);gain=gain*gain*(3-2*gain);take=(points[:,1]>1e-6)&(gain>0);points,p,gain=points[take],p[take],gain[take]
 for point,(tx,ty),weight in zip(points,p,gain):
  if slot==1 and (int(tx),int(ty))in protected_xy:continue
  mirror=Vector((point[0],-point[1],point[2]));hit,no,fi,distance=tree.find_nearest(mirror);assert hit is not None;dt=donors[fi];ids=list(dt.vertices);bary=np.array(barycentric_transform(hit,*[Vector(v)for v in verts[ids]],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))));bary=np.maximum(bary,0);bary/=bary.sum();duv=bary@np.array([uv.data[k].uv[:]for k in dt.loops]);dw,dh=sizes[dt.material_index];sx=int(np.clip(np.floor(duv[0]*dw),0,dw-1));sy=int(np.clip(np.floor((1-duv[1])*dh),0,dh-1));maps.append([slot,int(tx),int(ty),dt.material_index,sx,sy,float(weight),float(distance),int(t.polygon_index),int(dt.polygon_index)])
assert maps;data=np.array(maps);np.savez_compressed(out/'mapping.npz',map=data);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();report=dict(ok=True,kind='right_to_left_dorsal_existing_surface_color_map',baseline_sha256=sha(src/'fish.glb'),source_blend_sha256=sha(src/'fish.blend'),script_sha256=sha(__file__),mapping_sha256=sha(out/'mapping.npz'),sizes=sizes,mapped_texels=len(maps),donor_side='Native Y<0: screen-right with head up; screenshot top camera up=-GLTFZ maps native+Y to screen-up when head points right, so donor is original lower half.',receiver_side='Native Y>0 only; interpolated static normal Z weights full transfer above.55, fade.10–.55 near lateral flank.',maximum_mirror_surface_distance_m=float(data[:,7].max()),protected_native_lip_texels=len(protected),geometry_UV_materials_unedited=True,formal_acceptance=False);(out/'mapping.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
