"""Author an editable single-material source while retaining an established rig.

One authoring operation may read frozen reference normals/UVs. The resulting
source owns exact float corner attributes; its normal export reads no target GLB.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from patch_existing_fin_meshes import read
from repair_fin_clearance import values
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature
from export_packed_fish_source import EXACT_UV,PART_ID,SOURCE_VERTEX,FACE_PART,float_uv_signature,part_signature,material_signature,export_packed_source

ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def as_blender(v):return (v[0],-v[2],v[1])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);output=a.output.resolve();assert output.is_relative_to(ROOT/'projects/fishing-2d/experiments')and not(output/'fish.blend').exists()and not(output/'fish.glb').exists()and not(output.parent/'source-build.validation.json').exists(),'Fresh source/artifact/report paths required'
    recipe=json.loads(a.recipe.read_text());inputs={k:ROOT/v['path']for k,v in recipe['inputs'].items()}
    outputs={(output/'fish.blend').resolve(),(output/'fish.glb').resolve(),(output.parent/'source-build.validation.json').resolve()}
    assert len(outputs)==3 and not outputs.intersection({p.resolve()for p in inputs.values()}|{a.recipe.resolve()}),'Source outputs/report alias an input or recipe'
    assert not any(p.exists()for p in outputs),'Refuse overwriting source or report evidence'
    for k,path in inputs.items():assert sha(path)==recipe['inputs'][k]['sha256'],k+' stale authoring input'
    d,b=read(inputs['authoring_reference_glb']);assert len(d['meshes'])==1 and len(d['meshes'][0]['primitives'])==1
    pr=d['meshes'][0]['primitives'][0];at={k:values(d,b,v)for k,v in pr['attributes'].items()};indices=[x[0]for x in values(d,b,pr['indices'])];assert len(indices)==5130 and len(at['POSITION'])==1465 and set(indices)==set(range(1465))
    source_node=next(n for n in d['nodes']if 'mesh'in n);joint_names=[d['nodes'][j]['name']for j in d['skins'][source_node['skin']]['joints']];assert len(joint_names)==18
    packing=json.loads(inputs['packing_report'].read_text());assert packing['candidates']['merged-mask']['sha256']==sha(inputs['authoring_reference_glb'])
    parts=[];point_ids=[None]*1465;face_ids=[None]*1710
    for part_id,spec in enumerate(packing['parts'],1):
        start,end=spec['new_vertex_range'];i0,i1=spec['new_index_range'];name=spec['node']if spec['surface']==0 else 'Oral_cavity';role='mouth'if name=='Oral_cavity'else 'body_skin'if name=='Closed_body_B'else 'fin'
        record={'part_id':part_id,'name':name,'role':role,'source_node':spec['node'],'source_surface':spec['surface'],'source_vertex_start':start,'vertex_count':end-start,'index_start':i0,'index_count':i1-i0,'source_model_sha256':sha(inputs['authoring_reference_glb'])}
        parts.append(record)
        for i in range(start,end):assert point_ids[i]is None;point_ids[i]=part_id
        for i in range(i0//3,i1//3):assert face_ids[i]is None;face_ids[i]=part_id;assert all(start<=v<end for v in indices[i*3:i*3+3])
    assert all(x is not None for x in point_ids+face_ids)
    bpy.ops.wm.open_mainfile(filepath=str(inputs['source_blend']))
    objects=[ob for ob in bpy.data.objects if ob.type=='MESH'];assert len(objects)==8
    rigs=[ob for ob in bpy.data.objects if ob.type=='ARMATURE'];assert len(rigs)==1;rig=rigs[0]
    assert set(joint_names)==set(rig.data.bones.keys()),(joint_names,list(rig.data.bones.keys()))
    assert all(ob.parent==rig and all(m.type=='ARMATURE'and m.object==rig for m in ob.modifiers)for ob in objects)
    identity=Matrix.Identity(4)
    assert all(max(abs(ob.matrix_world[i][j]-identity[i][j])for i in range(4)for j in range(4))<1e-6 for ob in objects),'Source mesh transform requires explicit coordinate baking'
    rig_before={'matrix_world':[list(x)for x in rig.matrix_world],'bones':[(bone.name,bone.parent.name if bone.parent else None,[list(x)for x in bone.matrix_local])for bone in rig.data.bones],'active_action':rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None}
    packed=bpy.data.objects[recipe['source_mesh_name']]
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
    for i in range(1465):part_attr.data[i].value=point_ids[i];source_attr.data[i].value=i
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
    mesh['foundry_geometry_parts_json']=json.dumps(parts,sort_keys=True);mesh['foundry_authoring_reference_sha256']=sha(inputs['authoring_reference_glb']);mesh['foundry_normal_geometry_sha256']=geometry_signature(packed);mesh['foundry_exact_normal_sha256']=normal_attribute_signature(packed);mesh['foundry_exact_uv_sha256']=float_uv_signature(mesh);mesh['foundry_part_signature_sha256']=part_signature(mesh);material['foundry_material_signature_sha256']=material_signature(material)
    rig_after={'matrix_world':[list(x)for x in rig.matrix_world],'bones':[(bone.name,bone.parent.name if bone.parent else None,[list(x)for x in bone.matrix_local])for bone in rig.data.bones],'active_action':rig.animation_data.action.name if rig.animation_data and rig.animation_data.action else None};assert rig_before==rig_after
    # Remove only unreferenced old mesh/material/image data in this NEW source.
    for collection in (bpy.data.meshes,bpy.data.materials,bpy.data.images):
        for item in list(collection):
            if item.users==0:collection.remove(item)
    output.mkdir(parents=True,exist_ok=True);source=output/'fish.blend';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(source));export=export_packed_source(output/'fish.glb')
    for k,path in inputs.items():assert sha(path)==recipe['inputs'][k]['sha256'],k+' input changed'
    proof={'ok':True,'kind':'packed_editable_fish_source_authoring','recipe_sha256':sha(a.recipe),'builder_sha256':sha(__file__),'input_files':recipe['inputs'],'output_blend_sha256':sha(source),'output_model_sha256':sha(output/'fish.glb'),'source_mesh':packed.name,'triangles':len(mesh.polygons),'vertices':len(mesh.vertices),'bones':len(rig.data.bones),'surfaces':len(mesh.materials),'logical_parts':parts,'rig_and_active_action_unchanged_by_authoring':True,'source_owned_exact_normal_attribute':EXACT_NORMAL_ATTRIBUTE,'source_owned_exact_uv_attribute':EXACT_UV,'part_attribute':PART_ID,'source_vertex_attribute':SOURCE_VERTEX,'face_part_attribute':FACE_PART,'export_proof':export,'scope':'One-time source authoring from frozen assets, no old input writes. Full fresh source re-export and actual final gates still required.'};(output.parent/'source-build.validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'ok':True,'blend':sha(source),'model':sha(output/'fish.glb'),'parts':len(parts)}))
if __name__=='__main__':main()
