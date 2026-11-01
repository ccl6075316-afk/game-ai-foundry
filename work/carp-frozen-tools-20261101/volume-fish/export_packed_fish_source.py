"""Export one source-owned packed fish mesh with exact corner UV/NORMAL streams.

No reference GLB is read. Source geometry, logical ownership, atlas and material
signatures are validated before export; actual exported IDs define part metadata.
"""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from patch_existing_fin_meshes import read,write
from repair_fin_clearance import values
from restore_fin_source_normals import EXACT_NORMAL_ATTRIBUTE,geometry_signature,normal_attribute_signature
from export_source_with_frozen_normals import export_guarded

EXACT_UV='_FOUNDRY_UV_GLTF'
PART_ID='_FOUNDRY_PART_ID'
SOURCE_VERTEX='_FOUNDRY_SOURCE_VERTEX'
FACE_PART='foundry_logical_part_id'
def allowed_artifact(path):
    root=Path(__file__).resolve().parents[3];path=Path(path).resolve()
    return path.is_relative_to(root/'work')or path.is_relative_to(root/'output')or path.is_relative_to(root/'projects/fishing-2d/experiments')
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def float_uv_signature(mesh):return digest([tuple(x.vector)for x in mesh.attributes[EXACT_UV].data])
def part_signature(mesh):return digest({'parts':json.loads(mesh['foundry_geometry_parts_json']),'point_ids':[x.value for x in mesh.attributes[PART_ID].data],'source_vertices':[x.value for x in mesh.attributes[SOURCE_VERTEX].data],'face_ids':[x.value for x in mesh.attributes[FACE_PART].data]})
def material_signature(material):
    assert material.use_nodes,'Packed source requires Use Nodes'
    tree=material.node_tree;types={kind:[n for n in tree.nodes if n.type==kind]for kind in ('TEX_IMAGE','UVMAP','BSDF_PRINCIPLED','OUTPUT_MATERIAL')}
    assert len(tree.nodes)==4 and all(len(x)==1 for x in types.values()),'Exactly one explicit atlas/UV/BSDF/output chain required'
    assert all(not n.mute for n in tree.nodes),'Muted material node invalidates packed source'
    texture=types['TEX_IMAGE'][0];uvmap=types['UVMAP'][0];bsdf=types['BSDF_PRINCIPLED'][0];output=types['OUTPUT_MATERIAL'][0]
    assert texture.projection=='FLAT'and texture.interpolation=='Closest'and texture.extension=='EXTEND'
    assert texture.image and texture.image.alpha_mode=='STRAIGHT'and texture.image.colorspace_settings.name=='sRGB'
    assert uvmap.uv_map=='UVMap'and not uvmap.from_instancer
    expected_links={(uvmap.name,'UV',texture.name,'Vector'),(texture.name,'Color',bsdf.name,'Base Color'),(texture.name,'Alpha',bsdf.name,'Alpha'),(bsdf.name,'BSDF',output.name,'Surface')}
    assert {(x.from_node.name,x.from_socket.name,x.to_node.name,x.to_socket.name)for x in tree.links}==expected_links,'Explicit atlas color/alpha links required'
    def default(socket):
        value=socket.default_value
        return list(value)if hasattr(value,'__iter__')else value
    nodes=[]
    for n in material.node_tree.nodes:
        row={'name':n.name,'type':n.bl_idname,'mute':n.mute,'defaults':{s.name:default(s)for s in n.inputs if hasattr(s,'default_value')}}
        if n.type=='TEX_IMAGE':
            assert n.image and n.image.packed_file and not n.image.is_dirty,'Atlas must be packed and unchanged'
            row.update(packed_image_sha256=hashlib.sha256(n.image.packed_file.data).hexdigest(),colorspace=n.image.colorspace_settings.name,image_alpha_mode=n.image.alpha_mode,image_source=n.image.source,projection=n.projection,projection_blend=n.projection_blend,interpolation=n.interpolation,extension=n.extension)
        if n.type=='UVMAP':row.update(uv_map=n.uv_map,from_instancer=n.from_instancer)
        nodes.append(row)
    return digest({'guard_version':2,'use_nodes':material.use_nodes,'nodes':nodes,'links':sorted((x.from_node.name,x.from_socket.name,x.to_node.name,x.to_socket.name)for x in material.node_tree.links),'backface_culling':material.use_backface_culling,'surface_render_method':material.surface_render_method,'contract':json.loads(material['foundry_export_contract_json'])})

