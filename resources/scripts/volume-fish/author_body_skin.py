"""Blender: bake an explicitly reviewed existing body donor into a new source.

Keeps every mesh/UV/weight and the original independent fin images unchanged.
"""
import argparse,hashlib,json,struct,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from export_source_with_frozen_normals import export_guarded,EXACT_NORMAL_ATTRIBUTE
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def geometry():return {o.name:hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],[tuple(x.uv)for x in o.data.uv_layers.active.data])).encode()).hexdigest()for o in bpy.context.scene.objects if o.type=='MESH'}
p=argparse.ArgumentParser();p.add_argument('--blend',type=Path,required=True);p.add_argument('--texture-inputs',type=Path,required=True);p.add_argument('--slot',required=True);p.add_argument('--body',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--ordinary-source',action='store_true',help='Explicit ordinary source export; never bypass frozen-normal guards.');p.add_argument('--anterior-config',type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
root=Path(__file__).resolve().parents[3];out=a.output.resolve();assert out.is_relative_to(root/'projects/fishing-2d/experiments')and not out.exists();out.mkdir()
receipt=read(a.texture_inputs);texture=receipt['textures'][a.slot];image_path=Path(texture['path']);assert sha(image_path)==texture['sha256']
source_sha=sha(a.blend);bpy.ops.wm.open_mainfile(filepath=str(a.blend.resolve()));before=geometry()
has_guard=any(ob.type=='MESH'and EXACT_NORMAL_ATTRIBUTE in ob.data.attributes for ob in bpy.context.scene.objects)
assert not has_guard if a.ordinary_source else has_guard,'Choose explicit ordinary source export or preserve the existing exact normal guard'
body=bpy.data.objects[a.body];assert body.type=='MESH'
mat=body.data.materials[0].copy();mat.name='Frozen clean body donor; independent fins unchanged';body.data.materials[0]=mat
nodes=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'];assert len(nodes)==1
image=bpy.data.images.load(str(image_path),check_existing=False);image.pack();assert list(image.size)==texture['size'];nodes[0].image=image
assert geometry()==before
uv_patch={'changed_loops':0}
if a.anterior_config:
    import math
    settings=read(a.anterior_config);assert settings['body']==a.body and sha(a.blend)==settings['input_blend_sha256']
    sections=read(Path(settings['geometry_profile']))['body']['sections'];start,end=settings['u_interval'];lo,hi=settings['donor_u_interval'];s0,s1=settings['side_preservation'];assert 0<=lo<hi<1 and 0<=start<end<=1 and 0<=s0<s1<=1
    assert not any(ob.type=='MESH'and EXACT_NORMAL_ATTRIBUTE in ob.data.attributes for ob in bpy.context.scene.objects),'UV edits require an ordinary pre-freeze source'
    def smooth(x):return max(0.,min(1.,x))**2*(3-2*max(0.,min(1.,x)))
    def width(u):
        for left,right in zip(sections,sections[1:]):
            if u<=right[0]:return left[3]+(right[3]-left[3])*max(0.,min(1.,(u-left[0])/(right[0]-left[0])))
        return sections[-1][3]
    structure=lambda:hashlib.sha256(repr(([(tuple(v.co),[(g.group,g.weight)for g in v.groups])for v in body.data.vertices],[tuple(f.vertices)for f in body.data.polygons])).encode()).hexdigest()
    frozen_structure=structure();pixels=list(image.pixels[:]);w,h=image.size;changes=[]
    for poly in body.data.polygons:
        if poly.material_index!=0:continue
        for li in poly.loop_indices:
            co=body.data.vertices[body.data.loops[li].vertex_index].co;u=co.x+.5
            if u<start:continue
            side=max(0.,min(1.,abs(co.y)/max(width(u),1e-8)));amount=smooth((u-start)/(end-start))*(1-smooth((side-s0)/(s1-s0)))
            if amount<1e-7:continue
            uv=body.data.uv_layers.active.data[li].uv;old=tuple(uv);uv.x=uv.x*(1-amount)+(lo+(hi-lo)*side)*amount
            ix=max(0,min(w-1,int(uv.x*w)));iy=max(0,min(h-1,int(uv.y*h)));assert pixels[(iy*w+ix)*4+3]>.95,'Anterior donor is transparent'
            changes.append({'loop':li,'old_uv':old,'new_uv':tuple(uv)})
    assert changes and structure()==frozen_structure
    uv_patch={'changed_loops':len(changes),'config_sha256':sha(a.anterior_config),'changes':changes,'geometry_and_weights_unchanged':True,'scope':'Own finite anterior skin UV only, actual jaw geometry and deep oral material unchanged. Side preservation and safe two-dimensional source domain require actual image review.'}
blend=out/'fish.blend';model=out/'fish.glb';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
if a.ordinary_source:
    assert not any(ob.type=='MESH'and EXACT_NORMAL_ATTRIBUTE in ob.data.attributes for ob in bpy.context.scene.objects),'Use guarded exporter for a guarded source'
    bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.scene.objects:
        if ob.type in ('MESH','ARMATURE'):ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(model),export_format='GLB',use_selection=True,export_animations=True,export_yup=True,export_skins=True,export_materials='EXPORT')
    proof={'mode':'explicit_ordinary_source','scope':'Normal native Blender export; subsequent portable source/cold parity remains required.'}
else:proof=export_guarded(model)
raw=model.read_bytes();length,kind=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+length]);tail=raw[20+length:]
for node in doc['nodes']:
    if'mesh'not in node:continue
    for pr in doc['meshes'][node['mesh']]['primitives']:
        material=doc['materials'][pr['material']];material.update(alphaMode='OPAQUE'if node['name']==a.body else'MASK',doubleSided=False)
        if node['name']!=a.body:material['alphaCutoff']=.5
for sampler in doc.get('samplers',[]):sampler.update(magFilter=9728,minFilter=9728)
encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
model.write_bytes(struct.pack('<III',0x46546c67,2,20+len(encoded)+len(tail))+struct.pack('<II',len(encoded),kind)+encoded+tail)
assert sha(a.blend)==source_sha
report={'ok':True,'kind':'offline_clean_body_donor_authoring','input_source_sha256':source_sha,'image_sha256':sha(image_path),'texture_receipt_sha256':sha(a.texture_inputs),'body':a.body,'source_slot':a.slot,'geometry_UV_weights_fingerprints':before,'geometry_UV_weights_unchanged':not bool(uv_patch['changed_loops']),'anterior_uv_patch':uv_patch,'independent_fin_images_unchanged':True,'model_sha256':sha(model),'blend_sha256':sha(blend),'source_normal_export':proof,'scope':'Exact selected RGBA donor now belongs to editable source; optional explicit finite anterior UV mapping. No runtime recoloring. Requires hidden-fin body and multi-view review; not automatic acceptance.'}
(out/'skin-authoring.validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps({'ok':True,'model_sha256':sha(model),'blend_sha256':sha(blend)}))
