"""Blender fixture producer: intentionally different inventories, no fish assets."""
import argparse
from pathlib import Path
import sys
import bpy
from mathutils import Matrix
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--bones',type=int,default=3);p.add_argument('--parts',type=int,default=3);p.add_argument('--clips',type=int,default=2)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=a.output.resolve();root=Path(__file__).resolve().parents[5]
assert out.is_relative_to(root/'work/fish-portable-tools') and not out.exists();out.mkdir(parents=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
arm=bpy.data.armatures.new('Synthetic skeleton');rig=bpy.data.objects.new('FixtureRig',arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
previous=None
for i in range(a.bones):
    b=arm.edit_bones.new('Joint'+str(i));b.head=(i*.1,0,0);b.tail=(i*.1,.1,0)
    if previous:b.parent=previous
    previous=b
bpy.ops.object.mode_set(mode='OBJECT')
mat=bpy.data.materials.new('Fixture pixels');mat.use_nodes=True;bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.8,.4,.1,1);bsdf.inputs['Roughness'].default_value=1;bsdf.inputs['Metallic'].default_value=0;bsdf.inputs['Specular IOR Level'].default_value=0;mat.use_backface_culling=True
for i in range(a.parts):
    x=i*.4;verts=[(x,0,0),(x+.2,0,0),(x,.2,0),(x,0,.2)] if i%2==0 else [(x,0,0),(x+.2,0,0),(x,.2,0)]
    faces=[(0,2,1),(0,1,3),(1,2,3),(2,0,3)] if len(verts)==4 else [(0,1,2)]
    mesh=bpy.data.meshes.new('Fixture geometry '+str(i));mesh.from_pydata(verts,[],faces);mesh.update()
    ob=bpy.data.objects.new('Piece'+str(i),mesh);bpy.context.collection.objects.link(ob);ob.parent=rig;ob.matrix_world=Matrix.Identity(4);mod=ob.modifiers.new('Skin','ARMATURE');mod.object=rig
    for j in range(a.bones):ob.vertex_groups.new(name='Joint'+str(j))
    ob.vertex_groups[i%a.bones].add(list(range(len(verts))),1,'REPLACE');mesh.materials.append(mat);uv=mesh.uv_layers.new(name='UVMap')
    for item in uv.data:item.uv=(.375,.375)
    for face in mesh.polygons:face.use_smooth=True
rig.animation_data_create()
for clip in range(a.clips):
    action=bpy.data.actions.new('Clip'+str(clip));action.use_fake_user=True;rig.animation_data.action=action
    for bone in rig.pose.bones:
        bone.rotation_mode='XYZ'
        for frame,angle in [(1,0),(7,(clip+1)*.05),(13,0)]:
            bone.rotation_euler[2]=angle;bone.keyframe_insert(data_path='rotation_euler',frame=frame,group=bone.name)
bpy.context.scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(out/'source.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'unpacked.glb'),export_format='GLB',export_animations=True,export_yup=True,export_skins=True,export_attributes=True)