def append_rows(d,b,source,rows,index=False):
    a=copy.deepcopy(d['accessors'][source]);fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
    b.extend(b'\0'*(-len(b)%4));offset=len(b)
    for row in rows:b.extend(struct.pack('<'+fmt*len(row),*row))
    a.update(bufferView=len(d['bufferViews']),byteOffset=0,count=len(rows));a.pop('min',None);a.pop('max',None)
    if a['type']=='VEC3'and not index:a.update(min=[min(x[i]for x in rows)for i in range(3)],max=[max(x[i]for x in rows)for i in range(3)])
    d['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(b)-offset,'target':34963 if index else 34962});d['accessors'].append(a);return len(d['accessors'])-1

def compact_referenced_data(d,b):
    live=set()
    for mesh in d['meshes']:
        for p in mesh['primitives']:live.update(p['attributes'].values());live.add(p['indices'])
    for skin in d.get('skins',[]):
        if 'inverseBindMatrices'in skin:live.add(skin['inverseBindMatrices'])
    for animation in d.get('animations',[]):
        for sampler in animation['samplers']:live.update([sampler['input'],sampler['output']])
    assert all('sparse'not in d['accessors'][i]for i in live)
    views={d['accessors'][i]['bufferView']for i in live}|{x['bufferView']for x in d.get('images',[])}
    access_map={old:new for new,old in enumerate(sorted(live))};view_map={old:new for new,old in enumerate(sorted(views))};data=bytearray();new_views=[]
    for old in sorted(views):
        view=copy.deepcopy(d['bufferViews'][old]);start=view.get('byteOffset',0);payload=b[start:start+view['byteLength']];data.extend(b'\0'*(-len(data)%4));view['byteOffset']=len(data);view['buffer']=0;data.extend(payload);new_views.append(view)
    new_access=[]
    for old in sorted(live):
        a=copy.deepcopy(d['accessors'][old]);a['bufferView']=view_map[a['bufferView']];new_access.append(a)
    for mesh in d['meshes']:
        for p in mesh['primitives']:p['attributes']={k:access_map[v]for k,v in p['attributes'].items()};p['indices']=access_map[p['indices']]
    for skin in d.get('skins',[]):
        if 'inverseBindMatrices'in skin:skin['inverseBindMatrices']=access_map[skin['inverseBindMatrices']]
    for animation in d.get('animations',[]):
        for sampler in animation['samplers']:
            for key in ('input','output'):sampler[key]=access_map[sampler[key]]
    for image in d.get('images',[]):image['bufferView']=view_map[image['bufferView']]
    d['bufferViews']=new_views;d['accessors']=new_access;return data

def export_packed_source(output):
    output=Path(output).resolve();assert not output.exists(),'Refuse overwriting export'
    assert allowed_artifact(output)and output.suffix=='.glb','Export outside allowed artifact roots/format'
    meshes=[ob for ob in bpy.data.objects if ob.type=='MESH'];assert len(meshes)==1,'Only one actual packed mesh may export'
    ob=meshes[0];mesh=ob.data;assert len(mesh.materials)==1 and all(len(p.vertices)==3 and p.material_index==0 for p in mesh.polygons)
    assert mesh.uv_layers.active and mesh.uv_layers.active.name=='UVMap','The signed active UV must be the material UVMap'
    assert [layer.name for layer in mesh.uv_layers if layer.active_render]==['UVMap'],'The material UVMap must be the only render UV layer'
    assert geometry_signature(ob)==mesh['foundry_normal_geometry_sha256']
    assert normal_attribute_signature(ob)==mesh['foundry_exact_normal_sha256']
    assert float_uv_signature(mesh)==mesh['foundry_exact_uv_sha256']
    assert part_signature(mesh)==mesh['foundry_part_signature_sha256']
    material=mesh.materials[0];assert material_signature(material)==material['foundry_material_signature_sha256']
    uv_nodes=[n for n in material.node_tree.nodes if n.type=='UVMAP'];assert len(uv_nodes)==1 and uv_nodes[0].uv_map=='UVMap'and not uv_nodes[0].from_instancer,'Explicit source UVMap required'
    contract=json.loads(material['foundry_export_contract_json'])
    assert contract=={'alphaMode':'MASK','alphaCutoff':.5,'doubleSided':False,'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071,'roughnessFactor':1,'metallicFactor':0,'specularFactor':0},'Unsupported packed export contract'
    normal_proof=export_guarded(output)
    d,b=read(output)
    assert len(d['meshes'])==1 and len(d['meshes'][0]['primitives'])==1
    pr=d['meshes'][0]['primitives'][0];at=pr['attributes']
    assert EXACT_UV in at and PART_ID in at and SOURCE_VERTEX in at
    uv_index=at.pop(EXACT_UV);assert d['accessors'][uv_index]['type']=='VEC2';at['TEXCOORD_0']=uv_index
    part_values=[int(round(x[0]))for x in values(d,b,at.pop(PART_ID))]
    source_vertices=[int(round(x[0]))for x in values(d,b,at.pop(SOURCE_VERTEX))]
    indices=[x[0]for x in values(d,b,pr['indices'])]
    assert set(source_vertices)==set(range(len(mesh.vertices))),'Every source identity must export'
    attrs={key:values(d,b,at[key])for key in ('POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0')};representative={}
    for row,source_id in enumerate(source_vertices):
        if source_id in representative:
            previous=representative[source_id]
            assert all(rows[row]==rows[previous]for rows in attrs.values()),'Different final attributes for one source identity'
            assert part_values[row]==part_values[previous]
        else:representative[source_id]=row
    raw_row_count=len(source_vertices);order=[representative[i]for i in range(len(mesh.vertices))]
    pr['attributes']={key:append_rows(d,b,at[key],[rows[i]for i in order])for key,rows in attrs.items()}
    indices=[source_vertices[i]for i in indices];pr['indices']=append_rows(d,b,pr['indices'],[(i,)for i in indices],True)
    part_values=[part_values[i]for i in order];source_vertices=list(range(len(mesh.vertices)))
    specs=json.loads(mesh['foundry_geometry_parts_json']);parts=[]
    for spec in specs:
        part=spec['part_id'];verts=[i for i,p in enumerate(part_values)if p==part]
        triangles=[i//3 for i in range(0,len(indices),3)if part_values[indices[i]]==part]
        assert verts and triangles and verts==list(range(min(verts),max(verts)+1)),'Packed exported part vertices are not contiguous'
        assert triangles==list(range(min(triangles),max(triangles)+1)),'Packed exported part faces are not contiguous'
        for ti in triangles:assert all(part_values[v]==part for v in indices[ti*3:ti*3+3]),'Triangle crosses logical part ownership'
        assert len(verts)==spec['vertex_count']and len(triangles)*3==spec['index_count']
        assert sorted(source_vertices[i]for i in verts)==list(range(spec['source_vertex_start'],spec['source_vertex_start']+spec['vertex_count']))
        parts.append({**spec,'vertex_start':min(verts),'vertex_count':len(verts),'index_start':min(triangles)*3,'index_count':len(triangles)*3})
    assert sum(x['vertex_count']for x in parts)==len(source_vertices)and sum(x['index_count']for x in parts)==len(indices)
    assert len(d['materials'])==1
    # Blender's alpha export differs across versions. These mappings come only
    # from the guarded source material contract, never from a target model.
    target=d['materials'][0];target.update(alphaMode=contract['alphaMode'],alphaCutoff=contract['alphaCutoff'],doubleSided=contract['doubleSided'])
    pbr=target.setdefault('pbrMetallicRoughness',{});pbr['roughnessFactor']=contract['roughnessFactor'];pbr['metallicFactor']=contract['metallicFactor']
    target.setdefault('extensions',{})['KHR_materials_specular']={'specularFactor':contract['specularFactor']}
    d.setdefault('extensionsUsed',[])
    if 'KHR_materials_specular'not in d['extensionsUsed']:d['extensionsUsed'].append('KHR_materials_specular')
    for sampler in d['samplers']:sampler.update({k:contract[k]for k in ('magFilter','minFilter','wrapS','wrapT')})
    d.setdefault('extras',{}).update(foundry_geometry_parts_schema=1,geometry_parts=parts,geometry_parts_signature=mesh['foundry_part_signature_sha256'],source_authoring_reference_sha256=mesh['foundry_authoring_reference_sha256'])
    b=compact_referenced_data(d,b);write(output,d,b)
    return {'ok':True,'kind':'source_owned_packed_fish_export','exporter_sha256':sha(__file__),'output_sha256':sha(output),'mesh':ob.name,'triangles':len(indices)//3,'vertices':len(source_vertices),'surfaces':1,'parts':parts,'exact_NORMAL_and_UV_source_streams':True,'source_material_contract':contract,'source_atlas_signature':material['foundry_material_signature_sha256'],'source_guarded_normal_export':normal_proof,'generated_BIN_unchanged_after_source_binding':False,'source_row_compaction':{'generated_rows':raw_row_count,'source_rows':len(source_vertices),'merge_scope':'Only same source ID, after final POSITION/NORMAL/UV/JOINTS/WEIGHTS exact equality. Different source IDs never welded.','unused_streams_removed':True},'reference_GLB_read_during_export':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('blend','output','report'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);source=a.blend.resolve();output=a.output.resolve();report=a.report.resolve();assert len({source,output,report})==3 and source.is_file()and source.suffix=='.blend'and not output.exists()and not report.exists();assert allowed_artifact(output)and output.suffix=='.glb'and allowed_artifact(report)and report.suffix=='.json';before=sha(source)
    bpy.ops.wm.open_mainfile(filepath=str(source));proof=export_packed_source(output);assert sha(source)==before;proof['blend_sha256']=before;report.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'ok':True,'model_sha256':proof['output_sha256'],'blend_sha256':before,'parts':len(proof['parts'])}))
if __name__=='__main__':main()
