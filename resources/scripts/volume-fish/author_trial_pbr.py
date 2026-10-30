"""Blender: explicitly author a new trial's ordinary matte material contract.

This is an appearance change requiring review, never a parity conversion of an
accepted emissive/BLEND fish. Geometry/UV/weights/rig/actions are kept intact.
"""
import argparse,hashlib,json,sys,struct
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fingerprint():
    return {o.name:hashlib.sha256(repr(([(tuple(v.co),[(o.vertex_groups[g.group].name,g.weight)for g in v.groups])for v in o.data.vertices],[(tuple(f.vertices),f.material_index)for f in o.data.polygons],[(x.uv.x,x.uv.y)for x in o.data.uv_layers.active.data])).encode()).hexdigest()for o in bpy.context.scene.objects if o.type=='MESH'}
p=argparse.ArgumentParser();p.add_argument('--blend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--body',required=True);p.add_argument('--unique-mesh-names',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
source=a.blend.resolve();out=a.output.resolve()
assert source.is_file() and source.is_relative_to(ROOT)
assert out.is_relative_to(ROOT/'projects/fishing-2d/experiments') and not out.exists()
out.mkdir();before=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source));frozen=fingerprint();materials=[]
renames={}
if a.unique_mesh_names:
    bones={bone.name for ob in bpy.context.scene.objects if ob.type=='ARMATURE' for bone in ob.data.bones}
    for ob in list(bpy.context.scene.objects):
        if ob.type=='MESH' and ob.name in bones:
            name=ob.name;ob.name=name+'_mesh';renames[name]=ob.name
    frozen={renames.get(k,k):v for k,v in frozen.items()}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    for mat in ob.data.materials:
        if mat.name in materials:continue
        materials.append(mat.name)
        bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        for link in list(bsdf.inputs['Emission Color'].links):mat.node_tree.links.remove(link)
        bsdf.inputs['Emission Strength'].default_value=0
        bsdf.inputs['Metallic'].default_value=0;bsdf.inputs['Roughness'].default_value=1;bsdf.inputs['Specular IOR Level'].default_value=0
        mat.use_backface_culling=True
assert fingerprint()==frozen
bpy.ops.object.select_all(action='DESELECT')
for ob in bpy.context.scene.objects:
    if ob.type in ('MESH','ARMATURE'):ob.select_set(True)
blend=out/'fish.blend';glb=out/'fish.glb'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_skins=True,export_materials='EXPORT')
raw=glb.read_bytes();size,kind=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+size]);tail=raw[20+size:]
for node in doc['nodes']:
    if 'mesh'not in node:continue
    for primitive in doc['meshes'][node['mesh']]['primitives']:
        mat=doc['materials'][primitive['material']]
        # Explicit newly authored pipeline state; not an equivalence claim.
        mat['alphaMode']='OPAQUE' if node['name']==a.body else 'MASK'
        mat['doubleSided']=False
        if mat['alphaMode']=='MASK':mat['alphaCutoff']=.5
        assert not mat.get('emissiveTexture') and not any(mat.get('emissiveFactor',[]))
for sampler in doc.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728)
data=json.dumps(doc,separators=(',',':')).encode();data+=b' '*((-len(data))%4)
glb.write_bytes(struct.pack('<III',0x46546c67,2,20+len(data)+len(tail))+struct.pack('<II',len(data),kind)+data+tail)
assert sha(source)==before and fingerprint()==frozen
triangles=sum(doc['accessors'][p['indices']]['count']//3 for m in doc['meshes']for p in m['primitives'])
report={'ok':True,'kind':'trial_matte_material_authoring','source_blend':str(source.relative_to(ROOT)),'source_sha256':before,'blend_sha256':sha(blend),'model_sha256':sha(glb),'triangles':triangles,'geometry_uv_weight_fingerprints':frozen,'geometry_uv_weights_unchanged':True,'appearance_change':'Removed35percent emission; closed fin shells now MASK/.5 and backface culling; bodyOPAQUE. This is a new matte candidate awaiting review. Saved source has emission removed and original source images preserved; canonical source export is the subsequent portable guarded source.','formal_acceptance':False}
report['mesh_node_renames']=renames
(out/'authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report))
