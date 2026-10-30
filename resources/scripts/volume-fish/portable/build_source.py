"""Author an editable single-material source while retaining an established rig.

One authoring operation may read frozen reference normals/UVs. The resulting
source owns exact float corner attributes; its normal export reads no target GLB.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))


from fish_asset_spec import ROOT, load_spec_snapshot, input_paths, preflight, fresh_outputs, declared_parts, require

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def as_blender(v):return (v[0],-v[2],v[1])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True,help='Fresh directory below work/fish-portable-tools')
    p.add_argument('--json',action='store_true')
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    a=p.parse_args(argv)
    import bpy
    from mathutils import Matrix
    from patch_existing_fin_meshes import read
    from repair_fin_clearance import values
    from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature
    from export_packed_fish_source import EXACT_UV,PART_ID,SOURCE_VERTEX,FACE_PART,float_uv_signature,part_signature,material_signature
    from export_source import export_source as export_packed_source
    recipe,recipe_digest=load_spec_snapshot(a.spec); inputs=input_paths(recipe); check=preflight(a.spec)
    require(check['summary']['spec_sha256']==recipe_digest,'Spec changed between load and preflight')
    output=a.output.resolve()
    fresh_outputs([output,output/'fish.blend',output/'fish.glb',output/'source-build.validation.json'],list(inputs.values())+[a.spec])
    d,b=read(inputs['reference_glb']); pr=d['meshes'][0]['primitives'][0]
    at={k:values(d,b,v)for k,v in pr['attributes'].items()};indices=[x[0]for x in values(d,b,pr['indices'])]
    vertex_count=len(at['POSITION']); triangle_count=len(indices)//3
    source_node=next(n for n in d['nodes']if 'mesh'in n)
    require(source_node['name']==recipe['source_mesh_name'],'Source mesh must match packed reference owner name')
    joint_names=[d['nodes'][j]['name']for j in d['skins'][source_node['skin']]['joints']]
    parts=check['summary']['parts']; point_ids=[None]*vertex_count; face_ids=[None]*triangle_count
    for part in parts:
        start=part['source_vertex_start'];end=start+part['vertex_count'];i0=part['index_start'];i1=i0+part['index_count']
        for i in range(start,end):point_ids[i]=part['part_id']
        for i in range(i0//3,i1//3):
            face_ids[i]=part['part_id'];require(all(start<=v<end for v in indices[i*3:i*3+3]),'Triangle escapes declared part')
    bpy.ops.wm.open_mainfile(filepath=str(inputs['source_blend']))
    objects=[ob for ob in bpy.data.objects if ob.type=='MESH'];require(bool(objects),'Source contains no meshes')
    if 'source_mesh_objects' in recipe['expected']:require(len(objects)==recipe['expected']['source_mesh_objects'],'Source mesh object count differs')
    rigs=[ob for ob in bpy.data.objects if ob.type=='ARMATURE'];assert len(rigs)==1;rig=rigs[0]
    assert set(joint_names)==set(rig.data.bones.keys()),(joint_names,list(rig.data.bones.keys()))
    assert all(ob.parent==rig and all(m.type=='ARMATURE'and m.object==rig for m in ob.modifiers)for ob in objects)
    identity=Matrix.Identity(4)
    require(max(abs(rig.matrix_world[i][j]-identity[i][j])for i in range(4)for j in range(4))<1e-6,'Nonidentity source rig transform unsupported')
    assert all(max(abs(ob.matrix_world[i][j]-identity[i][j])for i in range(4)for j in range(4))<1e-6 for ob in objects),'Source mesh transform requires explicit coordinate baking'
    rig_before={'matrix_world':[list(x)for x in rig.matrix_world],'bones':[(bone.name,bone.parent.name if bone.parent else None,[list(x)for x in bone.matrix_local])for bone in rig.data.bones],'active_action':rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None}
    from source_snapshot import rig_action_snapshot
    full_rig_before=rig_action_snapshot()
    packed=bpy.data.objects[recipe['source_mesh_name']]
    require(packed in objects,'source_mesh_name must identify a mesh')
    require(not packed.constraints and not packed.children and not packed.animation_data,'Unsupported packed mesh behavior')
    for ob in objects:
        if ob==packed:continue
        assert not ob.animation_data and not ob.constraints and not ob.children,'Unexpected source mesh object behavior'
        name=ob.name;collections=list(ob.users_collection);parent=ob.parent;basis=ob.matrix_basis.copy();inverse=ob.matrix_parent_inverse.copy()
        bpy.data.objects.remove(ob,do_unlink=True);empty=bpy.data.objects.new(name,None)
        for collection in collections:collection.objects.link(empty)
        empty.parent=parent;empty.matrix_parent_inverse=inverse;empty.matrix_basis=basis
    mesh=bpy.data.meshes.new('Packed fish editable disconnected mesh');mesh.from_pydata([as_blender(x)for x in at['POSITION']],[],[indices[i:i+3]for i in range(0,len(indices),3)]);mesh.update();packed.data=mesh;packed.vertex_groups.clear()
    for name in joint_names:packed.vertex_groups.new(name=name)
    for i,(joints,weights)in enumerate(zip(at['JOINTS_0'],at['WEIGHTS_0'])):
        for joint,weight in zip(joints,weights):
            if weight>0:packed.vertex_groups[joint_names[joint]].add([i],weight,'REPLACE')
    uv=mesh.uv_layers.new(name='UVMap');exact_uv=mesh.attributes.new(EXACT_UV,'FLOAT2','CORNER');exact_normal=mesh.attributes.new(EXACT_NORMAL_ATTRIBUTE,'FLOAT_VECTOR','CORNER');part_attr=mesh.attributes.new(PART_ID,'FLOAT','POINT');source_attr=mesh.attributes.new(SOURCE_VERTEX,'FLOAT','POINT');face_attr=mesh.attributes.new(FACE_PART,'INT','FACE');normals=[]
    # Adding CustomData layers invalidates previously held RNA layer handles.
    # Re-acquire by name after every layer exists, before writing any values.
    uv=mesh.uv_layers['UVMap'];exact_uv=mesh.attributes[EXACT_UV];exact_normal=mesh.attributes[EXACT_NORMAL_ATTRIBUTE];part_attr=mesh.attributes[PART_ID];source_attr=mesh.attributes[SOURCE_VERTEX];face_attr=mesh.attributes[FACE_PART]
    mesh.uv_layers.active=uv;uv.active_render=True
    for i in range(vertex_count):part_attr.data[i].value=point_ids[i];source_attr.data[i].value=i
    for face in mesh.polygons:
        face.use_smooth=True;face_attr.data[face.index].value=face_ids[face.index]
        assert list(face.vertices)==indices[face.index*3:face.index*3+3]
        for li in face.loop_indices:
            vertex=mesh.loops[li].vertex_index;t=at['TEXCOORD_0'][vertex];n=at['NORMAL'][vertex];uv.data[li].uv=(t[0],1-t[1]);exact_uv.data[li].vector=t;exact_normal.data[li].vector=n;normals.append(as_blender(n))
    mesh.normals_split_custom_set(normals);mesh.update()
    for loop in mesh.loops:
        vertex=loop.vertex_index
        assert tuple(mesh.attributes[EXACT_NORMAL_ATTRIBUTE].data[loop.index].vector)==at['NORMAL'][vertex],'Authored float normal mismatch'
        assert tuple(mesh.attributes[EXACT_UV].data[loop.index].vector)==at['TEXCOORD_0'][vertex],'Authored float UV mismatch'
    material=bpy.data.materials.new('Packed fish native pixels');material.use_nodes=True;material.node_tree.nodes.clear();bsdf=material.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=material.node_tree.nodes.new('ShaderNodeOutputMaterial');texture=material.node_tree.nodes.new('ShaderNodeTexImage');image=bpy.data.images.load(str(inputs['atlas']),check_existing=False);image.pack();image.colorspace_settings.name='sRGB';texture.image=image;texture.interpolation='Closest';texture.extension='EXTEND'
    uv_node=material.node_tree.nodes.new('ShaderNodeUVMap');uv_node.uv_map='UVMap';material.node_tree.links.new(uv_node.outputs['UV'],texture.inputs['Vector'])
    material.node_tree.links.new(texture.outputs['Color'],bsdf.inputs['Base Color']);material.node_tree.links.new(texture.outputs['Alpha'],bsdf.inputs['Alpha']);material.node_tree.links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    for key,value in [('Roughness',1.),('Metallic',0.),('Specular IOR Level',0.)]:bsdf.inputs[key].default_value=value
    material.surface_render_method='DITHERED';material.use_backface_culling=True
    contract={'alphaMode':'MASK','alphaCutoff':.5,'doubleSided':False,'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071,'roughnessFactor':1,'metallicFactor':0,'specularFactor':0};material['foundry_export_contract_json']=json.dumps(contract,sort_keys=True);mesh.materials.append(material)
    mesh['foundry_geometry_parts_json']=json.dumps(parts,sort_keys=True);mesh['foundry_authoring_reference_sha256']=sha(inputs['reference_glb']);mesh['foundry_normal_geometry_sha256']=geometry_signature(packed);mesh['foundry_exact_normal_sha256']=normal_attribute_signature(packed);mesh['foundry_exact_uv_sha256']=float_uv_signature(mesh);mesh['foundry_part_signature_sha256']=part_signature(mesh);material['foundry_material_signature_sha256']=material_signature(material)
    rig_after={'matrix_world':[list(x)for x in rig.matrix_world],'bones':[(bone.name,bone.parent.name if bone.parent else None,[list(x)for x in bone.matrix_local])for bone in rig.data.bones],'active_action':rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None};assert rig_before==rig_after
    require(full_rig_before==rig_action_snapshot(),'Rig/rest/action data changed during authoring')
    # Remove only unreferenced old mesh/material/image data in this NEW source.
    for collection in (bpy.data.meshes,bpy.data.materials,bpy.data.images):
        for item in list(collection):
            if item.users==0:collection.remove(item)
    output.mkdir(parents=True,exist_ok=True);source=output/'fish.blend';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(source));export=export_packed_source(output/'fish.glb')
    for k,path in inputs.items():assert sha(path)==recipe['inputs'][k]['sha256'],k+' input changed'
    require(sha(a.spec)==recipe_digest,'Spec changed during source authoring')
    proof={'ok':True,'kind':'packed_editable_fish_source_authoring','recipe_sha256':recipe_digest,'builder_sha256':sha(__file__),'input_files':recipe['inputs'],'output_blend_sha256':sha(source),'output_model_sha256':sha(output/'fish.glb'),'source_mesh':packed.name,'triangles':len(mesh.polygons),'vertices':len(mesh.vertices),'bones':len(rig.data.bones),'surfaces':len(mesh.materials),'logical_parts':parts,'rig_and_active_action_unchanged_by_authoring':True,'all_rig_rest_actions_unchanged':True,'derived_reference_inventory':check['summary']['inventory'],'source_owned_exact_normal_attribute':EXACT_NORMAL_ATTRIBUTE,'source_owned_exact_uv_attribute':EXACT_UV,'part_attribute':PART_ID,'source_vertex_attribute':SOURCE_VERTEX,'face_part_attribute':FACE_PART,'export_proof':export,'scope':'One-time source authoring from frozen assets, no old input writes. Full fresh source re-export and actual final gates still required.'};(output/'source-build.validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'ok':True,'blend':sha(source),'model':sha(output/'fish.glb'),'parts':len(parts)}))
if __name__=='__main__':main()
