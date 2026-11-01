"""Blender compositing: confine an image-restoration reference to old fin masks."""
import bpy,json,sys
from pathlib import Path
base=Path(sys.argv[sys.argv.index('--')+1]).resolve();assert base.name=='round2'
registration=json.loads((base/'image-registration.validation.json').read_text());H=registration['homography_normalized']
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.resolution_x=1961;scene.render.resolution_y=972;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True;scene.render.filter_size=.01;scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0.;scene.view_settings.gamma=1.
bpy.ops.mesh.primitive_plane_add(size=2);plane=bpy.context.object;plane.scale.y=972/1961
mat=bpy.data.materials.new('Body restoration, protected original pixels');mat.use_nodes=True;plane.data.materials.append(mat);tree=mat.node_tree;tree.nodes.clear()
def node(kind):return tree.nodes.new(kind)
def connect(a,b):tree.links.new(a,b)
def math(op,a,b):
 n=node('ShaderNodeMath');n.operation=op
 for i,x in enumerate([a,b]):
  if isinstance(x,(int,float)):n.inputs[i].default_value=x
  else:connect(x,n.inputs[i])
 return n.outputs[0]
uv=node('ShaderNodeTexCoord').outputs['UV'];sep=node('ShaderNodeSeparateXYZ');connect(uv,sep.inputs[0]);u=sep.outputs['X'];y=math('SUBTRACT',1.,sep.outputs['Y'])
def row(values):return math('ADD',math('ADD',math('MULTIPLY',u,values[0]),math('MULTIPLY',y,values[1])),values[2])
den=row(H[2]);mapped=node('ShaderNodeCombineXYZ');connect(math('DIVIDE',row(H[0]),den),mapped.inputs['X']);connect(math('SUBTRACT',1.,math('DIVIDE',row(H[1]),den)),mapped.inputs['Y'])
def texture(filename,coords=uv):
 n=node('ShaderNodeTexImage');n.image=bpy.data.images.load(str(base/filename),check_existing=True);n.interpolation='Closest';n.extension='CLIP';connect(coords,n.inputs['Vector']);return n
original=texture('Closed_body-0-source_texture.png');restored=texture('body-clean-reference.png',mapped.outputs[0]);amount=0.
for name in ['Dorsal','Anal','Caudal','Pectoral_left','Pectoral_right','Pelvic_left','Pelvic_right']:
 amount=math('MAXIMUM',amount,texture(name+'-0-source_texture.png').outputs['Alpha'])
amount=math('MAXIMUM',amount,texture('fin-footprint-label.png').outputs['Color'])
protected=texture('Closed_body-0-pectoral142_mask.png');amount=math('MULTIPLY',amount,math('SUBTRACT',1.,protected.outputs['Color']))
mix=node('ShaderNodeMixRGB');mix.blend_type='MIX';connect(amount,mix.inputs[0]);connect(original.outputs['Color'],mix.inputs[1]);connect(restored.outputs['Color'],mix.inputs[2])
alpha=math('ADD',math('MULTIPLY',original.outputs['Alpha'],math('SUBTRACT',1.,amount)),math('MULTIPLY',restored.outputs['Alpha'],amount))
alpha=math('MULTIPLY',alpha,texture('body-projection-label.png').outputs['Color'])
emission=node('ShaderNodeEmission');connect(mix.outputs[0],emission.inputs['Color']);transparent=node('ShaderNodeBsdfTransparent');blend=node('ShaderNodeMixShader');connect(alpha,blend.inputs[0]);connect(transparent.outputs[0],blend.inputs[1]);connect(emission.outputs[0],blend.inputs[2]);out=node('ShaderNodeOutputMaterial');connect(blend.outputs[0],out.inputs[0])
bpy.ops.object.camera_add(location=(0,0,2));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=2;scene.camera=cam
for image in bpy.data.images:
 if image.source=='FILE':image.pack()
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(base/'body-skin-composite.blend'))
scene.render.filepath=str(base/'body-skin-complete.png');bpy.ops.render.render(write_still=True)
print('BODY_SKIN_BLENDER_READY')
