"""Merge exact revised body UV/colors and author fin-wall tissue donors in source.

Keeps the actual fin/body geometry, source normals, weights, rig and animation.
Only zero-source-area closing walls take inset tissue colors; cap source UV stays.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(Path(__file__).parent/'portable'),str(ROOT/'cli')]
from source_snapshot import rig_action_snapshot
from fish_budget import check_triangle_budget
sys.path.insert(0,str(Path(__file__).parent))
from native_fin_wall_chart import bake as bake_native_wall
from glb_io import read_glb
sys.path.insert(0,str(Path(__file__).parent))
from patch_existing_fin_meshes import write as write_glb
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def geometry():return repr([(o.name,[tuple(v.co)for v in o.data.vertices],[[(g.group,g.weight)for g in v.groups]for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],[tuple(n.vector)for n in o.data.corner_normals])for o in bpy.data.objects if o.type=='MESH'])
def canonical(name,image,masked):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.use_backface_culling=True;t=m.node_tree;t.nodes.clear();tex=t.nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';tex.extension='CLIP';bsdf=t.nodes.new('ShaderNodeBsdfPrincipled');bsdf.inputs['Roughness'].default_value=1;bsdf.inputs['Specular IOR Level'].default_value=0;t.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
 if masked:t.links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])
 out=t.nodes.new('ShaderNodeOutputMaterial');t.links.new(bsdf.outputs[0],out.inputs['Surface']);return m

p=argparse.ArgumentParser(description=__doc__)
for k in ['blend','config','output']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cfg=read(a.config);out=a.output.resolve();assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not out.exists();assert sha(a.blend)==cfg['blend_sha256'];receipt=ROOT/cfg['body_receipt'];assert sha(receipt)==cfg['body_receipt_sha256'];data=read(receipt)
bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));bpy.context.scene.frame_set(0);rig=rig_action_snapshot();frozen=geometry();body=bpy.data.objects[cfg['body']];assert np.max(np.abs(np.array([v.co[:]for v in body.data.vertices])-data['positions']))<1e-8;assert [list(f.vertices)for f in body.data.polygons]==data['faces'];assert len(body.data.uv_layers.active.data)==len(data['uv'])
body.data.materials.clear()
for m in data['materials']:
 path=Path(m['image']);assert sha(path)==m['sha256'];image=bpy.data.images.load(str(path),check_existing=False);image.pack();body.data.materials.append(canonical(m['name'],image,False))
for f,mi in zip(body.data.polygons,data['material_indices']):f.material_index=mi
for item,uv in zip(body.data.uv_layers.active.data,data['uv']):item.uv=uv
records=[]
for name in cfg['fins']:
 ob=bpy.data.objects[name];old=ob.data.materials[0];bsdf=next(n for n in old.node_tree.nodes if n.type=='BSDF_PRINCIPLED');tex=bsdf.inputs['Base Color'].links[0].from_node;assert tex.type=='TEX_IMAGE';image=tex.image;W,H=image.size;pixels=np.asarray(image.pixels[:]).reshape(H,W,4)[::-1];mask=pixels[:,:,3]>.95;inner=mask.copy()
 for _ in range(cfg['wall_inset_pixels']):
  pad=np.pad(inner,1);inner=np.logical_and.reduce([pad[dy:dy+H,dx:dx+W]for dy in range(3)for dx in range(3)])
 yy,xx=np.where(inner);assert len(xx)>0;safe=np.c_[xx,yy];center=np.mean(safe,axis=0);uv=ob.data.uv_layers.active.data;changes=[]
 if cfg.get('wall_native_alpha_ownership'):
  ob.data.materials.clear();ob.data.materials.append(canonical(name+'_native_caps',image,True))
  for f in ob.data.polygons:f.material_index=0
  proof=bake_native_wall(ob,image,safe,cfg['wall_inset_pixels'],cfg['source_pixels_per_native_unit'],canonical)
  records.append({'name':name,**proof,'scope':'Native tissue RGB with original cap-domain alpha on finite sidewalls; support margins cannot become detached opaque outlines.'})
  continue
 for f in ob.data.polygons:
  q=np.array([uv[li].uv[:]for li in f.loop_indices]);area=sum(np.cross(q[i]-q[0],q[i+1]-q[0])for i in range(1,len(q)-1))
  if abs(area)>1e-10:continue
  for li in f.loop_indices:
   olduv=np.array(uv[li].uv[:]);xy=olduv*[W,-H]+[0,H];direction=center-xy;sample=xy+direction/max(np.linalg.norm(direction),1e-9)*(cfg['wall_inset_pixels']+6);i=np.argmin(((safe-sample)**2).sum(axis=1));donor=safe[i];uv[li].uv=((donor[0]+.5)/W,1-(donor[1]+.5)/H);changes.append({'loop':li,'old_uv':olduv.tolist(),'source_donor_px':donor.tolist()})
 ob.data.materials.clear();ob.data.materials.append(canonical(name+'_native_caps_and_tissue_wall',image,True))
 for f in ob.data.polygons:f.material_index=0
 records.append({'name':name,'wall_loops':len(changes),'minimum_native_alpha_inset_px':cfg['wall_inset_pixels'],'changes':changes,'cap_UV_unchanged':True,'scope':'Inset actual fin tissue pixels, without global color filtering or stretched free-outline RGB.'})
for ob in bpy.data.objects:
 if ob.type!='MESH'or ob==body or ob.name in cfg['fins']:continue
 for i,old in enumerate(ob.data.materials):
  bsdf=next(n for n in old.node_tree.nodes if n.type=='BSDF_PRINCIPLED');tex=bsdf.inputs['Base Color'].links[0].from_node;assert tex.type=='TEX_IMAGE';ob.data.materials[i]=canonical(ob.name+'_native_tissue',tex.image,False)
assert geometry()==frozen,'Geometry, winding, weights or authored normals changed';assert rig_action_snapshot()==rig
triangles=0
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.data.calc_loop_triangles();triangles+=len(ob.data.loop_triangles)
budget=check_triangle_budget(triangles,cfg['real_length_cm']);out.mkdir(parents=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'fish.blend'));bpy.ops.export_scene.gltf(filepath=str(out/'fish.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True)
doc,blob=read_glb(out/'fish.glb')
for node in doc['nodes']:
 if 'mesh'not in node:continue
 for primitive in doc['meshes'][node['mesh']]['primitives']:
  material=doc['materials'][primitive['material']];material['alphaMode']='MASK'if node['name']in cfg['fins']else'OPAQUE'
  if material['alphaMode']=='MASK':material['alphaCutoff']=.5
for sampler in doc.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728,wrapS=33071,wrapT=33071)
write_glb(out/'fish.glb',doc,blob)
report={'ok':True,'kind':'source_native_body_and_fin_wall_materials','input_blend_sha256':sha(a.blend),'body_receipt_sha256':sha(receipt),'config_sha256':sha(a.config),'geometry_normals_weights_rig_actions_unchanged':True,'triangle_budget':budget,'fins':records,'blend_sha256':sha(out/'fish.blend'),'model_sha256':sha(out/'fish.glb'),'formal_acceptance':False,'scope':'Revised body color/UV and native inset fin-wall donors saved in editable source. No runtime patch; final multi-view, body/fin/action and cold-read gates pending.'};(out/'materials.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'triangles':triangles,'fins':len(records)}))
