"""Repaint an existing native body atlas, preserving geometry/UV and native lips.

Only posterior body texels receive prepared own-source/declared synthetic skin;
all face/eye/fin/lining resources and protected original lip pixels are retained.
"""
import bpy,sys,json,hashlib,shutil,math
from pathlib import Path
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent/'portable'));from source_snapshot import rig_action_snapshot
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 base,src,inputs,out=map(lambda p:Path(p).resolve(),sys.argv[sys.argv.index('--')+1:]);assert not out.exists()and'/experiments/'in str(out);bpy.ops.wm.open_mainfile(filepath=str(src/'fish.blend'));body=bpy.data.objects['Reference_head_body'];me=body.data;me.calc_loop_triangles();coords=np.array([v.co[:]for v in me.vertices]);before=[(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in me.vertices];faces=[tuple(p.vertices)for p in me.polygons];uv=np.array([l.uv[:]for l in me.uv_layers.active.data]);rig_before=rig_action_snapshot();ref=json.loads((base/'shape-r2/reference.input.json').read_text());head_limit=json.loads((inputs/'preparation.validation.json').read_text()).get('head_limit',.87);L=ref['source_canvas']['length_m'];origin=ref['source_canvas']['origin_u'];aspect=ref['source_canvas']['height']/ref['source_canvas']['width'];rows=ref['body_stations'];ts=[r['t']for r in rows];axis=ref['reference_body_axis_m'];span=ref['head_span_m'];sources={};samplers=np.load(inputs/'sampler-indices.npz')
 for role,tag in [('side','clean_side'),('top','dorsal'),('bottom','clean_bottom')]:
  image=bpy.data.images.load(str(inputs/f'clean-{role}.png'),check_existing=False);w,h=image.size;pixels=np.array(image.pixels[:],dtype=np.float32).reshape(h,w,4)[::-1];mask=pixels[:,:,3]>.9;yy=np.where(mask[:,int(.87*w):])[0];sources[tag]=(w,h,pixels,(yy.min()+yy.max())/2,yy.max()-yy.min())
 slots={p.material_index for p in me.polygons if me.materials[p.material_index].name!='Actual finite oral lining'};images={n.image for s in slots for n in me.materials[s].node_tree.nodes if n.type=='TEX_IMAGE'};assert len(images)==1;atlas_image=next(iter(images));W,H=atlas_image.size;old=np.array(atlas_image.pixels[:],dtype=np.float32).reshape(H,W,4);new=old.copy();changed=np.zeros((H,W),bool);protected=np.zeros((H,W),bool);native=np.load(base/'skin-r2/native-lip-pixel-map.npz')['map'];protected[H-1-native[:,1],native[:,0]]=True
 def sample(tag,xy):
  w,h,pixels,_,_=sources[tag];ix=np.clip(np.rint(xy[:,0]).astype(int),0,w-1);iy=np.clip(np.rint(xy[:,1]).astype(int),0,h-1);indices=samplers[tag];iy,ix=indices[:,iy,ix];c=pixels[iy,ix].copy();assert np.all(c[:,3]>.9);c[:,3]=1;return c
 for tri in me.loop_triangles:
  if tri.material_index not in slots:continue
  q=uv[list(tri.loops)]*[W,H]-.5;matrix=np.column_stack([q[1]-q[0],q[2]-q[0]]);det=np.linalg.det(matrix)
  if abs(det)<.00001:continue
  lo=np.maximum(np.floor(q.min(0)-1).astype(int),0);hi=np.minimum(np.ceil(q.max(0)+1).astype(int),[W-1,H-1]);xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1));flat=np.c_[xx.ravel(),yy.ravel()];b=(flat-q[0])@np.linalg.inv(matrix).T;beta=np.c_[1-b.sum(1),b];# Edge padding must stay near the finite UV triangle.
  assert np.isfinite(beta).all(),('Nonfinite UV raster',tri.index)
  inside=beta.min(1)>=-1e-7;distance=np.full(len(flat),1e9)
  for a,z in zip(q,np.roll(q,-1,axis=0)):
   e=z-a;t=np.clip(((flat-a)*e).sum(1)/max(float(e@e),1e-20),0,1);distance=np.minimum(distance,np.linalg.norm(flat-(a+t[:,None]*e),axis=1))
  take=inside|(distance<=.8);take&=~protected[flat[:,1],flat[:,0]]
  if not take.any():continue
  flat=flat[take];beta=np.maximum(beta[take],0);beta/=beta.sum(1)[:,None];p=beta@coords[list(tri.vertices)];u=p[:,0]/L+origin;fade=np.clip((head_limit-u)/.035,0,1);fade=fade*fade*(3-2*fade);good=fade>0
  assert np.isfinite(p).all()and np.isfinite(fade).all(),('Nonfinite body sample',tri.index)
  if not good.any():continue
  p=p[good];u=u[good];flat=flat[good];fade=fade[good];v=.5-p[:,2]/(aspect*L);t=(axis/2-p[:,0])/axis;zt=np.interp(t,ts,[r['top_z_m']for r in rows]);zb=np.interp(t,ts,[r['bottom_z_m']for r in rows]);height=(p[:,2]-(zt+zb)/2)/np.maximum((zt-zb)/2,1e-6);w,h,*_=sources['clean_side'];side=sample('clean_side',np.c_[u*w,v*h]);op=[]
  for tag in ['dorsal','clean_bottom']:
   w,h,pixels,center,spanpx=sources[tag];op.append(sample(tag,np.c_[u*(w-1),center+p[:,1]/span*spanpx]))
  blend=np.clip((abs(height)-.18)/.42,0,1);blend=blend*blend*(3-2*blend);field=side*(1-blend[:,None])+np.where(height[:,None]>0,op[0],op[1])*blend[:,None];previous=old[flat[:,1],flat[:,0]];color=previous*(1-fade[:,None])+field*fade[:,None];color[:,3]=previous[:,3];new[flat[:,1],flat[:,0]]=color;changed[flat[:,1],flat[:,0]]=True
 assert np.array_equal(new[protected],old[protected]);assert np.array_equal(new[~changed],old[~changed]);assert np.array_equal(new[:,:,3],old[:,:,3]);atlas_image.pixels.foreach_set(new.ravel());atlas_image.update();atlas_image.pack();assert before==[(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in me.vertices]and faces==[tuple(p.vertices)for p in me.polygons]and np.array_equal(uv,np.array([l.uv[:]for l in me.uv_layers.active.data]));assert rig_action_snapshot()==rig_before;out.mkdir();bpy.context.preferences.filepaths.save_version=0;bpy.ops.object.select_all(action='DESELECT')
 for ob in bpy.context.scene.objects:
  if ob.type in ['MESH','ARMATURE']:ob.select_set(True)
 bpy.context.view_layer.objects.active=body;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_def_bones=False);shutil.copyfile(src/'fin-authoring.json',out/'fin-authoring.json');np.savez_compressed(out/'body-color-mask.npz',changed=changed,protected_native_lips=protected);report=dict(ok=True,kind='existing_native_body_atlas_posterior_skin_repair',baseline_sha256=sha(src/'fish.glb'),model_sha256=sha(out/'fish.glb'),skin_inputs_sha256=sha(inputs/'preparation.validation.json'),body_geometry_topology_UV_weights_exact=True,rig_actions_exact=True,original_native_lip_texels_exact=True,non_target_atlas_texels_exact=True,alpha_exact=True,changed_texels=int(changed.sum()),protected_native_lip_texels=int(protected.sum()),head_field=f'u>={head_limit} unchanged;C1fade{head_limit-.035}..{head_limit}',source='Original own native views plus explicit generated ghost-footprint patches. Fins/eyes/lining material nodes untouched.',visual_review='pending',formal_acceptance=False);(out/'skin-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n');print('NATIVE_SKIN_CANDIDATE',base.name,report['changed_texels'])
if __name__=='__main__':main()
